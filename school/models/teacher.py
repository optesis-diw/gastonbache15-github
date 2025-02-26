# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SchoolTeacher(models.Model):
    '''Defining a Teacher information.'''

    _name = 'school.teacher'
    _description = 'Teacher Information'
    _inherit = ['mail.thread']  # Add this line to inherit from mail.thread


    employee_id = fields.Many2one('hr.employee', 'Employee ID',
                                  ondelete="cascade",
                                  delegate=True, required=True)
    
    #lier un Teacher à plusieurs classes (standard_id)
    standard_id = fields.Many2many('school.standard',
                                'school_teacher_standard_rel',
                                'teacher_id', #
                                'standard_id', # 
                                "Classes Responsables", 
                                help="Les classes dont l'enseignant est responsable.")
    
    @api.constrains('standard_id')
    def _check_standards(self):
        for rec in self:
            if not rec.standard_id:
                raise ValidationError("L'enseignant doit être responsable d'au moins une classe.")




    
    stand_id = fields.Many2one('school.standard', "Cours",
                           compute="_compute_stand_id", store=True)

    @api.depends('standard_id')
    def _compute_stand_id(self):
        for rec in self:
            rec.stand_id = rec.standard_id[:1]  # Prend la première classe


    subject_id = fields.Many2many('subject.subject', 'subject_teacher_rel',
                                  'teacher_id', 'subject_id',
                                  'Course-Subjects')
    school_id = fields.Many2one('school.school', "Campus",
                                related="standard_id.school_id", store=True)
    category_ids = fields.Many2many('hr.employee.category',
                                    'teacher_category_rel', 'emp_id',
                                    'categ_id', 'Tags')
    department_id = fields.Many2one('hr.department', 'Department')
    is_parent = fields.Boolean('Est parent')
    stu_parent_id = fields.Many2one('school.parent', 'Related Parent') #parent
    student_id = fields.Many2many('student.student',
                                  'students_teachers_parent_rel',
                                  'teacher_id', 'student_id',
                                  'Children') #Etudiant
    phone_numbers = fields.Char("Phone Number")
    work_location = fields.Char("Work Location")
   
    
    
    @api.onchange('is_parent')
    def _onchange_isparent(self):
        if self.is_parent:
            self.stu_parent_id = False
            self.student_id = [(6, 0, [])]

    @api.onchange('stu_parent_id')
    def _onchangestudent_parent(self):
        stud_list = []
        if self.stu_parent_id and self.stu_parent_id.student_id:
            for student in self.stu_parent_id.student_id:
                stud_list.append(student.id)
            self.student_id = [(6, 0, stud_list)]
    @api.model
    def create(self, vals):
        teacher_id = super(SchoolTeacher, self).create(vals)
        user_obj = self.env['res.users']
        user_vals = {'name': teacher_id.name,
                     'login': teacher_id.work_email,
                     'email': teacher_id.work_email,
                     }
        ctx_vals = {'teacher_create': True,
                    'school_id': teacher_id.school_id.company_id.id}
        user_id = user_obj.with_context(ctx_vals).create(user_vals)
        teacher_id.employee_id.write({'user_id': user_id.id})
        if vals.get('is_parent'):
            self.parent_crt(teacher_id)
        return teacher_id

    def parent_crt(self, manager_id):
        stu_parent = []
        if manager_id.stu_parent_id:
            stu_parent = manager_id.stu_parent_id
        if not stu_parent:
            emp_user = manager_id.employee_id
            students = [stu.id for stu in manager_id.student_id]
            parent_vals = {'name': manager_id.name,
                           'email': emp_user.work_email,
                           'parent_create_mng': 'parent',
                           'user_ids': [(6, 0, [emp_user.user_id.id])],
                           'partner_id': emp_user.user_id.partner_id.id,
                           'student_id': [(6, 0, students)]}
            stu_parent = self.env['school.parent'].create(parent_vals)
            manager_id.write({'stu_parent_id': stu_parent.id})
        user = stu_parent.user_ids
        user_rec = user[0]
        parent_grp_id = self.env.ref('school.group_school_parent')
        groups = parent_grp_id
        if user_rec.groups_id:
            groups = user_rec.groups_id
            groups += parent_grp_id
        group_ids = [group.id for group in groups]
        user_rec.write({'groups_id': [(6, 0, group_ids)]})

    def write(self, vals):
        if vals.get('is_parent'):
            self.parent_crt(self)
        if vals.get('student_id'):
            self.stu_parent_id.write({'student_id': vals.get('student_id')})
        if not vals.get('is_parent'):
            user_rec = self.employee_id.user_id
            parent_grp_id = self.env.ref('school.group_school_parent')
            
            if user_rec.has_group('school.group_school_parent'):
                # Supprimez le groupe si l'utilisateur en fait déjà partie
                user_rec.write({'groups_id': [(3, parent_grp_id.id)]})
            else:
                # Ajoutez l'utilisateur au groupe
                user_rec.write({'groups_id': [(4, parent_grp_id.id)]})
                
        return super(SchoolTeacher, self).write(vals)


    @api.onchange('address_id')
    def onchange_address_id(self):
        """Onchange method for address."""
        self.work_phone = False
        self.mobile_phone = False
        if self.address_id:
            self.work_phone = self.address_id.phone,
            self.mobile_phone = self.address_id.mobile

    @api.onchange('department_id')
    def onchange_department_id(self):
        """Onchange method for deepartment."""
        if self.department_id:
            self.parent_id = (self.department_id and
                              self.department_id.manager_id and
                              self.department_id.manager_id.id) or False

    @api.onchange('user_id')
    def onchange_user(self):
        """Onchange method for user."""
        if self.user_id:
            self.name = self.name or self.user_id.name
            self.work_email = self.user_id.email
            self.image = self.image or self.user_id.image

    @api.onchange('school_id')
    def onchange_school(self):
        """Onchange method for school."""
        self.address_id = False
        self.mobile_phone = False
        self.work_location = False
        self.work_email = False
        self.work_phone = False
        if self.school_id:
            self.address_id = self.school_id.company_id.partner_id.id
            self.mobile_phone = self.school_id.company_id.partner_id.mobile
            self.work_location = self.school_id.company_id.partner_id.city
            self.work_email = self.school_id.company_id.partner_id.email
            phone = self.school_id.company_id.partner_id.phone
            self.work_phone = phone
            self.phone_numbers = phone
            phone = self.school_id.company_id.partner_id.phone
