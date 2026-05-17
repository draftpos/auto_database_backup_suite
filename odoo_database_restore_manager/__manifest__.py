# -*- coding: utf-8 -*-
{
    'name': "Database Restore Manager",
    'version': "19.0.1.0.0",
    'category': "Extra Tools",
    'summary': "Restore and download backups from various storage services",
    'description': "Database Restore Manager for Odoo 19",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base_setup', 'auto_database_backup'],
    'data': [
        'security/ir.model.access.csv',
        'views/database_manager_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/database_restore_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            '/odoo_database_restore_manager/static/src/js/restore.js',
            '/odoo_database_restore_manager/static/src/xml/db_restore_dashboard_templates.xml',
            '/odoo_database_restore_manager/static/src/scss/db_restore.scss'
        ]
    },
    'external_dependencies': {'python': ['dropbox']},
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}