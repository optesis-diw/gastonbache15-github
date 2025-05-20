from odoo import _, api, models
from odoo.exceptions import ValidationError

class BatchExamReport(models.AbstractModel):
    _name = "report.exam.exam_exam_batch"
    _description = "Batch wise Exam Result"

    def get_student_results(self, exam):
        """Method to get student results in the required format"""
        result_obj = self.env["exam.result"]
        exam_result_rec = result_obj.search([("s_exam_ids", "=", exam.id)])
        
        all_subjects = []
        student_data = []
        
        # Collecter tous les sujets uniques
        for result in exam_result_rec:
            for line in result.result_ids:
                subject_name = line.subject_id.name or ""
                if subject_name not in all_subjects:
                    all_subjects.append(subject_name)
        
        # Organiser les données des étudiants
        for result in exam_result_rec:
            student_marks = {}
            for subject in all_subjects:
                student_marks[subject] = {'D': '-', 'C': '-'}
            
            for line in result.result_ids:
                subject_name = line.subject_id.name or ""
                student_marks[subject_name] = {
                    'D': line.devoir or 0.0,
                    'C': line.composition or 0.0,
                }
            
            student_data.append({
                'name': result.student_id.name or "",
                'marks': student_marks,
                'moyenne': result.moyenne or 0.0,
                'moyenne_classe': result.moyenne_classe or 0.0,
            })

        # Récupérer la moyenne de classe depuis exam.result (si elle existe déjà)
        moyenne_classe = exam_result_rec[0].moyenne_classe if exam_result_rec else 0.0
        
        return {
            'subjects': all_subjects,
            'students': student_data,
            'moyenne_classe': moyenne_classe,  # Ajout de la moyenne de classe
        }


    @api.model
    def _get_report_values(self, docids, data=None):
        batch_result = self.env["ir.actions.report"]._get_report_from_name(
            "exam.exam_exam_batch"
        )
        batch_model = self.env[batch_result.model].browse(docids)
        
        return {
            "doc_ids": docids,
            "doc_model": batch_result.model,
            "docs": batch_model,
            "data": data,
            "get_student_results": self.get_student_results,  # Bien passer la méthode
        }
