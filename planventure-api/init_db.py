from app import app, db
import models


def create_tables():
    with app.app_context():
        db.create_all()
    print("Database tables created successfully.")


if __name__ == "__main__":
    create_tables()