# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StudentAttendanceByMonth(models.TransientModel):
    """Defining Student Attendance By Month."""

    _name = "student.attendance.by.month"
    _description = "Student Monthly Attendance Report"
    
    #diw pour l'entéte du report 
    company_id = fields.Many2one(
        "res.company",
        "Company",
        change_default=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )
    def _get_current_academic_year(self):
        return self.env["academic.year"].search([("current", "=", True)])

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
        ],"session", invisible="1")
    
    #

    month = fields.Many2one("academic.month")
    year = fields.Many2one("academic.year")
    attendance_type = fields.Selection(
        [("daily", "FullDay"), ("lecture", "Lecture Wise")], "Type"
    )

    @api.model
    def default_get(self, fields):
        """Overriding DefaultGet."""
        res = super(StudentAttendanceByMonth, self).default_get(fields)
        students = self.env["student.student"].browse(
            self._context.get("active_id")
        )
        if students.state == "draft":
            raise ValidationError(
                _(
                    """You can not print report for student in \
unconfirm state!"""
                )
            )
        return res

    def print_report(self):
        """ This method prints report
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current Logged in User
        @param ids : Current Records
        @param context : standard Dictionary
        @return : printed report
        """
        stud_search = self.env["student.student"].search(
            [
                ("id", "=", self.env.context.get("active_id")),
                ("state", "=", "done"),
            ]
        )
        daily_attend = self.env["daily.attendance"]
        for rec in self:
            if not daily_attend.search(
                [
                    ("standard_id", "=", stud_search.standard_id.id),
                    ("date", ">=", rec.month.date_start),
                    ("date", "<=", rec.month.date_stop),
                ]
            ):
                raise ValidationError(
                    _(
                        "There is no data of attendance for student in "
                        "selected month or year!"
                    )
                )
        data = self.read([])[0]
        if data.get("year"):
            data["year"] = self.year.name
        data.update({"stud_ids": self.env.context.get("active_ids")})
        datas = {
            "ids": [],
            "model": "student.student",
            "type": "ir.actions.report.xml",
            "form": data,
        }
        return self.env.ref(
            "school_attendance.attendace_month_report"
        ).report_action([], data=datas)
