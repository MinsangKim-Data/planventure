from models.user import User


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
