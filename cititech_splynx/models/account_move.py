from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    splynx_reference = fields.Char()
