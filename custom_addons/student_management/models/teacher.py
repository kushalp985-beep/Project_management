from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Teacher(models.Model):
    _name = 'student.teacher'
    _description = 'Teacher'

    name = fields.Char(string='Teacher Name', required=True) 
    date_of_birth = fields.Date(string='Date of Birth')  

    @api.onchange('date_of_birth')
    def _onchange_date_of_birth(self):
        for record in self:
            if (
                record.date_of_birth
                and record.date_of_birth > fields.Date.today()
            ):
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
    photo = fields.Image(string='Photo')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    country_id = fields.Many2one('res.country',string='Country')
    state_id = fields.Many2one('res.country.state',string='State',domain="[('country_id', '=', country_id)]")
    city = fields.Char(string='City')
    active = fields.Boolean(string='Active',default=True)
    standard_id = fields.Many2one('student.standard',string='Standard')
    subject_ids = fields.Many2many('student.subject','subject_teacher_id',string='Subjects Taught')
