import os
import re
from datetime import datetime, timedelta

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
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

jwt = JWTManager(app)
db.init_app(app)

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]
CORS(
    app,
    resources={r"/*": {"origins": cors_origins}},
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


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


def serialize_trip(trip):
    return {
        "id": trip.id,
        "user_id": trip.user_id,
        "destination": trip.destination,
        "start_date": trip.start_date.isoformat() if trip.start_date else None,
        "end_date": trip.end_date.isoformat() if trip.end_date else None,
        "latitude": trip.latitude,
        "longitude": trip.longitude,
        "itinerary": trip.itinerary or [],
    }


def generate_default_itinerary(start_date, end_date):
    return [
        {
            "day": (trip_date - start_date).days + 1,
            "date": trip_date.isoformat(),
            "activities": [],
        }
        for trip_date in (
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        )
    ]


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


@app.route("/trips", methods=["GET"])
@jwt_required()
def get_trips():
    from models.trip import Trip

    current_user_id = int(get_jwt_identity())
    trips = Trip.query.filter_by(user_id=current_user_id).order_by(Trip.id.desc()).all()
    return jsonify([serialize_trip(trip) for trip in trips]), 200


@app.route("/trips", methods=["POST"])
@jwt_required()
def create_trip():
    from models.trip import Trip

    data = request.get_json(silent=True) or {}
    current_user_id = int(get_jwt_identity())

    destination = (data.get("destination") or "").strip()
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    itinerary = data.get("itinerary")

    if not destination or not start_date or not end_date:
        return jsonify({"error": "Destination, start_date, and end_date are required"}), 400

    try:
        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400

    if parsed_end < parsed_start:
        return jsonify({"error": "end_date must be after start_date"}), 400

    if itinerary is None:
        itinerary = generate_default_itinerary(parsed_start, parsed_end)
    elif not isinstance(itinerary, list):
        return jsonify({"error": "itinerary must be a list"}), 400

    trip = Trip(
        user_id=current_user_id,
        destination=destination,
        start_date=parsed_start,
        end_date=parsed_end,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        itinerary=itinerary,
    )

    db.session.add(trip)
    db.session.commit()

    return jsonify(serialize_trip(trip)), 201


@app.route("/trips/<int:trip_id>", methods=["GET"])
@jwt_required()
def get_trip(trip_id):
    from models.trip import Trip

    current_user_id = int(get_jwt_identity())
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()

    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    return jsonify(serialize_trip(trip)), 200


@app.route("/trips/<int:trip_id>", methods=["PUT"])
@jwt_required()
def update_trip(trip_id):
    from models.trip import Trip

    current_user_id = int(get_jwt_identity())
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    data = request.get_json(silent=True) or {}

    if "destination" in data and data["destination"]:
        trip.destination = data["destination"].strip()

    if "start_date" in data and data["start_date"]:
        try:
            trip.start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "start_date must be in YYYY-MM-DD format"}), 400

    if "end_date" in data and data["end_date"]:
        try:
            trip.end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "end_date must be in YYYY-MM-DD format"}), 400

    if "latitude" in data:
        trip.latitude = data["latitude"]
    if "longitude" in data:
        trip.longitude = data["longitude"]
    if "itinerary" in data:
        trip.itinerary = data["itinerary"] if isinstance(data["itinerary"], list) else []

    if trip.end_date < trip.start_date:
        return jsonify({"error": "end_date must be after start_date"}), 400

    db.session.commit()
    return jsonify(serialize_trip(trip)), 200


@app.route("/trips/<int:trip_id>", methods=["DELETE"])
@jwt_required()
def delete_trip(trip_id):
    from models.trip import Trip

    current_user_id = int(get_jwt_identity())
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    db.session.delete(trip)
    db.session.commit()
    return jsonify({"message": "Trip deleted successfully"}), 200


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
