from datetime import datetime

from odoo import fields, models

from ..planner import InventorySnapshot, SaleEvent, SkuProfile, plan_refill


class ProductProduct(models.Model):
    _inherit = "product.product"

    sch_max_capacity_qty = fields.Integer(string="Fridge Capacity")
    sch_min_display_qty = fields.Integer(string="Min Display Qty")
    sch_shelf_life_days = fields.Integer(string="Shelf Life Days")


class SchRefillPlan(models.Model):
    _name = "sch.refill.plan"
    _description = "Schrankerl Refill Plan"
    _order = "target_date desc, id desc"

    name = fields.Char(required=True, default="Draft refill plan")
    target_date = fields.Date(required=True, default=fields.Date.context_today)
    state = fields.Selection(
        [("draft", "Draft"), ("ready", "Ready")],
        required=True,
        default="draft",
    )
    generated_at = fields.Datetime(readonly=True)
    line_ids = fields.One2many("sch.refill.plan.line", "plan_id", string="Lines")

    def action_generate(self):
        for plan in self:
            plan.line_ids.unlink()
            fridges = self.env["sch.fridge"].search([])
            products = self.env["product.product"].search([("default_code", "!=", False)])
            product_by_code = {product.default_code: product for product in products}
            fridge_by_code = {fridge.code: fridge for fridge in fridges}

            lines = plan_refill(
                sales=[
                    SaleEvent(
                        event_ts=_as_datetime(event.event_ts),
                        fridge_code=event.fridge_id.code,
                        sku_code=event.product_id.default_code,
                        qty=event.qty,
                    )
                    for event in self.env["sch.sale.event"].search([])
                    if event.product_id.default_code and event.fridge_id.code
                ],
                inventory=[
                    InventorySnapshot(
                        snapshot_ts=_as_datetime(snapshot.snapshot_ts),
                        fridge_code=snapshot.fridge_id.code,
                        sku_code=snapshot.product_id.default_code,
                        on_hand_qty=snapshot.on_hand_qty,
                        days_to_expiry=snapshot.days_to_expiry or None,
                    )
                    for snapshot in self.env["sch.inventory.snapshot"].search([])
                    if snapshot.product_id.default_code and snapshot.fridge_id.code
                ],
                sku_profiles=[
                    SkuProfile(
                        sku_code=product.default_code,
                        sku_name=product.display_name,
                        max_capacity_qty=product.sch_max_capacity_qty or 0,
                        min_display_qty=product.sch_min_display_qty or 0,
                        shelf_life_days=product.sch_shelf_life_days or 0,
                    )
                    for product in products
                    if product.sch_max_capacity_qty
                ],
                target_date=plan.target_date,
            )
            self.env["sch.refill.plan.line"].create(
                [
                    {
                        "plan_id": plan.id,
                        "fridge_id": fridge_by_code[line.fridge_code].id,
                        "product_id": product_by_code[line.sku_code].id,
                        "forecast_qty": line.forecast_qty,
                        "safety_stock_qty": line.safety_stock_qty,
                        "usable_stock_qty": line.usable_stock_qty,
                        "on_hand_qty": line.on_hand_qty,
                        "recommended_qty": line.recommended_qty,
                        "capacity_qty": line.capacity_qty,
                        "reason": line.reason,
                    }
                    for line in lines
                    if line.fridge_code in fridge_by_code and line.sku_code in product_by_code
                ]
            )
            plan.write(
                {
                    "name": f"Refill plan {plan.target_date}",
                    "state": "ready",
                    "generated_at": fields.Datetime.now(),
                }
            )
        return True


class SchRefillPlanLine(models.Model):
    _name = "sch.refill.plan.line"
    _description = "Schrankerl Refill Plan Line"

    plan_id = fields.Many2one("sch.refill.plan", required=True, ondelete="cascade")
    fridge_id = fields.Many2one("sch.fridge", required=True)
    product_id = fields.Many2one("product.product", required=True)
    forecast_qty = fields.Float(readonly=True)
    safety_stock_qty = fields.Integer(readonly=True)
    usable_stock_qty = fields.Integer(readonly=True)
    on_hand_qty = fields.Integer(readonly=True)
    recommended_qty = fields.Integer(readonly=True)
    capacity_qty = fields.Integer(readonly=True)
    reason = fields.Char(readonly=True)


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    return fields.Datetime.to_datetime(value)
