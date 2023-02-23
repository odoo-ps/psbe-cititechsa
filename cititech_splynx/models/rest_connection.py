from datetime import datetime
from urllib import parse

import requests

from odoo import _, fields, models


class RESTConnectionApi(models.Model):
    _inherit = "edi.connection"
    _description = "EDI Connection"

    type = fields.Selection(selection_add=[("rest", "Rest API")], ondelete={"rest": "cascade"})
    access_token = fields.Char(invisible=True)
    access_token_expiration = fields.Datetime(invisible=True)
    refresh_token = fields.Char(invisible=True)
    refresh_token_expiration = fields.Datetime(invisible=True)

    # def _send_synchronization(self, filename, content, *args, **kwargs):
    #     self.ensure_one()
    #     if not self.type == "rest":
    #         return super()._send_synchronization(filename, content, *args, **kwargs)
    #     return self.post(content)

    def _fetch_synchronizations(self, *args, **kwargs):
        self.ensure_one()
        if not self.type == "rest":
            return super()._fetch_synchronizations(*args, **kwargs)
        if not kwargs.get("path"):
            raise ValueError(_("Please provide a path"))
        return self.get(kwargs.get("path"), params=kwargs.get("params", False))

    def _encode_params(self, params):
        encoded_params = []
        for key, value in params.items():
            encoded_params.append(f"{key}={parse.quote(value)}")
        return encoded_params

    def _create_url(self, path, params):
        config = self._read_configuration()
        host = config.get("host")
        url = f"{host}/{path}"
        if params:
            url = f"{url}?{'&'.join(self._encode_params(params))}"
        return url

    def _get_auth_header(self, force=False):
        token = self._get_auth_token(force)
        return {"Authorization": f"Splynx-EA (access_token={token})"}

    def _set_auth_token(self, json):
        self.access_token = json.get("access_token")
        self.access_token_expiration = datetime.fromtimestamp(json.get("access_token_expiration"))
        self.refresh_token = json.get("refresh_token")
        self.refresh_token_expiration = datetime.fromtimestamp(json.get("refresh_token_expiration"))

    def _get_auth_token(self, force=False):
        config = self._read_configuration()
        if self.access_token and fields.Datetime.now() < self.access_token_expiration and not force:
            return self.access_token
        elif self.refresh_token and fields.Datetime.now() < self.refresh_token_expiration and not force:
            url = f"{config.get('host')}/admin/auth/tokens/{self.refresh_token}"
            response = requests.get(url)
            json = response.json()
            self._set_auth_token(json)
            return self.access_token
        else:
            url = f"{config.get('host')}/admin/auth/tokens"
            user = config["user"]
            passwd = config["password"]
            body = {"auth_type": "admin", "login": user, "password": passwd}
            response = requests.post(url, json=body)
            json = response.json()
            self._set_auth_token(json)
            return self.access_token

    def get(self, path, params):
        self.ensure_one()
        response = requests.get(url=self._create_url(path, params), headers=self._get_auth_header())
        return response.json()
