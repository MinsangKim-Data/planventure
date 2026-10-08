import os
import sys
import uuid

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "planventure-api"))
sys.path.insert(0, PROJECT_ROOT)

from app import app, db


app.config["TESTING"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"


def setup_test_user(client, email="trip-user@example.com"):
    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "secret123"},
    )
    assert login_response.status_code == 200

    return login_response.get_json()["access_token"]


def test_trip_crud_requires_auth_and_uses_user_scope():
    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    token = setup_test_user(client)

    no_auth = client.get("/trips")
    assert no_auth.status_code == 401

    create_response = client.post(
        "/trips",
        json={
            "destination": "Paris",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "latitude": 48.8566,
            "longitude": 2.3522,
            "itinerary": [{"day": 1, "activity": "Eiffel Tower"}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    trip_payload = create_response.get_json()
    trip_id = trip_payload["id"]
    assert trip_payload["destination"] == "Paris"

    list_response = client.get("/trips", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    assert len(list_response.get_json()) == 1

    update_response = client.put(
        f"/trips/{trip_id}",
        json={"destination": "Rome", "itinerary": [{"day": 1, "activity": "Colosseum"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["destination"] == "Rome"

    delete_response = client.delete(
        f"/trips/{trip_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200

    fetch_after_delete = client.get(
        f"/trips/{trip_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fetch_after_delete.status_code == 404


def test_create_trip_generates_default_itinerary_when_omitted():
    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    token = setup_test_user(client, f"itinerary-{uuid.uuid4().hex}@example.com")

    response = client.post(
        "/trips",
        json={
            "destination": "Kyoto",
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.get_json()["itinerary"] == [
        {"day": 1, "date": "2026-11-01", "activities": []},
        {"day": 2, "date": "2026-11-02", "activities": []},
        {"day": 3, "date": "2026-11-03", "activities": []},
    ]
