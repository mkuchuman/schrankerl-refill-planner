import unittest
from datetime import date, datetime, timedelta

from schrankerl_refill_planner.mock_adapter import generate_mock_source, mock_event_id
from schrankerl_refill_planner.planner import InventorySnapshot, SaleEvent, SkuProfile, plan_refill


class PlannerTest(unittest.TestCase):
    def test_fast_mover_gets_refill(self):
        target = date(2026, 6, 19)
        rows = plan_refill(
            _sales("FR001", "SKU001", target, qty_per_day=3),
            [InventorySnapshot(datetime(2026, 6, 18, 18), "FR001", "SKU001", 1, 3)],
            [SkuProfile("SKU001", "Curry", 12, 2, 3)],
            target,
        )

        self.assertGreater(rows[0].recommended_qty, 0)

    def test_existing_stock_reduces_refill(self):
        target = date(2026, 6, 19)
        profile = [SkuProfile("SKU001", "Curry", 12, 2, 3)]
        sales = _sales("FR001", "SKU001", target, qty_per_day=2)
        low_stock = plan_refill(
            sales,
            [InventorySnapshot(datetime(2026, 6, 18, 18), "FR001", "SKU001", 0, 3)],
            profile,
            target,
        )[0].recommended_qty
        high_stock = plan_refill(
            sales,
            [InventorySnapshot(datetime(2026, 6, 18, 18), "FR001", "SKU001", 8, 3)],
            profile,
            target,
        )[0].recommended_qty

        self.assertLess(high_stock, low_stock)

    def test_capacity_cap_is_respected(self):
        target = date(2026, 6, 19)
        row = plan_refill(
            _sales("FR001", "SKU001", target, qty_per_day=10),
            [InventorySnapshot(datetime(2026, 6, 18, 18), "FR001", "SKU001", 4, 3)],
            [SkuProfile("SKU001", "Curry", 5, 2, 3)],
            target,
        )[0]

        self.assertEqual(row.recommended_qty, 1)

    def test_near_expiry_stock_is_not_usable(self):
        target = date(2026, 6, 19)
        row = plan_refill(
            _sales("FR001", "SKU001", target, qty_per_day=2),
            [InventorySnapshot(datetime(2026, 6, 18, 18), "FR001", "SKU001", 2, 1)],
            [SkuProfile("SKU001", "Curry", 12, 2, 3)],
            target,
        )[0]

        self.assertEqual(row.usable_stock_qty, 0)
        self.assertIn("near-expiry", row.reason)


class MockAdapterTest(unittest.TestCase):
    def test_mock_source_is_deterministic(self):
        args = (["FR001", "FR002"], ["SKU001", "SKU002", "SKU003", "SKU004", "SKU005"], date(2026, 6, 19))

        self.assertEqual(generate_mock_source(*args), generate_mock_source(*args))

    def test_mock_source_changes_with_salt(self):
        args = (["FR001", "FR002"], ["SKU001", "SKU002", "SKU003", "SKU004", "SKU005"], date(2026, 6, 19))
        first = generate_mock_source(*args, salt="1")
        second = generate_mock_source(*args, salt="2")

        self.assertNotEqual(first, second)
        self.assertEqual(len(first[0]), 70)
        self.assertEqual(len(first[1]), 10)
        self.assertEqual(len(second[0]), 70)
        self.assertEqual(len(second[1]), 10)

    def test_mock_source_counts_and_unique_event_ids(self):
        sales, snapshots = generate_mock_source(
            ["FR001", "FR002"],
            ["SKU001", "SKU002", "SKU003", "SKU004", "SKU005"],
            date(2026, 6, 19),
        )
        event_ids = [mock_event_id(event) for event in sales]

        self.assertEqual(len(sales), 70)
        self.assertEqual(len(snapshots), 10)
        self.assertEqual(len(event_ids), len(set(event_ids)))


def _sales(fridge_code, sku_code, target, qty_per_day):
    return [
        SaleEvent(
            datetime.combine(target - timedelta(days=offset), datetime.min.time()),
            fridge_code,
            sku_code,
            qty_per_day,
        )
        for offset in range(1, 8)
    ]


if __name__ == "__main__":
    unittest.main()
