# -*- coding: utf-8 -*-
{
    'name': "Automatic Database Backup To Local Server, Remote Server,"
            "Google Drive, Dropbox, Onedrive, Nextcloud and Amazon S3 Odoo19",
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Odoo Database Backup, Automatic Backup, Database Backup',
    'description': 'Odoo Database Backup, Automatic Backup for Odoo 19',
    'author': "Cybrosys Techno Solutions",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/db_backup_configure_views.xml',
        'wizard/dropbox_auth_code_views.xml',
    ],
    'external_dependencies': {
        'python': ['dropbox', 'boto3', 'nextcloud-api-wrapper', 'paramiko']},
    'images': ['static/description/banner.gif'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}