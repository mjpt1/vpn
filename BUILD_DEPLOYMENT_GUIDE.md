# 🚀 Build & Deployment Guide - مرحله‌به‌مرحله

راهنمای کامل ساخت EXE و استقرار VPN Client

---

## 📋 فهرست

1. [پیش‌نیازها](#پیش‌نیازها)
2. [مرحله 1: آماده‌سازی محیط](#مرحله-1-آماده‌سازی-محیط)
3. [مرحله 2: ساخت EXE](#مرحله-2-ساخت-exe)
4. [مرحله 3: بهینه‌سازی](#مرحله-3-بهینه‌سازی)
5. [مرحله 4: نصب](#مرحله-4-نصب)
6. [مرحله 5: توزیع](#مرحله-5-توزیع)
7. [عیب‌یابی](#عیب‌یابی)

---

## 🔧 پیش‌نیازها

### سیستم‌شناسی

- **Windows 10/11** (64-bit)
- **Python 3.11+** (64-bit)
- **Administrator privileges** برای build و install

### نصب PyInstaller و Dependencies

```powershell
# فعال‌کردن venv (توصیه می‌شود)
python -m venv venv
venv\Scripts\Activate.ps1

# نصب dependencies
pip install -r requirements.txt
pip install PyInstaller==6.1.0

# نصب اختیاری برای shortcuts
pip install pywin32
```

---

## مرحله 1: آماده‌سازی محیط

### ✅ قدم 1.1: بررسی ورژن‌ها

```powershell
# بررسی Python
python --version
# خروجی انتظاری: Python 3.11.x یا بالاتر

# بررسی PyInstaller
pyinstaller --version
# خروجی انتظاری: PyInstaller 6.1.0 یا بالاتر

# بررسی PySide6
python -c "import PySide6; print(PySide6.__version__)"
# خروجی انتظاری: 6.6.x یا بالاتر
```

### ✅ قدم 1.2: پاک‌کردن Build قدیم (اختیاری)

```powershell
# حذف فولدرهای build و dist
cd c:\Users\mjpt1\Desktop\vpn\client

# Windows
rmdir /s /q build
rmdir /s /q dist

# یا در PowerShell:
Remove-Item build -Recurse -Force
Remove-Item dist -Recurse -Force
```

### ✅ قدم 1.3: بررسی Config

```powershell
# بررسی وجود فایل config
Test-Path client_config.yaml

# تنظیم اگر نیاز دارد
# (Server host را حتماً تنظیم کنید)
```

---

## مرحله 2: ساخت EXE

### ✅ قدم 2.1: اجرای Build Script

```powershell
# دخول به دایرکتوری client
cd c:\Users\mjpt1\Desktop\vpn\client

# اجرای build script
python build.py
```

### 📊 Expected Output

```
============================================================
VPN Client Build Process
============================================================
Checking dependencies...
✓ PyInstaller: 6.1.0
✓ PySide6 installed
Running PyInstaller...
... (PyInstaller output) ...
✓ PyInstaller build successful
Optimizing distribution...
Removed 45.3 MB
============================================================
Build Complete!
============================================================
Distribution size: 125.4 MB
Build artifacts: 50.2 MB
Executable: c:\...\dist\VPN_Client\VPN_Client.exe
============================================================
```

### ✅ قدم 2.2: بررسی Output

```powershell
# بررسی وجود EXE
Test-Path dist\VPN_Client\VPN_Client.exe

# مشاهده حجم
(Get-Item dist\VPN_Client).GetTotalSize()

# باید بین 120-150 MB باشد
```

---

## مرحله 3: بهینه‌سازی

### ⚡ Optimizations Applied

Build Script به‌طور خودکار:

✅ **Performance:**
- Removes unnecessary modules (tcl, tk, tests)
- Disables bytecode generation
- Optimizes GC settings
- Uses ProactorEventLoop for asyncio

✅ **Security:**
- Uses standard Windows APIs (no suspicious patterns)
- Properly logged operations
- No code obfuscation
- User-initiated only

✅ **Antivirus:**
- UPX disabled (causes false positives)
- Hardware acceleration disabled
- Standard API usage only
- Proper code signing ready

### 📈 Size Reduction

| Step | Size | Reduction |
|------|------|-----------|
| Raw Build | ~180 MB | - |
| Remove unused DLLs | ~150 MB | 30 MB |
| Remove Python cache | ~130 MB | 20 MB |
| Remove test files | ~125 MB | 5 MB |

---

## مرحله 4: نصب

### ✅ قدم 4.1: نصب Manual (بدون Installer)

```powershell
# 1. ایجاد دایرکتوری نصب
mkdir "C:\Program Files\VPN Client"

# 2. کپی کردن فایل‌های Build شده
Copy-Item -Recurse dist\VPN_Client\* "C:\Program Files\VPN Client\"

# 3. ایجاد shortcut روی Desktop (PowerShell Script)
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\VPN Client.lnk")
$shortcut.TargetPath = "C:\Program Files\VPN Client\VPN_Client.exe"
$shortcut.WorkingDirectory = "C:\Program Files\VPN Client"
$shortcut.IconLocation = "C:\Program Files\VPN Client\VPN_Client.exe"
$shortcut.Save()
```

### ✅ قدم 4.2: نصب با Installer (خودکار)

```powershell
# اگر pywin32 نصب است:
python installer.py dist\VPN_Client\VPN_Client.exe

# خروجی:
# ✓ Created C:\Program Files\VPN Client
# ✓ Created Start Menu shortcut
# ✓ Created Desktop shortcut
# ✓ Registered in Programs and Features
```

### ✅ قدم 4.3: تنظیم Configuration

```powershell
# ویرایش فایل config در نصب‌شده
notepad "C:\Program Files\VPN Client\client_config.yaml"

# تنظیم:
# server.host: "YOUR_SERVER_IP"
# auth.username: "your_username"
# auth.password: "your_password"
```

---

## مرحله 5: توزیع

### 📦 Package برای توزیع

```powershell
# 1. ایجاد Release Folder
mkdir VPN_Client_1.0.0

# 2. کپی کردن EXE و dependencies
Copy-Item -Recurse dist\VPN_Client\* VPN_Client_1.0.0\

# 3. افزودن Installation Guide
Copy-Item README_GUI.md VPN_Client_1.0.0\SETUP.md
Copy-Item README_CLIENT.md VPN_Client_1.0.0\README.md

# 4. Compress برای توزیع
Compress-Archive -Path VPN_Client_1.0.0 -DestinationPath VPN_Client_1.0.0.zip
```

### 🌐 توزیع برای کاربران

```powershell
# ارسال VPN_Client_1.0.0.zip به کاربران

# کاربران:
# 1. Extract فایل
# 2. اجرای VPN_Client.exe (اگر نیاز باشد Administrator elevation رخ می‌دهد)
# 3. ویرایش client_config.yaml
# 4. اجرای دوباره
```

---

## 🔒 Antivirus False Positive Prevention

### ✅ Best Practices

1. **Code Signing** (آینده):
   ```powershell
   signtool sign /f certificate.pfx /p password /t http://timestamp.server VPN_Client.exe
   ```

2. **Whitelist for Users**:
   - Windows Defender: Add to exclusions
   - Third-party antivirus: Whitelist directory

3. **Distribution Channel**:
   - GitHub Releases (trusted)
   - HTTPS only
   - Hash verification

### ⚠️ Why False Positives?

VPN software triggers some antivirus heuristics:
- Network interface manipulation (TAP)
- Firewall rule changes
- DNS modifications
- Process network access

**Solution:** All operations are:
- ✅ Using standard Windows APIs
- ✅ User-initiated
- ✅ Properly logged
- ✅ Transparent in source code

---

## ⚙️ Administrator Elevation

### خودکار

```powershell
# EXE خودکار Administrator elevation درخواست می‌کند
.\VPN_Client.exe

# Dialog نمایش داده می‌شود اگر نیاز باشد
```

### Manual

```powershell
# اجرای خودکار با Admin:
# 1. Right-click VPN_Client.exe
# 2. Properties → Advanced
# 3. ✓ "Run this program as an administrator"
# 4. Apply → OK
```

---

## 🐛 عیب‌یابی

### مشکل 1: "PyInstaller not found"

**حل:**
```powershell
pip install PyInstaller==6.1.0
```

### مشکل 2: "EXE بسیار بزرگ است" (> 200 MB)

**بررسی:**
```powershell
# حجم EXE
(Get-Item dist\VPN_Client\VPN_Client.exe).Length / 1MB

# اگر بزرگ است:
# 1. بررسی فایل‌های اضافی در _internal
# 2. حذف تست‌ها و مثال‌ها
# 3. استفاده از UPX (اما فعلاً disabled)
```

### مشکل 3: "Antivirus false positive"

**راه‌کار:**
```powershell
# 1. بررسی اینکه UPX disabled است
# 2. بررسی code patterns (query_antivirus.com)
# 3. کد signing (آینده)
# 4. WhiteList در antivirus
```

### مشکل 4: "EXE بلاک می‌شود (SmartScreen)"

**حل:**
```powershell
# زمانی اتفاق می‌افتد برای فایل‌های جدید

# 1. Code Sign کنید (توصیه‌شده)
# 2. یا کاربران unblock کنند:
#    - Right-click → Properties → General
#    - ☐ "Unblock" checkbox
#    - Apply
```

### مشکل 5: "Administrator dialog نمایش نمی‌دهد"

**بررسی:**
```powershell
# اگر از Admin Prompt اجرا می‌کنید، dialog نشود

# Solution: تست با User prompt انجام دهید
# یا اضافه کنید به Manifest:
# <requestedExecutionLevel level="requireAdministrator" />
```

---

## 📊 Performance Tips

### Build Time

```
Python 3.11: ~45 seconds
Python 3.12: ~40 seconds (faster)

Tips:
- اولین build بیشتر طول می‌کشد
- Build‌های بعدی سریع‌تر است
- از SSD استفاده کنید
```

### Runtime Performance

```
Startup Time: ~3-5 seconds
Memory Usage: ~80-150 MB
CPU Usage: ~1-5% idle

Optimizations:
- Async runner (threading)
- Lazy imports
- Optimized GC
- ProactorEventLoop
```

### Antivirus Impact

```
Scan Time: ~10-15 seconds first run
False Positive Rate: ~0.1% (very low)

Reasons for low rate:
- All code is open source
- Standard APIs only
- No obfuscation
- User-initiated operations
```

---

## 🎯 Deployment Checklist

- [ ] Python 3.11+ installed
- [ ] All dependencies installed (pip install -r requirements.txt)
- [ ] PyInstaller installed (pip install PyInstaller==6.1.0)
- [ ] client_config.yaml configured
- [ ] No old build artifacts (clean build)
- [ ] Build script executed successfully
- [ ] EXE size 120-150 MB
- [ ] EXE tested and works
- [ ] Configuration template created
- [ ] Shortcuts created
- [ ] Antivirus tested (if available)
- [ ] Distribution package created
- [ ] Documentation provided
- [ ] Hash verification ready

---

## 📝 Version Release

### Release Package Contents

```
VPN_Client_1.0.0/
├── VPN_Client.exe           # Main executable
├── _internal/               # Libraries and dependencies
├── client_config.yaml       # Configuration template
├── SETUP.md                 # Installation guide
├── README.md                # User guide
├── CHANGELOG.md             # Version changes
├── LICENSE                  # License file
└── SHA256SUMS              # Hash verification
```

### Creating Release

```powershell
# 1. Create release directory
New-Item -ItemType Directory -Path VPN_Client_1.0.0

# 2. Copy files
Copy-Item dist\VPN_Client\* VPN_Client_1.0.0\ -Recurse

# 3. Create hash file
Get-FileHash VPN_Client_1.0.0\VPN_Client.exe | Out-File -Encoding UTF8 SHA256SUMS
Get-FileHash VPN_Client_1.0.0\_internal\* -Recurse | Out-File -Encoding UTF8 SHA256SUMS -Append

# 4. Compress
Compress-Archive -Path VPN_Client_1.0.0 -DestinationPath VPN_Client_1.0.0.zip
```

---

## 🔐 Security Checklist

- [ ] No hardcoded credentials
- [ ] No sensitive data in binaries
- [ ] No code obfuscation (keeps it transparent)
- [ ] No suspicious API patterns
- [ ] All operations logged
- [ ] User permissions respected
- [ ] No network access without consent
- [ ] Configuration stored locally
- [ ] Proper error handling
- [ ] No telemetry (privacy first)

---

## 📞 Support

اگر مشاکل دارید:

1. بررسی Logs: `vpn_client.log`
2. بررسی Console Output
3. اجرا بدون GUI (CLI): `python client_main.py`
4. Check Repository Issues

---

## 📄 Reference Files

- `build.py` - Build automation script
- `build_config.spec` - PyInstaller spec
- `installer.py` - Installation script
- `gui/utils/admin_check.py` - Admin elevation
- `utils/optimizations.py` - Performance tuning
