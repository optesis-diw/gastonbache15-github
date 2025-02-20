from odoo import models
from odoo.http import request
from werkzeug.exceptions import BadRequest
import logging

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_api_auth(cls):
        # Retrieve the API key from the Authorization header
        api_key = request.httprequest.headers.get("Authorization")
        
        if not api_key:
            _logger.error("Authorization header missing.")
            raise BadRequest("Authorization header with API key missing")

        # Validate the API key
        user_id = request.env["res.users.apikeys"]._check_credentials(scope="rpc", key=api_key)
        
        if not user_id:
            _logger.error("Invalid API key.")
            raise BadRequest("API key invalid")

        # Set the user context for the request
        request.uid = user_id
