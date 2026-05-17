# -*- coding: utf-8 -*-
import boto3
import dropbox
import errno
import ftplib
import json
import logging
import nextcloud_client
import os
import paramiko
import requests
import shutil
import subprocess
import tempfile
import odoo
from datetime import datetime, timedelta
from nextcloud import NextCloud
from requests.auth import HTTPBasicAuth
from werkzeug import urls
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config
from odoo.tools.misc import exec_pg_environ
from odoo.service import db
from odoo.http import request

_logger = logging.getLogger(__name__)
ONEDRIVE_SCOPE = ['offline_access', 'openid', 'Files.ReadWrite.All']
MICROSOFT_GRAPH_END_POINT = "https://graph.microsoft.com"
GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'

class DbBackupConfigure(models.Model):
    _name = 'db.backup.configure'
    _description = 'Automatic Database Backup'

    name = fields.Char(string='Name', required=True)
    db_name = fields.Char(string='Database Name', required=True)
    master_pwd = fields.Char(string='Master Password', required=True)
    backup_format = fields.Selection([
        ('zip', 'Zip'),
        ('dump', 'Dump')
    ], string='Backup Format', default='zip', required=True)
    backup_destination = fields.Selection([
        ('local', 'Local Storage'),
        ('google_drive', 'Google Drive'),
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
        ('dropbox', 'Dropbox'),
        ('onedrive', 'Onedrive'),
        ('next_cloud', 'Next Cloud'),
        ('amazon_s3', 'Amazon S3')
    ], string='Backup Destination')
    backup_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='daily', string='Backup Frequency')
    backup_path = fields.Char(string='Backup Path')
    sftp_host = fields.Char(string='SFTP Host')
    sftp_port = fields.Char(string='SFTP Port', default='22')
    sftp_user = fields.Char(string='SFTP User', copy=False)
    sftp_password = fields.Char(string='SFTP Password', copy=False)
    sftp_path = fields.Char(string='SFTP Path')
    ftp_host = fields.Char(string='FTP Host')
    ftp_port = fields.Char(string='FTP Port', default='21')
    ftp_user = fields.Char(string='FTP User', copy=False)
    ftp_password = fields.Char(string='FTP Password', copy=False)
    ftp_path = fields.Char(string='FTP Path')
    dropbox_client_key = fields.Char(string='Dropbox Client ID', copy=False)
    dropbox_client_secret = fields.Char(string='Dropbox Client Secret', copy=False)
    dropbox_refresh_token = fields.Char(string='Dropbox Refresh Token', copy=False)
    is_dropbox_token_generated = fields.Boolean(
        string='Dropbox Token Generated',
        compute='_compute_is_dropbox_token_generated'
    )
    dropbox_folder = fields.Char(string='Dropbox Folder')
    active = fields.Boolean(default=False, string='Active')
    hide_active = fields.Boolean(string="Hide Active")
    auto_remove = fields.Boolean(string='Remove Old Backups')
    days_to_remove = fields.Integer(string='Remove After')
    google_drive_folder_key = fields.Char(string='Drive Folder ID')
    notify_user = fields.Boolean(string='Notify User')
    user_id = fields.Many2one('res.users', string='User')
    backup_filename = fields.Char(string='Backup Filename')
    generated_exception = fields.Char(string='Exception')
    onedrive_client_key = fields.Char(string='Onedrive Client ID', copy=False)
    onedrive_client_secret = fields.Char(string='Onedrive Client Secret', copy=False)
    onedrive_access_token = fields.Char(string='Onedrive Access Token', copy=False)
    onedrive_refresh_token = fields.Char(string='Onedrive Refresh Token', copy=False)
    onedrive_token_validity = fields.Datetime(string='Onedrive Token Validity', copy=False)
    onedrive_folder_key = fields.Char(string='Folder ID')
    is_onedrive_token_generated = fields.Boolean(
        string='Onedrive Tokens Generated',
        compute='_compute_is_onedrive_token_generated'
    )
    gdrive_refresh_token = fields.Char(string='Google drive Refresh Token', copy=False)
    gdrive_access_token = fields.Char(string='Google Drive Access Token', copy=False)
    is_google_drive_token_generated = fields.Boolean(
        string='Google drive Token Generated',
        compute='_compute_is_google_drive_token_generated'
    )
    gdrive_client_key = fields.Char(string='Google Drive Client ID', copy=False)
    gdrive_client_secret = fields.Char(string='Google Drive Client Secret', copy=False)
    gdrive_token_validity = fields.Datetime(string='Google Drive Token Validity', copy=False)
    onedrive_redirect_uri = fields.Char(string='Onedrive Redirect URI', compute='_compute_redirect_uri')
    gdrive_redirect_uri = fields.Char(string='Google Drive Redirect URI', compute='_compute_redirect_uri')
    domain = fields.Char(string='Domain Name')
    next_cloud_user_name = fields.Char(string='User Name')
    next_cloud_password = fields.Char(string='Password')
    nextcloud_folder_key = fields.Char(string='Next Cloud Folder Id')
    aws_access_key = fields.Char(string="Amazon S3 Access Key")
    aws_secret_access_key = fields.Char(string='Amazon S3 Secret Key')
    bucket_file_name = fields.Char(string='Bucket Name')
    aws_folder_name = fields.Char(string='File Name')

    @api.depends('onedrive_redirect_uri', 'gdrive_redirect_uri')
    def _compute_redirect_uri(self):
        base_url = self.get_base_url()
        for rec in self:
            rec.onedrive_redirect_uri = f'{base_url}/onedrive/authentication'
            rec.gdrive_redirect_uri = f'{base_url}/google_drive/authentication'

    @api.depends('onedrive_access_token', 'onedrive_refresh_token')
    def _compute_is_onedrive_token_generated(self):
        for rec in self:
            rec.is_onedrive_token_generated = bool(rec.onedrive_access_token and rec.onedrive_refresh_token)

    @api.depends('dropbox_refresh_token')
    def _compute_is_dropbox_token_generated(self):
        for rec in self:
            rec.is_dropbox_token_generated = bool(rec.dropbox_refresh_token)

    @api.depends('gdrive_access_token', 'gdrive_refresh_token')
    def _compute_is_google_drive_token_generated(self):
        for rec in self:
            rec.is_google_drive_token_generated = bool(rec.gdrive_access_token and rec.gdrive_refresh_token)

    def action_s3cloud(self):
        if self.aws_access_key and self.aws_secret_access_key:
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_access_key
                )
                response = s3_client.head_bucket(Bucket=self.bucket_file_name)
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    self.active = self.hide_active = True
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'title': _("Connection Test Succeeded!"),
                            'message': _("Everything seems properly set up!"),
                            'sticky': False,
                        }
                    }
            except Exception:
                self.active = self.hide_active = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'title': _("Connection Test Failed!"),
                        'message': _("An error occurred while testing the connection."),
                        'sticky': False,
                    }
                }

    def action_nextcloud(self):
        if self.domain and self.next_cloud_password and self.next_cloud_user_name:
            try:
                ncx = NextCloud(self.domain, auth=HTTPBasicAuth(self.next_cloud_user_name, self.next_cloud_password))
                data = ncx.list_folders('/').__dict__
                if data['raw'].status_code == 207:
                    self.active = self.hide_active = True
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'success',
                            'title': _("Connection Test Succeeded!"),
                            'message': _("Everything seems properly set up!"),
                            'sticky': False,
                        }
                    }
            except Exception:
                self.active = self.hide_active = False
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'title': _("Connection Test Failed!"),
                        'message': _("An error occurred while testing the connection."),
                        'sticky': False,
                    }
                }

    def action_get_dropbox_auth_code(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dropbox Authorization Wizard',
            'res_model': 'dropbox.auth.code',
            'view_mode': 'form',
            'target': 'new',
            'context': {'dropbox_auth': True}
        }

    def action_get_onedrive_auth_code(self):
        AUTHORITY = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        base_url = self.get_base_url()
        action_id = self.env["ir.actions.act_window"].sudo()._for_xml_id("auto_database_backup.db_backup_configure_action")['id']
        url_return = f"{base_url}/web#id={self.id}&action={action_id}&view_type=form&model=db.backup.configure"
        state = {'backup_config_id': self.id, 'url_return': url_return}
        params = {
            'response_type': 'code',
            'client_id': self.onedrive_client_key,
            'state': json.dumps(state),
            'scope': ' '.join(ONEDRIVE_SCOPE),
            'redirect_uri': f"{base_url}/onedrive/authentication",
            'prompt': 'consent',
            'access_type': 'offline'
        }
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f"{AUTHORITY}?{urls.url_encode(params)}",
        }

    def action_get_gdrive_auth_code(self):
        base_url = self.get_base_url()
        action_id = self.env["ir.actions.act_window"].sudo()._for_xml_id("auto_database_backup.db_backup_configure_action")['id']
        url_return = f"{base_url}/web#id={self.id}&action={action_id}&view_type=form&model=db.backup.configure"
        state = {'backup_config_id': self.id, 'url_return': url_return}
        params = {
            'response_type': 'code',
            'client_id': self.gdrive_client_key,
            'scope': 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.file',
            'redirect_uri': f"{base_url}/google_drive/authentication",
            'access_type': 'offline',
            'state': json.dumps(state),
            'approval_prompt': 'force',
        }
        auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urls.url_encode(params)}"
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': auth_url,
        }

    def generate_onedrive_refresh_token(self):
        base_url = self.get_base_url()
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'scope': ' '.join(ONEDRIVE_SCOPE),
            'grant_type': "refresh_token",
            'redirect_uri': f"{base_url}/onedrive/authentication",
            'refresh_token': self.onedrive_refresh_token,
        }
        try:
            res = requests.post(token_url, data=data, headers=headers)
            res.raise_for_status()
            response = res.json()
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': datetime.now() + timedelta(seconds=expires_in),
                })
        except requests.HTTPError as error:
            _logger.exception("Bad Microsoft OneDrive request: %s", error.response.content)
            raise error

    def get_onedrive_tokens(self, authorize_code):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        base_url = self.get_base_url()
        data = {
            'code': authorize_code,
            'client_id': self.onedrive_client_key,
            'client_secret': self.onedrive_client_secret,
            'grant_type': 'authorization_code',
            'scope': ' '.join(ONEDRIVE_SCOPE),
            'redirect_uri': f"{base_url}/onedrive/authentication",
        }
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        try:
            res = requests.post(token_url, data=data, headers=headers)
            res.raise_for_status()
            response = res.json()
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'onedrive_access_token': response.get('access_token'),
                    'onedrive_refresh_token': response.get('refresh_token'),
                    'onedrive_token_validity': datetime.now() + timedelta(seconds=expires_in),
                })
        except requests.HTTPError as error:
            _logger.exception("Bad Microsoft OneDrive request: %s", error.response.content)
            raise error

    def generate_gdrive_refresh_token(self):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.gdrive_refresh_token,
            'client_id': self.gdrive_client_key,
            'client_secret': self.gdrive_client_secret,
            'grant_type': 'refresh_token',
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers)
            res.raise_for_status()
            response = res.json()
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'gdrive_access_token': response.get('access_token'),
                    'gdrive_token_validity': datetime.now() + timedelta(seconds=expires_in),
                })
        except requests.HTTPError as error:
            raise UserError(_("An error occurred while generating the token."))

    def get_gdrive_tokens(self, authorize_code):
        base_url = self.get_base_url()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': self.gdrive_client_key,
            'client_secret': self.gdrive_client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': f"{base_url}/google_drive/authentication",
        }
        try:
            res = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers)
            res.raise_for_status()
            response = res.json()
            if response:
                expires_in = response.get('expires_in', 0)
                self.write({
                    'gdrive_access_token': response.get('access_token'),
                    'gdrive_refresh_token': response.get('refresh_token'),
                    'gdrive_token_validity': datetime.now() + timedelta(seconds=expires_in) if expires_in else False,
                })
        except requests.HTTPError:
            raise UserError(_("Something went wrong during token generation."))

    def get_dropbox_auth_url(self):
        dbx_auth = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            self.dropbox_client_key,
            self.dropbox_client_secret,
            token_access_type='offline')
        return dbx_auth.start()

    def set_dropbox_refresh_token(self, auth_code):
        dbx_auth = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            self.dropbox_client_key,
            self.dropbox_client_secret,
            token_access_type='offline')
        oauth_result = dbx_auth.finish(auth_code)
        self.dropbox_refresh_token = oauth_result.refresh_token

    @api.constrains('db_name')
    def _check_db_credentials(self):
        database_list = db.list_dbs(force=True)
        if self.db_name not in database_list:
            raise ValidationError(_("Invalid Database Name!"))
        try:
            db.check_super(self.master_pwd)
        except Exception:
            raise ValidationError(_("Invalid Master Password!"))

    def action_sftp_connection(self):
        if self.backup_destination == 'sftp':
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(hostname=self.sftp_host, username=self.sftp_user, password=self.sftp_password, port=int(self.sftp_port))
                sftp = client.open_sftp()
                sftp.close()
            except Exception as e:
                raise UserError(_("SFTP Exception: %s") % e)
            finally:
                client.close()
        elif self.backup_destination == 'ftp':
            try:
                ftp_server = ftplib.FTP()
                ftp_server.connect(self.ftp_host, int(self.ftp_port))
                ftp_server.login(self.ftp_user, self.ftp_password)
                ftp_server.quit()
            except Exception as e:
                raise UserError(_("FTP Exception: %s") % e)
        self.active = self.hide_active = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Connection Test Succeeded!"),
                'message': _("Everything seems properly set up!"),
                'sticky': False,
            }
        }

    @api.onchange('backup_destination')
    def _onchange_backup_destination(self):
        if self.backup_destination == 'local':
            self.hide_active = True

    def _dump_database(self, db_name, stream, backup_format):
        """Odoo 19 compatible database dump"""
        pg_dump = shutil.which('pg_dump')
        if not pg_dump:
            raise UserError(_("pg_dump not found in PATH. Please install PostgreSQL client tools."))
        
        if backup_format == 'zip':
            with tempfile.TemporaryDirectory() as dump_dir:
                dump_sql = os.path.join(dump_dir, 'dump.sql')
                cmd = [pg_dump, '--no-owner', '--file=' + dump_sql, db_name]
                env = exec_pg_environ()
                subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True, text=True)
                
                filestore = config.filestore(db_name)
                if os.path.exists(filestore):
                    shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))
                
                with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
                    db_conn = odoo.sql_db.db_connect(db_name)
                    with db_conn.cursor() as cr:
                        json.dump(self._dump_db_manifest(cr), fh, indent=4)
                
                import odoo.tools.osutil as osutil
                osutil.zip_dir(dump_dir, stream, include_dir=False, fnct_sort=lambda fn: fn != 'dump.sql')
        else:
            cmd = [pg_dump, '--no-owner', '--format=c', db_name]
            env = exec_pg_environ()
            result = subprocess.run(cmd, env=env, capture_output=True, check=True, text=False)
            stream.write(result.stdout)

    def _dump_db_manifest(self, cr):
        pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
        cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
        modules = dict(cr.fetchall())
        return {
            'odoo_dump': '1',
            'db_name': cr.dbname,
            'version': odoo.release.version,
            'version_info': odoo.release.version_info,
            'major_version': odoo.release.major_version,
            'pg_version': pg_version,
            'modules': modules,
        }

    def action_test_backup(self):
        """Manually test backup for the current configuration"""
        try:
            # Create backup directory if it doesn't exist
            if self.backup_destination == 'local' and self.backup_path:
                if not os.path.exists(self.backup_path):
                    os.makedirs(self.backup_path)
            
            # Force a backup immediately
            self._schedule_auto_backup(self.backup_frequency)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Backup Started'),
                    'message': _('Backup has been triggered. Check the backup location shortly.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Backup Failed'),
                    'message': _(f'Error: {str(e)}'),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def _schedule_auto_backup(self, frequency, *args, **kwargs):
        records = self.search([('backup_frequency', '=', frequency), ('active', '=', True)])
        mail_template_success = self.env.ref('auto_database_backup.mail_template_data_db_backup_successful')
        mail_template_failed = self.env.ref('auto_database_backup.mail_template_data_db_backup_failed')
        
        for rec in records:
            backup_time = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"{rec.db_name}_{backup_time}.{rec.backup_format}"
            rec.backup_filename = backup_filename
            
            try:
                # Local backup
                if rec.backup_destination == 'local':
                    if not os.path.isdir(rec.backup_path):
                        os.makedirs(rec.backup_path)
                    backup_file = os.path.join(rec.backup_path, backup_filename)
                    with open(backup_file, "wb") as f:
                        self._dump_database(rec.db_name, f, rec.backup_format)
                    
                    if rec.auto_remove:
                        for filename in os.listdir(rec.backup_path):
                            file_path = os.path.join(rec.backup_path, filename)
                            create_time = datetime.fromtimestamp(os.path.getctime(file_path))
                            backup_duration = datetime.utcnow() - create_time
                            if backup_duration.days >= rec.days_to_remove:
                                os.remove(file_path)
                
                # FTP backup
                elif rec.backup_destination == 'ftp':
                    ftp_server = ftplib.FTP()
                    ftp_server.connect(rec.ftp_host, int(rec.ftp_port))
                    ftp_server.login(rec.ftp_user, rec.ftp_password)
                    ftp_server.encoding = "utf-8"
                    
                    try:
                        ftp_server.cwd(rec.ftp_path)
                    except ftplib.error_perm:
                        ftp_server.mkd(rec.ftp_path)
                        ftp_server.cwd(rec.ftp_path)
                    
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        with open(temp.name, "rb") as f:
                            ftp_server.storbinary(f'STOR {backup_filename}', f)
                    
                    if rec.auto_remove:
                        files = ftp_server.nlst()
                        for file in files:
                            create_time_str = ftp_server.sendcmd('MDTM ' + file)[4:]
                            create_time = datetime.strptime(create_time_str, "%Y%m%d%H%M%S")
                            diff_days = (datetime.now() - create_time).days
                            if diff_days >= rec.days_to_remove:
                                ftp_server.delete(file)
                    ftp_server.quit()
                
                # SFTP backup
                elif rec.backup_destination == 'sftp':
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(hostname=rec.sftp_host, username=rec.sftp_user, password=rec.sftp_password, port=int(rec.sftp_port))
                    sftp = client.open_sftp()
                    
                    try:
                        sftp.chdir(rec.sftp_path)
                    except IOError as e:
                        if e.errno == errno.ENOENT:
                            sftp.mkdir(rec.sftp_path)
                            sftp.chdir(rec.sftp_path)
                    
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        sftp.put(temp.name, backup_filename)
                    
                    if rec.auto_remove:
                        files = sftp.listdir()
                        for file in files:
                            file_mtime = datetime.fromtimestamp(sftp.stat(file).st_mtime)
                            if (datetime.now() - file_mtime).days >= rec.days_to_remove:
                                sftp.unlink(file)
                    sftp.close()
                    client.close()
                
                # Google Drive backup
                elif rec.backup_destination == 'google_drive':
                    if rec.gdrive_token_validity and rec.gdrive_token_validity <= datetime.now():
                        rec.generate_gdrive_refresh_token()
                    
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        
                        headers = {"Authorization": f"Bearer {rec.gdrive_access_token}"}
                        para = {"name": backup_filename, "parents": [rec.google_drive_folder_key]}
                        files = {
                            'data': ('metadata', json.dumps(para), 'application/json; charset=UTF-8'),
                            'file': open(temp.name, "rb")
                        }
                        requests.post(
                            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                            headers=headers, files=files
                        )
                        
                        if rec.auto_remove:
                            query = f"parents = '{rec.google_drive_folder_key}'"
                            files_req = requests.get(
                                f"https://www.googleapis.com/drive/v3/files?q={query}", headers=headers)
                            for file in files_req.json().get('files', []):
                                file_date_req = requests.get(
                                    f"https://www.googleapis.com/drive/v3/files/{file['id']}?fields=createdTime",
                                    headers=headers)
                                create_time_str = file_date_req.json()['createdTime'][:19].replace('T', ' ')
                                create_time = datetime.strptime(create_time_str, '%Y-%m-%d %H:%M:%S')
                                if (datetime.now() - create_time).days >= rec.days_to_remove:
                                    requests.delete(
                                        f"https://www.googleapis.com/drive/v3/files/{file['id']}", headers=headers)
                
                # Dropbox backup
                elif rec.backup_destination == 'dropbox':
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        temp.seek(0)
                        dbx = dropbox.Dropbox(
                            app_key=rec.dropbox_client_key,
                            app_secret=rec.dropbox_client_secret,
                            oauth2_refresh_token=rec.dropbox_refresh_token)
                        dropbox_destination = f"{rec.dropbox_folder}/{backup_filename}"
                        dbx.files_upload(temp.read(), dropbox_destination)
                        
                        if rec.auto_remove:
                            files = dbx.files_list_folder(rec.dropbox_folder)
                            for file in files.entries:
                                if (datetime.now() - file.client_modified).days >= rec.days_to_remove:
                                    dbx.files_delete_v2(file.path_display)
                
                # OneDrive backup
                elif rec.backup_destination == 'onedrive':
                    if rec.onedrive_token_validity and rec.onedrive_token_validity <= datetime.now():
                        rec.generate_onedrive_refresh_token()
                    
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        
                        headers = {'Authorization': f'Bearer {rec.onedrive_access_token}', 'Content-Type': 'application/json'}
                        upload_session_url = f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/{rec.onedrive_folder_key}:/{backup_filename}:/createUploadSession"
                        upload_session = requests.post(upload_session_url, headers=headers)
                        upload_session.raise_for_status()
                        upload_url = upload_session.json().get('uploadUrl')
                        
                        file_size = os.path.getsize(temp.name)
                        with open(temp.name, 'rb') as f:
                            headers_upload = {'Content-Length': str(file_size), 'Content-Range': f'bytes 0-{file_size - 1}/{file_size}'}
                            requests.put(upload_url, headers=headers_upload, data=f).raise_for_status()
                        
                        if rec.auto_remove:
                            list_url = f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/{rec.onedrive_folder_key}/children"
                            response = requests.get(list_url, headers=headers).json()
                            for file in response.get('value', []):
                                if file['name'] != backup_filename:
                                    create_time = datetime.strptime(file['createdDateTime'][:19], '%Y-%m-%dT%H:%M:%S')
                                    if (datetime.now() - create_time).days >= rec.days_to_remove:
                                        requests.delete(f"{MICROSOFT_GRAPH_END_POINT}/v1.0/me/drive/items/{file['id']}", headers=headers)
                
                # NextCloud backup
                elif rec.backup_destination == 'next_cloud':
                    nc = nextcloud_client.Client(rec.domain)
                    nc.login(rec.next_cloud_user_name, rec.next_cloud_password)
                    
                    folder_name = rec.nextcloud_folder_key
                    try:
                        nc.mkdir(folder_name)
                    except Exception:
                        pass
                    
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        remote_file_path = f"/{folder_name}/{backup_filename}"
                        nc.put_file(remote_file_path, temp.name)
                    
                    if rec.auto_remove:
                        for item in nc.list(f"/{folder_name}"):
                            backup_date_str = item.name.split("_")[1] if len(item.name.split("_")) > 1 else ""
                            if backup_date_str:
                                backup_date = datetime.strptime(backup_date_str, '%Y-%m-%d').date()
                                if (datetime.now().date() - backup_date).days >= rec.days_to_remove:
                                    nc.delete(item.path)
                
                # Amazon S3 backup
                elif rec.backup_destination == 'amazon_s3':
                    s3 = boto3.client('s3', aws_access_key_id=rec.aws_access_key, aws_secret_access_key=rec.aws_secret_access_key)
                    s3.put_object(Bucket=rec.bucket_file_name, Key=f"{rec.aws_folder_name}/")
                    
                    with tempfile.NamedTemporaryFile(suffix=f'.{rec.backup_format}') as temp:
                        with open(temp.name, "wb+") as tmp:
                            self._dump_database(rec.db_name, tmp, rec.backup_format)
                        remote_file_path = f"{rec.aws_folder_name}/{backup_filename}"
                        s3.upload_file(temp.name, rec.bucket_file_name, remote_file_path)
                    
                    if rec.auto_remove:
                        response = s3.list_objects(Bucket=rec.bucket_file_name, Prefix=rec.aws_folder_name)
                        for obj in response.get('Contents', []):
                            if obj['Key'] != f"{rec.aws_folder_name}/":
                                age_days = (datetime.now().date() - obj['LastModified'].date()).days
                                if age_days >= rec.days_to_remove:
                                    s3.delete_object(Bucket=rec.bucket_file_name, Key=obj['Key'])
                
                if rec.notify_user:
                    mail_template_success.send_mail(rec.id, force_send=True)
                    
            except Exception as e:
                rec.generated_exception = str(e)
                _logger.error(f'Backup failed for {rec.db_name}: {e}')
                if rec.notify_user:
                    mail_template_failed.send_mail(rec.id, force_send=True)