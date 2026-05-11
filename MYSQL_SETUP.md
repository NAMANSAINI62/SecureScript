# 🗄️ MySQL Setup Guide for Super AI Transcript

This project now uses **MySQL** instead of SQLite. MySQL is a powerful relational database that can handle multiple users and larger applications.

---

## 📋 Prerequisites

- MySQL Server installed (Community Edition is free)
- MySQL running on your local machine
- Port 3306 available (default MySQL port)

---

## 🔧 Installation & Setup

### Step 1: Install MySQL Server

#### Windows (Recommended)

**Option A: Using MySQL Installer (Easiest)**

1. Download MySQL Community Server: https://dev.mysql.com/downloads/mysql/
2. Run the `.msi` installer
3. Choose **Setup Type**: "Developer Default"
4. Click through the installation steps
5. For **MySQL Server Configuration**:
   - Port: `3306` (default)
   - Config Type: `Development Machine`
6. Create MySQL Windows Service (recommended)
7. For **MySQL Server User Configuration**:
   - Username: `root`
   - Password: Set a password (or leave empty for local dev)
   - Add MySQL User: Optional (can skip)
8. Complete the installation

**Option B: Using Chocolatey (Command-line)**

```powershell
choco install mysql
```

**Option C: Using Windows Subsystem for Linux (WSL)**

```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

#### macOS

Using Homebrew:
```bash
brew install mysql
brew services start mysql
```

#### Linux

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

---

### Step 2: Create Database & User

Open MySQL command line or MySQL Workbench and run these commands:

```sql
-- Create database
CREATE DATABASE super_ai_transcript;

-- Create user (if using password)
CREATE USER 'super_ai'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON super_ai_transcript.* TO 'super_ai'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify (optional)
SHOW DATABASES;
SELECT User, Host FROM mysql.user;
```

**Or use root with no password (development only):**

```sql
CREATE DATABASE super_ai_transcript;
```

---

### Step 3: Configure Your Application

Update `.env` file with your MySQL credentials:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=super_ai_transcript
```

**Examples:**

**If using root with no password:**
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=super_ai_transcript
```

**If using dedicated user:**
```env
DB_HOST=localhost
DB_USER=super_ai
DB_PASSWORD=your_secure_password
DB_NAME=super_ai_transcript
```

---

### Step 4: Verify MySQL Connection

Test that MySQL is running:

```powershell
# Windows (Command Prompt/PowerShell)
mysql -u root -p
# Leave password empty and just press Enter if no password set

# If successful, you'll see:
# mysql>
# Type 'exit' to quit
```

Or use MySQL Workbench (GUI): https://dev.mysql.com/downloads/workbench/

---

## 🚀 Running the Application

Once MySQL is set up and running:

```bash
cd c:\Super AI Transcript
python app.py
```

The app will:
1. Read credentials from `.env`
2. Create connection pool to MySQL
3. Create tables if they don't exist
4. Start Flask server on http://127.0.0.1:5000

---

## 📊 Database Schema

### `recordings` table

Stores audio files and transcriptions:

```sql
CREATE TABLE recordings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    audio_data LONGBLOB,
    audio_mime_type VARCHAR(50),
    original_transcript LONGTEXT,
    cleaned_transcript LONGTEXT,
    summary LONGTEXT,
    key_points LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### `qa_history` table

Stores Q&A data for recordings:

```sql
CREATE TABLE qa_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recording_id INT,
    question TEXT NOT NULL,
    answer LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
);
```

---

## 🔒 Security Best Practices

### Development (Local)

For local development, you can use:
- Simple password or no password
- User: `root` or `super_ai`

### Production (Hugging Face Spaces)

For production deployment:

1. Create strong password: `openssl rand -base64 32`
2. Use dedicated MySQL user (not root)
3. Store password in Hugging Face Secrets:
   ```
   DB_PASSWORD=<your_strong_password>
   ```
4. Never commit `.env` to git (already in `.gitignore`)

---

## 🆘 Troubleshooting

### Error: "Access denied for user 'root'@'localhost'"

**Solution:**
- Check MySQL is running
- Verify `DB_PASSWORD` in `.env` matches your MySQL password
- If no password set, leave `DB_PASSWORD=` empty in `.env`

### Error: "Can't connect to MySQL server on 'localhost'"

**Solution:**
- Ensure MySQL service is running
- Check port 3306 is not blocked by firewall
- Verify MySQL service is started:

**Windows:**
```powershell
Get-Service MySQL80  # or MySQL57, MySQL56, etc.
```

**Mac/Linux:**
```bash
sudo systemctl status mysql
```

### Error: "Unknown database 'super_ai_transcript'"

**Solution:**
- Create the database:
```sql
CREATE DATABASE super_ai_transcript;
```
- The app will automatically create tables on first run

### Error: "Can't create/write to file"

**Solution:**
- Check MySQL has permission to write data files
- Restart MySQL service:

**Windows:**
```powershell
Restart-Service MySQL80
```

**Mac/Linux:**
```bash
sudo systemctl restart mysql
```

---

## 📚 Useful MySQL Commands

```sql
-- Connect to database
USE super_ai_transcript;

-- Show all tables
SHOW TABLES;

-- Show table structure
DESCRIBE recordings;

-- Count records
SELECT COUNT(*) FROM recordings;

-- View recent recordings
SELECT id, filename, created_at FROM recordings ORDER BY created_at DESC LIMIT 10;

-- Delete all recordings (be careful!)
TRUNCATE TABLE recordings;
TRUNCATE TABLE qa_history;

-- Backup database
mysqldump -u root -p super_ai_transcript > backup.sql

-- Restore database
mysql -u root -p super_ai_transcript < backup.sql
```

---

## 🔄 Migrating from SQLite

If you were using SQLite before:

1. Your old data is backed up in `database_sqlite.py.bak`
2. SQLite database file: `super_ai_transcript.db` (still exists but not used)
3. New MySQL database will start fresh
4. To keep old data, you need to migrate manually or export/import

---

## 📈 Performance Tips

### Connection Pooling

The app uses MySQL connection pooling (default 5 connections):
- Better performance than creating new connections each time
- Automatic connection reuse
- Configurable in `database.py` if needed

### Indexing

Useful indexes for queries:
```sql
CREATE INDEX idx_created_at ON recordings(created_at);
CREATE INDEX idx_recording_id ON qa_history(recording_id);
```

### Backup Strategy

Regular backups recommended:
```bash
# Daily backup
mysqldump -u root -p super_ai_transcript > backups/backup_$(date +%Y%m%d).sql

# Compress backup
mysqldump -u root -p super_ai_transcript | gzip > backup.sql.gz
```

---

## 🎓 Learning Resources

- **MySQL Official Documentation:** https://dev.mysql.com/doc/
- **MySQL Workbench Guide:** https://dev.mysql.com/doc/workbench/en/
- **Python MySQL Connector:** https://dev.mysql.com/doc/connector-python/en/
- **SQL Tutorial:** https://www.w3schools.com/sql/

---

## ✅ Verification Checklist

- [ ] MySQL server installed
- [ ] MySQL service running
- [ ] Database `super_ai_transcript` created
- [ ] `.env` file configured with credentials
- [ ] `mysql-connector-python` installed (`pip install -r requirements.txt`)
- [ ] `python app.py` starts without errors
- [ ] Web UI accessible at http://127.0.0.1:5000

---

**Status: Ready for MySQL Testing!** 🚀

If you encounter issues, check the error message in the terminal and refer to the "Troubleshooting" section above.
