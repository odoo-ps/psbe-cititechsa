from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    splynx_account_id = fields.Many2one("account.account")
    splynx_payment_journal_id = fields.Many2one("account.journal")
