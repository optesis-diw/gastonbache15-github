# See LICENSE file for full copyright and licensing details.

# from cStringIO import StringIO
import base64
import calendar
import io
from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

try:
    import xlsxwriter
except BaseException:
    pass


class DailyAttendanceStudentRemark(models.TransientModel):
    _name = "monthly.attendance.wizard"
    _description = "Monthly Attendance Sheet"

    def _get_current_academic_year(self):
        return self.env["academic.year"].search([("current", "=", True)])

    academic_year_id = fields.Many2one(
        "academic.year",
        ondelete="restrict",
        string="Academic Session",
        default=lambda obj: obj.env["academic.year"].search(
            [("current", "=", True)]
        ),
    )
    course_id = fields.Many2one(
        "school.standard", "Semesters", ondelete="restrict"
    )
    
    
    user_id = fields.Many2one("school.teacher", "Teacher")
    month = fields.Selection(
        [
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        "Month",
    )
    month_str = fields.Char("Month")
    subject_ids = fields.Many2many(
        "subject.subject",
        "subject_wizard_rel",
        "subject_id",
        "wizard_id",
        "Subject",
        ondelete="restrict",
    )

    @api.onchange("month")
    def onchange_month(self):
        for rec in self:
            rec.month_str = ""
            if rec.month:
                months = {
                    "1": "January",
                    "2": "February",
                    "3": "March",
                    "4": "April",
                    "5": "May",
                    "6": "June",
                    "7": "July",
                    "8": "August",
                    "9": "September",
                    "10": "October",
                    "11": "November",
                    "12": "December",
                }
                rec.month_str = months.get(rec.month)
                

    def generate_attendance(self):
        # Parcourir chaque enregistrement.
        for rec in self:
            # Obtenir le dernier jour du mois spécifié dans l'année académique.
            last_day_month = calendar.monthrange(
                int(rec.academic_year_id.code), int(rec.month)
            )[1]

            # Obtenir l'année en cours à partir de stop_date.
            year_current = rec.academic_year_id.date_stop.year
            
            # Créer la chaîne de date pour le début du mois (1er jour du mois) au format "YYYY-MM-01". exemple: 2024-08-01
            start_date_str = f"{year_current}-{str(rec.month).zfill(2)}-01"
            
            # Créer la chaîne de date pour la fin du mois (dernier jour du mois) au format "YYYY-MM-DD 23:00:00".ex:2024-08-31
            end_date_str = f"{year_current}-{str(rec.month).zfill(2)}-{str(last_day_month).zfill(2)} 23:00:00"
            
            # Exécuter une requête SQL pour obtenir les identifiants de toutes les présences validées 
            # pour le cours et le mois spécifiés.
            self._cr.execute(
                """
                SELECT
                    id
                FROM
                    daily_attendance
                WHERE
                    state = 'validate' and
                    standard_id = %s and
                    date >= %s and
                    date <= %s ORDER BY user_id, date
                """,
                (rec.course_id.id, start_date_str, end_date_str),
            )
            # Si aucune donnée n'est trouvée, lever une erreur de validation.
            if not self._cr.fetchall():
                raise ValidationError(_("Data Not Found"))
        
        # Si aucun utilisateur n'est spécifié pour le rapport
        if not self.user_id:
            report_id = self.env.ref(
                "school_attendance.monthly_attendance_report"
            )
            
            # Retourner l'action du rapport avec les données lues.
            return report_id.report_action(self, data=self.read()[0], config=False)
           
    
    @api.model
    def _send_monthly_attendance(self):
        pr_mon = pre_month = (
            date.today().replace(day=1) - timedelta(days=1)
        ).month
        pr_mon = str(pr_mon)
        for subject in self.env["subject.subject"].search([]):
            for user in subject.teacher_ids:
                if int(pre_month) < 10:
                    pre_month = "0" + str(pre_month)
                academic_year = self.env["academic.year"].search(
                    [("current", "=", True)]
                )
                last_day_month = calendar.monthrange(
                    int(academic_year.code), int(pre_month)
                )[1]
                start_date_str = (
                    str(int(academic_year.code))
                    + "-"
                    + str(int(pre_month))
                    + "-01"
                )
                end_date_str = (
                    str(int(academic_year.code))
                    + "-"
                    + str(int(pre_month))
                    + "-"
                    + str(last_day_month)
                    + " 23:00:00"
                )
                self._cr.execute(
                    """select id
                                    from daily_attendance WHERE
                                    state = 'validate' and
                                    standard_id = %s and
                                    user_id = %s and
                                    date >= %s and
                                    date <= %s ORDER BY user_id,date
                                    """,
                    (
                        subject.course_id.id,
                        user.id,
                        start_date_str,
                        end_date_str,
                    ),
                )
                vals = {
                    "user_id": user.id,
                    "course_id": subject.course_id.id,
                    "month": pr_mon,
                    "subject_ids": [(6, 0, [subject.id])],
                }
                wizard = self.create(vals)
                wizard.onchange_month()
                attachment_id = wizard.generate_attendance()
                template_id = self.env["ir.model.data"].get_object_reference(
                    "school_attendance", "email_template_monthly_attendace"
                )[1]
                template_rec = self.env["mail.template"].browse(template_id)
                template_rec.write(
                    {"attachment_ids": [(6, 0, [attachment_id.id])]}
                )
                template_rec.send_mail(wizard.id, force_send=True)
        return True

    import calendar

    def get_total_class(self, rec, user, subject):
        total_class = 0
        
        # Récupération de l'utilisateur connecté
        user = self.env["res.users"].search([("name", "=", user)], limit=1)
        if not user:
            user = self.env.user  # Si l'utilisateur n'est pas trouvé, on prend l'utilisateur connecté

        # Vérification du sujet
        subject = self.env["subject.subject"].search([("id", "=", subject)], limit=1)

        # Calcul de la période du mois
        last_day_month = calendar.monthrange(int(rec.academic_year_id.code), int(rec.month))[1]
        start_date_str = f"{int(rec.academic_year_id.code)}-{int(rec.month)}-01"
        end_date_str = f"{int(rec.academic_year_id.code)}-{int(rec.month)}-{last_day_month} 23:00:00"

        # Exécution de la requête SQL
        self._cr.execute(
            """
            SELECT COUNT(id)
            FROM daily_attendance
            WHERE state = 'validate'
            AND standard_id = %s
            AND user_id = %s
            AND date >= %s
            AND date <= %s
            """,
            (rec.course_id.id, user.id, start_date_str, end_date_str),
        )

        total_class = self._cr.fetchone()[0] or 0

        total_class_att = {"total": total_class}
        class_str = "Total No. of Combined Classes: " if total_class else "Total No. of Classes: "
        class_str += str(total_class) if total_class else ""

        return class_str, total_class_att


    def print_report(self):
        attch_obj = self.env["ir.attachment"]
        fp = io.BytesIO()
        
        for rec in self:
            months = {
                "1": "January", "2": "February", "3": "March",
                "4": "April", "5": "May", "6": "June",
                "7": "July", "8": "August", "9": "September",
                "10": "October", "11": "November", "12": "December"
            }
            
            year = int(rec.academic_year_id.code)
            month = int(rec.month)
            days_in_month = calendar.monthrange(year, month)[1]
            month_days = range(1, days_in_month + 1)
            
            # Date range for the query
            start_date = f"{year}-{str(month).zfill(2)}-01"
            end_date = f"{year}-{str(month).zfill(2)}-{days_in_month} 23:59:59"

            # Get validated attendance records
            self._cr.execute("""
                SELECT id FROM daily_attendance
                WHERE state = 'validate'
                AND standard_id = %s
                AND date >= %s 
                AND date <= %s
                ORDER BY user_id, date
            """, (rec.course_id.id, start_date, end_date))
            
            attendance_ids = [x[0] for x in self._cr.fetchall() if x and x[0]]
            
            if not attendance_ids:
                raise ValidationError(_("No attendance data found for this period"))

            # Group attendance by user and date
            group_data = []
            for att in self.env["daily.attendance"].browse(attendance_ids):
                date_str = att.date.strftime("%Y-%m-%d")
                
                # Find or create user group
                user_group = next(
                    (g for g in group_data if g["user"].id == att.user_id.id), 
                    None
                )
                
                if not user_group:
                    user_group = {
                        "user": att.user_id,
                        "att_ids": [],
                        "divisions": att.standard_id.division_id.name if att.standard_id.division_id else ""
                    }
                    group_data.append(user_group)
                
                # Find or create date entry
                date_entry = next(
                    (d for d in user_group["att_ids"] if d["date"] == date_str),
                    None
                )
                
                if not date_entry:
                    date_entry = {"date": date_str, "att": []}
                    user_group["att_ids"].append(date_entry)
                
                date_entry["att"].append(att)

            # Process attendance data for each student
            res_data = []
            for gdata in group_data:
                student_data = {}
                
                for attdata in gdata["att_ids"]:
                    day = int(attdata["date"].split("-")[2])
                    
                    for att in attdata["att"]:
                        for line in att.line_ids:
                            if line.stud_id.id not in student_data:
                                student_data[line.stud_id.id] = {
                                    "roll_no": line.stud_id.roll_no,
                                    "student_code": line.stud_id.student_code,
                                    "name": line.stud_id.name,
                                    "school_name": line.stud_id.school_id.name,
                                    "divisions": gdata["divisions"],
                                    "att": {},
                                    "total_present": 0,
                                    "total_absent": 0
                                }
                            
                            # Mark attendance for this day
                            status = "P" if line.is_present else "A"
                            student_data[line.stud_id.id]["att"][day] = status
                            
                            # Update totals
                            if line.is_present:
                                student_data[line.stud_id.id]["total_present"] += 1
                            else:
                                student_data[line.stud_id.id]["total_absent"] += 1

                # Sort students by roll number
                sorted_students = sorted(
                    student_data.values(), 
                    key=lambda x: x["roll_no"]
                )
                
                res_data.append({
                    "user": gdata["user"].name,
                    "month": f"{months[rec.month]}-{year}",
                    "semester": rec.course_id.name,
                    "result_data": sorted_students,
                    "school_name": sorted_students[0]["school_name"] if sorted_students else ""
                })

            # Excel file generation
            workbook = xlsxwriter.Workbook(fp)
            
            # Formats
            header_format = workbook.add_format({
                "bold": True, "border": 1, "align": "center", 
                "bg_color": "#D3D3D3", "font_size": 10
            })
            
            cell_format = workbook.add_format({
                "border": 1, "font_size": 10, "align": "center"
            })
            
            name_format = workbook.add_format({
                "border": 1, "font_size": 10
            })
            
            title_format = workbook.add_format({
                "bold": True, "align": "center", "font_size": 14,
                "bg_color": "#DCDCDC", "border": 1
            })

            for data in res_data:
                sheet = workbook.add_worksheet(data["user"][:31])  # Limit sheet name length
                
                # Set column widths
                sheet.set_column(0, 0, 5)    # Sn.
                sheet.set_column(1, 1, 30)   # Name
                sheet.set_column(2, 2, 10)   # Reg. No
                sheet.set_column(3, days_in_month + 2, 3)  # Day columns
                
                # Headers
                sheet.merge_range(
                    0, 0, 0, days_in_month + 3,
                    data["school_name"], title_format
                )
                
                sheet.write(1, 0, f"Teacher: {data['user']}", header_format)
                sheet.write(1, 10, f"Month: {data['month']}", header_format)
                sheet.write(1, 20, "Key: P=Present, A=Absent", header_format)
                sheet.write(1, 30, f"Class: {data['semester']}", header_format)
                
                # Column headers
                sheet.write(3, 0, "Sn.", header_format)
                sheet.write(3, 1, "Name", header_format)
                sheet.write(3, 2, "Reg. No", header_format)
                
                for day in month_days:
                    sheet.write(3, 2 + day, day, header_format)
                
                sheet.write(3, days_in_month + 3, "P", header_format)
                sheet.write(3, days_in_month + 4, "A", header_format)

                # Student data
                for row, student in enumerate(data["result_data"], 4):
                    sheet.write(row, 0, row - 3, cell_format)  # Serial number
                    sheet.write(row, 1, student["name"], name_format)
                    sheet.write(row, 2, student["student_code"], cell_format)
                    
                    # Daily attendance
                    for day in month_days:
                        status = student["att"].get(day, "")
                        sheet.write(row, 2 + day, status, cell_format)
                    
                    # Totals - CORRECTION PRINCIPALE ICI
                    sheet.write(row, days_in_month + 3, student["total_present"], cell_format)
                    sheet.write(row, days_in_month + 4, student["total_absent"], cell_format)

            workbook.close()
            
            # Save and return the file
            file_data = base64.b64encode(fp.getvalue())
            fp.close()
            
            # Clean up old attachments
            self.env["ir.attachment"].search([
                ("res_model", "=", "monthly.attendance.wizard")
            ]).unlink()
            
            # Create new attachment
            doc_id = attch_obj.create({
                "name": f"{months[rec.month]} {rec.course_id.name} Monthly Attendance.xlsx",
                "datas": file_data,
                "res_model": "monthly.attendance.wizard",
            })
            
            return {
                "type": "ir.actions.act_url",
                "url": f"web/content/{doc_id.id}?download=true",
                "target": "current",
            }