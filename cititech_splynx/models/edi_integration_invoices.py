from datetime import datetime

from odoo import Command, fields, models


class EdiIntegrationCreditNotes(models.Model):
    _inherit = "edi.integration"

    type = fields.Selection(
        selection_add=[
            ("get_invoices_from_splynx_software", "Get invoices from Splynx software"),
            ("get_credit_notes_from_splynx_software", "Get credit notes from Splynx software"),
        ],
        ondelete={"get_invoices_from_splynx_software": "cascade", "get_credit_notes_from_splynx_software": "cascade"},
    )

    def _get_in_content(self):
        params = {
            "main_attributes[date_updated][0]": ">=",
            "main_attributes[date_updated][1]": self.lastcall.strftime("%Y-%m-%d"),
        }
        if self.type not in ["get_credit_notes_from_splynx_software", "get_invoices_from_splynx_software"]:
            return super()._get_in_content()
        elif self.type == "get_invoices_from_splynx_software":
            return self.connection_id._fetch_synchronizations(path="admin/finance/invoices", params=params)
        else:
            return self.connection_id._fetch_synchronizations(path="admin/finance/credit-notes", params=params)

    def _process_content(self, data):
        if self.type not in ["get_credit_notes_from_splynx_software", "get_invoices_from_splynx_software"]:
            return super()._process_content(data)
        is_credit_note = self.type == "get_credit_notes_from_splynx_software"
        return self._process_movements(data, "refunded" if is_credit_note else "paid", is_credit_note)

    def _get_synchronization_name_in(self, data):
        self.ensure_one()
        if self.type not in ["get_invoices_from_splynx_software", "get_credit_notes_from_splynx_software"]:
            return super()._get_synchronization_name_in(data)
        elif self.type == "get_invoices_from_splynx_software":
            entity_type = "Invoice"
        else:
            entity_type = "Credit Note"
        return f"{entity_type} - {fields.Datetime.now()}: {' '.join([d.get('id') for d in data])}"

    def _process_movements(self, data, paid_status, is_credit_note):
        self.ensure_one()
        movement_data = data[0]
        company_id = self.company_id or self.env.company
        if is_credit_note:
            invoice_id = movement_data.get("invoicesId")
            invoices = (
                self.env["account.move"]
                .search([("splynx_reference", "=", invoice_id)])
                .filtered(lambda invoice: invoice.is_invoice(True))
            )
            invoice = invoices[0] if invoices else invoices
            if not invoice:
                return "fail"
        movement_id = movement_data.get("id")
        movements = (
            self.env["account.move"]
            .search([("splynx_reference", "=", movement_id)])
            .filtered(lambda movement: movement.is_outbound(True) if is_credit_note else movement.is_invoice(True))
        )
        movement = movements[0] if movements else movements

        if not movement:
            customer_id = movement_data.get("customer_id")
            customer = self.env["res.partner"].search([("splynx_reference", "=", customer_id)], limit=1)
            if not customer:
                return "fail"
            movement_date = datetime.strptime(movement_data.get("date_created"), "%Y-%m-%d")
            movement_due_date = datetime.strptime(
                movement_data.get("date_till", movement_data.get("date_created")), "%Y-%m-%d"
            )
            account_move_lines = []
            movement_lines = movement_data.get("items")
            for movement_line in movement_lines:
                description = movement_line.get("description")
                quantity = movement_line.get("quantity")
                price = float(movement_line.get("price", 0.0))
                tax = movement_line.get("tax")
                tax_id = False
                if tax:
                    tax_id = self.env["account.tax"].search(
                        [("type_tax_use", "=", "sale"), ("amount", "=", tax)], limit=1
                    )
                    if not tax_id:
                        return "fail"
                account_move_lines.append(
                    Command.create(
                        {
                            "name": description,
                            "quantity": quantity,
                            "price_unit": price,
                            "tax_ids": [Command.link(tax_id.id)],
                            "account_id": company_id.splynx_account_id.id,
                        }
                    )
                )

            movement = self.env["account.move"].create(
                {
                    "partner_id": customer.id,
                    "splynx_reference": movement_id,
                    "invoice_date": movement_date,
                    "invoice_date_due": movement_due_date,
                    "line_ids": account_move_lines,
                    "journal_id": self.env.ref("cititech_splynx.splynx_account_journal").id,
                    "move_type": "out_refund" if is_credit_note else "out_invoice",
                }
            )
            movement.action_post()
        movement_paid = movement_data.get("status") == paid_status
        if movement_paid and movement.payment_state != "paid":
            payment_date = datetime.strptime(movement_data.get("date_payment"), "%Y-%m-%d")
            register_payment = (
                self.env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=[movement.id])
                .create({"payment_date": payment_date})
            )

            register_payment._create_payments()

        return "done"
