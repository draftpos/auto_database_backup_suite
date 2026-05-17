# -*- coding: utf-8 -*-
{
    'name': 'Auto Database Backup & Restore Suite',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Complete Database Backup and Restore Solution - One Click Install',
    'description': """
        ===================================================
        AUTO DATABASE BACKUP & RESTORE SUITE
        ===================================================
        
        This meta module installs BOTH backup and restore modules in ONE click!
        
        INSTALLED MODULES:
        ------------------
        1. Auto Database Backup - Automatic backups to multiple locations
        2. Database Restore Manager - Easy one-click restore
        
        FEATURES:
        ---------
        ✓ Automatic scheduled backups (Daily/Weekly/Monthly)
        ✓ Multiple storage destinations (Local, Google Drive, Dropbox, OneDrive, FTP, SFTP, NextCloud, Amazon S3)
        ✓ One-click restore from any backup
        ✓ Email notifications on success/failure
        ✓ Automatic cleanup of old backups
        
        Just install this module and everything else comes automatically!
    """,
    'author': 'Tatenda Tembo',
    'website': 'https://github.com/draftpos/auto_database_backup_suite',
    'depends': [
        'base',
        'auto_database_backup',           # This auto-installs the backup module
        'odoo_database_restore_manager',  # This auto-installs the restore module
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
