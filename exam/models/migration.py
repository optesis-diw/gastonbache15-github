from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import xmlrpc.client
import requests
from datetime import datetime
import time

_logger = logging.getLogger(__name__)

class ExamResultMigration(models.TransientModel):
    _name = 'exam.result.migration'
    _description = 'Migration des résultats d\'examen entre plateformes Odoo'

    # Configuration de la source Odoo externe
    source_url = fields.Char('URL Source Odoo', required=True, default='http://localhost:7097')
    source_db = fields.Char('Base de données Source', required=True, default='prod_gaston_bachelard')
    source_username = fields.Char('Utilisateur Source', required=True, default='admin')
    source_password = fields.Char('Mot de passe Source', required=True, default='D@k@r2029')
    
    # Filtres de migration
    academic_year_id = fields.Many2one('academic.year', 'Année Académique')
    session = fields.Selection([
        ('premier_semestre', '1er Session'),
        ('second_semestre', '2e Session'), 
        ('troisieme_semestre', '3e Session'),
    ], string="Session")
    standard_id = fields.Many2one('school.standard', 'Classe')
    
    # Options de connexion (non stockées)
    verify_ssl = fields.Boolean('Vérifier SSL', default=False, store=False)
    timeout = fields.Integer('Timeout (secondes)', default=30, store=False)
    
    # Statistiques
    migrated_count = fields.Integer('Résultats Migrés', readonly=True)
    error_count = fields.Integer('Erreurs', readonly=True)
    connection_status = fields.Char('Statut Connexion', readonly=True)

    def _test_connection_simple(self, url, db, username, password):
        """Test de connexion simple"""
        try:
            # Nettoyer l'URL
            source_url = url.strip()
            if not source_url.startswith('http'):
                source_url = 'http://' + source_url
            
            # Essayer différents ports
            ports_to_try = [7097, 8069, 8070, 8071, 8072]
            
            for port in ports_to_try:
                # Construire l'URL de test
                if 'localhost' in source_url or '127.0.0.1' in source_url:
                    test_url = f"http://localhost:{port}"
                else:
                    # Pour les URLs distantes, utiliser le port spécifié
                    test_url = source_url
                    if ':' not in test_url.split('//')[1].split('/')[0]:
                        test_url = f"{test_url}:{port}"
                
                try:
                    _logger.info(f"Test de connexion à {test_url}")
                    common = xmlrpc.client.ServerProxy(f'{test_url}/xmlrpc/2/common', allow_none=True)
                    
                    # Tester la connexion
                    uid = common.authenticate(db, username, password, {})
                    
                    if uid:
                        _logger.info(f"Connexion réussie à {test_url}")
                        return uid, test_url
                        
                except Exception as e:
                    _logger.debug(f"Échec connexion à {test_url}: {str(e)}")
                    continue
            
            # Essayer l'URL originale sans modification de port
            try:
                common = xmlrpc.client.ServerProxy(f'{source_url}/xmlrpc/2/common', allow_none=True)
                uid = common.authenticate(db, username, password, {})
                if uid:
                    _logger.info(f"Connexion réussie à {source_url}")
                    return uid, source_url
            except Exception as e:
                _logger.debug(f"Échec connexion à {source_url}: {str(e)}")
            
            return None, None
            
        except Exception as e:
            _logger.error(f"Erreur test connexion: {str(e)}")
            return None, None

    def action_test_connection(self):
        """Tester la connexion avec diagnostics détaillés"""
        try:
            # Utiliser une méthode simplifiée pour éviter les problèmes de champs
            uid, working_url = self._test_connection_simple(
                self.source_url, 
                self.source_db, 
                self.source_username, 
                self.source_password
            )
            
            if not uid:
                error_message = f"""
                <h3>❌ Test de Connexion Échoué</h3>
                <p><b>URL testée:</b> {self.source_url}</p>
                <p><b>Base de données:</b> {self.source_db}</p>
                <p><b>Utilisateur:</b> {self.source_username}</p>
                <p><b>Erreur:</b> Impossible de se connecter à l'instance Odoo source</p>
                <p><b>Vérifiez:</b></p>
                <ul>
                <li>L'instance Odoo source est démarrée</li>
                <li>Le port est correct (7097, 8069, etc.)</li>
                <li>La base de données existe</li>
                <li>Les identifiants sont valides</li>
                <li>Le service xmlrpc est activé</li>
                </ul>
                """
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Test de Connexion Échoué',
                        'message': error_message,
                        'type': 'danger',
                        'sticky': True,
                    }
                }
            
            # Connexion réussie - récupérer des informations
            models = xmlrpc.client.ServerProxy(f'{working_url}/xmlrpc/2/object')
            
            # Compter les enregistrements de base
            exam_count = 0
            student_count = 0
            
            try:
                exam_count = models.execute_kw(
                    self.source_db, uid, self.source_password,
                    'exam.result', 'search_count', [[]]
                )
            except:
                exam_count = "Non accessible"
            
            try:
                student_count = models.execute_kw(
                    self.source_db, uid, self.source_password,
                    'student.student', 'search_count', [[]]
                )
            except:
                student_count = "Non accessible"
            
            success_message = f"""
            <h3>✅ Test de Connexion Réussi</h3>
            <p><b>URL:</b> {working_url}</p>
            <p><b>Base de données:</b> {self.source_db}</p>
            <p><b>Résultats d'examen:</b> {exam_count}</p>
            <p><b>Étudiants:</b> {student_count}</p>
            <p><b>Statut:</b> Connexion établie avec succès</p>
            """
            
            # Mettre à jour le statut de connexion
            self.write({
                'connection_status': f"Connecté à {working_url}"
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test de Connexion Réussi',
                    'message': success_message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            error_message = f"""
            <h3>❌ Erreur Inattendue</h3>
            <p><b>Erreur:</b> {str(e)}</p>
            <p>Veuillez contacter l'administrateur système.</p>
            """
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur Inattendue',
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _get_source_connection(self):
        """Établir la connexion avec la source Odoo"""
        try:
            uid, working_url = self._test_connection_simple(
                self.source_url, 
                self.source_db, 
                self.source_username, 
                self.source_password
            )
            
            if not uid:
                raise ValidationError(_(
                    "Impossible de se connecter à la source Odoo. "
                    "Vérifiez l'URL, le port et les identifiants."
                ))
            
            models = xmlrpc.client.ServerProxy(f'{working_url}/xmlrpc/2/object')
            
            return uid, models, working_url
            
        except Exception as e:
            raise ValidationError(_(f"Erreur de connexion: {str(e)}"))

    def _migrate_data_safely(self, models, uid, model, method, *args, **kwargs):
        """Wrapper sécurisé pour les appels RPC"""
        try:
            return models.execute_kw(self.source_db, uid, self.source_password,
                                   model, method, *args, **kwargs)
        except Exception as e:
            _logger.error(f"Erreur RPC {model}.{method}: {str(e)}")
            return None

    def action_migrate_results(self):
        """Lancer la migration des résultats avec gestion de concurrence"""
        _logger.info("Début de la migration des résultats d'examen")
        
        try:
            # Établir la connexion
            uid, models, working_url = self._get_source_connection()
            
            # Construction du domaine de recherche simple
            domain = []
            if self.session:
                domain.append(('session', '=', self.session))
            
            # Limiter le nombre de résultats pour les tests
            limit = 100  # Commencer avec un petit nombre pour les tests
            
            _logger.info(f"Domaine de recherche: {domain}, Limite: {limit}")
            
            # Récupérer les résultats de la source avec limite
            source_results = self._migrate_data_safely(
                models, uid, 'exam.result', 'search_read',
                [domain],
                {
                    'fields': [
                        'id', 'student_id', 's_exam_ids', 'standard_id', 
                        'session', 'total', 'percentage', 'moyenne', 
                        'result', 'grade', 'academic_year', 'roll_no'
                    ],
                    'limit': limit
                }
            ) or []
            
            _logger.info(f"Found {len(source_results)} results to migrate")
            
            if not source_results:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Aucun résultat',
                        'message': 'Aucun résultat trouvé avec les critères sélectionnés.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            
            migrated_count = 0
            error_count = 0
            
            # Utiliser une transaction séparée pour chaque résultat pour éviter les conflits
            for index, source_result in enumerate(source_results):
                try:
                    # Petite pause pour réduire la charge
                    if index % 10 == 0:
                        time.sleep(0.1)
                    
                    # Créer un nouveau curseur pour chaque résultat
                    with self.env.registry.cursor() as new_cr:
                        new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                        result = self._migrate_single_result_with_env(source_result, uid, models, new_env)
                        
                        if result:
                            migrated_count += 1
                            # Commit après chaque résultat réussi
                            new_cr.commit()
                        else:
                            error_count += 1
                            new_cr.rollback()
                            
                except Exception as e:
                    error_count += 1
                    _logger.error(f"Erreur migration résultat {source_result.get('id')}: {str(e)}")
                    # Rollback en cas d'erreur
                    try:
                        new_cr.rollback()
                    except:
                        pass
            
            # Mettre à jour les statistiques dans la transaction principale
            self.write({
                'migrated_count': migrated_count,
                'error_count': error_count
            })
            
            # Afficher le rapport
            return self._show_migration_report(migrated_count, error_count)
            
        except Exception as e:
            _logger.error(f"Erreur générale de migration: {str(e)}")
            raise ValidationError(_(f"Erreur de migration: {str(e)}"))

    def _migrate_single_result_with_env(self, source_result, uid, models, env):
        """Migrer un seul résultat avec un environnement spécifique"""
        try:
            # Récupérer les données détaillées de l'étudiant
            student_data = self._migrate_data_safely(
                models, uid, 'student.student', 'read',
                [source_result['student_id'][0]] if source_result.get('student_id') else [],
                {'fields': ['id', 'name', 'pid', 'roll_no']}
            )
            
            if not student_data:
                _logger.warning(f"Étudiant non trouvé pour le résultat {source_result.get('id')}")
                return None
            
            student_data = student_data[0]
            
            # Récupérer les données de l'examen
            exam_data = self._migrate_data_safely(
                models, uid, 'exam.exam', 'read',
                [source_result['s_exam_ids'][0]] if source_result.get('s_exam_ids') else [],
                {'fields': ['id', 'name', 'exam_code', 'session']}
            )
            
            if not exam_data:
                _logger.warning(f"Examen non trouvé pour le résultat {source_result.get('id')}")
                return None
            
            exam_data = exam_data[0]
            
            # Récupérer les données des matières
            subject_data = self._migrate_data_safely(
                models, uid, 'exam.subject', 'search_read',
                [[('exam_id', '=', source_result['id'])]],
                {'fields': [
                    'subject_id', 'devoir_1', 'devoir_2', 'devoir_3',
                    'composition', 'moyenne_provisoire', 'obtain_marks', 
                    'grade', 'coefficient'
                ]}
            ) or []
            
            # Trouver ou créer l'étudiant
            student = self._find_or_create_student_with_env(student_data, env)
            
            # Trouver ou créer l'examen
            exam = self._find_or_create_exam_with_env(exam_data, env)
            
            # Créer le résultat
            return self._create_exam_result_with_env(source_result, student, exam, subject_data, env)
            
        except Exception as e:
            _logger.error(f"Erreur migration résultat individuel: {str(e)}")
            return None

    def _find_or_create_student_with_env(self, source_student_data, env):
        """Trouver ou créer l'étudiant avec un environnement spécifique"""
        student_obj = env['student.student']
        
        # Recherche par PID ou nom
        domain = []
        if source_student_data.get('pid'):
            domain = [('pid', '=', source_student_data.get('pid'))]
        elif source_student_data.get('name'):
            domain = [('name', '=ilike', source_student_data.get('name'))]
        else:
            return None
        
        student = student_obj.search(domain, limit=1)
        
        if not student:
            # Créer un nouvel étudiant si non trouvé
            student_vals = {
                'name': source_student_data.get('name'),
                'pid': source_student_data.get('pid'),
                'standard_id': self.standard_id.id if self.standard_id else False,
                'year': self.academic_year_id.id if self.academic_year_id else False,
                'state': 'done',
                'roll_no': source_student_data.get('roll_no', 0),
            }
            student = student_obj.create(student_vals)
            _logger.info(f"Étudiant créé: {student.name}")
        
        return student

    def _find_or_create_exam_with_env(self, source_exam_data, env):
        """Trouver ou créer l'examen avec un environnement spécifique"""
        exam_obj = env['exam.exam']
        
        exam = exam_obj.search([
            ('exam_code', '=', source_exam_data.get('exam_code'))
        ], limit=1)
        
        if not exam:
            exam_vals = {
                'name': source_exam_data.get('name'),
                'exam_code': source_exam_data.get('exam_code'),
                'standard_id': self.standard_id.id if self.standard_id else False,
                'academic_year': self.academic_year_id.id if self.academic_year_id else False,
                'session': source_exam_data.get('session', self.session),
                'state': 'finished',
            }
            exam = exam_obj.create(exam_vals)
            _logger.info(f"Examen créé: {exam.name}")
        
        return exam

    def _create_exam_result_with_env(self, source_result_data, student, exam, subject_data, env):
        """Créer le résultat d'examen avec un environnement spécifique"""
        result_obj = env['exam.result']
        
        # Vérifier si le résultat existe déjà
        existing_result = result_obj.search([
            ('student_id', '=', student.id),
            ('s_exam_ids', '=', exam.id),
            ('session', '=', source_result_data.get('session'))
        ], limit=1)
        
        result_vals = {
            'student_id': student.id,
            's_exam_ids': exam.id,
            'standard_id': self.standard_id.id if self.standard_id else False,
            'roll_no': student.roll_no or source_result_data.get('roll_no', 0),
            'session': source_result_data.get('session'),
            'academic_year': self.academic_year_id.id if self.academic_year_id else False,
            'total': source_result_data.get('total', 0),
            'percentage': source_result_data.get('percentage', 0),
            'moyenne': source_result_data.get('moyenne', 0),
            'result': source_result_data.get('result', 'Fail'),
            'grade': source_result_data.get('grade', ''),
            'state': 'draft',
        }
        
        if existing_result:
            existing_result.write(result_vals)
            result = existing_result
        else:
            result = result_obj.create(result_vals)
        
        # Migrer les matières si nécessaire
        if subject_data:
            self._create_exam_subjects_with_env(result, subject_data, env)
        
        _logger.info(f"Résultat migré: {student.name} - {exam.name}")
        return result

    def _create_exam_subjects_with_env(self, exam_result, source_subjects_data, env):
        """Créer les matières d'examen avec un environnement spécifique"""
        subject_obj = env['exam.subject']
        
        for source_subject in source_subjects_data:
            # Trouver la matière
            subject_id = self._find_or_create_subject_with_env(source_subject.get('subject_id'), env)
            if not subject_id:
                continue
                
            subject_vals = {
                'exam_id': exam_result.id,
                'subject_id': subject_id.id,
                'devoir_1': source_subject.get('devoir_1', 0),
                'devoir_2': source_subject.get('devoir_2', 0),
                'devoir_3': source_subject.get('devoir_3', 0),
                'composition': source_subject.get('composition', 0),
                'moyenne_provisoire': source_subject.get('moyenne_provisoire', 0),
                'obtain_marks': source_subject.get('obtain_marks', 0),
                'grade': source_subject.get('grade', ''),
                'coefficient': source_subject.get('coefficient', 1),
            }
            
            # Chercher si la matière existe déjà
            existing_subject = subject_obj.search([
                ('exam_id', '=', exam_result.id),
                ('subject_id', '=', subject_id.id)
            ], limit=1)
            
            if existing_subject:
                existing_subject.write(subject_vals)
            else:
                subject_obj.create(subject_vals)

    def _find_or_create_subject_with_env(self, source_subject_info, env):
        """Trouver ou créer une matière avec un environnement spécifique"""
        subject_obj = env['subject.subject']
        
        if isinstance(source_subject_info, list) and len(source_subject_info) == 2:
            subject_name = source_subject_info[1]
            subject_code = f"SUBJ_{source_subject_info[0]}"
        else:
            subject_name = "Matière Migrée"
            subject_code = f"SUBJ_{source_subject_info}"
        
        subject = subject_obj.search([
            ('name', '=ilike', subject_name)
        ], limit=1)
        
        if not subject:
            subject_vals = {
                'name': subject_name,
                'code': subject_code,
            }
            subject = subject_obj.create(subject_vals)
        
        return subject

    def _show_migration_report(self, migrated, errors):
        """Afficher le rapport de migration"""
        message_type = 'success' if errors == 0 else 'warning'
        
        message = f"""
        <h3>Migration Terminée</h3>
        <p><b>✅ Résultats migrés:</b> {migrated}</p>
        <p><b>❌ Erreurs:</b> {errors}</p>
        <p><b>📊 Total traités:</b> {migrated + errors}</p>
        """
        
        if migrated + errors > 0:
            success_rate = (migrated/(migrated+errors))*100
            message += f'<p><b>🎯 Taux de succès:</b> {success_rate:.1f}%</p>'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rapport de Migration',
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }