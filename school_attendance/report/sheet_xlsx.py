from odoo import models
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx

class DailyAttendanceXlsx(models.AbstractModel):
    _name = 'report.school_attendance.report_daily_attendance_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        sheet = workbook.add_worksheet('Daily Attendance')
        bold = workbook.add_format({'bold': True})

        sheet.write(0, 0, 'Eleve', bold)
        sheet.write(0, 1, 'Date', bold)
        sheet.write(0, 2, 'Employee', bold)

        row = 1
        for obj in objs:
            sheet.write(row, 0, obj.name)
            sheet.write(row, 1, str(obj.date))
            employees = ', '.join([employee.name for employee in obj.employee_ids])
            sheet.write(row, 2, employees)
            row += 1

DailyAttendanceXlsx('report.school_attendance.report_daily_attendance_xlsx')
