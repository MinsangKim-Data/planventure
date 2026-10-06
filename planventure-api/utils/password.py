import bcrypt


def generate_salt():
    return bcrypt.gensalt()


def hash_password(password, salt=None):
    if password is None or password == "":
        raise ValueError("Password cannot be empty")

    if salt is None:
        salt = generate_salt()

    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password, password_hash):
    if not password_hash:
        return False

    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )
