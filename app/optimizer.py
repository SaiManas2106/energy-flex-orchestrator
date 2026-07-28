"""Deterministic scheduling logic for a battery-enabled energy asset."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import quantiles
from typing import Iterable


@dataclass(frozen=True)
class TelemetryPoint:
    timestamp: str
    spot_price_sek_per_kwh: float
    base_load_kwh: float
    solar_generation_kwh: float


@dataclass(frozen=True)
class BatteryConfig:
    capacity_kwh: float = 10.0
    initial_soc_kwh: float = 5.0
    max_charge_kw: float = 3.0
    max_discharge_kw: float = 3.0
    round_trip_efficiency: float = 0.92
    grid_limit_kw: float = 8.0
    target_peak_kw: float = 4.0


def _price_thresholds(points: list[TelemetryPoint]) -> tuple[float, float]:
    prices = sorted(point.spot_price_sek_per_kwh for point in points)
    if len(prices) < 4:
        return prices[0], prices[-1]
    lower, _, upper = quantiles(prices, n=4, method="inclusive")
    return lower, upper


def optimise_schedule(points: Iterable[TelemetryPoint], config: BatteryConfig) -> dict:
    """Create a transparent, constraint-respecting battery plan.

    The scheduler first absorbs solar surplus, discharges during expensive periods,
    and charges from the grid only in low-price periods when capacity is available.
    One telemetry point represents one hour.
    """
    points = list(points)
    if not points:
        raise ValueError("At least one telemetry point is required")
    if not 0 <= config.initial_soc_kwh <= config.capacity_kwh:
        raise ValueError("Initial battery state of charge must be within capacity")
    if any(point.spot_price_sek_per_kwh < 0 or point.base_load_kwh < 0 or point.solar_generation_kwh < 0 for point in points):
        raise ValueError("Telemetry values must be non-negative")

    low_price, high_price = _price_thresholds(points)
    soc = config.initial_soc_kwh
    charge_efficiency = config.round_trip_efficiency ** 0.5
    discharge_efficiency = charge_efficiency
    baseline_cost = 0.0
    optimised_cost = 0.0
    peak_grid_kw = 0.0
    actions: list[dict] = []

    for point in points:
        net_load = point.base_load_kwh - point.solar_generation_kwh
        baseline_grid = max(0.0, net_load)
        baseline_cost += baseline_grid * point.spot_price_sek_per_kwh
        charge_from_solar = min(max(0.0, -net_load), config.max_charge_kw, (config.capacity_kwh - soc) / charge_efficiency)
        soc += charge_from_solar * charge_efficiency

        action = "idle"
        grid_charge = 0.0
        discharged = 0.0
        if net_load > 0 and point.spot_price_sek_per_kwh >= high_price and soc > 0:
            discharged = min(net_load, config.max_discharge_kw, soc * discharge_efficiency)
            soc -= discharged / discharge_efficiency
            action = "discharge"
        elif point.spot_price_sek_per_kwh <= low_price and soc < config.capacity_kwh:
            room = (config.capacity_kwh - soc) / charge_efficiency
            # Low-price charging must still preserve a configurable import ceiling
            # so cost optimisation does not create a new demand peak.
            grid_headroom = max(0.0, min(config.grid_limit_kw, config.target_peak_kw) - max(0.0, net_load))
            grid_charge = min(config.max_charge_kw, room, grid_headroom)
            if grid_charge > 0:
                soc += grid_charge * charge_efficiency
                action = "charge_low_price"
        elif charge_from_solar > 0:
            action = "charge_solar"

        grid_kwh = max(0.0, net_load) + grid_charge - discharged
        peak_grid_kw = max(peak_grid_kw, grid_kwh)
        optimised_cost += grid_kwh * point.spot_price_sek_per_kwh
        actions.append({
            "timestamp": point.timestamp,
            "action": action,
            "spot_price_sek_per_kwh": round(point.spot_price_sek_per_kwh, 3),
            "grid_kwh": round(grid_kwh, 3),
            "battery_soc_kwh": round(soc, 3),
        })

    return {
        "baseline_cost_sek": round(baseline_cost, 2),
        "optimised_cost_sek": round(optimised_cost, 2),
        "estimated_savings_sek": round(baseline_cost - optimised_cost, 2),
        "peak_grid_kw": round(peak_grid_kw, 2),
        "final_battery_soc_kwh": round(soc, 3),
        "actions": actions,
    }
