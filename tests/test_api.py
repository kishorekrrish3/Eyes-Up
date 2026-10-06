from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_status_route():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "Eyes Up"
    assert data["offline_ready"] is True


def test_touch_grass_score_route():
    response = client.get("/api/touch-grass-score")
    assert response.status_code == 200
    data = response.json()
    assert "ratio" in data
    assert "outdoor_minutes" in data
    assert "screen_minutes" in data


def test_outing_lifecycle_route():
    # Start outing
    res_start = client.post("/api/outing/start")
    assert res_start.status_code == 200
    outing_id = res_start.json()["outing_id"]

    # Check status
    res_status = client.get("/api/outing/status")
    assert res_status.status_code == 200
    assert res_status.json()["active"] is True

    # Stop outing
    res_stop = client.post(
        "/api/outing/stop",
        json={"outing_id": outing_id, "screen_seconds": 30},
    )
    assert res_stop.status_code == 200
    data_stop = res_stop.json()
    assert "outing" in data_stop
    assert "weekly_stats" in data_stop


def test_identify_route_with_audio():
    sample_file = Path("samples/sample_bird.wav")
    assert sample_file.exists()

    with open(sample_file, "rb") as f:
        response = client.post(
            "/api/identify",
            files={"audio": ("sample_bird.wav", f, "audio/wav")},
            data={"threshold": "0.10"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tts" in data
    if data["identified"]:
        assert data["top_species"] is not None
        assert "tip" in data["top_species"]
