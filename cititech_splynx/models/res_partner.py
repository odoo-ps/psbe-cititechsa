from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    splynx_reference = fields.Char()
