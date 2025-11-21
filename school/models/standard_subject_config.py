from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class StandardSubjectConfig(models.Model):
    _name = 'standard.subject.config'
    _description = 'Configuration Matière par Classe'

    class_ids = fields.Many2many(
    'school.standard',
    'standard_config_class_rel',
    'config_id',
    'class_id',
    string="Classes concernées",
    compute='_compute_class_ids',
    store=True,
    readonly=True,
)

    
    standard_id = fields.Many2one(
        'standard.standard', 
        'Niveau', 
        required=False,
        help="Niveau académique"
    )
    
    subject_id = fields.Many2one(
        'subject.subject', 
        'Matière', 
        help="Matière académique"
    )
    
    coefficient = fields.Integer(
        "Coefficient", 
        default=1,
        help="Coefficient de la matière pour cette classe"
    )
    
    maximum_marks = fields.Float(
        "Note Maximale", 
        required=False,
        digits=(16, 2),
        help="Note maximale pour cette matière dans cette classe"
    )
    
    minimum_marks = fields.Float(
        "Note Minimale", 
        default=0,
        digits=(16, 2),
        help="Note minimale pour cette matière dans cette classe"
    )
    
    _sql_constraints = [
        ('unique_standard_subject', 'unique(standard_id, subject_id)', 
         'Une matière ne peut avoir qu\'une configuration par niveau!')
    ]

    @api.depends('standard_id')
    def _compute_class_ids(self):
        for rec in self:
            if rec.standard_id:
                classes = self.env['school.standard'].search([
                    ('standard_id', '=', rec.standard_id.id)
                ])
                rec.class_ids = classes
            else:
                rec.class_ids = False


    @api.constrains("maximum_marks", "minimum_marks")
    def check_marks(self):
        """Vérification des notes"""
        for record in self:
            if record.maximum_marks <= 0:
                raise ValidationError(
                    _("La note maximale doit être supérieure à 0.")
                )
            if record.minimum_marks >= record.maximum_marks:
                raise ValidationError(
                    _("La note maximale doit être supérieure à la note minimale!")
                )
