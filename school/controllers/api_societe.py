 @http.route('/api/employee_companies', type='json', auth='public', methods=['POST'])
    def create_employee_companies(self, **post):
        try:
            # Charger les données JSON de la requête
            data = json.loads(request.httprequest.data)
    
            # Récupérer les informations
            name = data.get('name')
            email = data.get('email')
            phone = data.get('phone')
            street = data.get('street')
            zip = data.get('zip')
            city = data.get('city')
            user_type = data.get('user_type')
            fcm_token = data.get('fcm_token')
            remember_token = data.get('remember_token')
            created_at = data.get('created_at')
            updated_at = data.get('updated_at')
            pm_type = data.get('pm_type')
            pm_last_four = data.get('pm_last_four')
            trial_ends_at = data.get('trial_ends_at')
            avatar = data.get('avatar')
            last_name = data.get('last_name')
            first_name = data.get('first_name')
    
            deleted_at = data.get('deleted_at')
            step = data.get('step')
            car_id = data.get('car_id')
            verify_data = data.get('verify_data')
            code_reference = data.get('code_reference')
            type_company = data.get('type_company')
            nature_company = data.get('nature_company')
            vat_number = data.get('vat_number')
            is_active = data.get('is_active', False)
    
            is_company = data.get('is_company', True)
            is_employee_company = data.get('is_employee_company', True)
    
            # Vérification des champs obligatoires
            if not name:
                return {"status": "error", "message": "Le champ 'name' est obligatoire."}
            
            if not first_name or not last_name:
                return {"status": "error", "message": "Les champs 'first_name' et 'last_name' sont obligatoires pour une société d'employé."}
    
            # Concatenation du nom pour le partenaire (société)
            full_name = f"{first_name} {last_name}"
    
            # Création du partenaire (société)
            new_partner = request.env['res.partner'].sudo().create({
                'name': full_name,  # Utilisation du full_name pour le nom
                'email': email,
                'phone': phone,
                'street': street,
                'zip': zip,
                'city': city,
                'user_type': user_type,
                'fcm_token': fcm_token,
                'remember_token': remember_token,
                'created_at': created_at,
                'updated_at': updated_at,
                'pm_type': pm_type,
                'pm_last_four': pm_last_four,
                'trial_ends_at': trial_ends_at,
                'avatar': avatar,
                'last_name': last_name,
                'first_name': first_name,
                'deleted_at': deleted_at,
                'step': step,
                'car_id': car_id,
                'verify_data': verify_data,
                'code_reference': code_reference,
                'type_company': type_company,
                'nature_company': nature_company,
                'vat_number': vat_number,
                'is_active': is_active,
                'is_company': is_company,
                'is_employee_company': is_employee_company,
            })
    
            _logger.info(f"Société créée avec succès: {new_partner.id}")
    
            return {
                "status": "success",
                "message": "Société créée avec succès",
                "partner_id": new_partner.id
            }
    
        except Exception as e:
            _logger.error(f"Erreur lors de la création de la société: {e}")
            return {"status": "error", "message": str(e)}
















#Endpoint pour créer une société de transport
@http.route('/api/societes_transport', auth="public", type="json", methods=['POST'], csrf=False)
def create_societes_transport(self, **post):
    try:
        # Charger les données JSON de la requête
        data = json.loads(request.httprequest.data)

        # Récupérer les données du partenaire
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        name = f"{first_name} {last_name}"  # Concatenate first_name and last_name
        
        email = data.get('email')
        phone = data.get('phone')
        street = data.get('street')
        zip = data.get('zip')
        city = data.get('city')
        user_type = data.get('user_type')
        fcm_token = data.get('fcm_token')
        remember_token = data.get('remember_token')
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')
        pm_type = data.get('pm_type')
        pm_last_four = data.get('pm_last_four')
        trial_ends_at = data.get('trial_ends_at')
        avatar = data.get('avatar')

        deleted_at = data.get('deleted_at')
        step = data.get('step')
        car_id = data.get('car_id')
        verify_data = data.get('verify_data')
        code_reference = data.get('code_reference')
        type_company = data.get('type_company')
        nature_company = data.get('nature_company')
        vat_number = data.get('vat_number')
        is_active = data.get('is_active', False)

        # Champs spécifiques à la société de transport
        is_company = data.get('is_company', True)
        is_transport_company = data.get('is_transport_company', True)

        # Vérification des champs obligatoires
        if not name:
            return {"status": "error", "message": "Le champ 'name' est obligatoire."}

        # Création du partenaire (société de transport)
        new_partner = request.env['res.partner'].sudo().create({
            'name': name,  # Utilisation de first_name et last_name pour le nom
            'email': email,
            'phone': phone,
            'street': street,
            'zip': zip,
            'city': city,
            'user_type': user_type,
            'fcm_token': fcm_token,
            'remember_token': remember_token,
            'created_at': created_at,
            'updated_at': updated_at,
            'pm_type': pm_type,
            'pm_last_four': pm_last_four,
            'trial_ends_at': trial_ends_at,
            'avatar': avatar,
            'deleted_at': deleted_at,
            'step': step,
            'car_id': car_id,
            'verify_data': verify_data,
            'code_reference': code_reference,
            'type_company': type_company,
            'nature_company': nature_company,
            'vat_number': vat_number,
            'is_active': is_active,
            
            'is_company': is_company,
            'is_transport_company': is_transport_company,
        })

        _logger.info(f"Société de transport créée avec succès: {new_partner.id}")

        return {
            "status": "success",
            "message": "Société de transport créée avec succès",
            "partner_id": new_partner.id
        }

    except Exception as e:
        _logger.error(f"Erreur lors de la création de la société de transport: {e}")
        return {"status": "error", "message": str(e)}




#Endpoint pour créer une société de transport
@http.route('/api/societes_transport', auth="public", type="json", methods=['POST'], csrf=False)
def create_societes_transport(self, **post):
    try:
        # Charger les données JSON de la requête
        data = json.loads(request.httprequest.data)

        # Récupérer les données du partenaire
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        name = f"{first_name} {last_name}"  # Concatenate first_name and last_name
        
        email = data.get('email')
        phone = data.get('phone')
        street = data.get('street')
        zip = data.get('zip')
        city = data.get('city')
        user_type = data.get('user_type')
        fcm_token = data.get('fcm_token')
        remember_token = data.get('remember_token')
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')
        pm_type = data.get('pm_type')
        pm_last_four = data.get('pm_last_four')
        trial_ends_at = data.get('trial_ends_at')
        avatar = data.get('avatar')

        deleted_at = data.get('deleted_at')
        step = data.get('step')
        car_id = data.get('car_id')
        verify_data = data.get('verify_data')
        code_reference = data.get('code_reference')
        type_company = data.get('type_company')
        nature_company = data.get('nature_company')
        vat_number = data.get('vat_number')
        is_active = data.get('is_active', False)

        # Champs spécifiques à la société de transport
        is_company = data.get('is_company', True)
        is_transport_company = data.get('is_transport_company', True)

        # Vérification des champs obligatoires
        if not name:
            return {"status": "error", "message": "Le champ 'name' est obligatoire."}

        # Création du partenaire (société de transport)
        new_partner = request.env['res.partner'].sudo().create({
            'name': name,  # Utilisation de first_name et last_name pour le nom
            'email': email,
            'phone': phone,
            'street': street,
            'zip': zip,
            'city': city,
            'user_type': user_type,
            'fcm_token': fcm_token,
            'remember_token': remember_token,
            'created_at': created_at,
            'updated_at': updated_at,
            'pm_type': pm_type,
            'pm_last_four': pm_last_four,
            'trial_ends_at': trial_ends_at,
            'avatar': avatar,
            'deleted_at': deleted_at,
            'step': step,
            'car_id': car_id,
            'verify_data': verify_data,
            'code_reference': code_reference,
            'type_company': type_company,
            'nature_company': nature_company,
            'vat_number': vat_number,
            'is_active': is_active,
            
            'is_company': is_company,
            'is_transport_company': is_transport_company,
        })

        _logger.info(f"Société de transport créée avec succès: {new_partner.id}")

        return {
            "status": "success",
            "message": "Société de transport créée avec succès",
            "partner_id": new_partner.id
        }

    except Exception as e:
        _logger.error(f"Erreur lors de la création de la société de transport: {e}")
        return {"status": "error", "message": str(e)}
