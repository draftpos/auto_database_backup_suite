# 🗄️ Auto Database Backup & Restore Suite for Odoo 19

[![Version](https://img.shields.io/badge/version-19.0.1.0-blue.svg)](https://github.com/draftpos/auto_database_backup_suite/releases)
[![License](https://img.shields.io/badge/license-LGPL--3-green.svg)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Odoo](https://img.shields.io/badge/Odoo-19-purple.svg)](https://www.odoo.com)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/draftpos/auto_database_backup_suite.svg)](https://github.com/draftpos/auto_database_backup_suite/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/draftpos/auto_database_backup_suite.svg)](https://github.com/draftpos/auto_database_backup_suite/issues)

> **One-Click Complete Database Backup & Restore Solution for Odoo 19**

Automate your Odoo database backups to 8 different storage locations and restore with a single click. Never lose your business data again!

## ✨ Key Features

### 🔄 Automatic Backups
- **Scheduled Backups** - Daily, Weekly, or Monthly automatic backups
- **Multiple Formats** - Choose between Zip or Dump format
- **Email Notifications** - Get alerts on backup success/failure
- **Auto Cleanup** - Automatically remove old backups
- **Multi-Level Storage** - Store backups in multiple locations

### 🎯 One-Click Restore
- **Easy Restoration** - Restore any backup with one click
- **Direct PostgreSQL Restore** - Most reliable restoration method
- **Cross-Platform** - Works on Windows, Linux, and macOS

## ☁️ Supported Storage Locations

| Storage | Status | Authentication | Setup Difficulty |
|---------|--------|----------------|------------------|
| 💾 **Local Storage** | ✅ Full Support | File System | Easy |
| ☁️ **Google Drive** | ✅ Full Support | OAuth 2.0 | Moderate |
| 📦 **Dropbox** | ✅ Full Support | OAuth 2.0 | Moderate |
| 💙 **OneDrive** | ✅ Full Support | OAuth 2.0 | Moderate |
| 📁 **FTP** | ✅ Full Support | Username/Password | Easy |
| 🔒 **SFTP** | ✅ Full Support | SSH Key/Password | Moderate |
| 🌩️ **NextCloud** | ✅ Full Support | Basic Auth | Moderate |
| 🚀 **Amazon S3** | ✅ Full Support | Access Keys | Easy |

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## 🚀 Quick Start

### Prerequisites
- Odoo 19 Community or Enterprise
- PostgreSQL 16+
- Python 3.12+

### One-Line Installation
```bash
git clone https://github.com/draftpos/auto_database_backup_suite.git /opt/odoo/custom_addons/auto_database_backup_suite && pip install -r /opt/odoo/custom_addons/auto_database_backup_suite/requirements.txt


