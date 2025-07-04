# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TimeTable(models.Model):
    """Defining model for time table."""

    _description = 'Time Table'
    _name = 'time.table'

    #diw: utilisé pour le repport
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )

    academic_year_id = fields.Many2one(
        "academic.year",
        ondelete="restrict",
        string="Academic Session",
        default=lambda obj: obj.env["academic.year"].search(
            [("current", "=", True)]
        ),)

    year_date_start_s = fields.Char(string="Year Date Start", compute='_compute_year_date_start')
    year_date_stop_s = fields.Char(string="Year Date Stop", compute='_compute_year_date_stop')

    @api.depends('academic_year_id.date_start')
    def _compute_year_date_start(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_start:
                record.year_date_start_s = record.academic_year_id.date_start.year
            else:
                record.year_date_start_s = ''

    @api.depends('academic_year_id.date_stop')
    def _compute_year_date_stop(self):
        for record in self:
            if record.academic_year_id and record.academic_year_id.date_stop:
                record.year_date_stop_s = record.academic_year_id.date_stop.year
            else:
                record.year_date_stop_s = ''
                
    session = fields.Selection(
        [("premier_semestre", "1er semestre"),
            ("second_semestre", "2éme semestre"),
        ],"session")
    
    #fin diw 
    
    @api.depends('timetable_ids')
    def _compute_user(self):
        '''Method to compute user.'''
        for rec in self:
            rec.user_ids = [teacher.teacher_id.employee_id.user_id.id
                            for teacher in rec.timetable_ids
                            ]

    name = fields.Char('Description', help='Enter description of timetable')
    standard_id = fields.Many2one('school.standard', 'Academic Class',
                                  required=True,
                                  help="Select Standard")#le nom de la class
    
    niveau_id = fields.Many2one('standard.standard', 'Niveau',
                                  related="standard_id.standard_id") #niveau
    

    
    
    
    year_id = fields.Many2one('academic.year', 'Year', required=True,
                              help="Select academic year")
    
    timetable_ids = fields.One2many('time.table.line', 'table_id', 'TimeTable',
                                    help='Enter the timetable pattern')
    timetable_type = fields.Selection([('regular', 'Regular')],
                                      'Time Table Type', default="regular",
                                      invisible=True,
                                      help='Select time table type')
    user_ids = fields.Many2many('res.users', string="Users",
                                compute="_compute_user", store=True,
                                help='Teachers following this timetable')
    class_room_id = fields.Many2one('class.room', 'Room Number',
                                    help='''Class room in which tome table
                                    would be followed''')

    @api.constrains('timetable_ids')
    def _check_lecture(self):
        '''Method to check same lecture is not assigned on same day.'''
        if self.timetable_type == 'regular':
            domain = [('table_id', 'in', self.ids)]
            line_ids = self.env['time.table.line'].search(domain)
            for rec in line_ids:
                records = [rec_check.id for rec_check in line_ids
                           if (rec.week_day == rec_check.week_day and
                               rec.start_time == rec_check.start_time and
                               rec.end_time == rec_check.end_time and
                               rec.teacher_id.id == rec.teacher_id.id)]
                if len(records) > 1:
                    raise ValidationError(_('''
You cannot set lecture at same time %s  at same day %s for teacher %s.!
''') % (rec.start_time, rec.week_day, rec.teacher_id.name))
                # Checks if time is greater than 24 hours than raise error
                if rec.start_time > 24 or rec.end_time > 24:
                    raise ValidationError(_('''
Start and End Time should be less than 24 hours!'''))


class TimeTableLine(models.Model):
    """Defining model for time table."""

    _description = 'Time Table Line'
    _name = 'time.table.line'
    _rec_name = 'table_id'

    @api.constrains('teacher_id', 'subject_id')
    def check_teacher(self):
        '''Check if lecture is not related to teacher than raise error.'''
        for rec in self:
            if (rec.teacher_id.id not in rec.subject_id.teacher_ids.ids and
                    rec.table_id.timetable_type == 'regular'):
                raise ValidationError(_('''
                    The subject %s is not assigned to teacher %s.
                    ''') % (rec.subject_id.name, rec.teacher_id.name))

    teacher_id = fields.Many2one('school.teacher', 'Faculty Name',
                                 help="Select Teacher")
    subject_id = fields.Many2one('subject.subject', 'Subject Name',
                                 help="Select Subject")
    table_id = fields.Many2one('time.table', 'TimeTable')
    start_time = fields.Float('Start Time', required=True,
                              help="Time according to timeformat of 24 hours")
    end_time = fields.Float('End Time', required=True,
                            help="Time according to timeformat of 24 hours")
    week_day = fields.Selection([('monday', 'Monday'),
                                 ('tuesday', 'Tuesday'),
                                 ('wednesday', 'Wednesday'),
                                 ('thursday', 'Thursday'),
                                 ('friday', 'Friday'),
                                 ('saturday', 'Saturday'),
                                 ('sunday', 'Sunday')], "Week day",
                                help='Select weekday for timetable')
    class_room_id = fields.Many2one('class.room', 'Room Number',
                                    help='''Class room in which time
                                    table would be followed''')

    @api.constrains('teacher_id', 'class_room_id')
    def check_teacher_room(self):
        """Check available room for teacher."""
        for rec in self:
            timetable_rec = self.env['time.table'].search([
                                                ('id', '!=', rec.table_id.id)])
            for data in timetable_rec:
                for record in data.timetable_ids:
                    if (data.timetable_type == 'regular' and
                            rec.table_id.timetable_type == 'regular' and
                            rec.teacher_id == record.teacher_id and
                            rec.week_day == record.week_day and
                            rec.start_time == record.start_time):
                        raise ValidationError(_('''
                            There is a lecture of Lecturer at same time!'''))
                    if (data.timetable_type == 'regular' and
                            rec.table_id.timetable_type == 'regular' and
                            rec.class_room_id == record.class_room_id and
                            rec.start_time == record.start_time):
                        raise ValidationError(_("The room is occupied."))


class SubjectSubject(models.Model):
    _inherit = "subject.subject"

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        '''Override method to get subject related to teacher.'''
        teacher_id = self._context.get('teacher_id')
        if teacher_id:
            for teacher_data in self.env['school.teacher'].browse(teacher_id):
                args.append(('teacher_ids', 'in', [teacher_data.id]))
        return super(SubjectSubject, self)._search(
            args=args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid)
