from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        result = super().action_send_mail()

        for wizard in self:
            if wizard.model == 'student.management':
                student_ids = wizard._evaluate_res_ids()
                students = self.env['student.management'].browse(student_ids)
                students.write({'state': 'sent'})

        return result