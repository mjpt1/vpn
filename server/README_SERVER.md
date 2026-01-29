# 🚀 Iran VPN Gateway Server - Installation & Usage Guide

## 📋 Table of Contents
1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Server](#running-the-server)
5. [User Management](#user-management)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## ✅ Requirements

### System Requirements
- **OS**: Windows 10/11 or Linux (Ubuntu 20.04+, CentOS 8+)
- **Python**: 3.11 or higher
- **RAM**: Minimum 512MB (recommended 1GB+)
- **Network**: Public IP or port forwarding for port 8443

### Python Dependencies
All dependencies are listed in `requirements.txt`

---

## 📦 Installation

### Step 1: Install Python 3.11+
**Windows:**
```powershell
# Download from python.org or use winget
winget install Python.Python.3.11
```

**Linux:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

### Step 2: Create Virtual Environment
```powershell
# Windows PowerShell
cd C:\Users\mjpt1\Desktop\vpn\server
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# Linux
cd /path/to/vpn/server
python3.11 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Necessary Directories
```bash
mkdir -p logs certs data
```

---

## ⚙️ Configuration

### 1. Edit Configuration File
Edit `config.yaml`:

```yaml
server:
  host: "0.0.0.0"      # Listen on all interfaces
  port: 8443           # HTTPS-like port

database:
  path: "data/vpn_server.db"

tls:
  cert_file: "certs/server.crt"
  key_file: "certs/server.key"

logging:
  level: "INFO"
  file: "logs/server.log"
```

### 2. Generate TLS Certificate (Optional)
For testing, you can run without TLS. For production:

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 \
  -subj "/CN=vpn.example.com"
```

---

## 🚀 Running the Server

### First Run - Create Default User
```bash
python server_main.py --create-user
```

This creates:
- **Username**: `admin`
- **Password**: `admin123`
- **⚠️ CHANGE THIS PASSWORD IMMEDIATELY!**

### Start Server
```bash
python server_main.py
```

Or with custom config:
```bash
python server_main.py -c my_config.yaml --log-level DEBUG
```

### Expected Output
```
============================================================
Iran VPN Gateway Server v1.0.0
============================================================
[2026-01-29 10:00:00] [    INFO] [vpn_server] Configuration:
[2026-01-29 10:00:00] [    INFO] [vpn_server]   Host: 0.0.0.0
[2026-01-29 10:00:00] [    INFO] [vpn_server]   Port: 8443
[2026-01-29 10:00:00] [    INFO] [vpn_server]   Database: vpn_server.db
[2026-01-29 10:00:00] [    INFO] [vpn_server] Server started on ('0.0.0.0', 8443)
[2026-01-29 10:00:00] [    INFO] [vpn_server] Waiting for connections...
```

### Stop Server
Press `Ctrl+C` for graceful shutdown.

---

## 👥 User Management

### Using Python Interactive Shell

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.database.models import Base
from server.database.user_repo import UserRepository

# Connect to database
engine = create_engine('sqlite:///vpn_server.db')
Session = sessionmaker(bind=engine)
db = Session()
user_repo = UserRepository(db)

# Create user
user_repo.create_user(
    username="john",
    password="secure_password_123",
    email="john@example.com",
    max_sessions=3
)

# List users
users = user_repo.list_users()
for user in users:
    print(user.to_dict())

# Disable user
user_repo.disable_user(user_id=2)

# Change password
user_repo.update_password(user_id=1, new_password="new_password")

db.close()
```

---

## 🧪 Testing

### Test Server is Running
```bash
# Test if port is listening
netstat -an | grep 8443    # Linux
netstat -an | findstr 8443  # Windows
```

### Test with Telnet (TLS disabled)
```bash
telnet localhost 8443
```

### Test Encryption Module
```python
from server.core.encryption import EncryptionHandler

# Create handler
enc = EncryptionHandler()

# Encrypt
plaintext = b"Hello, World!"
encrypted = enc.encrypt(plaintext)
print(f"Encrypted: {encrypted.hex()}")

# Decrypt
decrypted = enc.decrypt(encrypted)
print(f"Decrypted: {decrypted}")
assert decrypted == plaintext
print("✅ Encryption works!")
```

### Test Authentication
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.database.user_repo import UserRepository
from server.core.auth_handler import AuthHandler

engine = create_engine('sqlite:///vpn_server.db')
Session = sessionmaker(bind=engine)
db = Session()

auth = AuthHandler(db)

# Test authentication
session, key = auth.authenticate_user(
    username="admin",
    password="admin123",
    client_ip="192.168.1.100",
    client_version="1.0.0"
)

print(f"✅ Session created: {session.session_token}")
print(f"   Assigned IP: {session.assigned_ip}")
print(f"   Encryption key: {key[:32]}...")

db.close()
```

---

## 🔧 Troubleshooting

### Issue: Port 8443 already in use
```bash
# Find process using port
netstat -ano | findstr :8443  # Windows
sudo lsof -i :8443            # Linux

# Kill process or change port in config.yaml
```

### Issue: Permission denied (Linux)
```bash
# Run with sudo for privileged ports (<1024)
sudo python server_main.py

# Or use port >1024 (e.g., 8443)
```

### Issue: Database locked
```bash
# Close all Python sessions accessing the database
# Delete database file and restart
rm vpn_server.db
python server_main.py --create-user
```

### Issue: TLS certificate error
```bash
# Regenerate certificate
rm certs/*
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 -subj "/CN=localhost"
```

### Issue: Module not found
```bash
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### Enable Debug Logging
```bash
python server_main.py --log-level DEBUG
```

---

## 📊 Monitoring

### Check Active Sessions
```python
from server.core.tunnel_server import TunnelServer
# Access server.session_manager.get_statistics()
```

### View Logs
```bash
# Tail log file
tail -f logs/server.log        # Linux
Get-Content logs/server.log -Tail 50 -Wait  # PowerShell
```

### Database Statistics
```python
from sqlalchemy import create_engine
from server.database.models import Session, User, ConnectionLog
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///vpn_server.db')
DBSession = sessionmaker(bind=engine)
db = DBSession()

# Count users
user_count = db.query(User).count()
print(f"Total users: {user_count}")

# Count active sessions
active_sessions = db.query(Session).filter(Session.is_active == True).count()
print(f"Active sessions: {active_sessions}")

# Recent connections
recent = db.query(ConnectionLog).order_by(ConnectionLog.connected_at.desc()).limit(10).all()
for log in recent:
    print(log.to_dict())

db.close()
```

---

## 🛡️ Security Recommendations

1. **Change default password immediately**
2. **Use strong TLS certificate (not self-signed in production)**
3. **Enable firewall and allow only port 8443**
4. **Regular database backups**
5. **Monitor logs for suspicious activity**
6. **Keep Python and dependencies updated**
7. **Use environment variables for sensitive config**

---

## 📝 Next Steps

- **Client Implementation**: Connect Windows client to this server
- **TUN/TAP Integration**: Implement actual packet forwarding (requires Linux)
- **DDNS Setup**: Configure dynamic DNS for changing IP
- **Monitoring Dashboard**: Add web interface for management
- **Load Balancing**: Scale to multiple servers

---

## 🆘 Support

For issues, check:
- Log files in `logs/`
- Database integrity: `sqlite3 vpn_server.db "PRAGMA integrity_check;"`
- Python version: `python --version` (must be 3.11+)

**Remember**: This is for personal use. Respect local laws and regulations.
