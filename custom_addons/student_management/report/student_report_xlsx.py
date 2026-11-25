import io
import base64
import xlsxwriter

from odoo import models


class StudentXlsxReport(models.AbstractModel):
    _name = 'report.student_management.student_report_xlsx'
    _description = 'Student XLSX Report'

    def generate_xlsx_report(self, workbook, data, students):
        sheet = workbook.add_worksheet('Students')

        headers = [
            'Student Name',
            'Admission Date',
            'Date of Birth',
            'Gender',
            'Mobile',
            'Email',
            'Roll Number',
            'City',
            'State',
            'Country',
        ]

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EAF7',
            'border': 1,
        })

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        for row, student in enumerate(students, start=1):
            sheet.write(row, 0, student.name or '')
            sheet.write(row, 1, str(student.admission_date or ''))
            sheet.write(row, 2, str(student.date_of_birth or ''))
            sheet.write(row, 3, student.gender or '')
            sheet.write(row, 4, student.mobile or '')
            sheet.write(row, 5, student.email or '')
            sheet.write(row, 6, student.roll_number or '')
            sheet.write(row, 7, student.city or '')
            sheet.write(row, 8, student.state_id.name if student.state_id else '')
            sheet.write(row, 9, student.country_id.name if student.country_id else '')

        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, len(students), len(headers) - 1)

        for col in range(len(headers)):
            sheet.set_column(col, col, 20)
