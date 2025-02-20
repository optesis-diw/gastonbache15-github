# See LICENSE file for full copyright and licensing details.

import time
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ReportAddExamResult(models.AbstractModel):
    _name = "report.exam.exam_result_report"
    _description = "Exam result Report"

    @api.model
    def _get_result_detail(self, subject_ids, result):
        """Method to get result data"""
        sub_list = []
        result_data = []
        for sub in subject_ids:
            sub_list.append(sub.id)
        sub_obj = self.env["exam.subject"]
        subject_exam_ids = sub_obj.search(
            [("id", "in", sub_list), ("exam_id", "=", result.id)]
        )
        for subject in subject_exam_ids:
            result_data.append(
                {
                    "subject": subject.subject_id.name or "",
                    "max_mark": subject.maximum_marks or "",
                    "mini_marks": subject.minimum_marks or "",
                    "obt_marks": subject.obtain_marks or "",
                    "reval_marks": subject.marks_reeval or "",
                    "devoir": subject.devoir or "",
                    "composition": subject.composition or "",
                    "rang": subject.rang or "",
                    "grade": subject.grade or "",
                    "moyenne_provisoire": subject.moyenne_provisoire or "",
                    "coefficient": subject.coefficient or "",
                    
                }
            )
        return result_data

    ##afficher une liste de sujets triés par mm_domaine_sub, en évitant les doublons de mm_domaine_sub
    #@api.model
    #def _get_report_values(self, docids, data=None):
        #"""Inherited method to get report values"""
        
        #result_data = self.env['exam.result'].browse(docids)

        #domaine_list = []
        #exist_domaine_sub = set()  # Créer un ensemble vide pour stocker les domaines existants
        
        #result_test = []
        
        
        #for subject in self.env["exam.subject"].search([("exam_id", "=", docids[0])]).sorted(key=lambda s: s.dom_subject.name):

            #mm_domaine_sub = subject.dom_subject.name #listes domaines des sujets

            # Vérifier si le domaine existe déjà dans exist_domaine_sub
            #if mm_domaine_sub not in exist_domaine_sub:
                #domaine_list.append({
                    #'mm_domaine_sub': mm_domaine_sub,
                    #'subjects': [],
                #})
                #exist_domaine_sub.add(mm_domaine_sub)  # Ajouter le domaine à exist_domaine_sub pour éviter les doublons
                
            #result_test.append({
                #"domaine_lie_suj": subject.subject_id.domaine_subject.name, 
                #"subject": subject.subject_id.name or "",
                #"max_mark": subject.maximum_marks or "",
                #"mini_marks": subject.minimum_marks or "",
                #"obt_marks": subject.obtain_marks or "",
                #"reval_marks": subject.marks_reeval or "",
                #})    

           
        #return {
            #"doc_ids": docids,
            #"data": data,
            #"doc_model": 'exam.result',
            #"docs": result_data,
            #"get_result_detail": self._get_result_detail,
            #"time": time,
            #'domaine_list': domaine_list,
            #'result_test': result_test
            
        #} 


    @api.model
    def _get_report_values(self, docids, data=None):
        active_model = self._context.get('active_model')
        report_result = self.env['ir.actions.report']._get_report_from_name(
            'exam.exam_result_report')
        result_data = self.env['exam.result'].browse(docids)
        return {
              "doc_ids": docids,
              "data": data,
              "doc_model": 'exam.result',
              "docs": result_data,
              "get_result_detail": self._get_result_detail,
              "time": time,
                }

