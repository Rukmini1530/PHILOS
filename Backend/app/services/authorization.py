"""Shared dataset visibility and ownership rules for API handlers."""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Dataset, User


def is_admin(user: Optional[User]) -> bool:
    return bool(user and user.is_superuser)


def can_access_dataset(dataset: Dataset, user: Optional[User]) -> bool:
    """Demo datasets are public; other datasets belong to their owner or admin."""
    if dataset.is_demo is True or is_admin(user):
        return True
    return bool(user and dataset.owner_id == user.id)


def accessible_datasets(db: Session, user: Optional[User]) -> Query:
    """Return a query scoped to datasets visible to the supplied principal."""
    query = db.query(Dataset)
    if is_admin(user):
        return query
    if user:
        return query.filter(
            or_(Dataset.is_demo.is_(True), Dataset.owner_id == user.id)
        )
    return query.filter(Dataset.is_demo.is_(True))


def get_accessible_dataset(
    db: Session, dataset_id: int, user: Optional[User]
) -> Dataset:
    """Fetch a visible dataset, hiding private dataset existence from outsiders."""
    dataset = accessible_datasets(db, user).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def require_dataset_write_access(dataset: Dataset, user: User) -> None:
    """Allow admins, or the owner of a non-demo dataset, to write it."""
    if is_admin(user):
        return
    if dataset.is_demo:
        raise HTTPException(status_code=403, detail="Demo datasets cannot be modified")
    if dataset.owner_id != user.id:
        raise HTTPException(
            status_code=403, detail="You do not have permission to modify this dataset"
        )


def can_modify_annotation(annotation, dataset: Dataset, user: User) -> bool:
    """Annotation creators own their work; private dataset owners can curate it."""
    if is_admin(user) or annotation.user_id == str(user.id):
        return True
    return bool(not dataset.is_demo and dataset.owner_id == user.id)
