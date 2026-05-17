# -*- coding: utf-8 -*-
{
    'name': 'Auto Database Backup & Restore Suite',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Complete Database Backup and Restore Solution - One Click Install',
    'description': 'One-click installation for complete database backup and restore solution.',
    'author': 'Showline Solutions',
    'depends': [
        'base',
        'auto_database_backup',
        'odoo_database_restore_manager'
    ],
    'data': [
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 1,
    'license': 'LGPL-3',
}
