"""Secure, operator-run administrator provisioning command.

Run from the Backend directory with DATABASE_URL and SECRET_KEY configured.
For an existing administrator account, enter that account's existing email,
username, and current password to promote its persisted superuser flag. For a
new account, choose a new password and enter it twice. Password input is hidden.
"""

import getpass
import logging
import sys
from pathlib import Path

# Allow invocation as ``python create_admin.py`` from Backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.services.auth import get_password_hash, verify_password

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_ADMIN_PROVISIONING_LOCK_ID = 70634815209741362


class ProvisioningError(ValueError):
    """A safe, operator-facing provisioning failure."""


def _acquire_provisioning_lock(db: Session) -> None:
    """Serialize first-admin provisioning on supported database engines."""
    connection = db.connection()
    dialect = connection.dialect.name
    if dialect == "postgresql":
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _ADMIN_PROVISIONING_LOCK_ID},
        )
    elif dialect == "sqlite":
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        raise ProvisioningError(
            "Administrator provisioning supports PostgreSQL and SQLite only."
        )


def provision_admin(
    db: Session,
    email: str,
    username: str,
    password: str,
    confirmation: str | None = None,
) -> User:
    """Create one initial administrator or promote an existing account.

    Existing accounts must prove possession of their current password. This
    function never changes an existing password or account identifier.
    """
    normalized_email = email.strip().lower()
    normalized_username = username.strip().lower()
    if not normalized_email or not normalized_username or not password:
        raise ProvisioningError("Email, username, and password are required.")
    if confirmation != password:
        raise ProvisioningError(
            "Password confirmation did not match; no changes were made."
        )

    try:
        _acquire_provisioning_lock(db)
        if db.query(User).filter(User.is_superuser.is_(True)).count():
            raise ProvisioningError(
                "An administrator already exists; no account changes were made."
            )

        user = db.query(User).filter(User.email == normalized_email).with_for_update().first()
        if user:
            if user.username.lower() != normalized_username:
                raise ProvisioningError(
                    "The supplied account identifiers do not match; no changes were made."
                )
            if not user.is_active:
                raise ProvisioningError(
                    "The existing account is inactive; no changes were made."
                )
            if not verify_password(password, user.hashed_password):
                raise ProvisioningError(
                    "The current account password was not accepted; no changes were made."
                )
            user.is_superuser = True
        else:
            username_conflict = (
                db.query(User).filter(User.username == normalized_username).first()
            )
            if username_conflict:
                raise ProvisioningError(
                    "The requested username is already in use; no changes were made."
                )
            if len(password) < 12 or len(password.encode("utf-8")) > 72:
                raise ProvisioningError(
                    "A new administrator password must be 12 to 72 UTF-8 bytes."
                )
            user = User(
                email=normalized_email,
                username=normalized_username,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=True,
            )
            db.add(user)

        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def main() -> int:
    email = input("Administrator email: ").strip()
    username = input("Administrator username: ").strip()
    password = getpass.getpass(
        "Enter the existing account password, or a new password if creating an account: "
    )
    confirmation = getpass.getpass(
        "Repeat the password (for an existing account, enter it again): "
    )

    db = SessionLocal()
    try:
        provision_admin(db, email, username, password, confirmation)
        logger.info("Administrator provisioning completed.")
        return 0
    except ProvisioningError as exc:
        logger.error("Provisioning stopped: %s", exc)
        return 1
    except Exception as exc:
        # Do not render the exception text; DB exceptions may contain input data.
        logger.error("Provisioning failed (%s). No credentials were logged.", type(exc).__name__)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
