from odoo import fields, models


class EdiIntegration(models.Model):
    _inherit = "edi.integration"

    type = fields.Selection(
        selection_add=[
            ("get_invoices_from_splynx_software", "Get invoices from Splynx software"),
            ("get_customers_from_splynx_software", "Get customers from Splynx software"),
        ],
        ondelete={"get_invoices_from_splynx_software": "cascade", "get_customers_from_splynx_software": "cascade"},
    )

    def _get_in_content(self):
        params = {
            "main_attributes[date_add][0]": ">=",
            "main_attributes[date_add][1]": self.lastcall.strftime("%Y-%m-%d"),
        }
        if self.type not in ["get_invoices_from_splynx_software", "get_customers_from_splynx_software"]:
            return super()._get_in_content()
        return self.connection_id._fetch_synchronizations(path="admin/customers/customer", params=params)

    def _process_content(self, data):
        if self.type not in ["get_invoices_from_splynx_software", "get_customers_from_splynx_software"]:
            return super()._process_content(data)
        return self._process_customers(data)

    def _create_synchronization_in(self, data):
        self.ensure_one()
        vals = {
            "integration_id": self.id,
            "name": self._get_synchronization_name_in(data),
            "synchronization_date": fields.Datetime.now(),
        }
        if self.write_content_on_sync:
            vals["content"] = data
        return self.env["edi.synchronization"].create(vals)

    def _get_synchronization_name_in(self, data):
        self.ensure_one()
        if self.type != "get_customers_from_splynx_software":
            return super()._get_synchronization_name_in(data)
        return f"Customers - {fields.Datetime.now()}: {' '.join([d.get('id') for d in data])}"

    def _process_customers(self, data):
        self.ensure_one()
        customer_data = data[0]
        customer_id = customer_data.get("id")
        customer_name = customer_data.get("name")
        customer = self.env["res.partner"].search(
            ["|", ("splynx_reference", "=", customer_id), ("name", "=", customer_name)], limit=1
        )
        if not customer:
            return "fail"

        customer.splynx_reference = customer_id
        return "done"
