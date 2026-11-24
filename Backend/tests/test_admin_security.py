import pytest

from app.models import User
from app.services.auth import get_password_hash, verify_password
from create_admin import ProvisioningError, provision_admin


def add_user(db, email, username, password, *, is_superuser=False):
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_anonymous_admin_initialization_is_not_exposed(client):
    response = client.post("/api/admin/init")
    assert response.status_code == 404


def test_anonymous_admin_access_is_rejected(client):
    response = client.get("/api/admin/stats")
    assert response.status_code == 401


def test_invalid_bearer_credentials_are_rejected_with_authentication_challenge(client):
    response = client.get(
        "/api/admin/stats",
        headers={"Authorization": "Bearer invalid-test-token"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/admin/users"),
        ("get", "/api/admin/datasets"),
        ("get", "/api/admin/activity"),
        ("delete", "/api/admin/datasets/999"),
        ("delete", "/api/admin/users/999"),
    ],
)
def test_anonymous_admin_endpoints_require_authentication(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401


def test_client_supplied_privilege_header_does_not_grant_admin_access(client):
    response = client.get(
        "/api/admin/stats",
        headers={"X-Is-Superuser": "true", "X-Role": "admin"},
    )
    assert response.status_code == 401


def test_regular_user_cannot_access_admin_api(client, database, login_token):
    add_user(database, "researcher@example.invalid", "researcher", "ordinary-test-password")
    token = login_token("researcher@example.invalid", "ordinary-test-password")

    response = client.get(
        "/api/admin/stats", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_superuser_can_access_admin_api(client, database, login_token):
    add_user(
        database,
        "operator@example.invalid",
        "operator",
        "administrator-test-password",
        is_superuser=True,
    )
    token = login_token("operator@example.invalid", "administrator-test-password")

    response = client.get(
        "/api/admin/stats", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"


def test_superuser_demotion_takes_effect_on_next_request(
    client, database, login_token
):
    administrator = add_user(
        database,
        "demoted-admin@example.invalid",
        "demotedadmin",
        "demotion-test-password",
        is_superuser=True,
    )
    token = login_token(administrator.email, "demotion-test-password")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/admin/stats", headers=headers).status_code == 200
    administrator.is_superuser = False
    database.commit()

    assert client.get("/api/admin/stats", headers=headers).status_code == 403


def test_deleted_user_token_is_rejected_on_next_request(
    client, database, login_token
):
    user = add_user(
        database, "deleted-user@example.invalid", "deleteduser", "deletion-test-password"
    )
    token = login_token(user.email, "deletion-test-password")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200
    database.delete(user)
    database.commit()

    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_deactivated_user_loses_protected_access_on_next_request(
    client, database, login_token
):
    user = add_user(
        database, "disabled-user@example.invalid", "disableduser", "disable-test-password"
    )
    token = login_token(user.email, "disable-test-password")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200
    user.is_active = False
    database.commit()

    assert client.get("/api/auth/me", headers=headers).status_code == 403


def test_username_spoofing_does_not_grant_admin_access(client, database, login_token):
    add_user(database, "spoof@example.invalid", "admin", "ordinary-test-password")
    token = login_token("spoof@example.invalid", "ordinary-test-password")

    response = client.get(
        "/api/admin/stats", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_last_active_administrator_cannot_be_deleted(
    client, database, login_token
):
    administrator = add_user(
        database,
        "last-admin@example.invalid",
        "lastadmin",
        "last-admin-test-password",
        is_superuser=True,
    )
    token = login_token(administrator.email, "last-admin-test-password")

    response = client.delete(
        f"/api/admin/users/{administrator.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    database.refresh(administrator)
    assert administrator.is_superuser is True


def test_registration_cannot_assign_administrator_role(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "self-assigned@example.invalid",
            "username": "self_assigned",
            "password": "ordinary-registration-test-password",
            "is_superuser": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["is_superuser"] is False
    token = response.json()["access_token"]
    admin_response = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_response.status_code == 403


def test_operator_provisioning_hashes_password_and_is_single_admin(database):
    password = "new-admin-test-password"
    admin_user = provision_admin(
        database,
        "new-operator@example.invalid",
        "new-operator",
        password,
        password,
    )

    assert admin_user.is_superuser is True
    assert admin_user.hashed_password != password
    assert verify_password(password, admin_user.hashed_password)
    assert database.query(User).filter(User.is_superuser.is_(True)).count() == 1

    with pytest.raises(ProvisioningError):
        provision_admin(
            database,
            "second-operator@example.invalid",
            "second-operator",
            "another-admin-test-password",
            "another-admin-test-password",
        )
    assert database.query(User).count() == 1


def test_operator_can_safely_promote_existing_account_without_password_change(database):
    existing_password = "existing-account-test-password"
    existing = add_user(
        database,
        "existing@example.invalid",
        "existing-user",
        existing_password,
    )
    original_hash = existing.hashed_password

    promoted = provision_admin(
        database,
        existing.email,
        existing.username,
        existing_password,
        existing_password,
    )

    assert promoted.id == existing.id
    assert promoted.is_superuser is True
    assert promoted.hashed_password == original_hash
    assert verify_password(existing_password, promoted.hashed_password)
    assert database.query(User).count() == 1


def test_wrong_existing_password_does_not_promote_account(database):
    existing = add_user(
        database,
        "existing@example.invalid",
        "existing-user",
        "existing-account-test-password",
    )

    with pytest.raises(ProvisioningError):
        provision_admin(
            database,
            existing.email,
            existing.username,
            "incorrect-test-password",
            "incorrect-test-password",
        )

    database.refresh(existing)
    assert existing.is_superuser is False


def test_existing_user_login_remains_compatible(client, database, login_token):
    add_user(database, "user@example.invalid", "user", "existing-user-test-password")
    token = login_token("user@example.invalid", "existing-user-test-password")

    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_superuser"] is False
