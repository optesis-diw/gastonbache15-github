
# See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
    
class StudentStudent(models.Model):
    _inherit = "student.student"
    _description = "Student Information"


    year_date_start_s = fields.Char(string="Year Date Start", compute='_compute_year_date_start')
    year_date_stop_s = fields.Char(string="Year Date Stop", compute='_compute_year_date_stop')

    @api.depends('year.date_start')
    def _compute_year_date_start(self):
        for record in self:
            if record.year and record.year.date_start:
                record.year_date_start_s = record.year.date_start.year
            else:
                record.year_date_start_s = ''

    @api.depends('year.date_stop')
    def _compute_year_date_stop(self):
        for record in self:
            if record.year and record.year.date_stop:
                record.year_date_stop_s = record.year.date_stop.year
            else:
                record.year_date_stop_s = ''
    

    exam_results_ids = fields.One2many(
        "exam.result",
        "student_id",
        "Exam History",
        readonly=True,
        help="Student exam history",
    )

    def set_alumni(self):
        """Override method to make exam results of student active false
        when student is alumni"""
        addexam_result_obj = self.env["additional.exam.result"]
        regular_examresult_obj = self.env["exam.result"]
        for rec in self:
            addexam_result_rec = addexam_result_obj.search(
                [("student_id", "=", rec.id)]
            )
            regular_examresult_rec = regular_examresult_obj.search(
                [("student_id", "=", rec.id)]
            )
            if addexam_result_rec:
                addexam_result_rec.active = False
            if regular_examresult_rec:
                regular_examresult_rec.active = False
        return super(StudentStudent, self).set_alumni()

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """Override method to get exam of student selected."""
        if self._context.get("exam"):
            exam_obj = self.env["exam.exam"]
            exam_rec = exam_obj.browse(self._context.get("exam"))
            std_ids = [std_id.id for std_id in exam_rec.standard_id]
            args.append(("standard_id", "in", std_ids))
        return super(StudentStudent, self)._search(
            args=args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )


class ExtendedTimeTable(models.Model):
    _inherit = "time.table"
    #calendrier
    
    
    
    
   
    timetable_type = fields.Selection(
        selection_add=[("exam", "Exam")],
        string="Time Table Type",
        required=True,
        ondelete={"exam": "set default"},
        help="Select timetable type",
    )
    exam_timetable_line_ids = fields.One2many(
        "time.table.line", "table_id", "TimeTable Lines", help="Timetable"
    )
    exam_id = fields.Many2one(
        "exam.exam", "Exam", help="Select exam for a respective timetable"
    )

    def unlink(self):
        """Inherited unlink method to check the state at record deletion."""
        exam_search_rec = self.env["exam.exam"].search(
            [("state", "=", "running")]
        )
        schedule_line_obj = self.env["exam.schedule.line"]
        for rec in self:
            for data in exam_search_rec:
                schedule_line_search_rec = schedule_line_obj.search(
                    [("exam_id", "=", data.id), ("timetable_id", "=", rec.id)]
                )
                if schedule_line_search_rec:
                    raise ValidationError(
                        _(
                            """
                You cannot delete schedule of exam which is in running!"""
                        )
                    )
        return super(ExtendedTimeTable, self).unlink()





    

    is_generate = fields.Boolean("Generate?", default=True)

    @api.onchange('name', 'year_id')
    def _onchange_exam_timetable_line_ids(self):
        if self.name and self.year_id:
            return {
                'warning': {
                    'title': "Attention",
                    'message': "Veuillez vérifier les dates et heures de l'examen.",
                }
            }

     
        
    def action_generate_lines(self):
        """Generate subjects and associated exam timetable lines."""
        for record in self:
            if record.standard_id:
                record.is_generate = False
                # Supprimer les lignes précédentes
                record.exam_timetable_line_ids.unlink()

                subjects = record.standard_id.subject_ids  # Récupérer les matières
                time_table_lines = []
                start_time = 8.0  # Début des cours à 08:00 AM
                duration = 2  # Durée de chaque cours (2h)

                # Vérifier s'il y a des enseignants
                teachers = self.env['school.teacher'].search([])
                if not teachers:
                    record.env.user.notify_warning(
                        message="Aucun enseignant trouvé dans la base de données!",
                        title="Attention",
                        sticky=True
                    )
                    return

                for subject in subjects:
                    teacher_id = teachers[0].id  # Sélectionner le premier enseignant

                    # 🔹 Vérification & Ajustement : Respect des horaires (entre 8h et 18h)
                    if start_time < 8.0:
                        start_time = 8.0  # Ajuster au minimum 8h
                    if start_time + duration > 18.0:
                        start_time = 8.0  # Recommencer à 8h si dépassement

                    end_time = start_time + duration  # Calcul de l'heure de fin

                    # 🔹 Vérification & Ajustement : L’heure de début doit être inférieure à l’heure de fin
                    if start_time >= end_time:
                        start_time = 8.0  # Réinitialiser au début de la journée
                        end_time = start_time + duration

                    time_table_lines.append({
                        'subject_id': subject.id,
                        'table_id': record.id,
                        'teacher_id': teacher_id,
                        'start_time': start_time,
                        'end_time': end_time,
                    })

                    start_time += duration  # Incrémenter pour le prochain cours

                if time_table_lines:
                    created_lines = self.env['time.table.line'].create(time_table_lines)
                    record.exam_timetable_line_ids = [(6, 0, created_lines.ids)]

                    

                    


    

class ExtendedTimeTableLine(models.Model):
    _inherit = "time.table.line"
    #calendrier line
    

    exm_date = fields.Date("Exam Date", help="Enter exam date")
    day_of_week = fields.Char("Week Day", help="Enter week day")
    class_room_id = fields.Many2one(
        "class.room", "Classroom", help="Enter class room"
    )

    @api.onchange("exm_date")
    def onchange_date_day(self):
        """Method to get weekday from date"""
        for rec in self:
            rec.day_of_week = False
            if rec.exm_date:
                rec.day_of_week = rec.exm_date.strftime("%A")

    @api.constrains("exm_date")
    def check_date(self):
        """Method to check constraint of start date and end date"""
        for line in self:
            if line.exm_date:
                exam_date = line.exm_date
                if line.day_of_week != exam_date.strftime("%A"):
                    return False
                elif exam_date < fields.Date.today():
                    raise ValidationError(
                        _("""Invalid Date Error !
Exam Date should be greater than today!"""))

    @api.constrains("teacher_id")
    def check_supervisior_exam(self):
        """Method to check supervisor in exam."""
        for rec in self:
            if rec.table_id.timetable_type == "exam" and not rec.teacher_id:
                raise ValidationError(_("""PLease Enter Supervisior!"""))

    @api.constrains("start_time", "end_time")
    def check_time(self):
        """Method to check constraint of start time and end time."""
        for rec in self:
            if rec.start_time >= rec.end_time:
                raise ValidationError(
                    _(
                        """
                        Start time should be less than end time!"""
                    )
                )
            # Checks if time is greater than 24 hours than raise error
            if rec.start_time > 24 or rec.end_time > 24:
                    raise ValidationError(_('''
Start and End Time should be less than 24 hours!'''))

    #commenté par diw
    """
    @api.constrains("teacher_id", "class_room_id")
    def check_teacher_room(self):
        for rec in self:
            timetable_rec = self.env["time.table"].search(
                [("id", "!=", rec.table_id.id)]
            )
            for data in timetable_rec:
                for record in data.timetable_ids:
                    if (
                        data.timetable_type == "exam"
                        and rec.table_id.timetable_type == "exam"
                        and rec.class_room_id == record.class_room_id
                        and rec.start_time == record.start_time
                    ):
                        raise ValidationError(_("The room is occupied!"))
    """                    

    @api.constrains("subject_id", "class_room_id")
    def check_exam_date(self):
        """Method to Check Exam Date."""
        for rec in self.table_id.exam_timetable_line_ids:
            record = self.table_id
            if rec.id not in self.ids:
                if (
                    record.timetable_type == "exam"
                    and self.exm_date == rec.exm_date
                    and self.start_time == rec.start_time
                ):
                    raise ValidationError(
                        _(
                            """
                            There is already Exam at same Date and Time!"""
                        )
                    )
                if (
                    record.timetable_type == "exam"
                    and self.table_id.timetable_type == "exam"
                    and self.subject_id == rec.subject_id
                ):
                    raise ValidationError(
                        _(
                            """
                            %s Subject Exam Already Taken
                            """
                        )
                        % (self.subject_id.name)
                    )
                if (
                    record.timetable_type == "exam"
                    and self.table_id.timetable_type == "exam"
                    and self.exm_date == rec.exm_date
                    and self.class_room_id == rec.class_room_id
                    and self.start_time == rec.start_time
                ):
                    raise ValidationError(
                        _(
                            """
                        %s is occupied by '%s' for %s class!
                    """
                        )
                        % (
                            self.class_room_id.name,
                            record.name,
                            record.standard_id.standard_id.name,
                        )
                    )


class ExamExam(models.Model):
    """Defining model for Exam."""

    _name = "exam.exam"
    _description = "Exam Information"

    

    """
    @api.constrains("start_date", "end_date")
    def check_date_exam(self):
        #Method to check constraint of exam start date and end date
        for rec in self:
            # Vérification si start_date ou end_date est None
            if not rec.start_date or not rec.end_date:
                raise ValidationError(_("Start Date and End Date must be set!"))

            # Vérification de l'ordre des dates
            if rec.end_date < rec.start_date:
                raise ValidationError(_("Exam end date should be greater than start date!"))

            # Vérification des dates dans l'emploi du temps de l'examen
            for line in rec.exam_schedule_ids:  # horaire exam
                if line.timetable_id:  # calendrier
                    for tt in line.timetable_id.exam_timetable_line_ids:
                        if not tt.exm_date:  # Vérifie si la date de l'examen est définie
                            raise ValidationError(_("Exam schedule date must be set!"))
                        if not (rec.start_date <= tt.exm_date <= rec.end_date):
                            raise ValidationError(
                                _(
                                    "Invalid Exam Schedule!
                                    \n\nExam Dates must be in between Start date and End date !"
                                )
                            )
    """     

    niveau_id = fields.Many2one(
        "standard.standard", "niveau", help="Select Standard", related="standard_id.standard_id"
    ) #niveau
    
    #pour entete rapport
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )

    year_date_start_s = fields.Char(string="Year Date Start", compute='_compute_year_date_start')
    year_date_stop_s = fields.Char(string="Year Date Stop", compute='_compute_year_date_stop')

    @api.depends('academic_year.date_start')
    def _compute_year_date_start(self):
        for record in self:
            if record.academic_year and record.academic_year.date_start:
                record.year_date_start_s = record.academic_year.date_start.year
            else:
                record.year_date_start_s = ''


    @api.depends('academic_year.date_stop')
    def _compute_year_date_stop(self):
        for record in self:
            if record.academic_year and record.academic_year.date_stop:
                record.year_date_stop_s = record.academic_year.date_stop.year
            else:
                record.year_date_stop_s = ''
                      
    #                         
    #Validation Avertissement si les résultats de l'examen ne sont pas terminés "done"
    @api.constrains("active")
    def check_active(self):
        """if exam results is not in done state then raise an
        validation Warning"""
        result_obj = self.env["exam.result"]
        if not self.active:
            for result in result_obj.search([("s_exam_ids", "=", self.id)]):
                if result.state != "done":
                    raise ValidationError(
                        _(
                            """
                        Kindly,mark as done %s examination results!
                    """
                        )
                        % (self.name)
                    )


    active = fields.Boolean(
        "Active", default="True", help="Activate/Deactivate record"
    )
    
    name = fields.Char("Exam Name", required=True, help="Name of Exam")
    exam_code = fields.Char(
        "Exam Code",
        required=True,
        readonly=True,
        help="Code of exam",
        default=lambda obj: obj.env["ir.sequence"].next_by_code("exam.exam"),
    )
    standard_id = fields.Many2one('school.standard', 'Classe',
                                  required=True,
                                  help="Select Standard")#le nom de la class
    
    start_date = fields.Date(
        "Exam Start Date", help="Exam will start from this date"
    )
    end_date = fields.Date("Exam End date", help="Exam will end at this date")
    
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("finished", "Finished"),
            ("cancelled", "Cancelled"),
        ],
        "State",
        readonly=True,
        default="draft",
        help="State of the exam",
    )
    
    # Champ grade_system pour accéder au grade master
    grade_system = fields.Many2one(
        "grade.master", "Grade System", help="Grade System selected", default=20.0
    )

    @api.depends('grade_system')
    def _compute_max_to_mark(self):
        """ Calculer la note maximale (to_mark) du grade system """
        for record in self:
            if record.grade_system:
                # Accéder aux lignes de grade associées au système de grades
                grade_lines = record.grade_system.grade_ids
                # Trouver le maximum de `to_mark` parmi les lignes de grade
                max_to_mark = max(grade_lines.mapped('to_mark'), default=0.0)
                record.max_to_mark = max_to_mark
            else:
                record.max_to_mark = 0.0
                
                
                 # Ajout d'un champ pour stocker la note maximale (to_mark)
    max_to_mark = fields.Float(
        string="Max To Marks",
        compute="_compute_max_to_mark",
        store=True,
        help="Maximum 'To Marks' in the selected grade system"
    )
    
    
    academic_year = fields.Many2one(
    'academic.year', 
    'Academic Year', 
    readonly=True, 
    default=lambda self: self.check_current_year()
)

    @api.model
    def check_current_year(self):
        res = self.env['academic.year'].search([('current', '=', True)], limit=1)
        if not res:
            raise ValidationError(_(
                "Il n'y a pas d'année académique en cours défini ! Veuillez contacter l'administrateur !"
            ))
        return res.id

    
    exam_schedule_ids = fields.One2many(
        "exam.schedule.line",
        "exam_id",
        "Exam Schedule",
        help="Enter exam schedule",
    )#calendrier des examens
    
    calendrier_exam = fields.Many2one(
        "exam.schedule.line",
        help="Enter exam schedule",
    )#calendrier d examens

    def set_to_draft(self):
        """Method to set state to draft"""
        self.state = "draft"

    def set_running(self):
        """Method to set state to running"""
        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_("Please Select Standard!"))
            if rec.standard_id:
                rec.state = "running"
            #else:
                #raise ValidationError(_("You must add one Exam Schedule!"))

    def set_finish(self):
        """Method to set state to finish"""
        self.state = "finished"

    def set_cancel(self):
        """Method to set state to cancel"""
        self.state = "cancelled"
        
    count_devoir = fields.Integer("Nombre de devoir", required=True)  
    
    @api.constrains('count_devoir')
    def _check_count_devoir(self):
        for rec in self:
            if rec.count_devoir < 1 or rec.count_devoir > 3:
                raise ValidationError("Le nombre de devoir doit être compris entre 1 et 3.")  

    
    session = fields.Selection(
        [
            ("premier_semestre", "1er Session"), 
            ("second_semestre", "2e Session"),
            ("troisieme_semestre", "3e Session"),  # Ajout de la troisième session
        ],
        string="Session",
        required=True,
        readonly=False,
    )
    
  

    @api.constrains('session', 'academic_year', 'standard_id')
    def _check_session_constraint(self):
        """
        Contrainte pour empêcher la sélection d'une session déjà utilisée pour la même classe et année académique.
        """
        result_obj = self.env["exam.result"]
        for rec in self:
            if not rec.standard_id or not rec.academic_year:
                continue

            # Rechercher les résultats existants pour cette classe et cette année académique
            prev_results = result_obj.search([
                ("standard_id", "=", rec.standard_id.id),
                ("academic_year", "=", rec.academic_year.id),
                ("session", "=", rec.session),
            ])

            # Si des résultats existent pour cette session, lever une erreur
            if prev_results:
                raise ValidationError(
                    f"La session '{rec.session}' est déjà utilisée pour la classe '{rec.standard_id.name}' "
                    f"et l'année académique '{rec.academic_year.name}'. Veuillez choisir une autre session."
                )
    
          
    
    
    #cette méthode permet de générer des résultats d'examen pour chaque étudiant inscrit, en créant des enregistrements de résultat si nécessaire    
    def generate_result(self):
        """Générer les résultats d'examen en fonction de la classe sélectionnée,
        et marquer la session comme 'premier_semestre', 'second_semestre' ou 'troisieme_semestre'.
        """
        result_obj = self.env["exam.result"]
        student_obj = self.env["student.student"]
        result_list = []

        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_("Veuillez sélectionner une classe."))

            # Récupérer les étudiants de la classe et de l'année académique sélectionnée
            students_rec = student_obj.search([
                ("standard_id", "=", rec.standard_id.id),
                ("year", "=", rec.academic_year.id),
                ("state", "=", "done"),
                ("school_id", "=", rec.standard_id.school_id.id),
            ])

            for student in students_rec:
                # Vérifier si un résultat existe déjà pour cet examen précis
                exam_result_rec = result_obj.search([
                    ("standard_id", "=", student.standard_id.id),
                    ("student_id", "=", student.id),
                    ("s_exam_ids", "=", rec.id),
                ])
                if exam_result_rec:
                    result_list.extend(exam_result_rec.ids)
                else:
                    # Récupérer les matières de la classe sélectionnée
                    subjects = rec.standard_id.subject_ids  
                    exam_line = []
                    
                    for subject in subjects:
                        sub_vals = {
                            "subject_id": subject.id,
                            "minimum_marks": subject.minimum_marks,
                            "maximum_marks": subject.maximum_marks,
                        }
                        exam_line.append((0, 0, sub_vals))

                    # Créer l'enregistrement du résultat
                    rs_dict = {
                        "s_exam_ids": rec.id,
                        "student_id": student.id,
                        "standard_id": student.standard_id.id,
                        "roll_no": student.roll_no,
                        "grade_system": rec.grade_system.id,
                        "result_ids": exam_line,
                        "session": rec.session,  # Utiliser la session calculée
                        "academic_year": rec.academic_year.id,
                        "count_devoir": rec.count_devoir,
                    }
                    result_rec = result_obj.create(rs_dict)
                    result_list.append(result_rec.id)

        return {
            "name": _("Result Info"),
            "view_mode": "tree,form",
            "res_model": "exam.result",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", result_list)],
        }
            


class ExamScheduleLine(models.Model):
    """Defining model for exam schedule line details."""

    _name = "exam.schedule.line"
    _description = "Exam Schedule Line Details"

    standard_id = fields.Many2one(
        "school.standard", "Standard", help="Select Standard"
    )
    timetable_id = fields.Many2one(
        "time.table", "Exam Schedule", help="Enter exam time table"
    )
    exam_id = fields.Many2one("exam.exam", "Exam", help="Enter exam")
    standard_ids = fields.Many2many(
        "standard.standard",
        string="Participant Standards",
        help="Enter standards for the exams",
    )


class AdditionalExam(models.Model):
    """Defining model for additional exam."""

    _name = "additional.exam"
    _description = "additional Exam Information"

    def _compute_color_name(self):
        """Compute method to assign color name"""
        for rec in self:
            rec.color_name = rec.subject_id.id

    name = fields.Char(
        "Additional Exam Name", required=True, help="Name of Exam"
    )
    addtional_exam_code = fields.Char(
        "Exam Code",
        required=True,
        help="Exam Code",
        readonly=True,
        default=lambda obj: obj.env["ir.sequence"].next_by_code(
            "additional.exam"
        ),
    )
    standard_id = fields.Many2one(
        "school.standard", "Standard", help="Select standard for exam"
    )
    subject_id = fields.Many2one(
        "subject.subject", "Subject Name", help="Select subject for exam"
    )
    exam_date = fields.Date("Exam Date", help="Select exam date")
    maximum_marks = fields.Float(
        "Maximum Mark", help="Minimum Marks of exam"
    )
    minimum_marks = fields.Float(
        "Minimum Mark", help="Maximum Marks of Exam"
    )
    weightage = fields.Char("WEIGHTAGE", help="Enter weightage of exam")
    color_name = fields.Integer(
        "Color index of creator",
        compute="_compute_color_name",
        store=False,
        help="Select color",
    )

    @api.constrains("maximum_marks", "minimum_marks")
    def check_marks(self):
        """Method to check marks."""
        if self.minimum_marks >= self.maximum_marks:
            raise ValidationError(
                _(
                    """
                    Configure Maximum marks greater than minimum marks!"""
                )
            )


class ExamResult(models.Model):
    """Defining Exam Result."""

    _name = "exam.result"
    _inherit = ["mail.thread", "resource.mixin"]
    _rec_name = "roll_no"
    _description = "exam result Information"
    
    # Nouveau nom du champ (exemple : "Note maximale du barème")
    note_maximale_grade = fields.Float(
    string="Note maximale",
    compute="_compute_note_maximale_grade",
    store=True,
    default=20.0
)

    @api.depends('grade_system')
    def _compute_note_maximale_grade(self):
        """ Calculer la note maximale (to_mark) du grade system """
        for record in self:
            if record.grade_system:
                # Accéder aux lignes de grade associées au système de grades
                grade_lines = record.grade_system.grade_ids
                # Trouver le maximum de `to_mark` parmi les lignes de grade
                note_maximale_grade = max(grade_lines.mapped('to_mark'), default=20.0)
                record.note_maximale_grade = note_maximale_grade
            else:
                record.note_maximale_grade = 20.0
                
    

    #add by diw yowit
    count_devoir = fields.Integer("Nombre de devoir") 
    
    academic_year = fields.Many2one(
    'academic.year', 
    'Academic Year', 
    readonly=True, 
    default=lambda self: self.check_current_year()
    )

    @api.model
    def check_current_year(self):
        res = self.env['academic.year'].search([('current', '=', True)], limit=1)
        if not res:
            raise ValidationError(_(
                "Il n'y a pas d'année académique en cours défini ! Veuillez contacter l'administrateur !"
            ))
        return res.id

    
    retards = fields.Integer("Retards")
    absences = fields.Integer("absences")

    annee_scolaire = fields.Many2one('academic.year', 'Academic Year', related="student_id.year")

    year_date_start_s = fields.Char(string="Year Date Start", related="student_id.year_date_start_s")
    year_date_stop_s = fields.Char(string="Year Date Stop", related="student_id.year_date_stop_s")


    class_redouble = fields.Integer(string="Classe redoublée")

    

    
    

    #diw :pour t'entéte
    session = fields.Selection(
        [("premier_semestre", "1er Session"), 
            ("second_semestre", "2e Session"),
            ("troisieme_semestre", "3e Session"),  # Ajout de la troisième session
        ],"session", required=True, default="premier_semestre")

    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
        help="Related company",
    )
    #fin diw
    
    @api.onchange('total', 'result_ids.obtain_marks', 'result_ids.marks_reeval', 'result_ids.coefficient', 'result_ids.state')
    def _compute_grade(self):
        """Méthode pour calculer la moyenne, le grade et le percentage"""
        for result in self:
            moyenne_provisoire = 0.0
            obtained_total = 0.0
            somme_coef = 0.0
            somme_maximum_marks = 0.0
            nombre_matieres = 0

            result.somme_obtain_marks = 0.0
            result.somme_coef = 0.0
            result.grade = ""
            result.moyenne = 0.0
            result.result = ""
            result.percentage = 0.0

            # Calcul simple de la somme des obtain_marks sans traitement spécial pour les matières surérogatoires
            for sub_line in result.result_ids:
                obtain_marks = sub_line.obtain_marks or 0.0
                moyenne_provisoire = sub_line.moyenne_provisoire or 0.0

                obtained_total += obtain_marks
                somme_coef += sub_line.coefficient or 0.0
                somme_maximum_marks += sub_line.maximum_marks or 0.0
                nombre_matieres += 1

            result.somme_coef = somme_coef
            result.somme_obtain_marks = obtained_total
            result.somme_maximum_marks = somme_maximum_marks

            if somme_coef > 0 and nombre_matieres > 0:
                result.total = obtained_total  # Total est maintenant directement la somme des obtain_marks

                moyenne_total = obtained_total / somme_coef
                maximum_marks_class = somme_maximum_marks / nombre_matieres

                moyenne_norm = (moyenne_total * result.note_maximale_grade) / maximum_marks_class if maximum_marks_class > 0 else 0.0

                result.moyenne = moyenne_norm
                result.percentage = (moyenne_norm / result.note_maximale_grade) * 100

                if result.grade_system:
                    grade_found = False
                    for grade_id in result.grade_system.grade_ids:
                        if grade_id.from_mark <= moyenne_norm <= grade_id.to_mark:
                            result.grade = grade_id.grade or ""
                            grade_found = True
                            break
                    if not grade_found:
                        result.grade = ""

                result.result = "Pass" if result.moyenne >= (result.note_maximale_grade/2) else "Fail"
            else:
                result.grade = ""
                result.moyenne = 0.0
                result.result = "Fail"
                result.percentage = 0.0

            
    @api.onchange("percentage")
    def _compute_result(self):
        """Method to compute result"""
        for rec in self:
            flag = False
            for grade in rec.result_ids:
                if not grade.grade_line_id.fail:
                    rec.result = "Pass"
                else:
                    flag = True
            if flag:
                rec.result = "Fail"
                

    s_exam_ids = fields.Many2one(
        "exam.exam", "Examination", required=True, help="Select Exam"
    )
    student_id = fields.Many2one(
        "student.student", "Student Name", required=True, help="Select Student"
    )
    
    
    
    
    roll_no = fields.Integer(
        string="Roll No", readonly=True, help="Enter student roll no."
    )
    pid = fields.Char(
        related="student_id.pid",
        string="Student ID",
        readonly=True,
        help="Student Personal ID No.",
    )
    standard_id = fields.Many2one(
        "school.standard", "Standard", help="Select Standard"
    ) #class
    
   
    
    #add diw :champs enseignant et école
    enseignant = fields.Many2one('school.teacher', 'Class Teacher', related="standard_id.user_id")
    school_id = fields.Many2one('school.school', 'School', related="standard_id.school_id")
    
    niveau_id = fields.Many2one(
        "standard.standard", "niveau", help="Select Standard", related="standard_id.standard_id"
    ) #niveau
    
    #
    result_ids = fields.One2many(
        "exam.subject", "exam_id", "Exam Subjects", help="Select exam subjects"
    )
    total = fields.Float(
        compute="_compute_grade",
        string="Obtain Total",
        store=True,
        help="Total of marks",
    )
    percentage = fields.Float(
        "Percentage",
        compute="_compute_grade",
        store=True,
        help="Percentage Obtained",
    )
    result = fields.Char(
        compute="_compute_grade",
        string="Result",
     
        help="Result Obtained",
    )
    grade = fields.Char(
        "Grade", compute="_compute_grade",  help="Grade Obtained"
    )

    
    moyenne = fields.Float("Moyenne", compute="_compute_grade", digits=(16,2))
    somme_coef = fields.Float("somme coef", compute="_compute_grade")
    somme_maximum_marks = fields.Float("somme notes", compute="_compute_grade")

    

    somme_obtain_marks = fields.Float("somme moyenne", compute="_compute_grade")
    
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirm"),
            ("re-evaluation", "Re-Evaluation"),
            ("re-evaluation_confirm", "Re-Evaluation Confirm"),
            ("done", "Done"),
        ],
        "State",
        readonly=True,
        tracking=True,
        default="draft",
        help="State of the exam",
    )
    color = fields.Integer("Color", help="Color")
    active = fields.Boolean(
        "Active", default=True, help="Activate/Deactivate record"
    )
    grade_system = fields.Many2one(
        "grade.master", "Grade System", help="Grade System selected"
    )
    message_ids = fields.One2many(
        "mail.message",
        "res_id",
        "Messages",
        domain=lambda self: [("model", "=", self._name)],
        auto_join=True,
        help="Messages can entered",
    )
    message_follower_ids = fields.One2many(
        "mail.followers",
        "res_id",
        "Followers",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Select message followers",
    )

    @api.model
    def create(self, vals):
        """Inherited the create method to assign the roll no and std"""
        if vals.get("student_id"):
            student_rec = self.env["student.student"].browse(
                vals.get("student_id")
            )
            vals.update(
                {
                    "roll_no": student_rec.roll_no,
                    "standard_id": student_rec.standard_id.id,
                }
            )
        return super(ExamResult, self).create(vals)

    def write(self, vals):
        """Inherited the write method to update the roll no and std"""
        if vals.get("student_id"):
            student_rec = self.env["student.student"].browse(
                vals.get("student_id")
            )
            vals.update(
                {
                    "roll_no": student_rec.roll_no,
                    "standard_id": student_rec.standard_id.id,
                }
            )
        return super(ExamResult, self).write(vals)

    def unlink(self):
        """Inherited the unlink method to check the state at the deletion."""
        for rec in self:
            if rec.state != "draft":
                raise ValidationError(
                    _(
                        """
                    You can delete record in unconfirm state only!"""
                    )
                )
        return super(ExamResult, self).unlink()

    @api.onchange("student_id")
    def onchange_student(self):
        """Method to get standard and roll no of student selected"""
        if self.student_id:
            self.standard_id = self.student_id.standard_id.id or False
            self.roll_no = self.student_id.roll_no or False

    def result_confirm(self):
        """Method to confirm result"""
        for rec in self:
            for line in rec.result_ids:
                if line.maximum_marks == 0:
                    # Check subject marks not greater than maximum marks
                    raise ValidationError(
                        _(
                            """
                        Kindly add maximum marks of subject "%s".
                    """
                        )
                        % (line.subject_id.name)
                    )
                elif line.minimum_marks < 0:
                    raise ValidationError(
                        _(
                            """
                        Kindly add minimum marks of subject "%s".
                    """
                        )
                        % (line.subject_id.name)
                    )
                elif (
                    line.maximum_marks == 0 or line.minimum_marks < 0
                ) and line.obtain_marks:
                    raise ValidationError(
                        _(
                            """
                        Kindly add marks details of subject "%s"!
                    """
                        )
                        % (line.subject_id.name)
                    )
            vals = {
                "grade": rec.grade,
                "percentage": rec.percentage,
                "state": "confirm",
            }
            rec.write(vals)

    def re_evaluation_confirm(self):
        """Method to change state to re_evaluation_confirm"""
        self.state = "re-evaluation_confirm"

    def result_re_evaluation(self):
        """Method to set state to re-evaluation"""
        for rec in self:
            for line in rec.result_ids:
                line.marks_reeval = line.obtain_marks
            rec.state = "re-evaluation"

    def set_done(self):
        """Method to obtain history of student"""
        history_obj = self.env["student.history"]
        for rec in self:
            vals = {
                "student_id": rec.student_id.id,
                "academice_year_id": rec.student_id.year.id,
                "standard_id": rec.standard_id.id,
                "percentage": rec.percentage,
                "result": rec.result,
            }
            history_rec = history_obj.search(
                [
                    ("student_id", "=", rec.student_id.id),
                    ("academice_year_id", "=", rec.student_id.year.id),
                    ("standard_id", "=", rec.standard_id.id),
                ]
            )
            if history_rec:
                history_obj.write(vals)
            elif not history_rec:
                history_obj.create(vals)
            rec.state = "done"

    rang = fields.Integer(string='Rang', compute='_compute_rang_exam')

    @api.onchange('total', 's_exam_ids', 'session')
    @api.depends('total', 's_exam_ids', 'session')
    def _compute_rang_exam(self):
        for rec in self:
            try:
                # Vérification des données obligatoires
                if not rec.s_exam_ids or not rec.session or not rec.total:
                    rec.rang = 0
                    continue

                # Recherche tous les résultats du même examen et de la même classe
                exam_results = self.env['exam.result'].search([
                    ('s_exam_ids', '=', rec.s_exam_ids.id),
                    ('standard_id', '=', rec.standard_id.id)
                ])

                if not exam_results:
                    rec.rang = 0
                    continue

                # Trie les résultats par note décroissante
                sorted_results = exam_results.sorted(key=lambda r: r.total or 0, reverse=True)

                # Initialisation des variables pour le calcul des rangs
                ranks = {}
                current_rank = 1
                
                # Groupe les élèves par note
                grouped_students = {}
                for result in sorted_results:
                    note = result.total or 0
                    if note not in grouped_students:
                        grouped_students[note] = []
                    grouped_students[note].append(result)

                # Attribution des rangs avec gestion des ex-æquo
                for note, students in grouped_students.items():
                    # Attribue le même rang à tous les élèves du groupe
                    for student in students:
                        ranks[student.id] = current_rank
                    # Incrémente le rang pour sauter les places occupées
                    current_rank += len(students)

                # Affecte le rang calculé à l'enregistrement courant
                rec.rang = ranks.get(rec.id, 0)

            except Exception as e:
                _logger.error(f"Erreur dans le calcul du rang pour l'élève {rec.id}: {str(e)}")
                rec.rang = 0
                
    

        # Ajouter le nouveau champ dans la classe
    rang_annuel = fields.Integer(string='Rang Annuel', compute='_compute_rang_annuel')


    # Nouvelle méthode pour le calcul du rang annuel
    @api.depends('moyenne_annuel', 'session', 'niveau_id.name')
    def _compute_rang_annuel(self):
        for rec in self:
            try:
                primary_levels = ['CP1', 'CP2', 'CE1', 'CE2', 'CM1', 'CM2']
                is_primary = rec.niveau_id.name in primary_levels if rec.niveau_id and rec.niveau_id.name else False

                # Vérifier si on doit calculer le rang annuel pour cet enregistrement
                if (is_primary and rec.session != "troisieme_semestre") or \
                (not is_primary and rec.session != "second_semestre"):
                    rec.rang_annuel = 0
                    continue

                # Rechercher les résultats à inclure dans le classement annuel
                domain = [
                    ('standard_id', '=', rec.standard_id.id),
                    ('annee_scolaire', '=', rec.annee_scolaire.id)
                ]
                
                if is_primary:
                    domain.append(('session', '=', 'troisieme_semestre'))
                else:
                    domain.append(('session', '=', 'second_semestre'))
                    
                exam_results = self.env['exam.result'].search(domain)

                if not exam_results:
                    rec.rang_annuel = 0
                    continue

                # Classement par moyenne annuelle
                sorted_results = exam_results.sorted(
                    key=lambda r: r.moyenne_annuel or 0.0, 
                    reverse=True
                )

                # Calcul des rangs avec gestion des ex-æquo
                ranks = {}
                current_rank = 1
                grouped_students = {}
                
                for result in sorted_results:
                    note = result.moyenne_annuel or 0.0
                    if note not in grouped_students:
                        grouped_students[note] = []
                    grouped_students[note].append(result)

                for note, students in grouped_students.items():
                    for student in students:
                        ranks[student.id] = current_rank
                    current_rank += len(students)

                rec.rang_annuel = ranks.get(rec.id, 0)

            except Exception as e:
                _logger.error(f"Erreur dans le calcul du rang annuel: {str(e)}")
                rec.rang_annuel = 0
     

                    
    moyenne_second_semester = fields.Float(string='Moyenne 2em Semester' , compute='_compute_moyenne_semestre' , digits=(16,2))

    moyenne_prem_semester = fields.Float(string='Moyenne 1er Semester', compute='_compute_moyenne_semestre' , digits=(16,2))

    moyenne_troisieme_semester = fields.Float(string='Moyenne 3ième  Semester' , compute='_compute_moyenne_semestre' , digits=(16,2))
    
    moyenne_annuel = fields.Float(string='moyenne annuelle' , compute='_compute_moyenne_semestre' , digits=(16,2))

    
    
    

    @api.depends('student_id', 'moyenne', 'session', 'annee_scolaire')
    def _compute_moyenne_semestre(self):
        for record in self:
            _logger.info(f"Calcul de la moyenne pour {record.student_id.name}, Session: {record.session}")
            if record.session == "premier_semestre":
                record.moyenne_prem_semester = record.moyenne or 0.0
                record.moyenne_second_semester = 0.0
                record.moyenne_troisieme_semester = 0.0
                record.moyenne_annuel = 0.0

            elif record.session == "second_semestre":
                # Rechercher la moyenne du premier semestre
                premier_semestre_result = self.env['exam.result'].search([
                    ('student_id', '=', record.student_id.id),
                    ('annee_scolaire', '=', record.annee_scolaire.id),
                    ('session', '=', 'premier_semestre')
                ], order="id desc", limit=1)

                if premier_semestre_result:
                    record.moyenne_prem_semester = premier_semestre_result.moyenne
                else:
                    record.moyenne_prem_semester = 0.0

                record.moyenne_second_semester = record.moyenne or 0.0
                record.moyenne_troisieme_semester = 0.0
                record.moyenne_annuel = (record.moyenne_prem_semester + record.moyenne_second_semester) / 2.0

            elif record.session == "troisieme_semestre":
                # Rechercher les moyennes des premier et deuxième semestres
                premier_semestre_result = self.env['exam.result'].search([
                    ('student_id', '=', record.student_id.id),
                    ('annee_scolaire', '=', record.annee_scolaire.id),
                    ('session', '=', 'premier_semestre')
                ], order="id desc", limit=1)

                second_semestre_result = self.env['exam.result'].search([
                    ('student_id', '=', record.student_id.id),
                    ('annee_scolaire', '=', record.annee_scolaire.id),
                    ('session', '=', 'second_semestre')
                ], order="id desc", limit=1)

                if premier_semestre_result:
                    record.moyenne_prem_semester = premier_semestre_result.moyenne
                else:
                    record.moyenne_prem_semester = 0.0

                if second_semestre_result:
                    record.moyenne_second_semester = second_semestre_result.moyenne
                else:
                    record.moyenne_second_semester = 0.0

                record.moyenne_troisieme_semester = record.moyenne or 0.0
                record.moyenne_annuel = (record.moyenne_prem_semester + record.moyenne_second_semester + record.moyenne_troisieme_semester) / 3.0

            else:
                record.moyenne_prem_semester = 0.0
                record.moyenne_second_semester = 0.0
                record.moyenne_troisieme_semester = 0.0
                record.moyenne_annuel = 0.0
    
        #diw


    moyenne_classe = fields.Float(string="Moyenne de la classe",
    compute="_compute_moyenne_classe", digits=(16, 2),
    help="Moyenne générale de la classe pour cette session")  


    @api.depends('standard_id', 'session', 'moyenne')
    def _compute_moyenne_classe(self):
        for record in self:
            # Rechercher tous les résultats de la même classe et même session
            results = self.env['exam.result'].search([
                ('standard_id', '=', record.standard_id.id),
                ('session', '=', record.session),
            ])
            
            if results:
                total_moyennes = sum(res.moyenne for res in results if res.moyenne)
                record.moyenne_classe = total_moyennes / len(results)
            else:
                record.moyenne_classe = 0.0  

    
                

class ExamGradeLine(models.Model):
    """Defining model for Exam Grade Line."""

    _name = "exam.grade.line"
    _description = "Exam Subject Information"
    _rec_name = "standard_id"

    standard_id = fields.Many2one(
        "standard.standard", "Standard", help="Select student standard"
    )#niveau
    exam_id = fields.Many2one("exam.result", "Result", help="Select exam")
    grade = fields.Char("Grade", help="Enter grade")


class ExamSubject(models.Model):
    """Defining model for Exam Subject Information."""

    _name = "exam.subject"
    _description = "Exam Subject Information"
    _rec_name = "subject_id"
    #c'est pour les informations sur le sujet d'examen
    

    

    
                   
    
               
                        
    exam_id = fields.Many2one("exam.result", "Result", help="Select exam")

    s_exam_ids = fields.Many2one(related="exam_id.s_exam_ids")
    
    standard_subject = fields.Many2one(related="exam_id.standard_id")
    
    
    
    
     
    state = fields.Selection(
        related="exam_id.state",
        string="State",
        help="State of the exam subject")
    
    subject_id = fields.Many2one(
        "subject.subject", "Subject Name", help="Select subject")
    
    #add by diw yowit
    session = fields.Selection(
        [("premier_semestre", "1er Session"), 
            ("second_semestre", "2e Session"),
            ("troisieme_semestre", "3e Session"),  # Ajout de la troisième session
        ],"session", required=True, related="exam_id.session")
    
   
   

    rang = fields.Integer(string='Rang', compute='_compute_rang')

    # Déclenche le calcul quand ces champs sont modifiés dans l'interface
    @api.onchange('moyenne_provisoire', 'exam_id', 'session')
    # Recalcule automatiquement quand ces champs changent (même en backend)
    @api.depends('moyenne_provisoire', 'exam_id', 'session', 's_exam_ids', 'standard_subject')
    def _compute_rang(self):
        # Parcours tous les enregistrements (élèves/matières) à traiter
        for rec in self:
            try:
                # Vérification des données obligatoires
                if not rec.exam_id or not rec.s_exam_ids or not rec.standard_subject or not rec.moyenne_provisoire:
                    rec.rang = 0  # Si données manquantes, rang = 0
                    continue  # Passe à l'élève suivant
                    
                # Recherche tous les examens correspondants :
                # - Même session d'examen (s_exam_ids)
                # - Même classe (standard_subject)
                exam_results = self.env['exam.result'].search([
                    ('s_exam_ids', '=', rec.s_exam_ids.id),
                    ('standard_id', '=', rec.standard_subject.id)
                ])
                
                # Log pour débogage (nombre de résultats trouvés)
                _logger.info(f"Found {len(exam_results)} exam results for subject {rec.id}")
                
                # Si aucun résultat trouvé, rang = 0
                if not exam_results:
                    rec.rang = 0
                    continue
                    
                # Récupère toutes les matières de ces examens
                # et filtre pour garder uniquement la matière actuelle
                all_subjects = exam_results.mapped('result_ids').filtered(
                    lambda x: x.subject_id.id == rec.subject_id.id
                )
                
                # Trie les résultats par moyenne (décroissant)
                sorted_subjects = all_subjects.sorted(
                    key=lambda s: s.moyenne_provisoire or 0,  # Si moyenne vide = 0
                    reverse=True  # Ordre décroissant
                )
                
                # Initialisation des variables pour le calcul des rangs
                ranks = {}  # Dictionnaire {id_élève: rang}
                current_rank = 1  # Commence au rang 1
                
                # Groupe les élèves par leur moyenne
                grouped_subjects = {}
                for subject in sorted_subjects:
                    moyenne = subject.moyenne_provisoire or 0
                    if moyenne not in grouped_subjects:
                        grouped_subjects[moyenne] = []  # Crée un nouveau groupe si nouvelle moyenne
                    grouped_subjects[moyenne].append(subject)  # Ajoute l'élève au groupe
                
                # Attribution des rangs
                for moyenne, subjects in grouped_subjects.items():
                    # Donne le même rang à tous les élèves du groupe (même moyenne)
                    for subject in subjects:
                        ranks[subject.id] = current_rank
                    # Incrémente le rang pour sauter les places prises par ce groupe
                    # Ex: 3 élèves à 18/20 → rang 1 → prochain rang = 1 + 3 = 4
                    current_rank += len(subjects)
                
                # Attribue le rang calculé à l'enregistrement actuel
                rec.rang = ranks.get(rec.id, 0)  # Si non trouvé → 0
                    
            # Gestion des erreurs
            except Exception as e:
                _logger.error(f"Error in computing rank for subject {rec.id}: {str(e)}")
                rec.rang = 0  # En cas d'erreur → rang = 0
    
    
    #diw coefficient = fields.Integer("Coefficient", default=1, related="subject_id.coefficient")
    
   
    
    cycle_id = fields.Many2one(related="standard_subject.medium_id")

    
    cycle_name = fields.Char(related="cycle_id.name")


    subject_name = fields.Char(related="subject_id.name")



    coefficient = fields.Integer("Coefficient", compute="_compute_coefficient", required=False )

    COEFFICIENTS = {
    "Élémentaire": {
        "Langue et Communication / Français - Ressources": 1,
        "Langue et Communication / Français - Compétence": 1,
        "Maths - Ressources": 1,
        "Maths - Compétence": 1,
        "Découverte du Monde – Ressources (HG – IST)": 1,
        "Découverte du Monde - Compétence": 1,
        "Éducation au Développement Durable - Ressources (Vivre Ensemble – Vivre dans son Milieu)": 1,
        "Éducation au Développement Durable - Compétence": 1,
        "Éducation Physique et Sportive": 1,
        "Éducation Artistique / Dessin / Art Plastique": 1,
        "Éducation Musicale (Récitation / Chant)": 1,
        "Arabe / Éducation Religieuse": 1,
        "Anglais Primaire": 1,
    },
    "Collége": {
        "Expression Ecrite / Rédaction / Dissertation": 2,
        "Dictée / Orthographe": 1,
        "TSQ": 1,
        "Maths": 3,
        "PC": 2,
        "SVT": 2,
        "Eco Fam": 2,
        "Anglais": 2,
        "Espagnol": 2,
        "Arabe": 2,
        "EPS": 2,
        "HG": 2,
        "EC": 1,
    },
    "TL2 et 1ère L2": {
        "Philo": 6,  # Seulement en Tle
        "HG": 6,
        "Français": 5,
        "Langue Vivante 1": 4,
        "Langue Vivante 2": 2,
        "Maths": 2,
        "SVT": 2,  # SVT OU PC
        "PC": 2,
        
    },
    "TL1 et 1ère L1": {
        "Français": 6,
        "LV1 Ecrit": 4,
        "LV1 Oral": 2,
        "Langue Vivante 2": 4,
        "Philo": 4,  # Seulement en Tle
        "HG": 2,
        "Maths": 2,
        
    },
    "TS2 et 1ère S2": {
        "SVT": 6,
        "PC": 6,
        "Maths": 5,
        "Français": 3,
        "Philo": 2,  # Seulement en Tle
        "Anglais": 2,
        "HG": 2,
        
    },
    "TS1 et 1ère S1": {
        "Maths": 8,
        "PC": 8,
        "Français": 3,
        "SVT": 2,
        "Anglais": 2,
        "Philo": 2,  # Seulement en Tle
        "HG": 2,
        
    },
    "2nd L": {
        "Français": 5,
        "Langue Vivante 1": 5,
        "HG": 4,
        "Langue Vivante 2": 3,
        "Économie": 2,
        "Maths": 2,
        "SVT": 2,  # SVT ou PC
        "PC": 2,
        
    },
    "2nd S": {
        "SVT": 5,
        "Maths": 5,
        "PC": 5,
        "Français": 3,
        "Anglais": 2,
        "HG": 2,
    },
}


    @api.onchange('cycle_name', 'subject_name')
    def _compute_coefficient(self):
        for subject_rec in self:
            cycle = subject_rec.cycle_name
            subject = subject_rec.subject_name

            if not cycle or not subject:
                subject_rec.coefficient = 0  # Coefficient par défaut
            else:
                subject_rec.coefficient = self.COEFFICIENTS.get(cycle, {}).get(subject, 0)

    count_devoir = fields.Integer("Nombre de devoir", related="exam_id.count_devoir") 
    
    """
    Si count_devoir = 1 : Seul le champ devoir_1 est visible.
    Si count_devoir = 2 : devoir_1 et devoir_2 sont visibles.
    Si count_devoir = 3 : Les trois champs sont visibles.
        """
    # Champs pour chacun des devoirs
    devoir_1 = fields.Float("Devoir 1")
    devoir_2 = fields.Float("Devoir 2") #
    devoir_3 = fields.Float("Devoir 3")
    
    # Champ calculé pour la moyenne des devoirs
    devoir = fields.Float("Devoir", compute="_compute_devoir", store=True, digits=(16,2))
    
    @api.depends('devoir_1', 'devoir_2', 'devoir_3', 'count_devoir')
    def _compute_devoir(self):
        for rec in self:
            if rec.count_devoir == 1:
                total = rec.devoir_1
            elif rec.count_devoir == 2:
                total = rec.devoir_1 + rec.devoir_2
            elif rec.count_devoir == 3:
                total = rec.devoir_1 + rec.devoir_2 + rec.devoir_3
            else:
                total = 0.0  
            rec.devoir = total / rec.count_devoir if rec.count_devoir else 0.0

    
    composition = fields.Float("Composition" , digits=(16,2))

    moyenne_provisoire = fields.Float("moyenne provisoire", compute="_compute_moyenne_prov", digits=(16,2))
    
    
   
    niveau_id = fields.Char(
         "niveau", help="Select Standard", related="exam_id.niveau_id.name"
    ) #niveau
    
    
    @api.depends("devoir", "composition")
    def _compute_moyenne_prov(self):
        for rec in self:
            # Gestion des valeurs None
            devoir = rec.devoir or 0
            composition = rec.composition or 0
            
            # Calcul selon le niveau
            if rec.niveau_id in ['CP1', 'CP2', 'CE1', 'CE2', 'CM1', 'CM2']:
                moyenne = composition
            else:
                moyenne = (devoir + composition) / 2
            
            # Arrondi explicite à 2 décimales
            moyenne_arrondie = round(float(moyenne), 2)
            
            # Validation
            if rec.maximum_marks and moyenne_arrondie > rec.maximum_marks:
                raise ValidationError(
                    f"La moyenne ({moyenne_arrondie}) dépasse la note maximale ({rec.maximum_marks})"
                )
                
            if rec.minimum_marks and moyenne_arrondie < rec.minimum_marks:
                raise ValidationError(
                    f"La moyenne ({moyenne_arrondie}) est inférieure au minimum ({rec.minimum_marks})"
                )
            
            # Assignation avec valeur arrondie
            rec.moyenne_provisoire = moyenne_arrondie
    

    valeur_sureogatoire = fields.Float(
        string="Valeur Surérogatoire",
        compute="_compute_valeur_sureogatoire",
        store=True,
        digits=(16,2),
        help="Valeur à ajouter ou soustraire pour les matières surérogatoires"
    )

    @api.depends("moyenne_provisoire", "subject_id", "exam_id.niveau_id")
    def _compute_valeur_sureogatoire(self):
        niveaux_sureogatoire_eps = [
            "2nde S", "2nde L", "1ère L1", "1ère L2",
            "Terminal L1", "Terminal L2", "1ère S1", "1ère S2",
            "Terminale S1", "Terminale S2"
        ]
        niveaux_sureogatoire_langue = ["2nde S", "1ère S1", "1ère S2"]
        
        for rec in self:
            valeur = 0.0
            niveau = rec.exam_id.niveau_id.name if rec.exam_id and rec.exam_id.niveau_id else ""
            subject_name = rec.subject_id.name if rec.subject_id and isinstance(rec.subject_id.name, str) else ""

            if niveau in niveaux_sureogatoire_eps and subject_name.lower() == "eps":
                if rec.moyenne_provisoire > 10:
                    valeur = rec.moyenne_provisoire - 10
                elif rec.moyenne_provisoire < 10:
                    valeur = -(10 - rec.moyenne_provisoire)

            elif niveau in niveaux_sureogatoire_langue:
                if subject_name.lower() in ["espagnol", "arabe", "économie"]:
                    if rec.moyenne_provisoire > 10:
                        valeur = rec.moyenne_provisoire - 10
                    elif rec.moyenne_provisoire < 10:
                        valeur = -(10 - rec.moyenne_provisoire)

            rec.valeur_sureogatoire = valeur


        
    obtain_marks = fields.Float("moyonne obtenue", group_operator="avg", compute="_compute_obtain_marks", digits=(16,2))
    
    
    @api.depends("moyenne_provisoire", "coefficient", "valeur_sureogatoire")
    def _compute_obtain_marks(self):
        for rec in self:
            # Pour les matières normales: moyenne * coefficient
            # Pour les matières surérogatoires: afficher la valeur à ajouter/soustraire
            if rec.valeur_sureogatoire != 0:
                rec.obtain_marks = rec.valeur_sureogatoire
            else:
                rec.obtain_marks = rec.moyenne_provisoire * rec.coefficient
           
            
           
    
    moyenne_prov_reeval = fields.Float("moyenne provisoire réeval ", help="moyenne provisoire réeval")
    
    marks_reeval = fields.Float("Marks After Re-evaluation", compute="_compute_marks_reeval") 
    
    @api.onchange("moyenne_prov_reeval")
    def _compute_marks_reeval(self):
        for rec in self:
            if rec.moyenne_prov_reeval != 0:
                rec.marks_reeval = rec.moyenne_prov_reeval * rec.coefficient
            else:
                rec.marks_reeval = 1
            
    dom_subject = fields.Many2one(string="Domaines", related="subject_id.domaine_subject")      
    #fin diw
    
    
    maximum_marks = fields.Float("Maximum marks", related="subject_id.maximum_marks", readonly=True, digits=(16,2))
    minimum_marks = fields.Float("Minimum marks", related="subject_id.minimum_marks", readonly=True, digits=(16,2))

    grade = fields.Char(
        "Grade", compute="_compute_grade_subject",  help="Grade Obtained"
    )
    
    grade_line_id = fields.Many2one(
        "grade.line", "Grade", compute="_compute_grade_subject", help="Grade"
    )
    
    note_maximale_grade = fields.Float(
    string="Note maximale",
    related="exam_id.note_maximale_grade",
    store=True,
    default=20.0, digits=(16,2))

    @api.onchange("exam_id", "moyenne_provisoire", "marks_reeval")
    def _compute_grade_subject(self):
        """Méthode pour calculer le grade après réévaluation"""
        for rec in self:
            rec.grade = False
            rec.grade_line_id = False

            if not rec.exam_id or not rec.exam_id.student_id:
                continue

            grade_lines = rec.exam_id.grade_system.grade_ids
            if not grade_lines:
                continue

            # Utiliser note_maximale_grade pour la normalisation
            max_subject_mark = rec.subject_id.maximum_marks or rec.note_maximale_grade

            if max_subject_mark != rec.note_maximale_grade:
                moyenne_norm = (rec.moyenne_provisoire / max_subject_mark) * rec.note_maximale_grade
            else:
                moyenne_norm = rec.moyenne_provisoire

            # Trouver le grade correspondant
            for grade_id in grade_lines:
                if grade_id.from_mark <= moyenne_norm <= grade_id.to_mark:
                    rec.grade = grade_id.grade
                    rec.grade_line_id = grade_id
                    break

            # Gestion de la moyenne de réévaluation
            if rec.marks_reeval:
                if max_subject_mark != rec.note_maximale_grade:
                    marks_reeval_norm = (rec.marks_reeval / max_subject_mark) * rec.note_maximale_grade
                else:
                    marks_reeval_norm = rec.marks_reeval

                for grade_id in grade_lines:
                    if grade_id.from_mark <= marks_reeval_norm <= grade_id.to_mark:
                        rec.grade_line_id = grade_id
                        break



    @api.constrains(
        "obtain_marks", "minimum_marks", "maximum_marks", "marks_reeval"
    )
    def _validate_marks(self):
        """Method to validate marks"""
        for rec in self:
            if rec.moyenne_provisoire > rec.maximum_marks:
                raise ValidationError(
                        _(
                    """The obtained marks should not extend maximum marks!"""
                        ))
            if rec.minimum_marks > rec.maximum_marks:
                raise ValidationError(
                    _(
                """The minimum marks should not extend maximum marks!"""
                    )
                )
            if rec.marks_reeval > rec.maximum_marks:
                raise ValidationError(
                    _(
                """The revaluation marks should not extend maximum marks!"""
                    )
                )


class AdditionalExamResult(models.Model):
    """Defining model for Additional Exam Result."""

    _name = "additional.exam.result"
    _description = "subject result Information"
    _rec_name = "roll_no"

    @api.onchange("a_exam_id", "obtain_marks")
    def _compute_student_result(self):
        """Method to compute result of student"""
        for rec in self:
            if rec.a_exam_id and rec.a_exam_id:
                if rec.a_exam_id.minimum_marks < rec.obtain_marks:
                    rec.result = "Pass"
                else:
                    rec.result = "Fail"

    a_exam_id = fields.Many2one(
        "additional.exam",
        "Additional Examination",
        required=True,
        help="Select Additional Exam",
    )
    student_id = fields.Many2one(
        "student.student", "Student Name", required=True, help="Select Student"
    )
    roll_no = fields.Integer(
        "Roll No", readonly=True, help="Student rol no."
    )
    standard_id = fields.Many2one(
        "school.standard", "Standard", readonly=True, help="School Standard"
    )
    obtain_marks = fields.Float("Obtain Marks", help="Marks obtain in exam")
    result = fields.Char(
        compute="_compute_student_result",
        string="Result",
        help="Result Obtained",
        store=True,
    )
    active = fields.Boolean(
        "Active", default=True, help="Activate/Deactivate record"
    )

    def _update_student_vals(self, vals):
        """This is the common method to update student
        record at creation and updation of the exam record"""
        student_rec = self.env["student.student"].browse(
            vals.get("student_id")
        )
        vals.update(
            {
                "roll_no": student_rec.roll_no,
                "standard_id": student_rec.standard_id.id,
            }
        )

    @api.model
    def create(self, vals):
        """Override create method to get roll no and standard"""
        if vals.get("student_id"):
            self._update_student_vals(vals)
        return super(AdditionalExamResult, self).create(vals)

    def write(self, vals):
        """Override write method to get roll no and standard"""
        if vals.get("student_id"):
            self._update_student_vals(vals)
        return super(AdditionalExamResult, self).write(vals)

    @api.onchange("student_id")
    def onchange_student(self):
        """ Method to get student roll no and standard by selecting student"""
        self.standard_id = self.student_id.standard_id.id
        self.roll_no = self.student_id.roll_no

    @api.constrains("obtain_marks")
    def _validate_obtain_marks(self):
        """Constraint to check obtain marks respective maximum marks"""
        if self.obtain_marks > self.a_exam_id.subject_id.maximum_marks:
            raise ValidationError(
                _(
                    """
                The obtained marks should not extend maximum marks!"""
                )
            )
