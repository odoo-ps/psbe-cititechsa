{
    "name": "Cititech Splynx",
    "summary": """Splynx integration""",
    "version": "16.0.1.0.0",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": ["edi_base", "account"],
    "data": [
        "data/account_journal.xml",
        "data/edi_connection.xml",
        "data/edi_integration.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner.xml",
        "views/account_move.xml",
    ],
    "odoo_task_ids": [3164310],
}
