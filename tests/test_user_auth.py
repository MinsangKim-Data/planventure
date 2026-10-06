import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "planventure-api"))
sys.path.insert(0, PROJECT_ROOT)

from app import app, db
from models.user import User


app.config["TESTING"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"


def test_user_password_round_trip():
    user = User(email="demo@example.com")
    user.set_password("secret123")

    assert user.password_hash
    assert user.check_password("secret123") is True
    assert user.check_password("wrong-password") is False


def test_user_hash_password_uses_salt():
    first = User.hash_password("secret123")
    second = User.hash_password("secret123")

    assert first != second
    assert User.generate_salt() is not None


def test_register_user_validates_email_and_creates_user():
    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()

    bad_response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "secret123"},
    )
    assert bad_response.status_code == 400

    good_response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "secret123"},
    )
    assert good_response.status_code == 201
    payload = good_response.get_json()
    assert payload["email"] == "user@example.com"

    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None
        assert user.check_password("secret123") is True
