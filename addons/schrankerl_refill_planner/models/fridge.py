from odoo import fields, models


class SchFridge(models.Model):
    _name = "sch.fridge"
    _description = "Schrankerl Fridge"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    partner_id = fields.Many2one("res.partner", string="Client")
    location_id = fields.Many2one("stock.location", string="Stock Location")
    active = fields.Boolean(default=True)
    notes = fields.Text()
