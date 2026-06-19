from odoo import api, fields, models

from ..mock_adapter import generate_mock_source, mock_event_id


class SchIntegrationRun(models.Model):
    _name = "sch.integration.run"
    _description = "Schrankerl Integration Run"
    _order = "started_at desc, id desc"

    name = fields.Char(required=True, default="Mock source sync")
    source = fields.Char(required=True, default="mock")
    started_at = fields.Datetime(required=True, default=fields.Datetime.now)
    finished_at = fields.Datetime(readonly=True)
    state = fields.Selection(
        [("running", "Running"), ("done", "Done"), ("error", "Error")],
        required=True,
        default="running",
    )
    sales_count = fields.Integer(readonly=True)
    snapshot_count = fields.Integer(readonly=True)
    plan_id = fields.Many2one("sch.refill.plan", readonly=True)
    line_count = fields.Integer(readonly=True)
    message = fields.Text(readonly=True)

    @api.model
    def run_mock_sync(self):
        self.search([("state", "=", "running"), ("finished_at", "=", False)]).write(
            {
                "state": "error",
                "finished_at": fields.Datetime.now(),
                "message": "Stale empty run closed before starting a real sync.",
            }
        )
        run = self.create({"name": "Mock source sync"})
        try:
            today = fields.Date.context_today(self)
            fridges = self.env["sch.fridge"].search([])
            products = self.env["product.product"].search(
                [("default_code", "!=", False), ("sch_max_capacity_qty", ">", 0)]
            )
            sales, snapshots = generate_mock_source(
                fridges.mapped("code"),
                products.mapped("default_code"),
                today,
                salt=str(run.id),
            )
            fridge_by_code = {fridge.code: fridge for fridge in fridges}
            product_by_code = {product.default_code: product for product in products}
            self.env["sch.sale.event"].search([("event_id", "=like", "MOCK-%")]).unlink()
            self.env["sch.inventory.snapshot"].search([("data_source", "=", "mock")]).unlink()

            for event in sales:
                event_id = mock_event_id(event)
                self.env["sch.sale.event"].create(
                    {
                        "event_id": event_id,
                        "event_ts": event.event_ts,
                        "fridge_id": fridge_by_code[event.fridge_code].id,
                        "product_id": product_by_code[event.sku_code].id,
                        "qty": event.qty,
                        "unit_price": 0.0,
                    }
                )

            for snapshot in snapshots:
                self.env["sch.inventory.snapshot"].create(
                    {
                        "snapshot_ts": snapshot.snapshot_ts,
                        "fridge_id": fridge_by_code[snapshot.fridge_code].id,
                        "product_id": product_by_code[snapshot.sku_code].id,
                        "on_hand_qty": snapshot.on_hand_qty,
                        "days_to_expiry": snapshot.days_to_expiry,
                        "data_source": "mock",
                    }
                )

            target_date = fields.Date.add(today, days=1)
            plan = self.env["sch.refill.plan"].search([("target_date", "=", target_date)], limit=1)
            if not plan:
                plan = self.env["sch.refill.plan"].create(
                    {"name": f"Refill plan {target_date}", "target_date": target_date}
                )
            plan.action_generate()
            run.write(
                {
                    "state": "done",
                    "finished_at": fields.Datetime.now(),
                    "sales_count": len(sales),
                    "snapshot_count": len(snapshots),
                    "plan_id": plan.id,
                    "line_count": len(plan.line_ids),
                    "message": f"Mock sync completed. Seed: {run.id}.",
                }
            )
        except Exception as exc:
            run.write(
                {
                    "state": "error",
                    "finished_at": fields.Datetime.now(),
                    "message": str(exc),
                }
            )
            raise
        return run

    @api.model
    def action_run_mock_sync(self):
        self.run_mock_sync()
        return self.env.ref("schrankerl_refill_planner.action_sch_integration_run").read()[0]
