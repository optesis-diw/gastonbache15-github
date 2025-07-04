# See LICENSE file for full copyright and licensing details.

import json
import time
from datetime import date, datetime

from dateutil.relativedelta import relativedelta as rd
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, Warning as UserError

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"




class AttendanceSheet(models.Model):
    """Définition des informations sur la feuille de présence mensuelle."""

    _description = "Feuille de présence"
    _name = "attendance.sheet"

    name = fields.Char("Description", readonly=True)
    standard_id = fields.Many2one(
        "school.standard",
        "Academic Class",
        required=True,
        help="Select Standard",
    )
    month_id = fields.Many2one(
        "academic.month", "Month", required=True, help="Select Academic Month"
    )
    year_id = fields.Many2one("academic.year", "Year", required=True)
    attendance_ids = fields.One2many(
        "attendance.sheet.line",
        "standard_id",
        "Attendance",
        help="Academic Year",
    )
    user_id = fields.Many2one(
    "res.users", "Utilisateur", help="Utilisateur actuellement connecté", 
    default=lambda self: self.env.user,  # Définit l'utilisateur connecté par défaut
    readonly=True
)

    
    attendance_type = fields.Selection(
        [("daily", "FullDay"), ("lecture", "Lecture Wise")], "Type"
    )

    @api.onchange("standard_id")
    def onchange_class_info(self):
        stud_list = []
        stud_obj = self.env["student.student"]
        for rec in self:
            if rec.standard_id:
                """
                Si standard_id (classe) est défini, la méthode effectue 1e recherche 
                dans le modèle student.student pour trouver tous les étudiants
                appartenant à la même classe (standard) et ayant l'état done 
                (état final ou validé).
                chaque étudiant trouvé, crée un dictionnaire contenant roll_no ,name
                """
                stud_list = [
                    {"roll_no": stu.roll_no, "name": stu.name}
                    for stu in stud_obj.search(
                        [
                            ("standard_id", "=", rec.standard_id),
                            ("state", "=", "done"),
                        ]
                    )
                ]
            rec.attendance_ids = stud_list

    """
    mettre à jour les noms des champs dans une vue en arborescence (tree) 
    en fonction d'une plage de dates et pour masquer les champs inutilisés
    """
    @api.model
    def fields_view_get(self, view_id=None, view_type="form", toolbar=False, submenu=False):
        res = super(AttendanceSheet, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        start = self._context.get("start_date")
        end = self._context.get("end_date")
        st_dates = end_dates = False
        
        if start:
            st_dates = datetime.strptime(start, DEFAULT_SERVER_DATE_FORMAT)
        if end:
            end_dates = datetime.strptime(end, DEFAULT_SERVER_DATE_FORMAT)
        
        if view_type == "form":
            digits_temp_dict = {
                1: "one",
                2: "two",
                3: "three",
                4: "four",
                5: "five",
                6: "six",
                7: "seven",
                8: "eight",
                9: "nine",
                10: "ten",
                11: "one_1",
                12: "one_2",
                13: "one_3",
                14: "one_4",
                15: "one_5",
                16: "one_6",
                17: "one_7",
                18: "one_8",
                19: "one_9",
                20: "one_0",
                21: "two_1",
                22: "two_2",
                23: "two_3",
                24: "two_4",
                25: "two_5",
                26: "two_6",
                27: "two_7",
                28: "two_8",
                29: "two_9",
                30: "two_0",
                31: "three_1",
            }
            flag = 1
            if st_dates and end_dates:
                while st_dates <= end_dates:
                    res["fields"]["attendance_ids"]["views"]["tree"]["fields"][
                        digits_temp_dict.get(flag)
                    ]["string"] = str(st_dates.day)
                    st_dates += timedelta(days=1)
                    flag += 1
             #Si le nombre de jours est inférieur à 31, les champs restants sont masqués
            if flag < 32:
                res["fields"]["attendance_ids"]["views"]["tree"]["fields"][
                    digits_temp_dict.get(flag)
                ]["string"] = ""
                doc2 = etree.XML(
                    res["fields"]["attendance_ids"]["views"]["tree"]["arch"]
                )
                nodes = doc2.xpath(
                    "//field[@name='" + digits_temp_dict.get(flag) + "']"
                )
                for node in nodes:
                    node.set("modifiers", json.dumps({"invisible": True}))
                res["fields"]["attendance_ids"]["views"]["tree"]["arch"] = etree.tostring(doc2, pretty_print=True).decode('utf-8')

        return res

    
    
        
       
           

class StudentleaveRequest(models.Model):
    """Un modèle de demande de congé étudiant."""

    _name = "studentleave.request"
    _description = "Student Leave Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _update_vals(self, student_id):
        student_obj = self.env["student.student"]
        student = student_obj.browse(student_id)
        return {
            "roll_no": student.roll_no,
            "standard_id": student.standard_id.id,
            #"teacher_id": student.standard_id.user_id.id,
        }

    @api.model
    def create(self, vals):
        if vals.get("student_id"):
            vals.update(self._update_vals(vals.get("student_id")))
        return super(StudentleaveRequest, self).create(vals)

    def write(self, vals):
        if vals.get("student_id"):
            vals.update(self._update_vals(vals.get("student_id")))
        return super(StudentleaveRequest, self).write(vals)

    @api.onchange("student_id")
    def onchange_student(self):
        """Method to get standard and roll no of student selected"""
        if self.student_id:
            self.standard_id = self.student_id.standard_id.id
            self.roll_no = self.student_id.roll_no
            self.teacher_id = self.student_id.standard_id.user_id.id or False

    def approve_state(self):
        """Change state to approve."""
        self.state = "approve"

    def draft_state(self):
        """Change state to draft."""
        self.state = "draft"

    def toapprove_state(self):
        """Change state to toapprove."""
        self.state = "toapprove"

    def reject_state(self):
        """Change state to reject."""
        self.state = "reject"

    @api.depends("start_date", "end_date")
    def _compute_days(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.days = (rec.end_date - rec.start_date).days + 1
            if rec.start_date == rec.end_date:
                rec.days = 1
            if not rec.start_date or not rec.end_date:
                rec.days = 0

    name = fields.Char("Type of Leave", required=True)
    student_id = fields.Many2one("student.student", "Student", required=True)
    roll_no = fields.Char("Roll Number")
    standard_id = fields.Many2one("school.standard", "Class", required=True)
    attachments = fields.Binary("Attachment")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("toapprove", "To Approve"),
            ("reject", "Reject"),
            ("approve", "Approved"),
        ],
        "Status",
        default="draft",
        tracking=True,
    )
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    teacher_id = fields.Many2one(
        "res.users", "Utilisateur",
        help="Select Surveillant",
        states={"validate": [("readonly", True)]},default=lambda self: self.env.user)

    days = fields.Integer("Days", compute="_compute_days", store=True)
    reason = fields.Text("Reason for Leave")

    @api.constrains("student_id", "start_date", "end_date")
    def check_student_request(self):
        if self.search(
            [
                ("student_id", "=", self.student_id.id),
                ("start_date", "=", self.start_date),
                ("end_date", "=", self.end_date),
                ("id", "not in", self.ids),
            ],
            limit=1,
        ):
            raise ValidationError(
                _("You cannot take leave on same date for the same student!")
            )

    @api.constrains("start_date", "end_date")
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError(
                _("Start date should be less than end date!")
            )
        if self.start_date < date.today():
            raise ValidationError(
                _(
                    "Your leave request start date should be greater than "
                    "current date!"
                )
            )


class AttendanceSheetLine(models.Model):
    """Defining Attendance Sheet Line Information."""

    def _compute_percentage(self):
        """Method to get attendance percent."""
        res = {}
        for attendance_sheet_data in self:
            att_count = 0
            percentage = 0.0
            if attendance_sheet_data.one:
                att_count = att_count + 1
            if attendance_sheet_data.two:
                att_count = att_count + 1
            if attendance_sheet_data.three:
                att_count = att_count + 1
            if attendance_sheet_data.four:
                att_count = att_count + 1
            if attendance_sheet_data.five:
                att_count = att_count + 1
            if attendance_sheet_data.six:
                att_count = att_count + 1
            if attendance_sheet_data.seven:
                att_count = att_count + 1
            if attendance_sheet_data.eight:
                att_count = att_count + 1
            if attendance_sheet_data.nine:
                att_count = att_count + 1
            if attendance_sheet_data.ten:
                att_count = att_count + 1

            if attendance_sheet_data.one_1:
                att_count = att_count + 1
            if attendance_sheet_data.one_2:
                att_count = att_count + 1
            if attendance_sheet_data.one_3:
                att_count = att_count + 1
            if attendance_sheet_data.one_4:
                att_count = att_count + 1
            if attendance_sheet_data.one_5:
                att_count = att_count + 1
            if attendance_sheet_data.one_6:
                att_count = att_count + 1
            if attendance_sheet_data.one_7:
                att_count = att_count + 1
            if attendance_sheet_data.one_8:
                att_count = att_count + 1
            if attendance_sheet_data.one_9:
                att_count = att_count + 1
            if attendance_sheet_data.one_0:
                att_count = att_count + 1

            if attendance_sheet_data.two_1:
                att_count = att_count + 1
            if attendance_sheet_data.two_2:
                att_count = att_count + 1
            if attendance_sheet_data.two_3:
                att_count = att_count + 1
            if attendance_sheet_data.two_4:
                att_count = att_count + 1
            if attendance_sheet_data.two_5:
                att_count = att_count + 1
            if attendance_sheet_data.two_6:
                att_count = att_count + 1
            if attendance_sheet_data.two_7:
                att_count = att_count + 1
            if attendance_sheet_data.two_8:
                att_count = att_count + 1
            if attendance_sheet_data.two_9:
                att_count = att_count + 1
            if attendance_sheet_data.two_0:
                att_count = att_count + 1
            if attendance_sheet_data.three_1:
                att_count = att_count + 1
            percentage = (float(att_count / 31.00)) * 100
            attendance_sheet_data.percentage = percentage
        return res

    _description = "Attendance Sheet Line"
    _name = "attendance.sheet.line"
    _order = "roll_no"
    
    

    roll_no = fields.Integer(
        "Roll Number", required=True, help="Roll Number of Student"
    )
    standard_id = fields.Many2one("attendance.sheet", "Standard")
    name = fields.Char("Student Name", readonly=True)
    one = fields.Boolean("1")
    two = fields.Boolean("2")
    three = fields.Boolean("3")
    four = fields.Boolean("4")
    five = fields.Boolean("5")
    seven = fields.Boolean("7")
    six = fields.Boolean("6")
    eight = fields.Boolean("8")
    nine = fields.Boolean("9")
    ten = fields.Boolean("10")
    one_1 = fields.Boolean("11")
    one_2 = fields.Boolean("12")
    one_3 = fields.Boolean("13")
    one_4 = fields.Boolean("14")
    one_5 = fields.Boolean("15")
    one_6 = fields.Boolean("16")
    one_7 = fields.Boolean("17")
    one_8 = fields.Boolean("18")
    one_9 = fields.Boolean("19")
    one_0 = fields.Boolean("20")
    two_1 = fields.Boolean("21")
    two_2 = fields.Boolean("22")
    two_3 = fields.Boolean("23")
    two_4 = fields.Boolean("24")
    two_5 = fields.Boolean("25")
    two_6 = fields.Boolean("26")
    two_7 = fields.Boolean("27")
    two_8 = fields.Boolean("28")
    two_9 = fields.Boolean("29")
    two_0 = fields.Boolean("30")
    three_1 = fields.Boolean("31")
    percentage = fields.Float(
        compute="_compute_percentage", string="Attendance (%)", store=False
    )


class DailyAttendance(models.Model):
    """Defining Daily Attendance Information."""

    _description = "Daily Attendance"
    _name = "daily.attendance"
    _rec_name = "standard_id"

   

    @api.depends("student_ids")
    def _compute_total(self):
        """Méthode pour compter les étudiants"""
        for rec in self:
            rec.total_student = len(
                rec.student_ids and rec.student_ids.ids or []
            )

    

    @api.depends("student_ids", "student_ids.is_present")
    def _compute_present(self):
        """Méthode pour compter les étudiants présents."""
        for rec in self:
            count = len([att.id for att in rec.student_ids if att.is_present])
            rec.total_presence = count

    @api.depends("student_ids", "student_ids.is_absent")
    def _compute_absent(self):
        """Méthode pour compter les étudiants absents"""
        for rec in self:
            count_fail = 0
            if rec.student_ids:
                for att in rec.student_ids:
                    if att.is_absent:
                        count_fail += 1
                rec.total_absent = count_fail

    @api.constrains("date")
    def validate_date(self):
        if self.date > date.today():
            raise ValidationError(
                _("""Date_absent doit être inférieur ou égal à la date actuelle!""")
            )

    date = fields.Date(
        "Date",
        help="Current Date",
        default=lambda *a: time.strftime("%Y-%m-%d"),
    )
    
    student_ids = fields.One2many(
        "daily.attendance.line",
        "standard_id",
        "Students",
        states={
            "validate": [("readonly", True)],
            "draft": [("readonly", False)],
        },
    )

    
    #class
    standard_id = fields.Many2one(
        "school.standard",
        "Academic Class",
        required=True,
        help="Select Standard",
        states={"validate": [("readonly", True)]},
    )
    
    #teacher
    
    
    
    user_id = fields.Many2one(
        "res.users", "Utilisateur",
        help="Select Surveillant",
        states={"validate": [("readonly", True)]},default=lambda self: self.env.user)

    def print_attendance_report(self):
        return self.env.ref('school_attendance.report_attendance').report_action(self)
        
    #commenté by diw
    #si user_id a une valeur, elle réinitialise standard_id à False.
    #@api.onchange("user_id")
    #def onchange_check_faculty_value(self):
        #if self.user_id:
            #self.standard_id = False
    #commenté by diw

    
    
    state = fields.Selection(
        [("draft", "Draft"), ("validate", "Validate")],
        "State",
        readonly=True,
        default="draft",
    )
    total_student = fields.Integer(
        compute="_compute_total",
        store=True,
        help="Total Students in class",
        string="Total Students",
    )
    total_presence = fields.Integer(
        compute="_compute_present",
        store=True,
        string="Present Students",
        help="Present Student",
    )
    total_absent = fields.Integer(
        compute="_compute_absent",
        store=True,
        string="Absent Students",
        help="Absent Students",
    )
    is_generate = fields.Boolean("Generate?")

    _sql_constraints = [
        (
            "attend_unique",
            "unique(standard_id,user_id,date)",
            "Attendance should be unique!",
        )
    ]

    #Réinitialise le champ student_ids(studiants) et is_generate à False
    def do_regenerate(self):
        self.is_generate = False
        self.student_ids = False

    #button générer: permet de sélectionner ls étudiants de la class selectionné  et d'initialiser leur présence ou absence en fonction des requêtes de congé approuvées
    def get_students(self):
        # Étudiants
        stud_obj = self.env["student.student"]
        # Congé
        leave_req_obj = self.env["studentleave.request"]
        
        for rec in self:
            student_list = []
            # Classe
            if rec.standard_id:
                # Parcourir les étudiants de la classe sélectionnée
                students = stud_obj.search([("standard_id", "=", rec.standard_id.id)])
                if not students:
                    raise ValidationError(_("Aucun étudiant n'est trouvé pour la classe sélectionnée!"))
    
                for stud in students:
                    # Création des valeurs de présence et d'absence pour chaque étudiant
                    stud_vals_abs = (0, 0, {
                        "roll_no": stud.roll_no,
                        "stud_id": stud.id,
                        "is_absent": True,
                    })
                    stud_vals = (0, 0, {
                        "roll_no": stud.roll_no,
                        "stud_id": stud.id,
                        "is_present": True,
                    })
    
                    # Vérification si l'étudiant a une demande de congé approuvée pour la date spécifiée
                    leave_approved = leave_req_obj.search_count([
                        ("state", "=", "approve"),
                        ("student_id", "=", stud.id),
                        ("standard_id", "=", rec.standard_id.id),
                        ("start_date", "<=", rec.date),
                        ("end_date", ">=", rec.date),
                    ]) > 0
    
                    if leave_approved:
                        #Si l'étudiant est en congé, il le marque comme absent
                        student_list.append(stud_vals_abs)
                    else:
                        #sinon, il le marque comme présent
                        student_list.append(stud_vals)
    
                # Réinitialiser la liste des étudiants et ajouter les nouveaux
                rec.student_ids = [(5, 0, 0)] 
                rec.student_ids = student_list 
    
                # Mise à jour 'is_generate'
                rec.is_generate = bool(rec.student_ids)
                
            else:
                raise ValidationError(_("Veuillez sélectionner une classe!"))
    
            if not rec.student_ids:
                raise ValidationError(_("Aucun étudiant n'est trouvé pour les critères sélectionnés!"))
                

    """
    Désigner les élèves de la classe sélectionnés en les marquant comme présents ou absents en fonction de leurs requêtes de congé approuvées
    """
    @api.model
    def create(self, vals):
        student_list = []
        #studients
        stud_obj = self.env["student.student"]
        #class
        standard_id = vals.get("standard_id")
        date = vals.get("date")

        # Recherche des étudiants du niveau(classe spécifié)et dont l'état est 'done'
        stud_ids = stud_obj.search([
            ("standard_id", "=", standard_id),
            ("state", "=", "done"),
        ])

        for stud in stud_ids:
            line_vals = {
                "roll_no": stud.roll_no,
                "stud_id": stud.id,
                "is_present": True,
            }

            # Vérification si une liste des présences/absences est fournie et la gestion des congés étudiants
            if vals.get("student_ids") and not vals.get("student_ids")[0][2].get("present_absentcheck"):
                student_leave = self.env["studentleave.request"].search_count([
                    ("state", "=", "approve"),
                    ("student_id", "=", stud.id),
                    ("standard_id", "=", standard_id),
                    ("start_date", "<=", date),
                    ("end_date", ">=", date),
                ]) > 0

                if student_leave:
                    line_vals.update({"is_absent": True, "is_present": False})

            student_list.append((0, 0, line_vals))

        vals.update({"student_ids": student_list})

        return super(DailyAttendance, self).create(vals)

    def attendance_draft(self):
        """Changer l'état de présence en brouillon"""
        #feuille de présence
        att_sheet_obj = self.env["attendance.sheet"]
        #année académique
        academic_year_obj = self.env["academic.year"]
        #mois
        academic_month_obj = self.env["academic.month"]
        #jr du mois
        month_dict = {
            1: "one",
            2: "two",
            3: "three",
            4: "four",
            5: "five",
            6: "six",
            7: "seven",
            8: "eight",
            9: "nine",
            10: "ten",
            11: "one_1",
            12: "one_2",
            13: "one_3",
            14: "one_4",
            15: "one_5",
            16: "one_6",
            17: "one_7",
            18: "one_8",
            19: "one_9",
            20: "one_0",
            21: "two_1",
            22: "two_2",
            23: "two_3",
            24: "two_4",
            25: "two_5",
            26: "two_6",
            27: "two_7",
            28: "two_8",
            29: "two_9",
            30: "two_0",
            31: "three_1",
        }

        for rec in self:
            if not rec.date:
                raise UserError(_("Please enter todays date."))
            year_search_ids = academic_year_obj.search(
                [("code", "=", rec.date.year)]
            )
            month_search_ids = academic_month_obj.search(
                [("code", "=", rec.date.month)]
            )
            sheet_ids = att_sheet_obj.search(
                [
                    ("standard_id", "=", rec.standard_id.id),
                    ("month_id", "=", month_search_ids.id),
                    ("year_id", "=", year_search_ids.id),
                ]
            )
            if sheet_ids:
                for data in sheet_ids:
                    for attendance_id in data.attendance_ids:
                        date = rec.date
                        day = month_dict.get(date.day, False)
                        dic = {}
                        if day:
                            dic = {day: False}
                        attendance_id.write(dic)
            rec.state = "draft"
        return True

    def attendance_validate(self):
        """Method to validate attendance."""
        sheet_line_obj = self.env["attendance.sheet.line"]
        acadmic_year_obj = self.env["academic.year"]
        acadmic_month_obj = self.env["academic.month"]
        attendance_sheet_obj = self.env["attendance.sheet"]

        for line in self:
            year_ids = acadmic_year_obj.search(
                [
                    ("date_start", "<=", line.date),
                    ("date_stop", ">=", line.date),
                ]
            )
            month_ids = acadmic_month_obj.search(
                [
                    ("date_start", "<=", line.date),
                    ("date_stop", ">=", line.date),
                    ("year_id", "in", year_ids.ids),
                ]
            )
            if month_ids:
                month_data = month_ids
                att_sheet_ids = attendance_sheet_obj.search(
                    [
                        ("month_id", "in", month_ids.ids),
                        ("year_id", "in", year_ids.ids),
                    ]
                )
                attendance_sheet_id = (
                    att_sheet_ids and att_sheet_ids[0] or False
                )
                date = line.date
                if not attendance_sheet_id:
                    sheet = {
                        "name": (month_data.name + "-" + str(line.date.year)),
                        "standard_id": line.standard_id.id,
                        "user_id": line.user_id.id,
                        "month_id": month_data.id,
                        "year_id": year_ids and year_ids.id or False,
                    }
                    attendance_sheet_id = attendance_sheet_obj.create(sheet)
                    for student_id in line.student_ids:
                        line_dict = {
                            "roll_no": student_id.roll_no,
                            "standard_id": attendance_sheet_id.id,
                            "name": student_id.stud_id.student_name,
                        }
                        sheet_line_obj.create(line_dict)
                        for student_id in line.student_ids:
                            search_id = sheet_line_obj.search(
                                [("roll_no", "=", student_id.roll_no)]
                            )
                            # compute attendance of each day
                            if date.day == 1 and student_id.is_absent:
                                val = {"one": False}

                            elif date.day == 1 and not student_id.is_absent:
                                val = {"one": True}

                            elif date.day == 2 and student_id.is_absent:
                                val = {"two": False}

                            elif date.day == 2 and not student_id.is_absent:
                                val = {"two": True}

                            elif date.day == 3 and student_id.is_absent:
                                val = {"three": False}

                            elif date.day == 3 and not student_id.is_absent:
                                val = {"three": True}

                            elif date.day == 4 and student_id.is_absent:
                                val = {"four": False}

                            elif date.day == 4 and not student_id.is_absent:
                                val = {"four": True}

                            elif date.day == 5 and student_id.is_absent:
                                val = {"five": False}

                            elif date.day == 5 and not student_id.is_absent:
                                val = {"five": True}

                            elif date.day == 6 and student_id.is_absent:
                                val = {"six": False}

                            elif date.day == 6 and not student_id.is_absent:
                                val = {"six": True}

                            elif date.day == 7 and student_id.is_absent:
                                val = {"seven": False}

                            elif date.day == 7 and not student_id.is_absent:
                                val = {"seven": True}

                            elif date.day == 8 and student_id.is_absent:
                                val = {"eight": False}

                            elif date.day == 8 and not student_id.is_absent:
                                val = {"eight": True}

                            elif date.day == 9 and student_id.is_absent:
                                val = {"nine": False}

                            elif date.day == 9 and not student_id.is_absent:
                                val = {"nine": True}

                            elif date.day == 10 and student_id.is_absent:
                                val = {"ten": False}

                            elif date.day == 10 and not student_id.is_absent:
                                val = {"ten": True}

                            elif date.day == 11 and student_id.is_absent:
                                val = {"one_1": False}

                            elif date.day == 11 and not student_id.is_absent:
                                val = {"one_1": True}

                            elif date.day == 12 and student_id.is_absent:
                                val = {"one_2": False}

                            elif date.day == 12 and not student_id.is_absent:
                                val = {"one_2": True}

                            elif date.day == 13 and student_id.is_absent:
                                val = {"one_3": False}

                            elif date.day == 13 and not student_id.is_absent:
                                val = {"one_3": True}

                            elif date.day == 14 and student_id.is_absent:
                                val = {"one_4": False}

                            elif date.day == 14 and not student_id.is_absent:
                                val = {"one_4": True}

                            elif date.day == 15 and student_id.is_absent:
                                val = {"one_5": False}

                            elif date.day == 15 and not student_id.is_absent:
                                val = {"one_5": True}

                            elif date.day == 16 and student_id.is_absent:
                                val = {"one_6": False}

                            elif date.day == 16 and not student_id.is_absent:
                                val = {"one_6": True}

                            elif date.day == 17 and student_id.is_absent:
                                val = {"one_7": False}

                            elif date.day == 17 and not student_id.is_absent:
                                val = {"one_7": True}

                            elif date.day == 18 and student_id.is_absent:
                                val = {"one_8": False}

                            elif date.day == 18 and not student_id.is_absent:
                                val = {"one_8": True}

                            elif date.day == 19 and student_id.is_absent:
                                val = {"one_9": False}

                            elif date.day == 19 and not student_id.is_absent:
                                val = {"one_9": True}

                            elif date.day == 20 and student_id.is_absent:
                                val = {"one_0": False}

                            elif date.day == 20 and not student_id.is_absent:
                                val = {"one_0": True}

                            elif date.day == 21 and student_id.is_absent:
                                val = {"two_1": False}

                            elif date.day == 21 and not student_id.is_absent:
                                val = {"two_1": True}

                            elif date.day == 22 and student_id.is_absent:
                                val = {"two_2": False}

                            elif date.day == 22 and not student_id.is_absent:
                                val = {"two_2": True}

                            elif date.day == 23 and student_id.is_absent:
                                val = {"two_3": False}

                            elif date.day == 23 and not student_id.is_absent:
                                val = {"two_3": True}

                            elif date.day == 24 and student_id.is_absent:
                                val = {"two_4": False}

                            elif date.day == 24 and not student_id.is_absent:
                                val = {"two_4": True}

                            elif date.day == 25 and student_id.is_absent:
                                val = {"two_5": False}

                            elif date.day == 25 and not student_id.is_absent:
                                val = {"two_5": True}

                            elif date.day == 26 and student_id.is_absent:
                                val = {"two_6": False}

                            elif date.day == 26 and not student_id.is_absent:
                                val = {"two_6": True}

                            elif date.day == 27 and student_id.is_absent:
                                val = {"two_7": False}

                            elif date.day == 27 and not student_id.is_absent:
                                val = {"two_7": True}

                            elif date.day == 28 and student_id.is_absent:
                                val = {"two_8": False}

                            elif date.day == 28 and not student_id.is_absent:
                                val = {"two_8": True}

                            elif date.day == 29 and student_id.is_absent:
                                val = {"two_9": False}

                            elif date.day == 29 and not student_id.is_absent:
                                val = {"two_9": True}

                            elif date.day == 30 and student_id.is_absent:
                                val = {"two_0": False}

                            elif date.day == 30 and not student_id.is_absent:
                                val = {"two_0": True}

                            elif date.day == 31 and student_id.is_absent:
                                val = {"three_1": False}

                            elif date.day == 31 and not student_id.is_absent:
                                val = {"three_1": True}
                            else:
                                val = {}
                            if search_id:
                                search_id.write(val)
                else:
                    for student_id in line.student_ids:
                        search_id = sheet_line_obj.search(
                            [
                                ("roll_no", "=", student_id.roll_no),
                                ("standard_id", "=", attendance_sheet_id.id),
                            ]
                        )

                        if date.day == 1 and student_id.is_absent:
                            val = {"one": False}

                        elif date.day == 1 and not student_id.is_absent:
                            val = {"one": True}

                        elif date.day == 2 and student_id.is_absent:
                            val = {"two": False}

                        elif date.day == 2 and not student_id.is_absent:
                            val = {"two": True}

                        elif date.day == 3 and student_id.is_absent:
                            val = {"three": False}

                        elif date.day == 3 and not student_id.is_absent:
                            val = {"three": True}

                        elif date.day == 4 and student_id.is_absent:
                            val = {"four": False}

                        elif date.day == 4 and not student_id.is_absent:
                            val = {"four": True}

                        elif date.day == 5 and student_id.is_absent:
                            val = {"five": False}

                        elif date.day == 5 and not student_id.is_absent:
                            val = {"five": True}

                        elif date.day == 6 and student_id.is_absent:
                            val = {"six": False}

                        elif date.day == 6 and not student_id.is_absent:
                            val = {"six": True}

                        elif date.day == 7 and student_id.is_absent:
                            val = {"seven": False}

                        elif date.day == 7 and not student_id.is_absent:
                            val = {"seven": True}

                        elif date.day == 8 and student_id.is_absent:
                            val = {"eight": False}

                        elif date.day == 8 and not student_id.is_absent:
                            val = {"eight": True}

                        elif date.day == 9 and student_id.is_absent:
                            val = {"nine": False}

                        elif date.day == 9 and not student_id.is_absent:
                            val = {"nine": True}

                        elif date.day == 10 and student_id.is_absent:
                            val = {"ten": False}

                        elif date.day == 10 and not student_id.is_absent:
                            val = {"ten": True}

                        elif date.day == 11 and student_id.is_absent:
                            val = {"one_1": False}

                        elif date.day == 11 and not student_id.is_absent:
                            val = {"one_1": True}

                        elif date.day == 12 and student_id.is_absent:
                            val = {"one_2": False}

                        elif date.day == 12 and not student_id.is_absent:
                            val = {"one_2": True}

                        elif date.day == 13 and student_id.is_absent:
                            val = {"one_3": False}

                        elif date.day == 13 and not student_id.is_absent:
                            val = {"one_3": True}

                        elif date.day == 14 and student_id.is_absent:
                            val = {"one_4": False}

                        elif date.day == 14 and not student_id.is_absent:
                            val = {"one_4": True}

                        elif date.day == 15 and student_id.is_absent:
                            val = {"one_5": False}

                        elif date.day == 15 and not student_id.is_absent:
                            val = {"one_5": True}

                        elif date.day == 16 and student_id.is_absent:
                            val = {"one_6": False}

                        elif date.day == 16 and not student_id.is_absent:
                            val = {"one_6": True}

                        elif date.day == 17 and student_id.is_absent:
                            val = {"one_7": False}

                        elif date.day == 17 and not student_id.is_absent:
                            val = {"one_7": True}

                        elif date.day == 18 and student_id.is_absent:
                            val = {"one_8": False}

                        elif date.day == 18 and not student_id.is_absent:
                            val = {"one_8": True}

                        elif date.day == 19 and student_id.is_absent:
                            val = {"one_9": False}

                        elif date.day == 19 and not student_id.is_absent:
                            val = {"one_9": True}

                        elif date.day == 20 and student_id.is_absent:
                            val = {"one_0": False}

                        elif date.day == 20 and not student_id.is_absent:
                            val = {"one_0": True}

                        elif date.day == 21 and student_id.is_absent:
                            val = {"two_1": False}

                        elif date.day == 21 and not student_id.is_absent:
                            val = {"two_1": True}

                        elif date.day == 22 and student_id.is_absent:
                            val = {"two_2": False}

                        elif date.day == 22 and not student_id.is_absent:
                            val = {"two_2": True}

                        elif date.day == 23 and student_id.is_absent:
                            val = {"two_3": False}

                        elif date.day == 23 and not student_id.is_absent:
                            val = {"two_3": True}

                        elif date.day == 24 and student_id.is_absent:
                            val = {"two_4": False}

                        elif date.day == 24 and not student_id.is_absent:
                            val = {"two_4": True}

                        elif date.day == 25 and student_id.is_absent:
                            val = {"two_5": False}

                        elif date.day == 25 and not student_id.is_absent:
                            val = {"two_5": True}

                        elif date.day == 26 and student_id.is_absent:
                            val = {"two_6": False}

                        elif date.day == 26 and not student_id.is_absent:
                            val = {"two_6": True}

                        elif date.day == 27 and student_id.is_absent:
                            val = {"two_7": False}

                        elif date.day == 27 and not student_id.is_absent:
                            val = {"two_7": True}

                        elif date.day == 28 and student_id.is_absent:
                            val = {"two_8": False}

                        elif date.day == 28 and not student_id.is_absent:
                            val = {"two_8": True}

                        elif date.day == 29 and student_id.is_absent:
                            val = {"two_9": False}

                        elif date.day == 29 and not student_id.is_absent:
                            val = {"two_9": True}

                        elif date.day == 30 and student_id.is_absent:
                            val = {"two_0": False}

                        elif date.day == 30 and not student_id.is_absent:
                            val = {"two_0": True}

                        elif date.day == 31 and student_id.is_absent:
                            val = {"three_1": False}

                        elif date.day == 31 and not student_id.is_absent:
                            val = {"three_1": True}
                        else:
                            val = {}
                        if search_id:
                            search_id.write(val)
        self.state = "validate"
        return True

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

class DailyAttendanceLine(models.Model):
    """Defining Daily Attendance Sheet Line Information."""

    _description = "Daily Attendance Line"
    _name = "daily.attendance.line"
    _order = "roll_no"
    _rec_name = "roll_no"

    roll_no = fields.Integer("Roll No.", help="Roll Number")
    standard_id = fields.Many2one("daily.attendance", "Standard")
    stud_id = fields.Many2one("student.student", "Name")
    is_present = fields.Boolean("Present", help="Check if student is present")
    is_absent = fields.Boolean("Absent", help="Check if student is absent")
    present_absentcheck = fields.Boolean("Present/Absent Boolean")

    @api.onchange("is_present")
    def onchange_attendance(self):
        """Méthode pour rendre is_absent à False lorsque l'étudiant est présent."""
        if self.is_present:
            self.is_absent = False
            self.present_absentcheck = True

    @api.onchange("is_absent")
    def onchange_absent(self):
        """Méthode pour rendre is_present à False lorsque l'étudiant est absent."""
        if self.is_absent:
            self.is_present = False
            self.present_absentcheck = True

    def action_absent(self):
        for rec in self:
            """
            Si l'état de rec.standard_id est "validate".
            Ou si rec.standard_id.is_generate est False: exception
            """
            if (rec.standard_id.state == "validate"):
                raise ValidationError(
                    _(
                     "Vous ne pouvez pas marquer comme absent,"
                    "tant que la présence est en état de validation!"
                    )
                )
            rec.write({"is_present": False})
            rec.write({"is_absent": True})
        return True

    def action_present(self):
        for rec in self:
            if (
                rec.standard_id.state == "validate"
            ):
                raise ValidationError(
                    _(
                        "You cannot mark as present,"
                        " While attendance is in validate state!"
                    )
                )
            rec.is_present = True
            rec.is_absent = False
        return True


class SHEETReport(models.AbstractModel):
    _name = 'report.school_attendance.report_attendance'
 
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["daily.attendance"].search(
            [("id", "in", docids)]
        )
        shett_model = self.env["ir.actions.report"]._get_report_from_name(
            "school_attendance.report_attendance"
        )
        return {
            "doc_ids": docids,
            "doc_model": shett_model.model,
            "docs": docs,
            "data": data,
        }
