from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import ceil


@dataclass(frozen=True)
class SkuProfile:
    sku_code: str
    sku_name: str
    max_capacity_qty: int
    min_display_qty: int = 0
    shelf_life_days: int = 0


@dataclass(frozen=True)
class SaleEvent:
    event_ts: datetime
    fridge_code: str
    sku_code: str
    qty: int


@dataclass(frozen=True)
class InventorySnapshot:
    snapshot_ts: datetime
    fridge_code: str
    sku_code: str
    on_hand_qty: int
    days_to_expiry: int | None = None


@dataclass(frozen=True)
class RefillLine:
    fridge_code: str
    sku_code: str
    sku_name: str
    forecast_qty: float
    safety_stock_qty: int
    usable_stock_qty: int
    on_hand_qty: int
    recommended_qty: int
    capacity_qty: int
    reason: str


def plan_refill(
    sales: list[SaleEvent],
    inventory: list[InventorySnapshot],
    sku_profiles: list[SkuProfile],
    target_date: date,
) -> list[RefillLine]:
    profiles = {sku.sku_code: sku for sku in sku_profiles}
    fridges = sorted({event.fridge_code for event in sales} | {snapshot.fridge_code for snapshot in inventory})
    latest_inventory = _latest_inventory(inventory)
    rows: list[RefillLine] = []

    for fridge_code in fridges:
        for sku_code, profile in sorted(profiles.items()):
            forecast = _forecast_daily_sales(sales, fridge_code, sku_code, target_date)
            safety_stock = ceil(forecast * 0.25) if forecast > 0 else 0
            snapshot = latest_inventory.get((fridge_code, sku_code))
            on_hand = snapshot.on_hand_qty if snapshot else 0
            usable_stock = _usable_stock(snapshot)
            space = max(0, profile.max_capacity_qty - on_hand)
            display_gap = max(0, profile.min_display_qty - usable_stock) if forecast > 0 else 0
            need = max(display_gap, ceil(forecast + safety_stock - usable_stock))
            recommended = min(space, max(0, need))

            if not any([recommended, forecast, on_hand]):
                continue

            expiry_note = ""
            if snapshot and snapshot.days_to_expiry is not None and snapshot.days_to_expiry <= 1:
                expiry_note = "; near-expiry stock excluded"

            forecast_qty = round(forecast, 2)
            reason = (
                f"forecast={forecast_qty:.2f}, safety={safety_stock}, "
                f"usable_stock={usable_stock}, capacity={profile.max_capacity_qty}{expiry_note}"
            )
            rows.append(
                RefillLine(
                    fridge_code=fridge_code,
                    sku_code=sku_code,
                    sku_name=profile.sku_name,
                    forecast_qty=forecast_qty,
                    safety_stock_qty=safety_stock,
                    usable_stock_qty=usable_stock,
                    on_hand_qty=on_hand,
                    recommended_qty=recommended,
                    capacity_qty=profile.max_capacity_qty,
                    reason=reason,
                )
            )

    return rows


def _latest_inventory(
    inventory: list[InventorySnapshot],
) -> dict[tuple[str, str], InventorySnapshot]:
    latest: dict[tuple[str, str], InventorySnapshot] = {}
    for snapshot in inventory:
        key = (snapshot.fridge_code, snapshot.sku_code)
        if key not in latest or snapshot.snapshot_ts > latest[key].snapshot_ts:
            latest[key] = snapshot
    return latest


def _usable_stock(snapshot: InventorySnapshot | None) -> int:
    if not snapshot:
        return 0
    if snapshot.days_to_expiry is not None and snapshot.days_to_expiry <= 1:
        return 0
    return snapshot.on_hand_qty


def _forecast_daily_sales(
    sales: list[SaleEvent],
    fridge_code: str,
    sku_code: str,
    target_date: date,
) -> float:
    by_day: dict[date, int] = defaultdict(int)
    start = target_date - timedelta(days=28)

    for event in sales:
        event_date = event.event_ts.date()
        if event.fridge_code == fridge_code and event.sku_code == sku_code and start <= event_date < target_date:
            by_day[event_date] += event.qty

    last_7 = _average_daily(by_day, target_date, 7)
    last_28 = _average_daily(by_day, target_date, 28)
    baseline = (0.65 * last_7) + (0.35 * last_28)
    if baseline == 0:
        return 0.0

    same_weekday_days = [
        target_date - timedelta(days=offset)
        for offset in range(1, 29)
        if (target_date - timedelta(days=offset)).weekday() == target_date.weekday()
    ]
    weekday_avg = sum(by_day[day] for day in same_weekday_days) / len(same_weekday_days)
    weekday_factor = max(0.6, min(1.8, weekday_avg / last_28)) if last_28 else 1.0
    return baseline * weekday_factor


def _average_daily(by_day: dict[date, int], target_date: date, days: int) -> float:
    return sum(by_day[target_date - timedelta(days=offset)] for offset in range(1, days + 1)) / days
