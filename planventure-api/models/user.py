from app import db
from utils.password import (
    generate_salt as generate_password_salt,
    hash_password as hash_password_value,
    verify_password,
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )
    trips = db.relationship("Trip", back_populates="user")

    @staticmethod
    def generate_salt():
        return generate_password_salt()

    @staticmethod
    def hash_password(password, salt=None):
        return hash_password_value(password, salt=salt)

    def set_password(self, password):
        self.password_hash = self.hash_password(password)

    def check_password(self, password):
        return verify_password(password, self.password_hash)