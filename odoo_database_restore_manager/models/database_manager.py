# -*- coding: utf-8 -*-
import boto3
import dropbox
import ftplib
import nextcloud_client
import os
import paramiko
import requests
from datetime import datetime
from odoo.http import request
from odoo import api, fields, models

class DatabaseManager(models.Model):
    _name = 'database.manager'
    _description = 'Database Manager'

    @api.model
    def action_import_files(self):
        return_data = {}
        backup_count = int(self.env['ir.config_parameter'].get_param('odoo_database_restore_manager.backup_count', 10))
        cids_cookie = request.httprequest.cookies.get('cids', '')
        current_company = cids_cookie.split(',')[0] if cids_cookie else self.env.company.id
        
        if backup_count <= 0:
            return ['error', 'Please set a backup count in Settings', 'Storages', current_company]
        
        backups = self.env['db.backup.configure'].search([])
        if not backups:
            return ['error', 'No backups configured in auto_database_backup module', 'auto_database_backup', current_company]
        
        for rec in backups:
            # Dropbox
            if rec.backup_destination == 'dropbox' and rec.dropbox_refresh_token:
                try:
                    dbx_dict = {}
                    dbx = dropbox.Dropbox(
                        app_key=rec.dropbox_client_key,
                        app_secret=rec.dropbox_client_secret,
                        oauth2_refresh_token=rec.dropbox_refresh_token
                    )
                    response = dbx.files_list_folder(path=rec.dropbox_folder or "")
                    for entry in response.entries:
                        if isinstance(entry, dropbox.files.FileMetadata):
                            link = dbx.files_get_temporary_link(path=entry.path_lower)
                            dbx_dict[entry.name] = [link.link, 'Dropbox', entry.client_modified]
                    return_data.update(dict(sorted(dbx_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'Dropbox', current_company]
            
            # OneDrive
            elif rec.backup_destination == 'onedrive' and rec.onedrive_access_token:
                try:
                    if rec.onedrive_token_validity and rec.onedrive_token_validity <= datetime.now():
                        rec.generate_onedrive_refresh_token()
                    
                    onedrive_dict = {}
                    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{rec.onedrive_folder_key}/children"
                    headers = {'Authorization': f'Bearer {rec.onedrive_access_token}'}
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()
                    
                    for file in response.json().get('value', []):
                        if '@microsoft.graph.downloadUrl' in file:
                            created_time = datetime.strptime(file['createdDateTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
                            onedrive_dict[file['name']] = [file['@microsoft.graph.downloadUrl'], 'OneDrive', created_time]
                    return_data.update(dict(sorted(onedrive_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'OneDrive', current_company]
            
            # Google Drive
            elif rec.backup_destination == 'google_drive' and rec.gdrive_access_token:
                try:
                    if rec.gdrive_token_validity and rec.gdrive_token_validity <= datetime.now():
                        rec.generate_gdrive_refresh_token()
                    
                    gdrive_dict = {}
                    headers = {"Authorization": f"Bearer {rec.gdrive_access_token}"}
                    params = {
                        "q": f"'{rec.google_drive_folder_key}' in parents",
                        "fields": "files(name, webContentLink, createdTime)",
                    }
                    response = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
                    response.raise_for_status()
                    
                    for file_data in response.json().get("files", []):
                        created_time = datetime.strptime(file_data.get("createdTime"), "%Y-%m-%dT%H:%M:%S.%fZ")
                        gdrive_dict[file_data.get("name")] = [file_data.get("webContentLink"), 'Google Drive', created_time]
                    return_data.update(dict(sorted(gdrive_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'Google Drive', current_company]
            
            # Local Storage
            elif rec.backup_destination == 'local' and rec.backup_path and os.path.exists(rec.backup_path):
                try:
                    local_dict = {}
                    for filename in os.listdir(rec.backup_path):
                        file_path = os.path.join(rec.backup_path, filename)
                        if os.path.isfile(file_path):
                            create_date = datetime.fromtimestamp(os.path.getctime(file_path))
                            local_dict[filename] = [file_path, 'Local Storage', create_date]
                    return_data.update(dict(sorted(local_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'Local Storage', current_company]
            
            # FTP
            elif rec.backup_destination == 'ftp':
                try:
                    ftp_dict = {}
                    ftp_server = ftplib.FTP()
                    ftp_server.connect(rec.ftp_host, int(rec.ftp_port))
                    ftp_server.login(rec.ftp_user, rec.ftp_password)
                    
                    for file in ftp_server.nlst(rec.ftp_path):
                        if '.' in os.path.basename(file):  # Only files
                            file_details = ftp_server.voidcmd(f"MDTM {file}")
                            file_time = datetime.strptime(file_details[4:].strip(), "%Y%m%d%H%M%S")
                            ftp_dict[os.path.basename(file)] = [file, 'FTP Storage', file_time]
                    ftp_server.quit()
                    return_data.update(dict(sorted(ftp_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'FTP', current_company]
            
            # SFTP
            elif rec.backup_destination == 'sftp':
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    sftp_dict = {}
                    client.connect(hostname=rec.sftp_host, username=rec.sftp_user, password=rec.sftp_password, port=int(rec.sftp_port))
                    sftp = client.open_sftp()
                    sftp.chdir(rec.sftp_path)
                    
                    for filename in sftp.listdir():
                        if '.' in filename:
                            file_stat = sftp.stat(filename)
                            file_time = datetime.fromtimestamp(file_stat.st_mtime)
                            sftp_dict[filename] = [os.path.join(rec.sftp_path, filename), 'SFTP Storage', file_time]
                    sftp.close()
                    return_data.update(dict(sorted(sftp_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'SFTP', current_company]
                finally:
                    client.close()
            
            # NextCloud
            elif rec.backup_destination == 'next_cloud':
                try:
                    nxt_dict = {}
                    nc = nextcloud_client.Client(rec.domain)
                    nc.login(rec.next_cloud_user_name, rec.next_cloud_password)
                    
                    folder_path = f"/{rec.nextcloud_folder_key}"
                    for file_info in nc.list(folder_path):
                        if not file_info.is_dir():
                            link_info = nc.share_file_with_link(f"{folder_path}/{file_info.name}", publicUpload=False)
                            modified_time = datetime.strptime(file_info.attributes['{DAV:}getlastmodified'], "%a, %d %b %Y %H:%M:%S %Z")
                            nxt_dict[file_info.name] = [link_info.get_link() + '/download', 'Nextcloud', modified_time]
                    return_data.update(dict(sorted(nxt_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'Nextcloud', current_company]
            
            # Amazon S3
            elif rec.backup_destination == 'amazon_s3':
                try:
                    s3_dict = {}
                    s3_client = boto3.client('s3', aws_access_key_id=rec.aws_access_key, aws_secret_access_key=rec.aws_secret_access_key)
                    response = s3_client.list_objects_v2(Bucket=rec.bucket_file_name, Prefix=rec.aws_folder_name)
                    
                    for obj in response.get('Contents', []):
                        if obj['Size'] > 0 and obj['Key'] != f"{rec.aws_folder_name}/":
                            url = s3_client.generate_presigned_url('get_object', Params={'Bucket': rec.bucket_file_name, 'Key': obj['Key']}, ExpiresIn=3600)
                            filename = os.path.basename(obj['Key'])
                            s3_dict[filename] = [url, 'Amazon S3', obj['LastModified']]
                    return_data.update(dict(sorted(s3_dict.items(), key=lambda x: x[1][2], reverse=True)[:backup_count]))
                except Exception as e:
                    return ['error', str(e), 'Amazon S3', current_company]
        
        return [return_data, current_company]