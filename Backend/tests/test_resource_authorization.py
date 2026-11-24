"""Authorization tests against isolated in-memory test databases."""

import pytest

from app.models import Annotation, Dataset, User
from app.services.auth import get_password_hash


def add_user(db, email, username, password):
    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_dataset(db, name, *, owner=None, demo=False):
    dataset = Dataset(
        name=name,
        description=f"Description for {name}",
        category="space",
        owner_id=owner.id if owner else None,
        original_file_path=f"{name}.tif",
        tile_base_path=f"tiles/{name}",
        width=1024,
        height=512,
        min_zoom=0,
        max_zoom=3,
        tile_size=256,
        processing_status="completed",
        is_demo=demo,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def add_annotation(db, dataset, user, label="Crater"):
    annotation = Annotation(
        dataset_id=dataset.id,
        user_id=str(user.id) if user else "anonymous",
        geometry_json={"type": "Point", "coordinates": [0.25, 0.75]},
        annotation_type="point",
        label=label,
        description="Test annotation",
        properties={},
        confidence=1.0,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_anonymous_can_read_demo_annotations_but_not_private_annotations(
    client, database, login_token
):
    owner = add_user(database, "owner@example.invalid", "owner", "test-owner-password")
    demo = add_dataset(database, "public-demo", demo=True)
    private = add_dataset(database, "owner-private", owner=owner)
    add_annotation(database, demo, owner)
    add_annotation(database, private, owner)

    assert client.get(f"/api/annotations/{demo.id}").status_code == 200
    assert client.get(f"/api/annotations/{private.id}").status_code == 404


def test_anonymous_cannot_create_annotations(client, database):
    demo = add_dataset(database, "create-demo", demo=True)
    response = client.post(
        "/api/annotations",
        json={
            "dataset_id": demo.id,
            "user_id": "9999",
            "geometry": {"type": "Point", "coordinates": [0.1, 0.2]},
            "annotation_type": "point",
            "label": "Anonymous attempt",
        },
    )
    assert response.status_code in {401, 403}


def test_authenticated_demo_annotation_ignores_spoofed_user_id(
    client, database, login_token
):
    user = add_user(database, "creator@example.invalid", "creator", "test-creator-password")
    demo = add_dataset(database, "annotated-demo", demo=True)
    token = login_token(user.email, "test-creator-password")

    response = client.post(
        "/api/annotations",
        headers=auth_header(token),
        json={
            "dataset_id": demo.id,
            "user_id": "another-user",
            "geometry": {"type": "Point", "coordinates": [0.1, 0.2]},
            "annotation_type": "point",
            "label": "Owned annotation",
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == str(user.id)


def test_private_dataset_owner_can_read_annotations_but_other_user_cannot(
    client, database, login_token
):
    owner = add_user(database, "owner2@example.invalid", "owner2", "test-owner-password")
    other = add_user(database, "other@example.invalid", "other", "test-other-password")
    private = add_dataset(database, "private-read", owner=owner)
    add_annotation(database, private, owner)
    owner_token = login_token(owner.email, "test-owner-password")
    other_token = login_token(other.email, "test-other-password")

    assert client.get(
        f"/api/annotations/{private.id}", headers=auth_header(owner_token)
    ).status_code == 200
    assert client.get(
        f"/api/annotations/{private.id}", headers=auth_header(other_token)
    ).status_code == 404


@pytest.mark.parametrize("method", ["put", "delete"])
def test_cross_user_cannot_modify_or_delete_private_annotation(
    client, database, login_token, method
):
    owner = add_user(database, "owner3@example.invalid", "owner3", "test-owner-password")
    other = add_user(database, "other3@example.invalid", "other3", "test-other-password")
    private = add_dataset(database, "private-write", owner=owner)
    annotation = add_annotation(database, private, owner)
    token = login_token(other.email, "test-other-password")

    url = f"/api/annotations/{annotation.id}"
    if method == "put":
        response = client.put(
            url,
            headers=auth_header(token),
            json={"label": "Unauthorized change"},
        )
    else:
        response = client.delete(url, headers=auth_header(token))
    assert response.status_code == 404


def test_demo_annotation_creator_can_update_and_delete(
    client, database, login_token
):
    creator = add_user(database, "creator2@example.invalid", "creator2", "test-creator-password")
    other = add_user(database, "other4@example.invalid", "other4", "test-other-password")
    demo = add_dataset(database, "demo-owned-annotation", demo=True)
    annotation = add_annotation(database, demo, creator)
    creator_token = login_token(creator.email, "test-creator-password")
    other_token = login_token(other.email, "test-other-password")

    assert client.put(
        f"/api/annotations/{annotation.id}",
        headers=auth_header(other_token),
        json={"label": "Other user edit"},
    ).status_code == 403
    assert client.put(
        f"/api/annotations/{annotation.id}",
        headers=auth_header(creator_token),
        json={"label": "Creator edit"},
    ).status_code == 200
    assert client.delete(
        f"/api/annotations/{annotation.id}", headers=auth_header(creator_token)
    ).status_code == 200


def test_annotation_search_is_limited_to_accessible_datasets(
    client, database, login_token
):
    owner = add_user(database, "search-owner@example.invalid", "searchowner", "test-owner-password")
    other = add_user(database, "search-other@example.invalid", "searchother", "test-other-password")
    demo = add_dataset(database, "search-public", demo=True)
    private = add_dataset(database, "search-private", owner=owner)
    add_annotation(database, demo, owner, label="Visible crater")
    add_annotation(database, private, owner, label="Secret crater")
    other_token = login_token(other.email, "test-other-password")

    response = client.get(
        "/api/search",
        params={"q": "crater"},
        headers=auth_header(other_token),
    )
    assert response.status_code == 200
    assert [item["label"] for item in response.json()] == ["Visible crater"]

    spatial = client.get(
        "/api/search/spatial",
        params={"bbox": "0,0,1,1", "dataset_id": demo.id},
        headers=auth_header(other_token),
    )
    assert spatial.status_code == 200
    assert {item["label"] for item in spatial.json()} == {"Visible crater"}

    private_spatial = client.get(
        "/api/search/spatial",
        params={"bbox": "0,0,1,1", "dataset_id": private.id},
        headers=auth_header(other_token),
    )
    assert private_spatial.status_code == 404


def test_private_annotation_search_responses_are_no_store(
    client, database, login_token
):
    owner = add_user(database, "cache-annotation-owner@example.invalid", "cacheannotationowner", "test-annotation-cache")
    demo = add_dataset(database, "cache-annotation-demo", demo=True)
    private = add_dataset(database, "cache-annotation-private", owner=owner)
    demo_annotation = add_annotation(database, demo, owner, label="Shared crater")
    add_annotation(database, private, owner, label="Shared crater")
    token = login_token(owner.email, "test-annotation-cache")
    headers = auth_header(token)

    private_annotations = client.get(
        f"/api/annotations/{private.id}", headers=headers
    )
    public_annotations = client.get(f"/api/annotations/{demo.id}")
    assert private_annotations.headers["cache-control"] == "private, no-store"
    assert "cache-control" not in public_annotations.headers

    text_search = client.get(
        "/api/search", params={"q": "Shared crater"}, headers=headers
    )
    spatial_search = client.get(
        "/api/search/spatial", params={"bbox": "0,0,1,1"}, headers=headers
    )
    similar_search = client.get(
        "/api/search/similar",
        params={"annotation_id": demo_annotation.id},
        headers=headers,
    )
    for response in (text_search, spatial_search, similar_search):
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"

    public_search = client.get("/api/search", params={"q": "Shared crater"})
    assert public_search.status_code == 200
    assert "cache-control" not in public_search.headers
