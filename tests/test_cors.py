import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "planventure-api"))
sys.path.insert(0, PROJECT_ROOT)

from app import app


def test_react_origin_can_send_authorized_api_requests():
    response = app.test_client().options(
        "/trips",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "authorization" in response.headers["Access-Control-Allow-Headers"].lower()
    assert "content-type" in response.headers["Access-Control-Allow-Headers"].lower()
    assert "POST" in response.headers["Access-Control-Allow-Methods"]


def test_unconfigured_origin_is_not_allowed():
    response = app.test_client().get(
        "/health",
        headers={"Origin": "http://malicious.example"},
    )

    assert "Access-Control-Allow-Origin" not in response.headers