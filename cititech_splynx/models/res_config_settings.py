from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    splynx_account_id = fields.Many2one("account.account", related="company_id.splynx_account_id", readonly=False)
    splynx_payment_journal_id = fields.Many2one(
        "account.journal", related="company_id.splynx_payment_journal_id", readonly=False
    )
