from odoo import http
from odoo.http import request
import json
import base64
import logging

_logger = logging.getLogger(__name__)

class OdooAPIController(http.Controller):

    @http.route('/api_contact', auth="public", type="json", methods=['POST'], csrf=False)
    def contact_form(self, **post):
        try:
            # Charger les données de la requête
            data = json.loads(request.httprequest.data)
            name = data.get('name')
            email = data.get('email')
            fichier_bin_encoded = data.get('fichier_bin')  # Le fichier doit être encodé en base64

            # Valider les entrées
            if not name or not email:
                return {"status": "error", "message": "Missing required fields: 'name' and 'email'"}

            if not fichier_bin_encoded:
                return {"status": "error", "message": "Missing file field: 'fichier_bin'"}

            # Décoder le fichier base64
            try:
                fichier_bin = base64.b64decode(fichier_bin_encoded)
            except Exception as e:
                return {"status": "error", "message": f"Invalid file encoding: {str(e)}"}

            # Créer le partenaire avec le fichier
            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'fichier_bin': fichier_bin_encoded,  # Champ binaire
            })

            return {"status": "success", "partner_id": partner.id}
        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return {"status": "error", "message": str(e)}
