from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, time

class DailyAttendanceCombinedReport(models.AbstractModel):
    _name = "report.school_attendance.daily_attendance_combined"
    _description = "Rapport de Présence Combinée"

    @api.model
    def _get_report_values(self, docids, data=None):
        """Génère les valeurs pour le rapport QWeb"""
        # Récupère la feuille de présence actuelle
        current_sheet = self.env['daily.attendance'].browse(docids)
        
        if not current_sheet:
            raise ValidationError(_("Aucune feuille de présence sélectionnée!"))
        
        # Utilise la date et la classe de la feuille actuelle
        reference_date = current_sheet.date
        reference_class = current_sheet.standard_id
        
        # Récupère toutes les feuilles  pour cette date et classe
        all_feuilles = self.env['daily.attendance'].search([
            ('date', '=', reference_date),
            ('standard_id', '=', reference_class.id),
        ], order='start_time')  # Tri par heure de début
        
        # Récupère tous les étudiants de la classe
        all_student = self.env['student.student'].search([
            ('standard_id', '=', reference_class.id)
        ])
        
        students_data = []
        
        for student in all_student:
            student_courses = []
            
            for sheet in all_feuilles:
                # Trouve la ligne de présence de l'étudiant
                #daily.attendance.line: ligne de présence
                attendance_line = sheet.student_ids.filtered(
                    lambda l: l.stud_id == student
                )
                
                # Détermine le statut de présence
                if attendance_line:
                    status = _("Présent") if attendance_line.is_present else _("Absent")
                else:
                    status = _("Absent")
                
                # Formatage des heures
                start_time = self._float_to_time(sheet.start_time)
                end_time = self._float_to_time(sheet.end_time)
                
                student_courses.append({
                    'subject': sheet.subject_id.name or _("Non spécifié"),
                    'start_time': start_time,
                    'end_time': end_time,
                    'status': status,
                    'teacher': sheet.user_id.name or _("Non spécifié")
                })
            
            # Ajoute seulement les étudiants ayant des cours ce jour-là
            if student_courses:
                students_data.append({
                    'student': student,
                    'roll_no': student.roll_no,
                    'student_name': student.name or _("Nom non disponible"),
                    'courses': student_courses
                })
        
        return {
            'doc_ids': docids,
            'docs': current_sheet,
            'date': fields.Date.to_string(reference_date),
            'class_name': reference_class.name,
            'students_data': students_data,
            'company': self.env.user.company_id,
        }
    
    def _float_to_time(self, float_time):
        """Convertit un float (8.5) en string temps (08:30)"""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"