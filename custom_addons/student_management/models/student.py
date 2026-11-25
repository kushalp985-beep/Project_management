from odoo import models, fields, api
from odoo.exceptions import ValidationError 
import typing
import base64
import io
import xlsxwriter
if typing.TYPE_CHECKING:
    from .res_users import UsersView as ResUsers
    from .res_bank import ResPartnerBank
    from .res_country import Country, CountryState
    from .res_company import Company as ResCompany

class Student(models.Model):
    _name = 'student.management'
    _description = 'Student Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Student Name', required=True)
    admission_date = fields.Date(string='Admission Date')
    date_of_birth = fields.Date(string='Date of Birth')
    @api.onchange('date_of_birth')
    def _onchange_date_of_birth(self):
     for record in self:
        if record.date_of_birth and record.date_of_birth > fields.Date.today():
            raise ValidationError(
                "Date of Birth cannot be a future date."
            )

    gender = fields.Selection(
        [
            ('male', 'Male'),   
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        string='Gender'
    )
    name = fields.Char(string='name', required=True)
    photo = fields.Image(string='Photo')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    active = fields.Boolean(string='Active', default=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    country_code = fields.Char(related='country_id.code', string="Country Code")
    notes = fields.Text(string='Notes')
    roll_number = fields.Integer(string='Roll Number')
    standard_id = fields.Many2one('student.standard', string='Standard')
    document_name = fields.Char(string='Document Name')
    document_attachment_ids = fields.Many2many('ir.attachment','student_marksheet_attachment_rel',string='Marksheet Documents')
    document_notes = fields.Text(string='Document Notes')
    class_line_id = fields.Many2one('student.standard.line', string='Class',domain="[('standard_id', '=', standard_id)]")
    subject_ids = fields.Many2many('student.subject',string='Subjects',domain="[('standard_ids', 'in', standard_id)]")

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        self.class_line_id = False

    class_name = fields.Char(
        related='class_line_id.class_name',
        string='Class',
        store=True
    )

    class_teacher_id = fields.Many2one(
        related='class_line_id.teacher_id',
        string='Class Teacher',
        store=True,
        readonly=True
    )

    state = fields.Selection([
       ('draft', 'Draft'),
       ('sent', 'Sent'),
     ], string='Status', default='draft')


    marksheet_ids = fields.One2many(
        'student.marks.sheet',
        'student_id',
        string='Marks.sheets'
    )
    def action_view_marks_sheets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Marks.sheets',
            'res_model': 'student.marks.sheet',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_student_id': self.id
            },
        }

    def action_open_student_html_report(self):
        self.ensure_one()
        return self.env.ref(
         'student_management.student_html_report_action'
        ).report_action(self)
    
    @api.model  
    def create(self, vals):
        if not vals.get('admission_date'):
            vals['admission_date'] = self.env['ir.sequence'].next_by_code(
                'student.management'
            )

        if vals.get('standard_id') and not vals.get('roll_number'):
            last_student = self.search(
                [
                    ('standard_id', '=', vals['standard_id']),
                    ('roll_number', '>', 0),
                ],
                order='roll_number desc, id desc',
                limit=1
            )
            vals['roll_number'] = (
                last_student.roll_number + 1
                if last_student
                else 1
            )

        return super().create(vals)

    @api.model
    def student_birthday_reminder(self):
        today = fields.Date.today()

        students = self.search([
            ('date_of_birth', '!=', False),
            ('email', '!=', False)
        ])

        for student in students:
            if (student.date_of_birth.month == today.month
                    and student.date_of_birth.day == today.day):

                mail = self.env['mail.mail'].create({
                    'subject': 'Happy Birthday!',
                    'email_to': student.email,
                    'body_html': '<p>Dear %s,</p><p>Wishing you a very Happy Birthday!</p>' % student.name,
                })
                mail.send()

    def action_open_document_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Student Documents',
            'res_model': 'student.document.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
            },
        }       
    def action_send_email(self):
      self.ensure_one()

      template = self.env.ref(
        'student_management.email_template_student_details'
     )
 
      report = self.env.ref(
        'student_management.action_student_details_pdf'
     )

      pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
        report, res_ids=self.ids
    )

      attachment = self.env['ir.attachment'].create({
        'name': f'{self.name}_Details.pdf',
        'type': 'binary',
        'datas': base64.b64encode(pdf_content),
        'res_model': self._name,
        'res_id': self.id,
        'mimetype': 'application/pdf',
    })

      return {
        'type': 'ir.actions.act_window',
        'name': 'Send Email',
        'res_model': 'mail.compose.message',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_model': 'student.management',
            'default_res_ids': self.ids,
            'default_use_template': True,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_attachment_ids': [(6, 0, [attachment.id])],
        },
    }


    def action_download_student_xlsx(self):
        self.ensure_one()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
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

        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        student = self
        values = [
        student.name or '',
        str(student.admission_date or ''),
        str(student.date_of_birth or ''),
        student.gender or '',
        student.mobile or '',
        student.email or '',
        student.roll_number or '',
        student.city or '',
        student.state_id.name if student.state_id else '',
        student.country_id.name if student.country_id else '',
      ]

        for col, value in enumerate(values):
            sheet.write(1, col, value)

            sheet.set_column(0, 0, 20)  
        sheet.set_column(1, 1, 20)  
        sheet.set_column(2, 2, 20)  
        sheet.set_column(3, 3, 10)  
        sheet.set_column(4, 4, 15)  
        sheet.set_column(5, 5, 30)  
        sheet.set_column(6, 6, 8)  
        sheet.set_column(7, 7, 20) 
        sheet.set_column(8, 8, 22)  
        sheet.set_column(9, 9, 22)  


 

        workbook.close()
        xlsx_data = output.getvalue()
        output.close()

        attachment = self.env['ir.attachment'].create({
          'name': f'{self.name}_Details.xlsx',
          'type': 'binary',
          'datas': base64.b64encode(xlsx_data),
          'res_model': self._name,
          'res_id': self.id,
          'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
    
        return {
        'type': 'ir.actions.act_url',
        'url': f'/web/content/{attachment.id}?download=true',
        'target': 'self',
    }

       
    