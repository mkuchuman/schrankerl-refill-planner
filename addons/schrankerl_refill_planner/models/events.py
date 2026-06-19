from odoo import fields, models


class SchSaleEvent(models.Model):
    _name = "sch.sale.event"
    _description = "Schrankerl Sale Event"
    _order = "event_ts desc"

    event_id = fields.Char(required=True, index=True)
    event_ts = fields.Datetime(required=True)
    fridge_id = fields.Many2one("sch.fridge", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    qty = fields.Integer(required=True, default=1)
    unit_price = fields.Float()

    _sql_constraints = [
        ("event_id_unique", "unique(event_id)", "Sale event ID must be unique."),
    ]


class SchInventorySnapshot(models.Model):
    _name = "sch.inventory.snapshot"
    _description = "Schrankerl Inventory Snapshot"
    _order = "snapshot_ts desc"

    snapshot_ts = fields.Datetime(required=True)
    fridge_id = fields.Many2one("sch.fridge", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    on_hand_qty = fields.Integer(required=True)
    days_to_expiry = fields.Integer()
    data_source = fields.Char(default="csv")
