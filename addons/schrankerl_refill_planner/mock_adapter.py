from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from .planner import InventorySnapshot, SaleEvent


def generate_mock_source(
    fridge_codes: list[str],
    sku_codes: list[str],
    as_of: date,
    salt: str = "",
) -> tuple[list[SaleEvent], list[InventorySnapshot]]:
    sales: list[SaleEvent] = []
    snapshots: list[InventorySnapshot] = []

    for fridge_code in sorted(fridge_codes):
        for sku_code in sorted(sku_codes):
            seed = f"{as_of.isoformat()}:{fridge_code}:{sku_code}"
            rng = random.Random(f"{seed}:{salt}" if salt else seed)
            base = rng.randint(1, 4)

            for offset in range(1, 8):
                day = as_of - timedelta(days=offset)
                qty = max(1, base + rng.randint(-1, 2))
                hour = 8 + rng.randint(0, 7)
                minute = rng.randint(0, 59)
                sales.append(
                    SaleEvent(
                        event_ts=datetime.combine(day, time(hour, minute)),
                        fridge_code=fridge_code,
                        sku_code=sku_code,
                        qty=qty,
                    )
                )

            snapshots.append(
                InventorySnapshot(
                    snapshot_ts=datetime.combine(as_of, time(18, 0)),
                    fridge_code=fridge_code,
                    sku_code=sku_code,
                    on_hand_qty=rng.randint(0, 8),
                    days_to_expiry=rng.randint(1, 20),
                )
            )

    return sales, snapshots


def mock_event_id(event: SaleEvent) -> str:
    return (
        f"MOCK-{event.event_ts.date().isoformat()}-"
        f"{event.fridge_code}-{event.sku_code}-{event.event_ts.hour:02d}{event.event_ts.minute:02d}"
    )
