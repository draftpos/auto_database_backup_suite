# -*- coding: utf-8 -*-
import ftplib
import logging
import os
import paramiko
import requests
import tempfile
import subprocess
import zipfile
import shutil
import odoo
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.http import dispatch_rpc
from odoo.service import db
from odoo.tools import config
from odoo.tools.misc import str2bool

_logger = logging.getLogger(__name__)


class DataBaseRestore(models.TransientModel):
    _name = "database.restore"
    _description = "Database Restore"

    db_file = fields.Char(string="File")
    db_name = fields.Char(string="Database Name")
    db_master_pwd = fields.Char(string="Database Master Password")
    backup_location = fields.Char(string="Backup Location")

    def _download_backup_file(self, temp_file):
        """Download backup file to temp location"""
        if self.backup_location == 'Google Drive':
            import gdown
            gdown.download(self.db_file, temp_file.name, quiet=False)
            
        elif self.backup_location in ['Dropbox', 'OneDrive', 'Nextcloud', 'AmazonS3']:
            response = requests.get(self.db_file, stream=True, timeout=120)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
                
        elif self.backup_location == 'FTP Storage':
            backup_config = self.env['db.backup.configure'].search([
                ('backup_destination', '=', 'ftp')
            ], limit=1)
            if backup_config:
                ftp_server = ftplib.FTP()
                ftp_server.connect(backup_config.ftp_host, int(backup_config.ftp_port))
                ftp_server.login(backup_config.ftp_user, backup_config.ftp_password)
                ftp_server.retrbinary("RETR " + self.db_file, temp_file.write)
                ftp_server.quit()
                
        elif self.backup_location == 'SFTP Storage':
            backup_config = self.env['db.backup.configure'].search([
                ('backup_destination', '=', 'sftp')
            ], limit=1)
            if backup_config:
                sftp_client = paramiko.SSHClient()
                sftp_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                sftp_client.connect(
                    hostname=backup_config.sftp_host,
                    username=backup_config.sftp_user,
                    password=backup_config.sftp_password,
                    port=int(backup_config.sftp_port)
                )
                sftp_server = sftp_client.open_sftp()
                sftp_server.getfo(self.db_file, temp_file)
                sftp_server.close()
                sftp_client.close()
                
        elif self.backup_location == 'Local Storage':
            temp_file.name = self.db_file
            
        temp_file.flush()
        return temp_file

    def _extract_odoo_backup(self, zip_path):
        """Extract Odoo's ZIP backup format"""
        extract_dir = tempfile.mkdtemp(prefix='odoo_restore_')
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        
        # Find the SQL dump file
        sql_dump = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'dump.sql':
                    sql_dump = os.path.join(root, file)
                    break
            if sql_dump:
                break
        
        if not sql_dump:
            raise UserError("Invalid backup format: No dump.sql found")
        
        # Find filestore
        filestore = None
        for root, dirs, files in os.walk(extract_dir):
            if 'filestore' in dirs:
                filestore = os.path.join(root, 'filestore')
                break
        
        return extract_dir, sql_dump, filestore

    def action_restore_database(self, copy=False):
        """Restore database using Odoo's restore method"""
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and self.db_master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", self.db_master_pwd])
        
        temp_file = None
        extract_dir = None
        
        try:
            # Verify master password
            db.check_super(self.db_master_pwd)
            
            # Download backup
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_file = self._download_backup_file(temp_file)
            temp_file.close()
            
            # Check if it's a ZIP file (Odoo backup format)
            if zipfile.is_zipfile(temp_file.name):
                _logger.info("Detected Odoo ZIP backup format")
                extract_dir, sql_dump, filestore = self._extract_odoo_backup(temp_file.name)
                
                # Get PostgreSQL config - convert port to string
                pg_port = config.get('db_port', '5432')
                if isinstance(pg_port, int):
                    pg_port = str(pg_port)
                
                # Restore using SQL dump
                restore_cmd = [
                    'psql', '-U', config.get('db_user', 'odoo'),
                    '-h', config.get('db_host', 'localhost'),
                    '-p', pg_port,
                    '-d', self.db_name, '-f', sql_dump
                ]
                
                env = os.environ.copy()
                pg_password = config.get('db_password', '')
                if pg_password:
                    env['PGPASSWORD'] = pg_password
                
                result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
                if result.returncode != 0:
                    # Check if it's just warnings
                    if 'ERROR' in result.stderr.upper():
                        raise UserError(f"Restore failed: {result.stderr[:500]}")
                    else:
                        _logger.warning(f"Restore warnings: {result.stderr[:200]}")
                
                # Restore filestore if present
                if filestore and os.path.exists(filestore):
                    filestore_dest = os.path.join(config['data_dir'], 'filestore', self.db_name)
                    if os.path.exists(filestore_dest):
                        shutil.rmtree(filestore_dest)
                    shutil.copytree(filestore, filestore_dest)
                    _logger.info(f"Filestore restored to {filestore_dest}")
            else:
                # Try Odoo's native restore for other formats
                db.restore_db(self.db_name, temp_file.name, str2bool(copy))
            
            # Clean up
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web?db={self.db_name}',
                'target': 'self',
            }
            
        except Exception as e:
            _logger.error(f"Restore error: {str(e)}")
            raise UserError(f"Database restore error: {str(e)}")

    def action_restore_database_direct(self):
        """Direct PostgreSQL restore - handles Odoo ZIP backups"""
        temp_file = None
        extract_dir = None
        
        try:
            # Verify master password
            db.check_super(self.db_master_pwd)
            
            # Get PostgreSQL configuration - ensure port is string
            pg_user = config.get('db_user', 'odoo')
            pg_password = config.get('db_password', '')
            pg_host = config.get('db_host', 'localhost')
            pg_port = config.get('db_port', '5432')
            
            # Convert port to string if it's an integer
            if isinstance(pg_port, int):
                pg_port = str(pg_port)
            
            _logger.info(f"PostgreSQL config: user={pg_user}, host={pg_host}, port={pg_port}")
            
            env = os.environ.copy()
            if pg_password:
                env['PGPASSWORD'] = pg_password
            
            # Download backup
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_file = self._download_backup_file(temp_file)
            temp_file.close()
            
            _logger.info(f"Restoring from {temp_file.name} to {self.db_name}")
            
            # Check if it's an Odoo ZIP backup
            if zipfile.is_zipfile(temp_file.name):
                _logger.info("Detected Odoo ZIP backup format - extracting")
                extract_dir, sql_dump, filestore = self._extract_odoo_backup(temp_file.name)
                restore_source = sql_dump
                is_sql_dump = True
                _logger.info(f"Extracted SQL dump: {sql_dump}")
            else:
                restore_source = temp_file.name
                is_sql_dump = False
            
            # Drop existing database if it exists
            drop_result = subprocess.run(
                ['dropdb', '--if-exists', '-U', pg_user, '-h', pg_host, '-p', pg_port, self.db_name],
                env=env, capture_output=True, text=True
            )
            _logger.info(f"Drop result: {drop_result.returncode}")
            
            # Create new database
            create_result = subprocess.run(
                ['createdb', '-U', pg_user, '-h', pg_host, '-p', pg_port, self.db_name],
                env=env, capture_output=True, text=True
            )
            
            if create_result.returncode != 0:
                raise UserError(f"Failed to create database: {create_result.stderr}")
            
            _logger.info("Database created successfully")
            
            # Restore
            if is_sql_dump:
                # For SQL dumps, use psql
                restore_cmd = ['psql', '-U', pg_user, '-h', pg_host, '-p', pg_port, '-d', self.db_name, '-f', restore_source]
                _logger.info(f"Running psql restore...")
            else:
                # For PostgreSQL custom format, use pg_restore
                restore_cmd = ['pg_restore', '-U', pg_user, '-h', pg_host, '-p', pg_port, '-d', self.db_name, '--no-owner', '--clean', restore_source]
                _logger.info(f"Running pg_restore...")
            
            result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Check if it's just warnings or real errors
                if 'ERROR' in result.stderr.upper():
                    _logger.error(f"Restore error: {result.stderr[:500]}")
                    raise UserError(f"Restore failed: {result.stderr[:500]}")
                else:
                    _logger.warning(f"Restore completed with warnings: {result.stderr[:200]}")
            
            _logger.info("Database restore completed")
            
            # Restore filestore if present
            if 'filestore' in locals() and filestore and os.path.exists(filestore):
                filestore_dest = os.path.join(config['data_dir'], 'filestore', self.db_name)
                if os.path.exists(filestore_dest):
                    shutil.rmtree(filestore_dest)
                shutil.copytree(filestore, filestore_dest)
                _logger.info(f"Filestore restored to {filestore_dest}")
            
            # Set database owner
            subprocess.run(
                ['psql', '-U', pg_user, '-h', pg_host, '-p', pg_port, '-d', self.db_name, '-c', f'ALTER DATABASE "{self.db_name}" OWNER TO "{pg_user}";'],
                env=env, capture_output=True
            )
            
            # Clean up
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            
            _logger.info(f"Successfully restored database {self.db_name}")
            
            # Update module list in restored database
            _logger.info("Updating module list...")
            subprocess.run([
                '.\.venv\Scripts\python.exe', 'odoo-bin', '-c', 'odoo.conf', 
                '-d', self.db_name, '--update', 'all', '--stop-after-init'
            ], capture_output=True)
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web?db={self.db_name}',
                'target': 'self',
            }
            
        except subprocess.CalledProcessError as e:
            _logger.error(f"Restore subprocess error: {e.stderr}")
            raise UserError(f"Database restore failed: {e.stderr}")
        except Exception as e:
            _logger.error(f"Restore error: {str(e)}")
            raise UserError(f"Database restore error: {str(e)}")