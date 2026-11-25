from odoo import models, fields
from odoo.exceptions import ValidationError


class StudentDocumentWizard(models.TransientModel):
    _name = 'student.document.wizard'
    _description = 'Student Document Wizard'

    student_id = fields.Many2one('student.management',string='Student',required=True)
    document_name = fields.Char(string='Document Name')
    document_attachment_ids = fields.Many2many('ir.attachment','student_document_wizard_rel','wizard_id','attachment_id',string='Documents')
    document_notes = fields.Text(string='Document Notes')

   
    def action_submit(self):
      self.ensure_one()

      vals = {
        'document_name': self.document_name,
        'document_notes': self.document_notes,
      }
      self.student_id.write(vals)

      if self.document_attachment_ids:
       self.document_attachment_ids.write({
         'res_model': 'student.management',
        'res_id': self.student_id.id,
    })

      self.student_id.write({
        'document_attachment_ids': [
            (6, 0, self.document_attachment_ids.ids)
        ]
    })

      return {'type': 'ir.actions.act_window_close'}
