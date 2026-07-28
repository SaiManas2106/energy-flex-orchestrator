from app.optimizer import BatteryConfig, TelemetryPoint, optimise_schedule


def scenario():
    return [
        TelemetryPoint("2026-07-01T00:00:00Z", 0.50, 2.0, 0.0),
        TelemetryPoint("2026-07-01T01:00:00Z", 0.55, 2.0, 0.0),
        TelemetryPoint("2026-07-01T12:00:00Z", 1.20, 2.0, 4.0),
        TelemetryPoint("2026-07-01T18:00:00Z", 2.20, 5.0, 0.0),
        TelemetryPoint("2026-07-01T19:00:00Z", 2.30, 5.0, 0.0),
    ]


def test_schedule_respects_battery_bounds_and_reduces_peak_import():
    plan = optimise_schedule(scenario(), BatteryConfig(initial_soc_kwh=2.0, capacity_kwh=8.0))
    assert 0 <= plan["final_battery_soc_kwh"] <= 8.0
    assert plan["peak_grid_kw"] < 5.0
    assert any(action["action"] == "discharge" for action in plan["actions"])


def test_schedule_produces_a_transparent_action_for_every_point():
    plan = optimise_schedule(scenario(), BatteryConfig())
    assert len(plan["actions"]) == len(scenario())
    assert all("battery_soc_kwh" in action and "grid_kwh" in action for action in plan["actions"])


def test_invalid_initial_charge_is_rejected():
    try:
        optimise_schedule(scenario(), BatteryConfig(initial_soc_kwh=11.0, capacity_kwh=10.0))
    except ValueError as error:
        assert "state of charge" in str(error)
    else:
        raise AssertionError("Invalid state of charge was accepted")
