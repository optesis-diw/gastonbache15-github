# See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
    
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






    def action_generate_lines(self):
        """Generate subjects and associated exam timetable lines."""
        for record in self:
            if record.standard_id:
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

    #Méthode pour vérifier la contrainte de la date de début et de la date de fin de l'examen.
    @api.constrains("start_date", "end_date")
    def check_date_exam(self):
        """Method to check constraint of exam start date and end date."""
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
                                    """Invalid Exam Schedule!
                                    \n\nExam Dates must be in between Start date and End date !"""
                                )
                            )
                            
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
    standard_id = fields.Many2many(
        "standard.standard",
        "standard_standard_exam_rel",
        "standard_id",
        "event_id",
        "Participant Standards",
        help="Select Standard",
    )
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
    grade_system = fields.Many2one(
        "grade.master", "Grade System", help="Select Grade System"
    )
    academic_year = fields.Many2one(
        "academic.year", "Academic Year", help="Select Academic Year"
    )
    exam_schedule_ids = fields.One2many(
        "exam.schedule.line",
        "exam_id",
        "Exam Schedule",
        help="Enter exam schedule",
    )#calendrier des examens

    def set_to_draft(self):
        """Method to set state to draft"""
        self.state = "draft"

    def set_running(self):
        """Method to set state to running"""
        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_("Please Select Standard!"))
            if rec.exam_schedule_ids:
                rec.state = "running"
            else:
                raise ValidationError(_("You must add one Exam Schedule!"))

    def set_finish(self):
        """Method to set state to finish"""
        self.state = "finished"

    def set_cancel(self):
        """Method to set state to cancel"""
        self.state = "cancelled"

    #cette méthode permet de générer des résultats d'examen pour chaque étudiant inscrit, en créant des enregistrements de résultat si nécessaire    
    def generate_result(self):
        """Method to generate result"""
        result_obj = self.env["exam.result"]
        student_obj = self.env["student.student"]
        result_list = []
        for rec in self:
            #parcourt l'objet exam_schedule = calendrier exam, Pr rechercher la class, year, school
            for exam_schedule in rec.exam_schedule_ids: 
                #on a utilisé 1 domaine pr rechercher ls étudiants qui ont été inscrits à l'examen.
                domain = [
                    ("standard_id", "=", exam_schedule.standard_id.id),
                    ("year", "=", rec.academic_year.id),
                    ("state", "=", "done"),
                    ("school_id", "=", exam_schedule.standard_id.school_id.id),
                ]
                students_rec = student_obj.search(domain)
                
                
                #Pour chaque étudiant trouvé
                for student in students_rec:
                    #on a utilise 1 domaine pour rechercher s'il y a déjà un résultat à cet examen
                    domain = [
                        ("standard_id", "=", student.standard_id.id),
                        ("student_id", "=", student.id),
                        ("s_exam_ids", "=", rec.id),
                    ]
                    exam_result_rec = result_obj.search(domain) 
                    
                    #si l'etudiant a deja 1 resultat, l'identifiant du resultat est ajouté à la liste "result_list
                    if exam_result_rec:
                        [result_list.append(res.id) for res in exam_result_rec]
                    #sinon on crée un nouvel enregistrement exam.result pr cet étudiant à cet exam
                    else:
                        rs_dict = {
                            "s_exam_ids": rec.id,
                            "student_id": student.id,
                            "standard_id": student.standard_id.id,
                            "roll_no": student.roll_no,
                            "grade_system": rec.grade_system.id,
                        }
                        exam_line = []
                        timetable = exam_schedule.sudo().timetable_id
                        for line in timetable.sudo().timetable_ids:
                            min_mrks = line.subject_id.minimum_marks
                            max_mrks = line.subject_id.maximum_marks
                            sub_vals = {
                                "subject_id": line.subject_id.id,
                                "minimum_marks": min_mrks,
                                "maximum_marks": max_mrks,
                            }
                            exam_line.append((0, 0, sub_vals))
                        rs_dict.update({"result_ids": exam_line})
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
    maximum_marks = fields.Integer(
        "Maximum Mark", help="Minimum Marks of exam"
    )
    minimum_marks = fields.Integer(
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

    #add by diw yowit
    retards = fields.Integer("Retards")
    absences = fields.Integer("absences")

    annee_scolaire = fields.Many2one('academic.year', 'Academic Year', related="student_id.year")

    year_date_start_s = fields.Char(string="Year Date Start", related="student_id.year_date_start_s")
    year_date_stop_s = fields.Char(string="Year Date Stop", related="student_id.year_date_stop_s")


    class_redouble = fields.Integer(string="Classe redoublée")

    

    
    

    #diw :pour t'entéte
    session = fields.Selection(
        [("premier_semestre", "1er semestre"),
            ("second_semestre", "2éme semestre"),
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
    
    
    
    """
    @api.depends(
        "result_ids", "result_ids.obtain_marks", "result_ids.marks_reeval"
    )
    def _compute_total(self):
        for rec in self:
            total = 0.0
            if rec.result_ids:
                for line in rec.result_ids:
                    obtain_marks = line.obtain_marks
                    if line.state == "re-evaluation":
                        obtain_marks = line.marks_reeval
                    total += obtain_marks
            rec.total = total
   

    @api.depends('total', 'result_ids.obtain_marks', 'result_ids.marks_reeval', 'result_ids.state', 'result_ids.coefficient')
    def _compute_per(self):
         
        for result in self:
            total = 0.0
            obtained_total = 0.0
            per = 0.0
            coefficient= 0.0
            result.grade = ""
            for sub_line in result.result_ids:
                obtain_marks = sub_line.marks_reeval if sub_line.state == "re-evaluation" else sub_line.obtain_marks
                coefficient += sub_line.coefficient or 1.0
                total = (sub_line.maximum_marks or 0) * coefficient
                obtained_total += obtain_marks or 0
                
            if total > 0:
                per = (obtained_total / total) * 100
                result.percentage = per
                if result.grade_system:
                    grade_found = False
                    for grade_id in result.grade_system.grade_ids:
                        if grade_id.from_mark <= per <= grade_id.to_mark:
                            result.grade = grade_id.grade or ""
                            grade_found = True
                            break
                        else:
                            result.grade = ""
                            
                    if not grade_found:
                        result.grade = ""
            else:
                result.percentage = 0.0
                result.grade = ""
                        
    """


    

    @api.onchange('total', 'result_ids.obtain_marks', 'result_ids.marks_reeval', 'result_ids.coefficient', 'result_ids.state')
    def _compute_grade(self):
        """Méthode pour calculer la moyenne, le grade et le percentage en excluant certaines matières du calcul pondéré et en ajustant la moyenne"""
        niveaux_surérogatoire_eps = ["2nde S", "2nde L", "1ère L1", "1ère L2", "Terminal L1", "Terminal L2", "1ère S1", "1ère S2", "Terminale S1", "Terminale S2"]
        niveaux_surérogatoire_langue = ["2nde S", "1ère S1", "1ère S2"]
        
        for result in self:
            moyenne_provisoire = 0.0
            obtained_total = 0.0  # Somme des notes obtenues (hors exclusions= sauf les matiéres surérogatoires)
            somme_coef = 0.0  # Somme des coefficients (hors exclusions)
            somme_maximum_marks = 0.0  # Somme des maximum_marks (hors exclusions)
            nombre_matieres = 0  # Nombre total de matières (hors exclusions)
            
            note_eps = None #moyenne eps (seconde à la terminal)
            note_e_a = None #moyenne Espagnol ou Arabe (2nde S et 1ère S)
            note_ec = None
            
            result.somme_obtain_marks = 0.0
            result.somme_coef = 0.0
            result.grade = ""
            result.moyenne = 0.0
            result.result = ""
            result.percentage = 0.0

            for sub_line in result.result_ids:
                obtain_marks = sub_line.obtain_marks
                moyenne_provisoire = sub_line.moyenne_provisoire
                
                #On prend la moyenne provisoire pour les matières surérogatoires, car leurs coefficients sont 0.
                if result.niveau_id.name in niveaux_surérogatoire_eps and sub_line.subject_id.name.lower() == "eps":
                    note_eps = moyenne_provisoire or 0.0  # Stocke la note EPS sur obtained_total
                    continue  # On exclut EPS du calcul pondéré
                
                if result.niveau_id.name in niveaux_surérogatoire_langue and (sub_line.subject_id.name.lower() == "espagnol" or sub_line.subject_id.name.lower() == "arabe"):
                    note_e_a = moyenne_provisoire or 0.0  # Stocke la note Espagnol / Arabe
                    continue  # On exclut Espagnol / Arabe du calcul pondéré

                
                if result.niveau_id.name in niveaux_surérogatoire_langue and sub_line.subject_id.name.lower() == "ec":
                    note_ec = moyenne_provisoire or 0.0  # Stocke la note EC
                    continue  # On exclut EC du calcul pondéré
                
                obtained_total += obtain_marks or 0.0
                somme_coef += sub_line.coefficient or 0.0
                somme_maximum_marks += sub_line.maximum_marks or 0.0
                nombre_matieres += 1

            result.somme_coef = somme_coef
            result.somme_obtain_marks = obtained_total

            if somme_coef > 0 and nombre_matieres > 0:
                
                # Ajustement avec EPS uniquement pour les niveaux concernés
                if result.niveau_id.name in niveaux_surérogatoire_eps and note_eps is not None:
                    if note_eps > 10:
                        obtained_total += (note_eps - 10)
                    elif note_eps < 10:
                        obtained_total -= (10 - note_eps)

                # Ajustement avec Espagnol / Arabe et EC uniquement pour les niveaux concernés
                if result.niveau_id.name in niveaux_surérogatoire_langue:
                    if note_e_a is not None:
                        if note_e_a > 10:
                            obtained_total += (note_e_a - 10)
                        elif note_e_a < 10:
                            obtained_total -= (10 - note_e_a)

                    if note_ec is not None:
                        if note_ec > 10:
                            obtained_total += (note_ec - 10)
                        elif note_ec < 10:  # Correction ici : on vérifie bien note_ec et pas note_eps
                            obtained_total -= (10 - note_ec)

                # Mise à jour du total avec les matières surérogatoires
                result.total = obtained_total

                
                moyenne_total = obtained_total / somme_coef  # Moyenne pondérée classique
                #si la moyenne de la classe est supérieure à 20
                maximum_marks_class = somme_maximum_marks / nombre_matieres  # Moyenne maximale
                
                #la moyenne de la classe est > 20
                moyenne_norm = (moyenne_total * 20) / maximum_marks_class if maximum_marks_class > 0 else 0.0
                
                result.moyenne = moyenne_norm
                
                # Calcul du percentage
                result.percentage = (moyenne_norm / 20) * 100

                # Attribution du grade
                if result.grade_system:
                    grade_found = False
                    for grade_id in result.grade_system.grade_ids:
                        if grade_id.from_mark <= moyenne_norm <= grade_id.to_mark:
                            result.grade = grade_id.grade or ""
                            grade_found = True
                            break
                    if not grade_found:
                        result.grade = ""

                # Résultat final : Pass si moyenne >= 10
                result.result = "Pass" if result.moyenne >= 10 else "Fail"
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

    
    moyenne = fields.Float("Moyenne", compute="_compute_grade")
    somme_coef = fields.Float("somme coef", compute="_compute_grade")
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
    
    @api.onchange('total', 's_exam_ids', 'session')  # Déclencher le calcul du rang quand `total`, `s_exam_ids` ou `session` changent
    def _compute_rang_exam(self):
        for rec in self:
            if rec.s_exam_ids:  
                # Vérifier que la session et l'examen sont valides
                if rec.session and rec.s_exam_ids:
                    # Rechercher tous les résultats pour le même examen et la même session
                    exam_results = self.env['exam.result'].search([
                        ('s_exam_ids', '=', rec.s_exam_ids.id),
                        ('standard_id', '=', rec.standard_id.id)
                        
                    ])
                    
                    # Vérifier si des résultats existent
                    if exam_results:
                        # Trier les résultats par `total` (note obtenue) décroissant
                        sorted_results = exam_results.sorted(key=lambda r: r.total or 0, reverse=True)
                        
                        # Mise à jour des rangs en une seule opération
                        for idx, result in enumerate(sorted_results, start=1):
                            result.rang = idx  # Assigner le rang selon la position
                    else:
                        rec.rang = 1  # Si aucun résultat, définir rang à 0
                else:
                    rec.rang = 0  # Si pas de session ou examen, définir rang à 0
            else:
                rec.rang = 0  # Aucun examen associé → rang = 0
                
                    
    moyenne_second_semester = fields.Float(string='Moyenne 2em Semester', compute='_compute_moyenne_semestre')

    moyenne_prem_semester = fields.Float(string='Moyenne 1er Semester', compute='_compute_moyenne_semestre')

    moyenne_annuel = fields.Float(string='Moyenne A', compute='_compute_moyenne_semestre')

    
    
    

    @api.depends('student_id', 'moyenne', 'session', 'annee_scolaire')
    def _compute_moyenne_semestre(self):
        for record in self:
            _logger.info(f"Calcul de la moyenne pour {record.student_id.name}, Session: {record.session}")
            if record.session == "premier_semestre":
                record.moyenne_prem_semester = record.moyenne or 0.0
                record.moyenne_second_semester = 0.0
                record.moyenne_annuel = 0.0

                _logger.info(f"Premier semestre détecté, moyenne: {record.moyenne_prem_semester}")

            elif record.session == "second_semestre":
                # Rechercher la moyenne du premier semestre
                premier_semestre_result = self.env['exam.result'].search([
                    ('student_id', '=', record.student_id.id),
                    ('annee_scolaire', '=', record.annee_scolaire.id),
                    ('session', '=', 'premier_semestre')
                ], order="id desc", limit=1)

                if premier_semestre_result:
                    record.moyenne_prem_semester = premier_semestre_result.moyenne
                    _logger.info(f"Moyenne du premier semestre trouvée: {record.moyenne_prem_semester}")
                else:
                    record.moyenne_prem_semester = 0.0
                    _logger.warning(f"Aucune moyenne trouvée pour le premier semestre de {record.student_id.name}")

                record.moyenne_second_semester = record.moyenne or 0.0
                record.moyenne_annuel = (record.moyenne_prem_semester + record.moyenne_second_semester) / 2.0

                _logger.info(f"Moyenne annuelle calculée: {record.moyenne_annuel}")

            else:
                record.moyenne_prem_semester = 0.0
                record.moyenne_second_semester = 0.0
                record.moyenne_annuel = 0.0

    @api.constrains('student_id', 'session', 'annee_scolaire')
    def _check_unique_session_per_year(self):
        """Empêcher un élève d'avoir deux sessions identiques et forcer le second semestre si nécessaire"""
        for record in self:
            # Vérifier si une session identique existe déjà
            existing_sessions = self.env['exam.result'].search([
                ('student_id', '=', record.student_id.id),
                ('annee_scolaire', '=', record.annee_scolaire.id),
                ('session', '=', record.session),
                ('id', '!=', record.id)  # Exclure l'enregistrement actuel
            ])
            if existing_sessions:
                raise ValidationError(
                    f"L'élève {record.student_id.name} a déjà une session '{dict(self.fields_get('session')['session']['selection'])[record.session]}' pour l'année scolaire {record.annee_scolaire.name}."
                )

            # Vérifier si un "premier_semestre" existe déjà
            existing_premier_semestre = self.env['exam.result'].search([
                ('student_id', '=', record.student_id.id),
                ('annee_scolaire', '=', record.annee_scolaire.id),
                ('session', '=', 'premier_semestre'),
                ('id', '!=', record.id)
            ], limit=1)

            if existing_premier_semestre and record.session == 'premier_semestre':
                raise ValidationError(
                    f"L'élève {record.student_id.name} a déjà un 'Premier Semestre' pour l'année {record.annee_scolaire.name}. Il ne peut pas en avoir un deuxième !"
                )

            # Si l'élève a déjà un "premier_semestre", forcer la session en "second_semestre"
            if existing_premier_semestre and record.session != 'second_semestre':
                raise ValidationError(
                    f"L'élève {record.student_id.name} a déjà un 'Premier Semestre'. Sa prochaine session doit être 'Second Semestre' !"
                )

                     

    #diw

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
        [("premier_semestre", "1er semestre"),
            ("second_semestre", "2éme semestre"),
        ],"session", required=True, related="exam_id.session")
    
   
   

    rang = fields.Integer(string='Rang', compute='_compute_rang')

    @api.onchange('moyenne_provisoire', 'exam_id', 'session')
    def _compute_rang(self):
        for rec in self:
            if rec.exam_id:
                if rec.s_exam_ids and rec.standard_subject:
                    exam_results = self.env['exam.result'].search([
                        ('s_exam_ids', '=', rec.s_exam_ids.id),
                        ('standard_id', '=', rec.standard_subject.id),
                        ('session', '=', rec.session)
                    ])

                    if exam_results:

                        subject_results = {}

                        for result in exam_results:
                            for subject in result.result_ids:
                                if subject.subject_id:
                                    subject_id = subject.subject_id.id
                                    if subject_id not in subject_results:
                                        subject_results[subject_id] = []
                                    subject_results[subject_id].append(subject)

                        for subject_id, subjects in subject_results.items():
                            sorted_subjects = sorted(subjects, key=lambda s: s.moyenne_provisoire or 0, reverse=True)
                            for idx, subject in enumerate(sorted_subjects, start=1):
                                subject.rang = idx
                    else:
                        rec.rang = 1
                        
                else:
                    rec.rang = 0

    
    devoir = fields.Float("Devoir")
    
    composition = fields.Float("Composition" )
    
    #diw coefficient = fields.Integer("Coefficient", default=1, related="subject_id.coefficient")
    
   
    
    cycle_id = fields.Many2one(related="standard_subject.medium_id")

    
    cycle_name = fields.Char(related="cycle_id.name")


    subject_name = fields.Char(related="subject_id.name")



    coefficient = fields.Integer("Coefficient", compute="_compute_coefficient", readonly=False)

    COEFFICIENTS = {
    "Élémentaire": {
        "Langue et Communication / Français - Ressources": 1,
        "Langue et Communication / Français - Compétence": 1,
        "Math - Ressources": 1,
        "Math - Compétence": 1,
        "Découverte du Monde – Ressources (HG – IST)": 1,
        "Découverte du Monde - Compétence": 1,
        "Éducation au Développement Durable - Ressources (Vivre Ensemble – Vivre dans son Milieu)": 1,
        "Éducation au Développement Durable - Compétence": 1,
        "EPS": 1,
        "Éducation Artistique / Dessin / Art Plastique": 1,
        "Éducation Musicale (Récitation / Chant)": 1,
        "Arabe": 1,
        "Anglais": 1,
    },
    "Collége": {
        "Expression Ecrite / Rédaction / Dissertation": 2,
        "Dictée / Orthographe": 1,
        "TSQ": 1,
        "Math": 3,
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
        "Math": 2,
        "SVT": 2,  # SVT OU PC
        "PC": 2,
        
    },
    "TL1 et 1ère L1": {
        "Français": 6,
        "LV1 Écrit": 4,
        "LV1 Oral": 2,
        "Langue Vivante 2": 4,
        "Philo": 4,  # Seulement en Tle
        "HG": 2,
        "Math": 2,
        
    },
    "TS2 et 1ère S2": {
        "SVT": 6,
        "PC": 6,
        "Math": 5,
        "Français": 3,
        "Philo": 2,  # Seulement en Tle
        "Anglais": 2,
        "HG": 2,
        
    },
    "TS1 et 1ère S1": {
        "Math": 8,
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
        "EC": 2,
        "Math": 2,
        "SVT": 2,  # SVT ou PC
        "PC": 2,
        
    },
    "2nd S": {
        "SVT": 5,
        "Math": 5,
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


    moyenne_provisoire = fields.Float("moyenne provisoire", compute="_compute_moyenne_prov")
    
    
   

    @api.onchange("devoir", "composition")
    def _compute_moyenne_prov(self):
        for rec in self:
            if rec.devoir == 0 and rec.composition == 0:
                rec.moyenne_provisoire = 1
            else:
                moyenne = (rec.devoir + rec.composition) / 2

                # Vérification des bornes
                if moyenne > rec.maximum_marks:
                    raise ValidationError(f"La moyenne provisoire ({moyenne}) ne peut pas dépasser la note maximale ({rec.maximum_marks}).")
                
                if moyenne < rec.minimum_marks:
                    raise ValidationError(f"La moyenne provisoire ({moyenne}) ne peut pas être inférieure à la note minimale ({rec.minimum_marks}).")

                rec.moyenne_provisoire = moyenne


        
    obtain_marks = fields.Float("moyonne obtenue", group_operator="avg", compute="_compute_obtain_marks")
    
    
    @api.onchange("moyenne_provisoire")
    def _compute_obtain_marks(self):
        for rec in self:
            if rec.moyenne_provisoire != 0:
                rec.obtain_marks = rec.moyenne_provisoire * rec.coefficient
            else:
                rec.obtain_marks = 1
            
           
    
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
    
    
    maximum_marks = fields.Integer("Maximum marks", related="subject_id.maximum_marks", readonly=True)
    minimum_marks = fields.Integer("Minimum marks", related="subject_id.minimum_marks", readonly=True)

    grade = fields.Char(
        "Grade", compute="_compute_grade_subject",  help="Grade Obtained"
    )
    
    grade_line_id = fields.Many2one(
        "grade.line", "Grade", compute="_compute_grade_subject", help="Grade"
    )
    
    # utilisée pr savoir le grade de étudiant pour chaque subjecthh
    @api.onchange("exam_id", "moyenne_provisoire", "marks_reeval")
    def _compute_grade_subject(self):
        """Méthode pour calculer le grade après réévaluation"""
        for rec in self:
            rec.grade = False  # Assurer qu'une valeur est toujours assignée
            rec.grade_line_id = False  

            if not rec.exam_id or not rec.exam_id.student_id:
                continue  # Sécurité : si pas d'examen ou d'étudiant, on passe

            grade_lines = rec.exam_id.grade_system.grade_ids
            if not grade_lines:
                continue  # Si aucun système de notation défini, on ignore

            # Vérifier si l'échelle est différente de 20 pour normaliser
            max_subject_mark = rec.subject_id.maximum_marks or 20 
            
            if max_subject_mark != 20:
                moyenne_norm = (rec.moyenne_provisoire / max_subject_mark) * 20
                
            else:
                moyenne_norm = rec.moyenne_provisoire

            # Vérifier si la moyenne normalisée est dans la plage d'un grade
            for grade_id in grade_lines:
                if grade_id.from_mark <= moyenne_norm <= grade_id.to_mark:
                    rec.grade = grade_id.grade
                    rec.grade_line_id = grade_id
                    break  # Dès qu'on trouve un grade correspondant, on sort

            # Vérification de la moyenne de réévaluation
            if rec.marks_reeval:
                if max_subject_mark != 20:
                    marks_reeval_norm = (rec.marks_reeval / max_subject_mark) * 20
                else:
                    marks_reeval_norm = rec.marks_reeval

                for grade_id in grade_lines:
                    if grade_id.from_mark <= marks_reeval_norm <= grade_id.to_mark:
                        rec.grade_line_id = grade_id  # Mettre à jour le grade si nécessaire
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
