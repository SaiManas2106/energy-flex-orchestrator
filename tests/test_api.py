from fastapi.testclient import TestClient

from app.main import app, store

client = TestClient(app)


def payload():
    return {
        "asset_id": "demo-property-1",
        "points": [
            {"timestamp": "2026-07-01T00:00:00Z", "spot_price_sek_per_kwh": 0.5, "base_load_kwh": 2, "solar_generation_kwh": 0},
            {"timestamp": "2026-07-01T12:00:00Z", "spot_price_sek_per_kwh": 1.2, "base_load_kwh": 2, "solar_generation_kwh": 4},
            {"timestamp": "2026-07-01T18:00:00Z", "spot_price_sek_per_kwh": 2.2, "base_load_kwh": 5, "solar_generation_kwh": 0},
            {"timestamp": "2026-07-01T19:00:00Z", "spot_price_sek_per_kwh": 2.3, "base_load_kwh": 5, "solar_generation_kwh": 0},
        ],
    }


def test_health_and_plan_lifecycle(tmp_path):
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/telemetry", json=payload())
    assert response.status_code == 201
    response = client.post("/plans", json=payload())
    assert response.status_code == 201
    plan_id = response.json()["plan_id"]
    saved = client.get(f"/plans/{plan_id}")
    assert saved.status_code == 200
    assert len(saved.json()["actions"]) == 4
