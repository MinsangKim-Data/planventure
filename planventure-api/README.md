# Planventure API

A Flask REST API for Planventure. It provides user registration and login, JWT-protected trip CRUD operations, and a health endpoint. SQLAlchemy stores users and trips; SQLite is the default database.

## Features

- Register and log in with an email and password
- Hash passwords with bcrypt
- Issue JWT access tokens that expire after 24 hours
- Create, list, retrieve, update, and delete trips
- Scope trip queries and changes to the authenticated user
- Generate a dated, empty itinerary when a trip is created without one
- Configure browser CORS origins for a React frontend

## Requirements

- Python 3.8 or later
- pip

## Local setup

From the repository root, create and activate a virtual environment, then install the API dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r planventure-api/requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source venv/bin/activate
pip install -r planventure-api/requirements.txt
```

Create the API environment file from the sample. On PowerShell:

```powershell
Copy-Item planventure-api/.sample.env planventure-api/.env
```

On macOS or Linux:

```bash
cp planventure-api/.sample.env planventure-api/.env
```

Replace the placeholder `SECRET_KEY` and `JWT_SECRET_KEY` values with distinct, randomly generated secrets. Keep `.env` private and do not commit it.

## Configuration

The API reads these values from `planventure-api/.env`:

| Variable | Purpose | Default/sample |
| --- | --- | --- |
| `SECRET_KEY` | Flask application secret | Set a private random value |
| `JWT_SECRET_KEY` | Signs JWT access tokens | Set a different private random value |
| `DATABASE_URL` | SQLAlchemy database connection | `sqlite:///planventure.db` |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API | `http://localhost:3000,http://localhost:5173` |
| `FLASK_DEBUG` | Enables Flask debug mode when true | `true` in the sample; disable outside local development |

The ports `3000` and `5173` are common React development-server ports. Keep only the origins your frontend actually uses, and add your deployed frontend origin when deploying. Origins include scheme and port, for example `http://localhost:5173`.

CORS permits the API methods `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, and `OPTIONS`, and request headers `Content-Type` and `Authorization`. CORS is a browser access policy; it does not replace JWT authentication.

## Initialize the database

From the repository root:

```powershell
python planventure-api/init_db.py
```

Or change into `planventure-api` and run:

```powershell
python init_db.py
```

The script creates the tables defined by the SQLAlchemy models. It does not erase existing data.

## Run the API

From the API directory:

```powershell
cd planventure-api
flask --app app run --debug
```

The development server is available at `http://127.0.0.1:5000`. Use `--debug` only for local development.

## Authentication

Register an account:

```http
POST /auth/register
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

A successful registration returns `201 Created` with the user ID and email. Invalid or duplicate emails and missing fields return `400 Bad Request`.

Log in to receive an access token:

```http
POST /auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

A successful response includes an `access_token`. Invalid credentials return `401 Unauthorized`.

Send that token with protected requests:

```http
Authorization: Bearer <access_token>
```

Tokens expire after 24 hours. Protected routes return `401 Unauthorized` if the token is missing or invalid.

## API endpoints

| Method | Path | Auth required | Description |
| --- | --- | --- | --- |
| `GET` | `/` | No | Welcome message |
| `GET` | `/health` | No | Basic health response (`{"status":"healthy"}`) |
| `POST` | `/auth/register` | No | Register an account |
| `POST` | `/auth/login` | No | Log in and receive a JWT |
| `GET` | `/protected` | Yes | Example protected endpoint |
| `GET` | `/trips` | Yes | List the authenticated user's trips |
| `POST` | `/trips` | Yes | Create a trip for the authenticated user |
| `GET` | `/trips/<trip_id>` | Yes | Retrieve one of the user's trips |
| `PUT` | `/trips/<trip_id>` | Yes | Update one of the user's trips |
| `DELETE` | `/trips/<trip_id>` | Yes | Delete one of the user's trips |

Trip endpoints only expose trips owned by the authenticated user. A trip belonging to another user is returned as `404 Not Found`.

### Create a trip

```http
POST /trips
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "destination": "Kyoto",
  "start_date": "2026-11-01",
  "end_date": "2026-11-03",
  "latitude": 35.0116,
  "longitude": 135.7681
}
```

`destination`, `start_date`, and `end_date` are required. Dates use `YYYY-MM-DD`; the end date cannot be before the start date. `latitude`, `longitude`, and `itinerary` are optional. If `itinerary` is omitted, the API creates an entry for each date in the trip, inclusive, with an empty `activities` list. A supplied itinerary must be a JSON array.

Example generated itinerary:

```json
[
  {"day": 1, "date": "2026-11-01", "activities": []},
  {"day": 2, "date": "2026-11-02", "activities": []},
  {"day": 3, "date": "2026-11-03", "activities": []}
]
```

`PUT /trips/<trip_id>` accepts the trip fields to update as a JSON object. `DELETE` returns a success message when the trip is removed.

## Run tests

Tests are located in the repository-level `tests/` directory. From the repository root, with the virtual environment active:

```powershell
python -m pytest tests
```

The suite covers authentication, trip CRUD and ownership, default itinerary generation, and CORS behavior.

## Production notes

- Replace all development secrets with secure deployment secrets.
- Disable Flask debug mode in production.
- Configure `CORS_ORIGINS` with only trusted frontend origins.
- Use a production WSGI server; Flask's built-in server is for development.
- The `/health` endpoint is a basic liveness response and does not check database availability.
