from odoo import http
from odoo.http import request
import json
import base64
import logging
import requests  # Importation de la bibliothèque requests

_logger = logging.getLogger(__name__)

class OdooAPIController(http.Controller):

    @http.route('/api_contact', auth="public", type="json", methods=['POST'], csrf=False)
    def contact_form(self, **post):
        try:
            # Charger les données de la requête envoyée par l'utilisateur
            data = json.loads(request.httprequest.data)
            name = data.get('name')
            email = data.get('email')
            fichier_bin_encoded = data.get('fichier_bin')  # Le fichier doit être encodé en base64

            # Validation des champs requis
            if not name or not email:
                return {"status": "error", "message": "Missing required fields: 'name' and 'email'"}

            if not fichier_bin_encoded:
                return {"status": "error", "message": "Missing file field: 'fichier_bin'"}

            # Décoder le fichier base64 (si nécessaire)
            try:
                fichier_bin = base64.b64decode(fichier_bin_encoded)
            except Exception as e:
                return {"status": "error", "message": f"Invalid file encoding: {str(e)}"}

            # Créer le partenaire dans Odoo (enregistrer dans la base de données)
            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'fichier_bin': fichier_bin_encoded,  # Champ binaire
            })

            # Données à envoyer vers l'API externe
            payload = {
                'name': name,
                'email': email,
                'fichier_bin': fichier_bin_encoded  # Fichier base64
            }

            # URL de l'API externe où envoyer les données
            external_api_url = "https://example.com/api/endpoint"  # Remplacez par l'URL de votre API externe

            # Effectuer la requête POST vers l'API externe
            response = requests.post(external_api_url, json=payload)

            # Vérifier la réponse de l'API externe
            if response.status_code == 200:
                return {"status": "success", "partner_id": partner.id, "message": "Data sent to external API successfully"}
            else:
                return {"status": "error", "message": f"Failed to send data to external API. Status code: {response.status_code}"}

        except Exception as e:
            _logger.error(f"Error occurred: {e}")
            return {"status": "error", "message": str(e)}
