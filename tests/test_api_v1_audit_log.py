"""Activity log: recorded changes, filters, richer fields and filter facets (issue #96)."""

from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest

from tests.image_fixtures import png_bytes
from tests.test_api_v1_authz import _csrf_headers, _set_user_session, seeded_identity_data  # noqa: F401


def _events(client, query=""):
    response = client.get(f"/api/v1/audit-events?page_size=200{query}")
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()["data"]


@pytest.fixture()
def admin_activity(client, seeded_identity_data):  # noqa: F811
    """Some recorded activity by the administrator: a jigsaw edit and a user edit."""
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    jigsaw_id = seeded_identity_data["available_jigsaw_id"]
    edited = client.patch(
        f"/api/v1/jigsaws/{jigsaw_id}",
        headers=_csrf_headers(),
        json={"title": "Harbour Sunset (100% edition)", "piece_count": 1000},
    )
    assert edited.status_code == 200
    member_id = seeded_identity_data["member_user_id"]
    updated = client.patch(
        f"/api/v1/users/{member_id}",
        headers=_csrf_headers(),
        json={"display_name": "Member Renamed", "password": "NewMemberPassword123!"},
    )
    assert updated.status_code == 200
    return {"jigsaw_id": jigsaw_id, "member_id": member_id, **seeded_identity_data}


@pytest.mark.functional
def test_jigsaw_edit_records_old_and_new_values(client, admin_activity):
    event = _events(client, f"&action=jigsaw.updated&entity_id={admin_activity['jigsaw_id']}")[0]

    assert event["payload"]["changes"] == {"title": {"from": "Harbor Sunset", "to": "Harbour Sunset (100% edition)"}}
    # Fields sent without a change are listed as updated but not as changed.
    assert event["payload"]["updated_fields"] == ["piece_count", "title"]


@pytest.mark.functional
def test_user_edit_records_changes_but_never_the_password(client, admin_activity):
    event = _events(client, f"&action=user.updated&entity_id={admin_activity['member_id']}")[0]

    changes = event["payload"]["changes"]
    assert changes["display_name"] == {"from": "Member User", "to": "Member Renamed"}
    assert changes["password"] == {"changed": True}
    assert "NewMemberPassword123!" not in str(event)
    assert "pbkdf2" not in str(event) and "scrypt" not in str(event)


@pytest.mark.functional
def test_image_tag_change_records_the_previous_tag(client, seeded_identity_data):  # noqa: F811
    _set_user_session(client, seeded_identity_data["admin_user_id"])
    uploaded = client.post(
        f"/api/v1/jigsaws/{seeded_identity_data['available_jigsaw_id']}/images",
        headers=_csrf_headers(),
        data={"tag": "Box front", "image": (BytesIO(png_bytes(b"issue96-tag")), "box.png")},
        content_type="multipart/form-data",
    )
    image_id = uploaded.get_json()["data"]["id"]
    retagged = client.patch(
        f"/api/v1/image-library/images/{image_id}/tag", headers=_csrf_headers(), json={"tag": "Reference"}
    )
    assert retagged.status_code == 200

    event = _events(client, f"&action=jigsaw.image_tag_updated&entity_id={image_id}")[0]
    assert event["payload"]["changes"] == {"tag": {"from": "Box front", "to": "Reference"}}


@pytest.mark.functional
def test_events_carry_actor_details_parsed_payload_and_client_ip(client, admin_activity):
    event = _events(client, "&action=jigsaw.updated")[0]

    assert event["actor"] == {"id": admin_activity["admin_user_id"], "display_name": "Admin User", "email": "admin@example.com"}
    assert isinstance(event["payload"], dict)
    assert event["client_ip"]
    # The original fields are still there for existing clients.
    for field in ("actor_user_id", "action", "entity_type", "entity_id", "payload_json", "created_at"):
        assert field in event


@pytest.mark.functional
@pytest.mark.parametrize(
    ("query", "expected_actions"),
    [
        ("&action=user.updated", {"user.updated"}),
        ("&category=jigsaw", {"jigsaw.updated"}),
        ("&entity_type=user", {"user.updated"}),
        ("&q=member%20renamed", {"user.updated"}),
        ("&q=100%25%20edition", {"jigsaw.updated"}),
    ],
    ids=["action", "category", "record-type", "search-payload", "search-literal-percent"],
)
def test_filters_narrow_the_events(client, admin_activity, query, expected_actions):
    actions = {event["action"] for event in _events(client, query)}

    assert actions == expected_actions


@pytest.mark.functional
def test_search_matches_the_account_name(client, admin_activity):
    events = _events(client, "&q=admin%20user")

    assert events
    assert all(event["actor_user_id"] == admin_activity["admin_user_id"] for event in events)


@pytest.mark.functional
def test_search_wildcards_are_taken_literally(client, admin_activity):
    assert _events(client, "&q=%25%25") == []
    assert _events(client, "&q=_____nothing") == []


@pytest.mark.functional
def test_account_and_date_filters(client, admin_activity):
    admin_id = admin_activity["admin_user_id"]
    assert all(event["actor_user_id"] == admin_id for event in _events(client, f"&actor_user_id={admin_id}"))
    assert _events(client, f"&actor_user_id={admin_activity['borrower_user_id']}") == []

    now = datetime.now(timezone.utc)
    later = (now + timedelta(hours=1)).isoformat()
    earlier = (now - timedelta(hours=1)).isoformat()
    assert _events(client, f"&from={later.replace('+', '%2B')}") == []
    assert len(_events(client, f"&from={earlier.replace('+', '%2B')}&to={later.replace('+', '%2B')}")) >= 2


@pytest.mark.functional
@pytest.mark.parametrize(
    "query",
    ["&actor_user_id=abc", "&actor_user_id=-1", "&from=not-a-date", "&q=" + "x" * 201],
    ids=["actor-text", "actor-negative", "bad-date", "long-search"],
)
def test_invalid_filters_are_rejected(client, admin_activity, query):
    response = client.get(f"/api/v1/audit-events?page_size=10{query}")

    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_error"


@pytest.mark.functional
def test_facets_list_what_the_filters_can_offer(client, admin_activity):
    response = client.get("/api/v1/audit-events/facets")

    assert response.status_code == 200
    facets = response.get_json()["data"]
    assert {"jigsaw.updated", "user.updated"} <= set(facets["actions"])
    assert {"jigsaw", "user"} <= set(facets["entity_types"])
    assert {"id": admin_activity["admin_user_id"], "display_name": "Admin User", "email": "admin@example.com"} in facets["actors"]


@pytest.mark.functional
def test_members_only_see_and_filter_their_own_events(client, admin_activity):
    _set_user_session(client, admin_activity["member_user_id"])
    client.patch("/api/v1/auth/me", headers=_csrf_headers(), json={"display_name": "Member Self"})

    own = _events(client)
    assert own and all(event["actor_user_id"] == admin_activity["member_user_id"] for event in own)
    assert _events(client, f"&actor_user_id={admin_activity['admin_user_id']}") == []

    facets = client.get("/api/v1/audit-events/facets").get_json()["data"]
    assert [actor["id"] for actor in facets["actors"]] == [admin_activity["member_user_id"]]
    assert "jigsaw.updated" not in facets["actions"]
