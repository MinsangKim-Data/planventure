import os
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    decode_token,
    get_jwt_identity,
    jwt_required,
)
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///planventure.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"

jwt = JWTManager(app)
db.init_app(app)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
CORS(app, origins=[origin.strip() for origin in cors_origins.split(",")])


def generate_token(user_id):
    with app.app_context():
        return create_access_token(identity=str(user_id))


def validate_token(token):
    if not token:
        return None

    token_value = token.replace("Bearer ", "").strip()

    try:
        with app.app_context():
            payload = decode_token(token_value)
        return payload.get("sub")
    except Exception:
        return None


def is_valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


@app.route("/auth/register", methods=["POST"])
def register_user():
    from models.user import User

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User with this email already exists"}), 400

    try:
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Unable to register user"}), 500

    return jsonify({
        "message": "User registered successfully",
        "email": user.email,
        "user_id": user.id,
    }), 201


@app.route("/auth/login", methods=["POST"])
def login_user():
    from models.user import User

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "email": user.email,
        "user_id": user.id,
        "access_token": token,
    }), 200


@app.route('/')
def home():
    return jsonify({"message": "Welcome to PlanVenture API"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})


@app.route('/protected')
@jwt_required()
def protected_route():
    current_user_id = get_jwt_identity()
    return jsonify({"message": "Access granted", "user_id": current_user_id}), 200


if __name__ == '__main__':
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() in {"1", "true", "yes"})
