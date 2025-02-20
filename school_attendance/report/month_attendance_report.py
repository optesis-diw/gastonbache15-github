# See LICENSE file for full copyright and licensing details.

import calendar
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import _, api, fields, models


class ReportMonthAttendace(models.AbstractModel):
    _name = "report.school_attendance.monthly_attendance_report_tmpl"
    _description = "Monthly Attendance Report"

    def get_dates(self, rec):
        days_of_month = calendar.monthrange(
            int(rec.academic_year_id.code), int(rec.month)
        )[1]
        return range(1, days_of_month + 1)

    def get_data(self, rec):
        
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
        group_data = []
        month = rec.month
        if int(rec.month) < 10:
            month = "0" + rec.month
            last_day_month = calendar.monthrange(
                int(rec.academic_year_id.code), int(rec.month)
            )[1]

            # Obtenir l'année en cours à partir de stop_date.
            year_current = rec.academic_year_id.date_stop.year
            
            # Créer la chaîne de date pour le début du mois (1er jour du mois) au format "YYYY-MM-01". exemple: 2024-08-01
            start_date_str = f"{year_current}-{str(rec.month).zfill(2)}-01"
            
            # Créer la chaîne de date pour la fin du mois (dernier jour du mois) au format "YYYY-MM-DD 23:00:00".ex:2024-08-31
            end_date_str = f"{year_current}-{str(rec.month).zfill(2)}-{str(last_day_month).zfill(2)} 23:00:00"
        else:
            month = rec.month
            last_day_month = calendar.monthrange(
                int(rec.academic_year_id.code), int(rec.month)
            )[1]

            # Obtenir l'année en cours à partir de stop_date.
            year_current = rec.academic_year_id.date_stop.year
            
            # Créer la chaîne de date pour le début du mois (1er jour du mois) au format "YYYY-MM-01". exemple: 2024-08-01
            start_date_str = f"{year_current}-{month}-01"

            # Créer la chaîne de date pour la fin du mois (dernier jour du mois) au format "YYYY-MM-DD 23:00:00"
            end_date_str = f"{year_current}-{month}-{str(last_day_month).zfill(2)} 23:00:00"
     
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
                date <= %s ORDER BY user_id,date
            """,
            (rec.course_id.id, start_date_str, end_date_str),
        )
        
        records = []
        for record in self._cr.fetchall():
            if record and record[0]:
                records.append(record[0])
        for att in self.env["daily.attendance"].browse(records):
            date = datetime.strptime(str(att.date), "%Y-%m-%d")
            day_date = date.strftime("%Y-%m-%d")
            if not group_data:
                group_data.append(
                    {
                        "user": att.user_id,
                        "school_name": att.user_id.sudo().school_id.name,
                        "att_ids": [{"date": day_date, "att": [att]}],
                    }
                )
            else:
                flag = False
                for gdata in group_data:
                    if gdata.get("user").id == att.user_id.id:
                        flag = True
                        flag_date = False
                        for att_id in gdata.get("att_ids"):
                            if att_id.get("date") == day_date:
                                flag_date = True
                                att_id.get("att").append(att)
                                break
                        if not flag_date:
                            gdata.get("att_ids").append(
                                {"date": day_date, "att": [att]}
                            )
                if not flag:
                    group_data.append(
                        {
                            "user": att.user_id,
                            "school_name": att.user_id.sudo().school_id.name,
                            "att_ids": [{"date": day_date, "att": [att]}],
                        }
                    )
        res_data = []
        for gdata in group_data:
            result_data = []
            att_data = {}
            data = []
            days_of_month = calendar.monthrange(
                int(rec.academic_year_id.code), int(date.strftime("%m"))
            )[1]
            for attdata in gdata.get("att_ids"):
                date = datetime.strptime(attdata.get("date"), "%Y-%m-%d")
                day_date = int(date.strftime("%d"))
                for att in attdata.get("att"):
                    no_of_class = 1
                    self._cr.execute(
                        """
                            SELECT
                                id
                            FROM
                                daily_attendance_line
                            WHERE
                                standard_id = %s
                            ORDER BY roll_no
                        """,
                        (att.id,),
                    )
                    lines = []
                    for line in self._cr.fetchall():
                        if line and line[0]:
                            lines.append(line[0])
                    matched_dates = []
                    for student in self.env["daily.attendance.line"].browse(
                        lines
                    ):
                        for att_count in range(1, days_of_month + 1):
                            if day_date == att_count:
                                status = "A"
                                if student.is_present:
                                    status = no_of_class
                                    if (
                                        day_date in matched_dates
                                        or not matched_dates
                                    ):
                                        if att_data.get(
                                            student.stud_id.name
                                        ) and att_data.get(
                                            student.stud_id.name
                                        ).get(
                                            att_count
                                        ):
                                            if (
                                                att_data.get(
                                                    student.stud_id.name
                                                ).get(att_count)
                                                != "A"
                                            ):
                                                status = (
                                                    int(
                                                        att_data.get(
                                                            student.stud_id.name
                                                        ).get(att_count)
                                                    )
                                                    + no_of_class
                                                )
                                else:
                                    if day_date in matched_dates:
                                        if att_data.get(
                                            student.stud_id.name
                                        ) and att_data.get(
                                            student.stud_id.name
                                        ).get(
                                            att_count
                                        ):
                                            if (
                                                att_data.get(
                                                    student.stud_id.name
                                                ).get(att_count)
                                                != "A"
                                            ):
                                                status = int(
                                                    att_data.get(
                                                        student.stud_id.name
                                                    ).get(att_count)
                                                )
                                if not att_data.get(student.stud_id.name):
                                    att_data.update(
                                        {
                                            student.stud_id.name: {
                                                att_count: str(status)
                                            }
                                        }
                                    )
                                    total_absent = 0
                                    if not student.is_present:
                                        total_absent = no_of_class
                                    data.append(
                                        {
                                            "roll_no": student.stud_id.roll_no,
                                            "student_code": student.stud_id.student_code,
                                            "total_absent": total_absent,
                                            "name": student.stud_id.name,
                                            "att": {att_count: str(status)},
                                        }
                                    )
                                else:
                                    att_data.get(student.stud_id.name).update(
                                        {att_count: str(status)}
                                    )
                                    for stu in data:
                                        if (
                                            stu.get("name")
                                            == student.stud_id.name
                                        ):
                                            if not student.is_present:
                                                stu.update(
                                                    {
                                                        "total_absent": stu.get(
                                                            "total_absent"
                                                        )
                                                        + no_of_class
                                                    }
                                                )
                                            stu.get("att").update(
                                                {att_count: str(status)}
                                            )
                            if day_date not in matched_dates:
                                matched_dates.append(day_date)
                roll_no_list = []
            for stu in data:
                roll_no_list.append(stu.get("roll_no"))
            roll_no_list.sort()
            for roll_no in roll_no_list:
                for stu in data:
                    if stu.get("roll_no") == roll_no:
                        result_data.append(stu)
                        data.remove(stu)
            res_data.append(
                {
                    "user": gdata.get("user").name,
                    "school_name": gdata.get("school_name"),
                    "month": (months.get(rec.month) or "Month") + "-" + rec.academic_year_id.code,  # Utiliser une valeur par défaut
                    "batch": rec.course_id.standard_id.name,
                    "result_data": result_data,
                }
            )
        return res_data

    
    def get_total_class(self, rec):
        start_date_str = None
        end_date_str = None
        total_class = 0
        last_day_month = calendar.monthrange(
                int(rec.academic_year_id.code), int(rec.month)
            )[1]

            # Obtenir l'année en cours à partir de stop_date.
        year_current = rec.academic_year_id.date_stop.year
            
            # Créer la chaîne de date pour le début du mois (1er jour du mois) au format "YYYY-MM-01". exemple: 2024-08-01
        start_date_str = f"{year_current}-{str(rec.month).zfill(2)}-01"
            
            # Créer la chaîne de date pour la fin du mois (dernier jour du mois) au format "YYYY-MM-DD 23:00:00".ex:2024-08-31
        end_date_str = f"{year_current}-{str(rec.month).zfill(2)}-{str(last_day_month).zfill(2)} 23:00:00"
            
        self._cr.execute(
            """
            SELECT
                id
            FROM
                daily_attendance
            WHERE
                state = 'validate' and
                standard_id = %s and
                date >= '%s' and
                date <= '%s' ORDER BY user_id,date
                """,
            (rec.course_id.id, start_date_str, end_date_str),
        )
        records = []
        for record in self._cr.fetchall():
            if record and record[0]:
                records.append(record[0])
            total_class += 1
        return {"total": total_class}

    @api.model
    def _get_report_values(self, docids, data):
        report = self.env["ir.actions.report"]
        emp_report = report._get_report_from_name(
            "school_attendance.monthly_attendance_report_tmpl"
        )
        model = self.env.context.get("active_model")
        docs = self.env[model].browse(self.env.context.get("active_id"))
        return {
            "doc_ids": docids,
            "doc_model": emp_report.model,
            "data": data,
            "docs": docs,
            "get_dates": self.get_dates,
            "get_total_class": self.get_total_class,
            "get_data": self.get_data,
        }
