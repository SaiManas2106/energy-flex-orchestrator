# Energy Flex Orchestrator

A company-neutral Python service that turns property telemetry and spot-price signals into transparent battery and charging schedules. It is designed as a portfolio-quality example of the control logic behind energy flexibility platforms.

## What it demonstrates

- FastAPI endpoints for telemetry ingestion, optimisation plans, plan retrieval, and health checks
- SQLite persistence for time-series telemetry and generated plans
- Deterministic scheduling that absorbs solar surplus, charges at low prices, and discharges during high-price periods
- Battery state-of-charge, power, and grid-import constraints with explainable action output
- REST APIs, Docker packaging, Pytest coverage, and GitHub Actions CI

## Architecture

```text
Property telemetry and spot prices
                |
                v
        FastAPI ingestion API ----> SQLite telemetry store
                |
                v
  Constraint-aware scheduling engine
                |
                v
   Transparent plan API and persisted plan
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Test

```bash
pytest -q
```

## Example request

```json
POST /plans
{
  "asset_id": "demo-property-1",
  "points": [
    {"timestamp": "2026-07-01T00:00:00Z", "spot_price_sek_per_kwh": 0.50, "base_load_kwh": 2.0, "solar_generation_kwh": 0.0},
    {"timestamp": "2026-07-01T12:00:00Z", "spot_price_sek_per_kwh": 1.20, "base_load_kwh": 2.0, "solar_generation_kwh": 4.0},
    {"timestamp": "2026-07-01T18:00:00Z", "spot_price_sek_per_kwh": 2.20, "base_load_kwh": 5.0, "solar_generation_kwh": 0.0}
  ]
}
```

The response includes each control action, grid import, battery state of charge, estimated cost, and estimated savings. The scheduler is intentionally deterministic and explainable, which makes its behaviour easy to test and evolve before replacing it with a more advanced optimisation solver.
