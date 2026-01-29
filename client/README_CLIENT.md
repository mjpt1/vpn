# VPN Client (بدون UI)

Client Core VPN ویندوزی - **بدون رابط گرافیکی**

این Client فقط منطق اتصال و شبکه را پیاده‌سازی می‌کند. در فاز بعدی UI اضافه خواهد شد.

---

## 📋 پیش‌نیازها

### 1. Python 3.11+
```powershell
python --version
```

### 2. TAP-Windows Driver
**مهم:** برای ایجاد Interface مجازی نیاز است:

```powershell
# دانلود OpenVPN (شامل TAP-Windows6 driver)
# از اینجا: https://openvpn.net/community-downloads/
# یا استفاده از Chocolatey:
choco install openvpn
```

بعد از نصب، یک TAP interface در Network Connections ایجاد می‌شود.

### 3. دسترسی Administrator
Client نیاز به دسترسی Administrator دارد برای:
- تنظیم IP روی TAP interface
- تغییر Routing Table
- تنظیم DNS
- افزودن Firewall Rules

---

## 🚀 نصب و راه‌اندازی

### مرحله 1: نصب Dependencies

```powershell
# نصب از requirements.txt
pip install -r requirements.txt
```

### مرحله 2: ساخت Configuration File

```powershell
# ایجاد فایل پیکربندی پیش‌فرض
python client_main.py --create-config
```

این دستور فایل `client_config.yaml` را می‌سازد.

### مرحله 3: ویرایش Configuration

فایل `client_config.yaml` را باز کنید و موارد زیر را تنظیم کنید:

```yaml
server:
  host: "YOUR_SERVER_IP"    # IP سرور در ایران

auth:
  username: "admin"          # نام کاربری شما
  password: "your_password"  # رمز عبور شما
```

### مرحله 4: اجرا (با دسترسی Administrator)

```powershell
# اجرا به‌صورت Administrator
python client_main.py
```

---

## 📂 ساختار Client

```
client/
├── core/                           # هسته اصلی Client
│   ├── encryption.py               # ChaCha20-Poly1305 encryption
│   ├── packet_processor.py        # پردازش بسته‌های IP
│   ├── auto_reconnect.py           # منطق اتصال مجدد خودکار
│   ├── tunnel_client.py            # اتصال امن به Server
│   └── connection_manager.py       # مدیریت Lifecycle اتصال
│
├── network/                        # مدیریت شبکه (Windows-specific)
│   ├── tap_interface.py            # مدیریت TAP Interface
│   ├── routing_manager.py          # مدیریت Routing Table
│   ├── dns_manager.py              # مدیریت DNS
│   └── firewall_manager.py         # Kill Switch (Firewall Rules)
│
├── utils/                          # ابزارها
│   ├── config_loader.py            # بارگذاری Configuration
│   └── logger.py                   # Logger Setup
│
├── client_main.py                  # نقطه ورود اصلی (بدون UI)
├── requirements.txt                # Dependencies
└── client_config.yaml              # فایل پیکربندی
```

---

## ⚙️ ویژگی‌ها

### ✅ پیاده‌سازی شده

1. **اتصال امن به Server**
   - TLS 1.3 encryption
   - ChaCha20-Poly1305 برای داده‌ها
   - احراز هویت با نام کاربری/رمز عبور

2. **Auto-Reconnect**
   - اتصال مجدد خودکار با Exponential Backoff
   - حداکثر backoff: 30 ثانیه
   - تلاش مجدد بی‌نهایت

3. **Network Management**
   - TAP Interface (TAP-Windows6)
   - Routing Table Management
   - DNS Configuration
   - Kill Switch (Firewall Rules)

4. **Packet Processing**
   - اعتبارسنجی بسته‌های IP v4/v6
   - آمار ارسال/دریافت
   - Replay Protection

### ⏳ در حال توسعه (فاز بعدی)

- رابط گرافیکی (GUI)
- Split Tunneling
- Traffic Obfuscation
- IPv6 Support کامل

---

## 🔒 امنیت

### Encryption
- **Data Encryption:** ChaCha20-Poly1305 AEAD (256-bit)
- **Transport Encryption:** TLS 1.3
- **Password Hashing:** SHA256 (موقت - در آینده Argon2)

### Kill Switch
وقتی فعال باشد، تمام ترافیک بلاک می‌شود به‌جز:
- اتصال به VPN Server
- Loopback (127.0.0.1)
- LAN (اختیاری)

### Replay Protection
- Sliding Window (64 packets)
- Nonce-based counter
- Timestamp validation

---

## 🧪 تست Client

### تست اتصال

```powershell
# اجرا با لاگ DEBUG
python client_main.py --config client_config.yaml
```

### بررسی TAP Interface

```powershell
# لیست Interface‌ها
netsh interface show interface

# بررسی IP
ipconfig
```

### بررسی Routing Table

```powershell
# مشاهده مسیرها
route print
```

### بررسی DNS

```powershell
# مشاهده DNS تنظیم‌شده
ipconfig /all
```

### بررسی Firewall Rules

```powershell
# لیست Rule‌های VPN
netsh advfirewall firewall show rule name=all | findstr VPN_KillSwitch
```

---

## 🐛 عیب‌یابی

### 1. خطای "No TAP adapter found"

**حل:**
```powershell
# نصب TAP-Windows6 driver
# دانلود OpenVPN از: https://openvpn.net/community-downloads/
```

### 2. خطای "Access Denied"

**حل:**
```powershell
# اجرا به‌صورت Administrator
# راست‌کلیک روی PowerShell -> Run as Administrator
```

### 3. خطای "Connection timeout"

**بررسی:**
- آیا Server در حال اجراست؟
- آیا `server.host` در config صحیح است؟
- آیا Firewall Server پورت 8443 را بلاک کرده؟

```powershell
# تست اتصال به Server
Test-NetConnection -ComputerName YOUR_SERVER_IP -Port 8443
```

### 4. خطای "Authentication failed"

**بررسی:**
- نام کاربری/رمز عبور صحیح است؟
- آیا کاربر در Database Server وجود دارد؟

```bash
# در Server
python server_main.py --create-user admin password123
```

### 5. اینترنت کار نمی‌کند

**بررسی:**
```powershell
# بررسی IP دریافتی
ipconfig

# بررسی مسیرها
route print

# بررسی DNS
nslookup google.com

# پینگ Gateway
ping 10.8.0.1
```

---

## 📊 آمار و Monitoring

### مشاهده آمار در Console

Client هر 30 ثانیه آمار را چاپ می‌کند:
- وضعیت اتصال
- Uptime
- Bytes sent/received
- Packets sent/received

### فایل لاگ

```powershell
# مشاهده لاگ‌ها
Get-Content vpn_client.log -Tail 50 -Wait
```

---

## 🔧 توسعه

### ساختار Modular

Client با معماری Modular طراحی شده:
- **Core:** منطق اتصال و رمزنگاری
- **Network:** مدیریت شبکه (Windows-specific)
- **Utils:** ابزارهای عمومی

### افزودن قابلیت جدید

1. ایجاد ماژول جدید در پوشه مربوطه
2. Import در `connection_manager.py`
3. فراخوانی در `_setup_network()` یا `_cleanup_network()`

---

## ⚠️ محدودیت‌ها (نسخه فعلی)

1. **فقط Windows:** Network managers برای Windows طراحی شده‌اند
2. **بدون GUI:** رابط خط‌فرمان فقط
3. **IPv4 Only:** پشتیبانی کامل از IPv6 در حال توسعه
4. **Single-threaded TAP:** خواندن/نوشتن TAP هنوز پیاده‌سازی نشده

---

## 📝 فاز بعدی

### فاز 5: Client GUI (PyQt6 / Tkinter)
- رابط گرافیکی کاربرپسند
- System Tray Icon
- Connection Status Display
- Statistics Charts
- Log Viewer

### فاز 6: Testing & Deployment
- Unit Tests
- Integration Tests
- Performance Tests
- Windows Installer (.exe)
- Auto-Update Mechanism

---

## 📄 مجوز

این پروژه برای استفاده شخصی توسعه داده شده است.

---

## 🤝 مشارکت

برای گزارش باگ یا پیشنهاد قابلیت جدید، لطفاً Issue ایجاد کنید.
