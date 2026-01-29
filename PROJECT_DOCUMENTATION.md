# 🔐 Iran VPN Gateway - Complete Project Documentation

**Project Type**: Personal VPN Gateway System  
**Technology Stack**: Python 3.11+, PyQt6, TLS 1.3, ChaCha20-Poly1305  
**Target Platform**: Windows 10/11 (Client) + Linux (Server)  
**Date Created**: January 29, 2026  
**Architecture**: Reverse Connection VPN with Full Tunnel Support

---

# 📑 Table of Contents

1. [فاز ۱: Design Overview & Architecture](#فاز-۱-design-overview--architecture)
2. [فاز ۲: Project Structure & Dependencies](#فاز-۲-project-structure--dependencies)

---

# فاز ۱: Design Overview & Architecture

## 1️⃣ معماری کل سیستم

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERNET IRAN                             │
│  ┌──────────────────────────────────────┐                   │
│  │  Server (Gateway) - IRAN             │                   │
│  │  ┌────────────────────────────────┐  │                   │
│  │  │ Control Server (TCP 8443)      │◄─┼───────┐           │
│  │  │ - Client Authentication        │  │       │           │
│  │  │ - Session Management           │  │       │           │
│  │  │ - Dynamic Port Assignment      │  │       │           │
│  │  └────────────────────────────────┘  │       │           │
│  │  ┌────────────────────────────────┐  │       │           │
│  │  │ TUN/TAP Interface              │  │       │           │
│  │  │ - IP: 10.8.0.1/24             │  │       │           │
│  │  │ - NAT Masquerading             │  │       │           │
│  │  │ - IP Forwarding                │  │       │           │
│  │  └────────────────────────────────┘  │       │           │
│  │  ┌────────────────────────────────┐  │       │           │
│  │  │ Tunnel Handler (Dynamic Port)  │  │       │           │
│  │  │ - ChaCha20-Poly1305 Encryption │  │       │           │
│  │  │ - Per-Client Sessions          │  │       │           │
│  │  └────────────────────────────────┘  │       │           │
│  └──────────────────────────────────────┘       │           │
└──────────────────────────────────────────────────┼───────────┘
                                                   │
                              Reverse Connection   │
                              (Client → Server)    │
                                                   │
┌──────────────────────────────────────────────────┼───────────┐
│                  INTERNET OUTSIDE                │           │
│  ┌────────────────────────────────────┐          │           │
│  │  Client - WINDOWS (Behind CGNAT)   │          │           │
│  │  ┌──────────────────────────────┐  │          │           │
│  │  │ GUI Application (PyQt6)      │  │          │           │
│  │  │ - Connection Manager         │  │          │           │
│  │  │ - System Tray Integration    │  │          │           │
│  │  └──────────────────────────────┘  │          │           │
│  │  ┌──────────────────────────────┐  │          │           │
│  │  │ TUN/TAP Interface            │  │          │           │
│  │  │ - IP: 10.8.0.x/24           │  │          │           │
│  │  │ - Default Route via Tunnel   │  │          │           │
│  │  └──────────────────────────────┘  │          │           │
│  │  ┌──────────────────────────────┐  │          │           │
│  │  │ Tunnel Client                │──┼──────────┘           │
│  │  │ - Persistent Connection      │  │                      │
│  │  │ - Auto-Reconnect Logic       │  │                      │
│  │  └──────────────────────────────┘  │                      │
│  └────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ Step-by-Step Packet Flow

### **Phase A: Connection Establishment (Reverse Connection)**

```
1. CLIENT → SERVER (Control Channel)
   [Client behind CGNAT] --TCP SYN--> [Server:8443]
   - Client initiates connection (bypasses CGNAT)
   - TLS 1.3 handshake begins
   
2. TLS HANDSHAKE
   Client → Server: ClientHello (TLS 1.3, SNI, ALPN)
   Server → Client: ServerHello, Certificate, CertificateVerify
   Client ← Server: Finished
   - X25519 ECDHE key exchange
   
3. AUTHENTICATION
   Client → Server: {username, password_hash, client_version}
   Server validates credentials
   Server → Client: {session_token, tunnel_port, client_ip: 10.8.0.x}
   
4. TUNNEL ESTABLISHMENT
   Client → Server: Connect to tunnel_port (same TCP connection upgrade)
   Server creates dedicated session
   Server assigns virtual IP and routing
```

### **Phase B: Data Tunnel Flow (Full Tunnel)**

```
5. CLIENT SENDS DATA
   ┌─────────────────────────────────────────────────┐
   │ App (Browser) → TUN Interface (10.8.0.x)        │
   │   Original Packet: [SrcIP: 10.8.0.5 | DstIP: 8.8.8.8 | Data: DNS Query] 
   └─────────────────────────────────────────────────┘
                          ↓
   ┌─────────────────────────────────────────────────┐
   │ Tunnel Client encrypts packet                   │
   │   ChaCha20-Poly1305(packet) + sequence_number   │
   └─────────────────────────────────────────────────┘
                          ↓
   ┌─────────────────────────────────────────────────┐
   │ TCP Stream → Server (Encrypted Tunnel)          │
   │   [Real SrcIP: Client WAN | DstIP: Server Iran] │
   │   Payload: [Encrypted(Original Packet)]         │
   └─────────────────────────────────────────────────┘
   
6. SERVER PROCESSES
   ┌─────────────────────────────────────────────────┐
   │ Server receives encrypted packet                │
   │   Decrypt with ChaCha20-Poly1305                │
   │   Extract: [SrcIP: 10.8.0.5 | DstIP: 8.8.8.8]  │
   └─────────────────────────────────────────────────┘
                          ↓
   ┌─────────────────────────────────────────────────┐
   │ Write to TUN Interface (10.8.0.1)               │
   │   Linux kernel routing table                    │
   │   NAT/Masquerade: 10.8.0.5 → Server_Public_IP   │
   └─────────────────────────────────────────────────┘
                          ↓
   ┌─────────────────────────────────────────────────┐
   │ Forward to Internet (Iran IP)                   │
   │   [SrcIP: Server_Public_IP | DstIP: 8.8.8.8]   │
   └─────────────────────────────────────────────────┘

7. RESPONSE PATH (Reverse)
   Internet → Server (8.8.8.8 response)
   Server NAT translates back: Server_IP → 10.8.0.5
   Server writes to TUN → Tunnel encrypts → Client
   Client decrypts → writes to TUN → Application receives
```

---

## 3️⃣ انتخاب نوع Tunnel: **TCP-based با TLS 1.3**

### ✅ **انتخاب: TCP + TLS 1.3**

**دلایل فنی:**

1. **CGNAT Compatibility**: 
   - TCP SYN همیشه از کلاینت شروع می‌شود → NAT mapping پایدار
   - UDP در CGNAT ایران timeout سریع دارد (30-60 ثانیه)
   
2. **Firewall Traversal**:
   - Port 8443 (HTTPS) فیلتر نمی‌شود
   - Traffic به HTTPS معمولی شبیه است (DPI evasion)
   
3. **Reliability**:
   - TCP خودش retransmission دارد → ساده‌تر از UDP reliability
   - در اینترنت ایران با packet loss بالا مفیدتر است
   
4. **TLS 1.3 Benefits**:
   - 0-RTT resumption برای reconnect سریع
   - Perfect Forward Secrecy (PFS)
   - Camouflage به عنوان HTTPS traffic

**⚠️ Trade-off:**
- TCP-over-TCP باعث performance overhead می‌شود
- **راه‌حل**: استفاده از TCP BBR congestion control + پارامترهای بهینه

### 🔄 **Fallback Option: UDP با KCP Protocol**
- اگر TCP مسدود شد: KCP-over-UDP (port 443)
- KCP: Fast retransmission برای UDP
- احتیاج به keepalive agressive دارد

---

## 4️⃣ Reverse Connection برای عبور از CGNAT

### **مشکل CGNAT:**
```
Client (10.100.x.x) → ISP NAT → CGNAT (100.64.x.x) → Internet
                                    ↑
                          Port mapping dynamic & shared
                          Inbound connection impossible
```

### **راه‌حل: Client-Initiated Persistent Connection**

```
┌──────────────────────────────────────────────────────┐
│ STEP 1: Client Connects (Outbound)                   │
│   Client → Server:8443 (TCP SYN)                     │
│   CGNAT creates mapping: [Client:Random → Server:8443]│
│   This mapping stays alive while connection active   │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│ STEP 2: Connection Upgrade                           │
│   Client authenticates over TLS control channel      │
│   Server sends: "Upgrade to tunnel mode"             │
│   Same TCP socket converted to bidirectional tunnel  │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│ STEP 3: Keepalive Mechanism                          │
│   Client → Server: Ping every 15 seconds             │
│   Server → Client: Pong response                     │
│   If no pong: reconnect immediately                  │
│   Prevents CGNAT timeout (typically 60-120s)         │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│ STEP 4: Auto-Reconnect Strategy                      │
│   Exponential backoff: 1s, 2s, 4s, 8s, 15s (max)    │
│   Session token cached → fast re-auth                │
│   TLS 1.3 session resumption (0-RTT)                 │
│   User traffic queued during reconnect (5s buffer)   │
└──────────────────────────────────────────────────────┘
```

### **مدیریت IP داینامیک Server:**
- Server هر 5 دقیقه IP خود را به **Dynamic DNS** می‌فرستد
- Client از DDNS hostname استفاده می‌کند (مثلاً: `myserver.ddns.net`)
- DNS cache TTL: 60 seconds
- اگر connection fail → resolve DDNS دوباره

---

## 5️⃣ استراتژی امنیتی

### **Layer 1: Transport Security (TLS 1.3)**
```
┌─────────────────────────────────────────────┐
│ TLS 1.3 Control Channel                     │
│  - Cipher: TLS_CHACHA20_POLY1305_SHA256     │
│  - Key Exchange: X25519 (ECDHE)             │
│  - Certificate: Self-signed (pinned on client)│
│  - SNI: randomized (example.com lookalike)  │
└─────────────────────────────────────────────┘
```

### **Layer 2: Application Encryption (Data Tunnel)**
```
┌─────────────────────────────────────────────┐
│ ChaCha20-Poly1305 AEAD                       │
│  - Key derivation: HKDF-SHA256               │
│  - Master key from TLS session               │
│  - Per-packet nonce: counter + timestamp     │
│  - Authentication tag: 16 bytes (Poly1305)   │
│  - Replay protection: sliding window (64)    │
└─────────────────────────────────────────────┘

Encrypted Packet Structure:
[2 bytes: Length | 8 bytes: Nonce | N bytes: Ciphertext | 16 bytes: Tag]
```

### **Layer 3: Authentication & Authorization**
```
┌─────────────────────────────────────────────┐
│ Initial Auth:                                │
│  1. Client sends: SHA256(password + salt)    │
│  2. Server validates against database        │
│  3. Server generates: session_token (UUID)   │
│  4. Token valid for 24 hours                 │
│                                              │
│ Subsequent Auth:                             │
│  - Client sends session_token                │
│  - Server validates + extends expiry         │
│  - If expired: re-authenticate               │
└─────────────────────────────────────────────┘
```

### **Layer 4: Key Rotation**
```
- Session keys rotate every 4 hours
- Server sends: REKEY command
- New keys derived from current key + random nonce
- Seamless rotation (no disconnection)
```

### **Layer 5: Anti-DPI Measures**
```
1. TLS fingerprint randomization:
   - Random cipher order
   - Random extension padding
   
2. Traffic shaping:
   - Random delays (0-50ms) between packets
   - Dummy packets mixed in (10% ratio)
   
3. SNI camouflage:
   - Rotate SNI: google.com, cloudflare.com, etc.
```

---

## 6️⃣ Full Tunnel Implementation (Windows)

### **A. TUN/TAP Interface Setup**
```
Component: OpenVPN TAP-Windows6 Driver (open-source)
Installation: Automatic via PyWinTAP library

Virtual Adapter Configuration:
  - Name: "Iran VPN Adapter"
  - IP: 10.8.0.x/24 (assigned by server)
  - MTU: 1420 (to avoid fragmentation)
  - Metric: 1 (highest priority)
```

### **B. Routing Table Modification**
```
Original Routes (Before Connection):
  0.0.0.0/0 → Default Gateway (192.168.1.1)
  
Step 1: Add specific route for VPN server
  netsh interface ip add route <server_ip>/32 interface="Ethernet" nexthop=192.168.1.1
  → Ensures control connection doesn't go through tunnel
  
Step 2: Change default route
  netsh interface ip add route 0.0.0.0/1 interface="Iran VPN Adapter" nexthop=10.8.0.1 metric=1
  netsh interface ip add route 128.0.0.0/1 interface="Iran VPN Adapter" nexthop=10.8.0.1 metric=1
  → Splits default route (higher priority than 0.0.0.0/0)
  
Step 3: Lower original default route metric
  netsh interface ip set route 0.0.0.0/0 interface="Ethernet" metric=9999
  → Keeps as fallback
```

### **C. DNS Configuration**
```
Problem: DNS leaks reveal real location

Solution:
  1. Set TUN interface DNS to Iranian DNS:
     netsh interface ip set dns "Iran VPN Adapter" static 10.202.10.202
     netsh interface ip add dns "Iran VPN Adapter" static 10.202.10.102 index=2
     
  2. Disable DNS on other interfaces:
     Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses @()
     
  3. Clear DNS cache:
     ipconfig /flushdns
     
  4. Enable DNS over Tunnel:
     Server forwards DNS queries to Iran DNS servers
```

### **D. Firewall Rules**
```
Windows Firewall Configuration:
  
  1. Allow VPN application:
     netsh advfirewall firewall add rule name="Iran VPN Client" dir=out action=allow program="C:\path\to\vpn.exe"
     
  2. Block non-VPN traffic (Kill Switch):
     netsh advfirewall firewall add rule name="Block All Out" dir=out action=block enable=yes
     netsh advfirewall firewall add rule name="Allow VPN Out" dir=out action=allow program="vpn.exe" enable=yes
     netsh advfirewall firewall add rule name="Allow LAN" dir=out action=allow remoteip=192.168.0.0/16,10.0.0.0/8 enable=yes
```

### **E. Disconnect Cleanup**
```
On disconnect, restore original state:
  1. Delete tunnel routes
  2. Restore original default route metric
  3. Re-enable original DNS settings
  4. Remove firewall rules
  5. Delete virtual adapter (or keep for next connection)
```

---

## 7️⃣ ریسک‌ها و محدودیت‌ها

### **🔴 ریسک‌های فنی**

1. **DPI (Deep Packet Inspection)**
   - **خطر**: سیستم‌های DPI ایران TLS را تحلیل می‌کنند
   - **کاهش**: TLS fingerprint randomization + traffic obfuscation
   - **محدودیت**: اگر IP سرور Iran blacklist شود → نیاز به IP جدید

2. **Performance Overhead**
   - **TCP-over-TCP**: تا 30% کاهش throughput
   - **Encryption**: ~5% CPU overhead
   - **راه‌حل**: BBR congestion control + hardware AES-NI support

3. **CGNAT Timeout**
   - **خطر**: اگر keepalive fail شود → connection drop
   - **تأثیر**: 3-5 ثانیه reconnect time
   - **کاهش**: Aggressive keepalive (15s) + fast reconnect

4. **IP Blacklisting**
   - **خطر**: Server IP ایران در فیلترینگ
   - **راه‌حل**: چندین IP backup + DDNS rotation

### **🟡 محدودیت‌های قانونی و اخلاقی**

1. **استفاده شخصی**
   - ⚠️ این سیستم فقط برای استفاده شخصی است
   - 🚫 ارائه به عموم یا فروش تجاری ممنوع
   - 📜 رعایت قوانین محلی مسئولیت کاربر است

2. **مسئولیت امنیتی**
   - Server در ایران = Traffic از IP ایران
   - مسئولیت فعالیت‌ها روی صاحب Server
   - نیاز به logging و monitoring

### **🟢 محدودیت‌های عملیاتی**

1. **Bandwidth**
   - محدود به upload سرور در ایران (~2-10 Mbps معمولی)
   - چند کاربر همزمان → تقسیم bandwidth

2. **Latency**
   - RTT: 150-300ms (ایران → اروپا → ایران)
   - Gaming و real-time apps: تجربه ضعیف

3. **Compatibility**
   - فقط Windows 10/11
   - نیاز به Administrator privileges
   - برخی antivirus ممکن است TAP driver را block کنند

4. **Maintenance**
   - Server در ایران نیاز به نگهداری دارد
   - Dynamic IP → احتیاج به DDNS update
   - Software updates باید manual باشد

### **⚫ نقاط شکست (Single Points of Failure)**

1. **Server Downtime**
   - اگر سرور ایران خاموش شود → هیچ fallback
   - **راه‌حل**: Health monitoring + auto-restart

2. **Internet Outage (Iran)**
   - اگر اینترنت ایران قطع شود → تمام کاربران قطع
   - **راه‌حل**: چندین سرور در شهرهای مختلف

3. **Certificate Expiry**
   - Self-signed cert expired → connection fails
   - **راه‌حل**: Auto-renewal + 1 year validity

### **🔵 مقایسه با راه‌حل‌های موجود**

| Feature | این سیستم | OpenVPN | WireGuard | Shadowsocks |
|---------|-----------|---------|-----------|-------------|
| CGNAT Support | ✅ Excellent | ✅ Good | ⚠️ Needs help | ✅ Good |
| DPI Resistance | ✅ Good | ⚠️ Detectable | ❌ Blocked | ✅ Excellent |
| Performance | ⚠️ Medium | ⚠️ Medium | ✅ Excellent | ✅ Good |
| Setup Complexity | ✅ Easy | ❌ Complex | ✅ Easy | ⚠️ Medium |
| Windows Native | ✅ Yes | ⚠️ Needs TAP | ⚠️ Needs driver | ✅ Yes |

---

# فاز ۲: Project Structure & Dependencies

## 1️⃣ ساختار کلی پروژه

```
vpn/
│
├── 📁 server/                          # Server Component (Iran Gateway)
│   ├── 📁 core/                        # Core functionality
│   │   ├── __init__.py
│   │   ├── tunnel_server.py            # Main tunnel server logic
│   │   ├── session_manager.py          # Client session management
│   │   ├── auth_handler.py             # Authentication & authorization
│   │   ├── encryption.py               # ChaCha20-Poly1305 implementation
│   │   └── packet_processor.py         # Packet encryption/decryption
│   │
│   ├── 📁 network/                     # Network layer
│   │   ├── __init__.py
│   │   ├── tun_interface.py            # TUN/TAP interface (Linux)
│   │   ├── routing_manager.py          # IP forwarding & NAT setup
│   │   ├── connection_handler.py       # TCP connection management
│   │   └── keepalive.py                # Keepalive mechanism
│   │
│   ├── 📁 database/                    # User & session storage
│   │   ├── __init__.py
│   │   ├── models.py                   # SQLAlchemy models
│   │   ├── user_repo.py                # User CRUD operations
│   │   └── session_repo.py             # Session CRUD operations
│   │
│   ├── 📁 utils/                       # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py                   # Centralized logging
│   │   ├── config_loader.py            # YAML config parser
│   │   ├── certificate_manager.py      # TLS certificate generation
│   │   └── ddns_updater.py             # Dynamic DNS update client
│   │
│   ├── 📁 monitoring/                  # Monitoring & stats
│   │   ├── __init__.py
│   │   ├── stats_collector.py          # Bandwidth, connection stats
│   │   └── health_check.py             # Server health monitoring
│   │
│   ├── 📄 server_main.py               # Server entry point
│   ├── 📄 config.yaml                  # Server configuration file
│   ├── 📄 requirements.txt             # Server dependencies
│   └── 📄 install_server.sh            # Server setup script (Linux)
│
├── 📁 client/                          # Client Component (Windows)
│   ├── 📁 core/                        # Core functionality
│   │   ├── __init__.py
│   │   ├── tunnel_client.py            # Main tunnel client logic
│   │   ├── connection_manager.py       # Connection lifecycle management
│   │   ├── encryption.py               # ChaCha20-Poly1305 (same as server)
│   │   ├── packet_processor.py         # Packet encryption/decryption
│   │   └── auto_reconnect.py           # Reconnection strategy
│   │
│   ├── 📁 network/                     # Network layer (Windows-specific)
│   │   ├── __init__.py
│   │   ├── tap_interface.py            # TAP-Windows adapter management
│   │   ├── routing_manager.py          # Windows routing table manipulation
│   │   ├── dns_manager.py              # DNS configuration
│   │   ├── firewall_manager.py         # Windows Firewall rules
│   │   └── network_monitor.py          # Connection quality monitoring
│   │
│   ├── 📁 gui/                         # PyQt6 User Interface
│   │   ├── __init__.py
│   │   ├── main_window.py              # Main application window
│   │   ├── system_tray.py              # System tray icon & menu
│   │   ├── login_dialog.py             # Login/authentication dialog
│   │   ├── settings_dialog.py          # Settings configuration
│   │   ├── stats_widget.py             # Real-time statistics display
│   │   ├── log_viewer.py               # Log viewer widget
│   │   └── resources/                  # UI resources
│   │       ├── icons/                  # Application icons
│   │       ├── styles.qss              # Qt stylesheet (dark theme)
│   │       └── ui_templates/           # Qt Designer .ui files (optional)
│   │
│   ├── 📁 utils/                       # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py                   # Centralized logging
│   │   ├── config_manager.py           # Local config storage (JSON)
│   │   ├── admin_privileges.py         # UAC elevation handler
│   │   └── crypto_utils.py             # Password hashing, key derivation
│   │
│   ├── 📁 services/                    # Background services
│   │   ├── __init__.py
│   │   ├── tunnel_service.py           # Main tunnel service (runs in background)
│   │   └── watchdog_service.py         # Process monitoring & auto-restart
│   │
│   ├── 📄 client_main.py               # Client GUI entry point
│   ├── 📄 service_main.py              # Background service entry point
│   ├── 📄 config.json                  # Client configuration (auto-generated)
│   ├── 📄 requirements.txt             # Client dependencies
│   ├── 📄 build_installer.py           # PyInstaller build script
│   └── 📄 installer_config.nsi         # NSIS installer script (optional)
│
├── 📁 shared/                          # Shared code between client & server
│   ├── __init__.py
│   ├── protocol.py                     # Protocol definitions & constants
│   ├── message_format.py               # Message serialization (msgpack)
│   ├── encryption_base.py              # Base encryption interface
│   └── exceptions.py                   # Custom exceptions
│
├── 📁 tests/                           # Unit & integration tests
│   ├── 📁 server/
│   │   ├── test_tunnel_server.py
│   │   ├── test_auth_handler.py
│   │   └── test_encryption.py
│   │
│   ├── 📁 client/
│   │   ├── test_tunnel_client.py
│   │   ├── test_routing_manager.py
│   │   └── test_encryption.py
│   │
│   └── 📁 integration/
│       └── test_end_to_end.py
│
├── 📁 tools/                           # Development & deployment tools
│   ├── generate_cert.py                # Self-signed certificate generator
│   ├── user_manager.py                 # CLI user management tool
│   ├── performance_test.py             # Bandwidth & latency testing
│   └── ddns_setup.py                   # DDNS configuration helper
│
├── 📁 docs/                            # Documentation
│   ├── SERVER_SETUP.md                 # Server installation guide
│   ├── CLIENT_USAGE.md                 # Client user manual
│   ├── ARCHITECTURE.md                 # Technical architecture doc
│   └── TROUBLESHOOTING.md              # Common issues & solutions
│
├── 📄 README.md                        # Project overview
├── 📄 LICENSE                          # License file
└── 📄 .gitignore                       # Git ignore patterns
```

---

## 2️⃣ نقش دقیق فایل‌های کلیدی

### **🖥️ Server Components**

| فایل | نقش | ورودی | خروجی |
|------|-----|-------|-------|
| **server_main.py** | Entry point سرور، راه‌اندازی همه سرویس‌ها | CLI args, config.yaml | Running server process |
| **tunnel_server.py** | مدیریت TLS listener، accept کردن کلاینت‌ها | Port 8443, TLS config | Client sessions |
| **session_manager.py** | مدیریت session های active، تخصیص IP | Client auth data | Session objects, Virtual IPs |
| **auth_handler.py** | Authentication و token generation | Username/password hash | Session token, user info |
| **encryption.py** | Encrypt/decrypt packets با ChaCha20-Poly1305 | Plaintext packets, keys | Encrypted packets |
| **packet_processor.py** | خواندن/نوشتن packets از TUN interface | Raw IP packets | Processed packets |
| **tun_interface.py** | ساخت و مدیریت TUN interface در Linux | Interface name, IP range | File descriptor |
| **routing_manager.py** | تنظیم IP forwarding، NAT، iptables | Network config | Routing rules applied |
| **connection_handler.py** | مدیریت TCP connections، send/recv | Socket connections | Data streams |
| **keepalive.py** | ارسال/دریافت keepalive packets | Active sessions | Ping/pong status |
| **models.py** | Database schema (Users, Sessions, Logs) | SQLAlchemy definitions | ORM models |
| **config_loader.py** | پارس کردن YAML config | config.yaml path | Config object |
| **certificate_manager.py** | ساخت/مدیریت TLS certificates | Domain, validity period | .pem files |
| **ddns_updater.py** | بروزرسانی Dynamic DNS | Current public IP | DDNS API call |
| **stats_collector.py** | جمع‌آوری آمار bandwidth، connections | Session data | Statistics metrics |

### **💻 Client Components**

| فایل | نقش | ورودی | خروجی |
|------|-----|-------|-------|
| **client_main.py** | Entry point GUI، راه‌اندازی PyQt6 app | None | GUI window |
| **tunnel_client.py** | مدیریت tunnel connection با سرور | Server address, credentials | Tunnel connection |
| **connection_manager.py** | Lifecycle: connect, disconnect, reconnect | User commands | Connection states |
| **encryption.py** | Encrypt/decrypt packets (همانند server) | Plaintext packets, keys | Encrypted packets |
| **auto_reconnect.py** | Exponential backoff reconnection logic | Connection status | Reconnect attempts |
| **tap_interface.py** | مدیریت TAP-Windows driver | Adapter name, IP | TAP adapter handle |
| **routing_manager.py** | تغییر routing table ویندوز (netsh) | Routes to add/delete | PowerShell commands |
| **dns_manager.py** | تنظیم DNS servers روی TAP interface | DNS IPs | netsh DNS config |
| **firewall_manager.py** | مدیریت Windows Firewall rules | Rules to add/remove | netsh firewall commands |
| **network_monitor.py** | مانیتور کیفیت connection (latency, loss) | Ping results | Quality metrics |
| **main_window.py** | پنجره اصلی GUI (connect/disconnect button) | User actions | UI updates |
| **system_tray.py** | System tray icon، notification، quick actions | Connection status | Tray menu |
| **login_dialog.py** | Dialog ورود (username, password, server) | User input | Credentials |
| **settings_dialog.py** | تنظیمات (DDNS, port, encryption) | User preferences | config.json update |
| **stats_widget.py** | نمایش real-time: speed, latency, data usage | Stats from tunnel | Charts/labels |
| **log_viewer.py** | نمایش logs در GUI | Log file | Scrollable text view |
| **config_manager.py** | ذخیره/بارگذاری config از JSON | config.json | Config dictionary |
| **admin_privileges.py** | UAC elevation برای تغییرات network | Executable path | Admin process |
| **tunnel_service.py** | Background service (اجرا در پس‌زمینه) | Service commands | Tunnel running |

### **🔗 Shared Components**

| فایل | نقش | استفاده در |
|------|-----|-----------|
| **protocol.py** | Constants: packet types, versions, ports | Client & Server |
| **message_format.py** | Serialize/deserialize با msgpack | Client & Server |
| **encryption_base.py** | Abstract base class برای encryption | Client & Server |
| **exceptions.py** | Custom exceptions: AuthError, TunnelError | Client & Server |

---

## 3️⃣ لیست کتابخانه‌ها (Requirements)

### **📦 Server Requirements (`server/requirements.txt`)**

```txt
# ============================================================
# Core Dependencies
# ============================================================

# Async I/O framework for high-performance network server
asyncio==3.11.0                    # Built-in, but specified for clarity
aiofiles==23.2.1                   # Async file I/O operations

# TLS/SSL support
cryptography==42.0.5               # TLS certificate generation, X25519 ECDHE
PyOpenSSL==24.0.0                  # OpenSSL wrapper for TLS configuration

# ============================================================
# Network & Tunnel
# ============================================================

# Python TUN/TAP interface (Linux)
python-pytun==2.4.1                # Create virtual network interfaces
# Alternative: pyroute2==0.7.12    # More comprehensive netlink library

# Network configuration
netifaces==0.11.0                  # Query network interfaces and routes

# ============================================================
# Encryption & Security
# ============================================================

# ChaCha20-Poly1305 AEAD cipher
pycryptodome==3.20.0               # Provides ChaCha20_Poly1305 class
# Alternative: cryptography (above) also has ChaCha20Poly1305

# Password hashing
argon2-cffi==23.1.0                # Argon2 for secure password storage

# ============================================================
# Database
# ============================================================

# ORM for user and session management
SQLAlchemy==2.0.29                 # Database abstraction layer
alembic==1.13.1                    # Database migrations

# SQLite driver (default, can switch to PostgreSQL)
# Built-in sqlite3 module

# ============================================================
# Configuration & Serialization
# ============================================================

# YAML configuration parsing
PyYAML==6.0.1                      # Parse config.yaml

# Binary serialization for protocol messages
msgpack==1.0.8                     # Fast binary serialization

# ============================================================
# Logging & Monitoring
# ============================================================

# Structured logging
python-json-logger==2.0.7          # JSON log formatting

# System resource monitoring
psutil==5.9.8                      # CPU, memory, network stats

# ============================================================
# Dynamic DNS
# ============================================================

# HTTP client for DDNS API calls
requests==2.31.0                   # HTTP library
requests-cache==1.2.0              # Cache DDNS responses (optional)

# ============================================================
# Testing & Development
# ============================================================

# Testing framework
pytest==8.1.1                      # Unit testing
pytest-asyncio==0.23.6             # Async test support
pytest-cov==5.0.0                  # Code coverage

# Code quality
black==24.3.0                      # Code formatter
flake8==7.0.0                      # Linter
mypy==1.9.0                        # Type checker

# ============================================================
# Utilities
# ============================================================

# Date/time utilities
python-dateutil==2.9.0             # Date parsing and manipulation

# Environment variable management
python-dotenv==1.0.1               # Load .env files (for secrets)
```

### **💻 Client Requirements (`client/requirements.txt`)**

```txt
# ============================================================
# Core Dependencies
# ============================================================

# Async I/O
asyncio==3.11.0                    # Built-in async framework

# ============================================================
# GUI Framework
# ============================================================

# PyQt6 for native Windows GUI
PyQt6==6.6.1                       # Qt6 Python bindings
PyQt6-Qt6==6.6.1                   # Qt6 libraries
PyQt6-sip==13.6.0                  # SIP bindings

# Charts for statistics display
PyQtGraph==0.13.7                  # Real-time plotting library
# Alternative: matplotlib==3.8.3   # More features but heavier

# ============================================================
# Network & Tunnel (Windows-specific)
# ============================================================

# TAP-Windows driver interface
pywin32==306                       # Windows API access
wintun==0.1.5                      # WinTun driver (modern alternative to TAP)
# Note: Also requires manual TAP-Windows6 driver installation

# Network utilities
netifaces==0.11.0                  # Query network interfaces
scapy==2.5.0                       # Packet manipulation (optional, for testing)

# ============================================================
# Encryption & Security
# ============================================================

# ChaCha20-Poly1305 (same as server)
pycryptodome==3.20.0               # ChaCha20_Poly1305 cipher

# TLS/SSL
cryptography==42.0.5               # Certificate pinning, X25519
PyOpenSSL==24.0.0                  # TLS client configuration

# Password hashing (client-side pre-hash)
argon2-cffi==23.1.0                # Argon2 hashing

# ============================================================
# Configuration & Serialization
# ============================================================

# JSON configuration (client uses JSON instead of YAML)
# Built-in json module

# Binary serialization (protocol messages)
msgpack==1.0.8                     # Same as server

# ============================================================
# Windows System Integration
# ============================================================

# Admin privileges handling
pyuac==0.1.0                       # UAC elevation dialog

# Windows Registry access
winreg==1.0.1                      # Built-in, but specified

# System tray notifications
plyer==2.1.0                       # Cross-platform notifications (uses Windows Toast)

# ============================================================
# Logging & Monitoring
# ============================================================

# Structured logging
python-json-logger==2.0.7          # JSON logs

# System monitoring
psutil==5.9.8                      # Network speed, CPU usage

# ============================================================
# Packaging & Distribution
# ============================================================

# Create standalone executable
PyInstaller==6.5.0                 # Bundle Python app to .exe

# Optional: NSIS installer
# (NSIS itself is external tool, not a Python package)

# ============================================================
# Utilities
# ============================================================

# Keyring for secure credential storage
keyring==25.1.0                    # Windows Credential Manager integration

# HTTP client (for server API calls if needed)
requests==2.31.0                   # HTTP library

# ============================================================
# Testing & Development
# ============================================================

# Testing (same as server)
pytest==8.1.1
pytest-asyncio==0.23.6
pytest-qt==4.4.0                   # PyQt testing support

# Code quality
black==24.3.0
flake8==7.0.0
mypy==1.9.0
```

---

## 4️⃣ دلیل انتخاب هر کتابخانه

### **🔹 Core Frameworks**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **asyncio** | Non-blocking I/O برای handle کردن چندین connection همزمان بدون threading overhead | Twisted (قدیمی‌تر), Trio (جدید اما کمتر mature) |
| **PyQt6** | Native Windows UI، performance بالا، Qt Designer support، system tray integration | Tkinter (زشت)، Kivy (موبایل)، wxPython (کمتر active) |

### **🔹 Networking**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **python-pytun** | Pure Python interface برای TUN/TAP، simple API | pyroute2 (پیچیده‌تر)، direct ioctl calls (low-level) |
| **pywin32** | دسترسی مستقیم به Windows API برای TAP adapter management | ctypes (manual)، WinAPI wrappers (incomplete) |
| **wintun** | Modern، high-performance alternative به TAP-Windows، توسط WireGuard توسعه داده شده | TAP-Windows6 (قدیمی‌تر، اما stable تر) |
| **netifaces** | Cross-platform، reliable برای query کردن network interfaces | psutil.net_if_addrs() (سبک‌تر اما less detailed) |

### **🔹 Encryption & Security**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **pycryptodome** | Fast implementation of ChaCha20-Poly1305، hardware acceleration support | cryptography library (هردو خوب، pycryptodome lightweight تر) |
| **cryptography** | Industry-standard، X25519 ECDHE support، audited security | OpenSSL direct bindings (complex) |
| **argon2-cffi** | State-of-the-art password hashing، winner of Password Hashing Competition | bcrypt (قدیمی‌تر)، scrypt (کمتر secure) |

### **🔹 Database**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **SQLAlchemy** | ORM قدرتمند، async support، migration friendly | Django ORM (نیاز به Django)، PeeWee (ساده‌تر اما محدودتر) |
| **SQLite** | Built-in، zero-configuration، perfect برای small-scale deployment | PostgreSQL (overkill برای personal use)، MySQL (نیاز به external server) |

### **🔹 Configuration & Data**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **PyYAML** | Human-readable config files، comments support، hierarchical | JSON (no comments)، TOML (کمتر popular)، ConfigParser (محدود) |
| **msgpack** | Binary serialization، 2x faster از JSON، smaller size | JSON (text-based، بزرگتر)، Protocol Buffers (نیاز به schema) |

### **🔹 Windows Integration**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **pyuac** | Simple UAC elevation، no external dependencies | Manual ShellExecuteEx (complex)، UAC manifest (compile-time only) |
| **keyring** | Secure storage در Windows Credential Manager | Plain text config (insecure)، custom encryption (reinventing wheel) |
| **plyer** | Cross-platform notifications با Windows Toast support | win10toast (Windows-only)، manual Windows API calls |

### **🔹 Packaging**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **PyInstaller** | Mature، wide compatibility، single-file .exe support | cx_Freeze (less features)، py2exe (outdated)، Nuitka (compile به C، complex) |

### **🔹 Monitoring & Logging**

| کتابخانه | دلیل انتخاب | جایگزین‌ها |
|----------|-------------|-----------|
| **python-json-logger** | Structured logging برای parsing آسان، machine-readable | Standard logging (plain text)، loguru (heavier) |
| **psutil** | Cross-platform، comprehensive system stats، active maintenance | WMI (Windows-only)، manual parsing /proc (Linux-only) |

---

## 5️⃣ استانداردهای کدنویسی و Naming Conventions

### **📐 Code Style Guide**

```python
# ============================================================
# PEP 8 Compliance با استثناهای زیر:
# ============================================================

# Line length: 100 characters (instead of 79)
# Reason: Modern screens, readability for complex network code

# String quotes: Double quotes preferred for user-facing text
USER_MESSAGE = "Connected successfully"  # ✅
INTERNAL_KEY = 'encryption_key'          # ✅ (internal constants)

# Imports order:
# 1. Standard library
# 2. Third-party libraries
# 3. Local application imports
# 4. Separated by blank lines

import asyncio
import logging
from pathlib import Path

import msgpack
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from shared.protocol import PacketType
from core.encryption import EncryptionHandler
```

### **🏷️ Naming Conventions**

| نوع | کانونشن | مثال | دلیل |
|-----|---------|------|------|
| **Modules** | `lowercase_with_underscores` | `tunnel_server.py` | PEP 8 standard |
| **Classes** | `PascalCase` | `TunnelServer`, `SessionManager` | PEP 8 standard |
| **Functions/Methods** | `lowercase_with_underscores` | `handle_connection()`, `encrypt_packet()` | PEP 8 standard |
| **Constants** | `UPPER_CASE_WITH_UNDERSCORES` | `MAX_PACKET_SIZE`, `DEFAULT_PORT` | PEP 8 standard |
| **Private attributes** | `_leading_underscore` | `_session_key`, `_internal_buffer` | Indicate internal use |
| **Protected methods** | `_leading_underscore` | `_validate_token()`, `_cleanup()` | Subclass can access |
| **Magic methods** | `__dunder__` | `__init__()`, `__enter__()` | Python convention |
| **Variables** | `lowercase_with_underscores` | `client_ip`, `packet_count` | PEP 8 standard |
| **Type hints** | Always use | `def func(x: int) -> str:` | Python 3.11+ best practice |

### **📂 File Naming**

```
✅ Preferred:
  tunnel_server.py          # Clear, descriptive
  session_manager.py        # Action-oriented
  encryption.py             # Noun (module purpose)

❌ Avoid:
  TunnelServer.py           # Wrong case (not Java)
  tunnel-server.py          # Hyphens (import issues)
  ts.py                     # Abbreviation unclear
```

### **🏗️ Class Structure Template**

```python
class TunnelServer:
    """
    Brief one-line description.
    
    Detailed multi-line description explaining purpose,
    responsibilities, and key behavior.
    
    Attributes:
        host (str): Server bind address
        port (int): Server listen port
        _sessions (dict): Active client sessions (private)
    
    Example:
        >>> server = TunnelServer("0.0.0.0", 8443)
        >>> await server.start()
    """
    
    # Class-level constants
    MAX_CLIENTS = 100
    TIMEOUT = 30
    
    def __init__(self, host: str, port: int) -> None:
        """Initialize server with host and port."""
        # Public attributes
        self.host = host
        self.port = port
        
        # Private attributes
        self._sessions: dict[str, Session] = {}
        self._running = False
    
    # Public methods
    async def start(self) -> None:
        """Start the tunnel server."""
        pass
    
    async def stop(self) -> None:
        """Gracefully stop the server."""
        pass
    
    # Private methods
    async def _handle_client(self, reader, writer) -> None:
        """Handle individual client connection (internal)."""
        pass
    
    # Properties
    @property
    def client_count(self) -> int:
        """Return number of active clients."""
        return len(self._sessions)
```

### **📝 Documentation Standards**

```python
# ============================================================
# Docstring Format: Google Style
# ============================================================

def encrypt_packet(
    packet: bytes,
    key: bytes,
    nonce: bytes
) -> tuple[bytes, bytes]:
    """
    Encrypt IP packet with ChaCha20-Poly1305 AEAD.
    
    Takes a raw IP packet and encrypts it using the provided
    symmetric key and nonce. Returns both ciphertext and
    authentication tag.
    
    Args:
        packet: Raw IP packet (layer 3) to encrypt
        key: 32-byte ChaCha20 symmetric key
        nonce: 12-byte unique nonce (must not repeat)
    
    Returns:
        A tuple of (ciphertext, auth_tag) where:
            - ciphertext (bytes): Encrypted packet data
            - auth_tag (bytes): 16-byte Poly1305 MAC
    
    Raises:
        ValueError: If key or nonce have incorrect length
        EncryptionError: If encryption fails
    
    Example:
        >>> key = os.urandom(32)
        >>> nonce = os.urandom(12)
        >>> ciphertext, tag = encrypt_packet(b"IP packet", key, nonce)
    
    Note:
        Nonce must be unique for each packet with the same key.
        Recommended to use counter + timestamp.
    """
    pass
```

### **🔧 Configuration Constants**

```python
# ============================================================
# Constants Organization: Group by category
# ============================================================

# Network
DEFAULT_SERVER_PORT = 8443
CONTROL_PORT = 8443
TUNNEL_BASE_PORT = 9000
MAX_TUNNEL_PORTS = 100

# Tunnel
TUN_INTERFACE_NAME = "iran_vpn0"
TUN_IP_RANGE = "10.8.0.0/24"
TUN_SERVER_IP = "10.8.0.1"
TUN_MTU = 1420

# Encryption
ENCRYPTION_ALGORITHM = "ChaCha20-Poly1305"
KEY_SIZE = 32  # bytes
NONCE_SIZE = 12  # bytes
TAG_SIZE = 16  # bytes

# Protocol
PROTOCOL_VERSION = "1.0.0"
MAGIC_BYTES = b"\x49\x52\x56\x50"  # "IRVP" (Iran VPN)
MAX_PACKET_SIZE = 1500
KEEPALIVE_INTERVAL = 15  # seconds
RECONNECT_MAX_DELAY = 30  # seconds

# Timeouts
CONNECTION_TIMEOUT = 10  # seconds
AUTH_TIMEOUT = 5  # seconds
KEEPALIVE_TIMEOUT = 30  # seconds

# Paths (use pathlib)
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
LOG_DIR = PROJECT_ROOT / "logs"
CERT_DIR = PROJECT_ROOT / "certs"
DB_PATH = PROJECT_ROOT / "data" / "server.db"
```

### **⚠️ Error Handling Standards**

```python
# ============================================================
# Custom Exceptions: Specific and descriptive
# ============================================================

class VPNException(Exception):
    """Base exception for all VPN-related errors."""
    pass

class AuthenticationError(VPNException):
    """Raised when authentication fails."""
    pass

class TunnelError(VPNException):
    """Raised when tunnel operation fails."""
    pass

class EncryptionError(VPNException):
    """Raised when encryption/decryption fails."""
    pass

class NetworkError(VPNException):
    """Raised when network operation fails."""
    pass

# Usage:
try:
    session = await authenticate_client(credentials)
except AuthenticationError as e:
    logger.error(f"Auth failed: {e}")
    raise
except NetworkError as e:
    logger.warning(f"Network issue: {e}, retrying...")
    # Retry logic
```

### **📊 Logging Standards**

```python
# ============================================================
# Logging Levels: Consistent usage
# ============================================================

import logging

logger = logging.getLogger(__name__)  # Always use module name

# DEBUG: Detailed information for debugging
logger.debug(f"Packet received: {len(packet)} bytes, seq={seq_num}")

# INFO: General operational messages
logger.info(f"Client connected: {client_ip}, assigned IP: {virtual_ip}")

# WARNING: Something unexpected but handled
logger.warning(f"Keepalive timeout for {client_ip}, reconnecting...")

# ERROR: Error that affects functionality
logger.error(f"Failed to decrypt packet from {client_ip}: {e}")

# CRITICAL: Severe error, service may stop
logger.critical(f"TUN interface creation failed: {e}, shutting down")

# Always log exceptions with stack trace:
try:
    risky_operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")  # Includes traceback
```

### **🧪 Testing Standards**

```python
# ============================================================
# Test Naming: test_<function>_<scenario>_<expected_result>
# ============================================================

import pytest

class TestEncryption:
    """Test encryption module."""
    
    def test_encrypt_packet_valid_input_returns_ciphertext(self):
        """Test encryption with valid inputs."""
        pass
    
    def test_encrypt_packet_invalid_key_raises_error(self):
        """Test encryption with wrong key size."""
        with pytest.raises(ValueError):
            encrypt_packet(b"data", b"short_key", nonce)
    
    @pytest.mark.asyncio
    async def test_tunnel_server_start_binds_to_port(self):
        """Test server starts and binds to specified port."""
        pass
```

### **🎨 Type Hints Standards**

```python
# ============================================================
# Type Annotations: Always use for function signatures
# ============================================================

from typing import Optional, Union, List, Dict, Callable
from collections.abc import Awaitable

# Simple types
def get_client_ip(session_id: str) -> str:
    pass

# Optional (can be None)
def find_session(token: str) -> Optional[Session]:
    pass

# Union (multiple types)
def process_data(data: Union[bytes, str]) -> bytes:
    pass

# Collections (prefer lowercase in Python 3.9+)
def get_active_sessions() -> dict[str, Session]:
    pass

# Async functions
async def connect_to_server(host: str) -> Awaitable[bool]:
    pass

# Callable
def register_callback(callback: Callable[[str], None]) -> None:
    pass

# Complex types
from dataclasses import dataclass

@dataclass
class PacketMetadata:
    sequence: int
    timestamp: float
    source_ip: str

def parse_packet(data: bytes) -> tuple[bytes, PacketMetadata]:
    pass
```

---

## 📋 Development Status

### ✅ Completed Phases

- **فاز ۱**: Design Overview & Architecture
- **فاز ۲**: Project Structure & Dependencies

### 🔜 Next Phases

- **فاز ۳**: Shared Components Implementation
- **فاز ۴**: Server Core Implementation
- **فاز ۵**: Client Core Implementation
- **فاز ۶**: GUI Development
- **فاز ۷**: Testing & Optimization
- **فاز ۸**: Deployment & Documentation

---

**Last Updated**: January 29, 2026  
**Status**: Design & Architecture Complete  
**Next Action**: Await Phase 3 instructions
