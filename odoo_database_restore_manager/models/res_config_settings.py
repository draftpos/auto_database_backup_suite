# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    backup_count = fields.Integer(
        string='Backup Count',
        default=10,
        help='Number of backups to display in Restore Manager',
        config_parameter='odoo_database_restore_manager.backup_count'
    )