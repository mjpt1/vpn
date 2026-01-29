"""
Protocol Definitions and Constants
Defines all protocol-level constants, message types, and packet structures.
"""

from enum import IntEnum
from typing import Final

# ============================================================
# Protocol Version
# ============================================================

PROTOCOL_VERSION: Final[str] = "1.0.0"
MAGIC_BYTES: Final[bytes] = b"\x49\x52\x56\x50"  # "IRVP" - Iran VPN


# ============================================================
# Network Configuration
# ============================================================

# Server
DEFAULT_SERVER_PORT: Final[int] = 8443
CONTROL_PORT: Final[int] = 8443
TUNNEL_BASE_PORT: Final[int] = 9000
MAX_TUNNEL_PORTS: Final[int] = 100

# TUN/TAP
TUN_INTERFACE_NAME: Final[str] = "iran_vpn0"
TUN_IP_RANGE: Final[str] = "10.8.0.0/24"
TUN_SERVER_IP: Final[str] = "10.8.0.1"
TUN_CLIENT_IP_START: Final[str] = "10.8.0.2"
TUN_MTU: Final[int] = 1420

# DNS Servers (Iran)
IRAN_DNS_PRIMARY: Final[str] = "10.202.10.202"
IRAN_DNS_SECONDARY: Final[str] = "10.202.10.102"


# ============================================================
# Encryption Configuration
# ============================================================

ENCRYPTION_ALGORITHM: Final[str] = "ChaCha20-Poly1305"
KEY_SIZE: Final[int] = 32  # 256 bits
NONCE_SIZE: Final[int] = 12  # 96 bits
TAG_SIZE: Final[int] = 16  # 128 bits (Poly1305 MAC)

# Key derivation
KDF_ALGORITHM: Final[str] = "HKDF-SHA256"
KDF_SALT_SIZE: Final[int] = 32
KDF_INFO: Final[bytes] = b"IranVPN-v1.0"


# ============================================================
# Packet Configuration
# ============================================================

MAX_PACKET_SIZE: Final[int] = 1500  # Standard MTU
PACKET_HEADER_SIZE: Final[int] = 2  # Length field
ENCRYPTED_PACKET_OVERHEAD: Final[int] = NONCE_SIZE + TAG_SIZE  # 12 + 16 = 28 bytes

# Replay protection
REPLAY_WINDOW_SIZE: Final[int] = 64


# ============================================================
# Timing Configuration
# ============================================================

# Keepalive
KEEPALIVE_INTERVAL: Final[int] = 15  # seconds
KEEPALIVE_TIMEOUT: Final[int] = 30  # seconds

# Reconnection
RECONNECT_INITIAL_DELAY: Final[int] = 1  # seconds
RECONNECT_MAX_DELAY: Final[int] = 30  # seconds
RECONNECT_BACKOFF_MULTIPLIER: Final[float] = 2.0

# Timeouts
CONNECTION_TIMEOUT: Final[int] = 10  # seconds
AUTH_TIMEOUT: Final[int] = 5  # seconds
SESSION_TIMEOUT: Final[int] = 86400  # 24 hours

# Key rotation
KEY_ROTATION_INTERVAL: Final[int] = 14400  # 4 hours


# ============================================================
# Session Configuration
# ============================================================

MAX_CLIENTS: Final[int] = 100
MAX_SESSIONS_PER_USER: Final[int] = 3


# ============================================================
# Message Types
# ============================================================

class MessageType(IntEnum):
    """Types of control messages exchanged between client and server."""
    
    # Authentication
    AUTH_REQUEST = 0x01
    AUTH_RESPONSE = 0x02
    AUTH_SUCCESS = 0x03
    AUTH_FAILURE = 0x04
    
    # Session management
    SESSION_CREATE = 0x10
    SESSION_CREATED = 0x11
    SESSION_DESTROY = 0x12
    SESSION_DESTROYED = 0x13
    
    # Connection control
    CONNECT_REQUEST = 0x20
    CONNECT_ACCEPT = 0x21
    DISCONNECT = 0x22
    
    # Keepalive
    PING = 0x30
    PONG = 0x31
    
    # Key management
    REKEY_REQUEST = 0x40
    REKEY_RESPONSE = 0x41
    
    # Data tunnel
    TUNNEL_DATA = 0x50
    
    # Errors
    ERROR = 0xFF


class PacketType(IntEnum):
    """Types of packets in the tunnel."""
    
    CONTROL = 0x01      # Control channel message
    DATA = 0x02         # Encrypted IP packet
    KEEPALIVE = 0x03    # Keepalive packet


class ConnectionState(IntEnum):
    """Connection state machine."""
    
    DISCONNECTED = 0
    CONNECTING = 1
    AUTHENTICATING = 2
    CONNECTED = 3
    RECONNECTING = 4
    DISCONNECTING = 5


class AuthMethod(IntEnum):
    """Authentication methods."""
    
    PASSWORD = 0x01
    TOKEN = 0x02


# ============================================================
# Error Codes
# ============================================================

class ErrorCode(IntEnum):
    """Error codes for ERROR messages."""
    
    # General errors (0x00 - 0x0F)
    UNKNOWN_ERROR = 0x00
    INVALID_MESSAGE = 0x01
    PROTOCOL_VERSION_MISMATCH = 0x02
    
    # Authentication errors (0x10 - 0x1F)
    AUTH_FAILED = 0x10
    INVALID_CREDENTIALS = 0x11
    INVALID_TOKEN = 0x12
    TOKEN_EXPIRED = 0x13
    TOO_MANY_SESSIONS = 0x14
    USER_DISABLED = 0x15
    
    # Session errors (0x20 - 0x2F)
    SESSION_NOT_FOUND = 0x20
    SESSION_EXPIRED = 0x21
    SESSION_LIMIT_REACHED = 0x22
    
    # Tunnel errors (0x30 - 0x3F)
    TUNNEL_CREATION_FAILED = 0x30
    IP_ALLOCATION_FAILED = 0x31
    ROUTING_ERROR = 0x32
    
    # Encryption errors (0x40 - 0x4F)
    ENCRYPTION_FAILED = 0x40
    DECRYPTION_FAILED = 0x41
    KEY_EXCHANGE_FAILED = 0x42
    REPLAY_ATTACK_DETECTED = 0x43
    
    # Network errors (0x50 - 0x5F)
    NETWORK_ERROR = 0x50
    CONNECTION_LOST = 0x51
    TIMEOUT = 0x52
    
    # Server errors (0x60 - 0x6F)
    SERVER_OVERLOADED = 0x60
    MAINTENANCE_MODE = 0x61


# ============================================================
# Message Format Helpers
# ============================================================

def validate_protocol_version(version: str) -> bool:
    """
    Validate protocol version compatibility.
    
    Args:
        version: Version string to validate (e.g., "1.0.0")
    
    Returns:
        True if compatible, False otherwise
    """
    try:
        major, minor, patch = map(int, version.split('.'))
        expected_major, expected_minor, _ = map(int, PROTOCOL_VERSION.split('.'))
        
        # Major version must match exactly
        if major != expected_major:
            return False
        
        # Minor version must be compatible (<=)
        if minor > expected_minor:
            return False
        
        return True
    except (ValueError, AttributeError):
        return False


def packet_type_to_string(packet_type: int) -> str:
    """Convert packet type to human-readable string."""
    try:
        return PacketType(packet_type).name
    except ValueError:
        return f"UNKNOWN({packet_type})"


def message_type_to_string(message_type: int) -> str:
    """Convert message type to human-readable string."""
    try:
        return MessageType(message_type).name
    except ValueError:
        return f"UNKNOWN({message_type})"


def error_code_to_string(error_code: int) -> str:
    """Convert error code to human-readable string."""
    try:
        return ErrorCode(error_code).name
    except ValueError:
        return f"UNKNOWN_ERROR({error_code})"


# ============================================================
# IP Address Management
# ============================================================

def get_next_client_ip(client_index: int) -> str:
    """
    Get next available client IP address.
    
    Args:
        client_index: Index of the client (0-based)
    
    Returns:
        IP address string (e.g., "10.8.0.2")
    
    Raises:
        ValueError: If client_index is out of range
    """
    if client_index < 0 or client_index > 253:  # .2 to .254 (253 clients)
        raise ValueError(f"Client index {client_index} out of range (0-253)")
    
    return f"10.8.0.{client_index + 2}"


def ip_to_client_index(ip_address: str) -> int:
    """
    Convert client IP address to index.
    
    Args:
        ip_address: IP address string (e.g., "10.8.0.5")
    
    Returns:
        Client index (0-based)
    
    Raises:
        ValueError: If IP is not a valid client IP
    """
    parts = ip_address.split('.')
    if len(parts) != 4 or parts[0:3] != ['10', '8', '0']:
        raise ValueError(f"Invalid client IP: {ip_address}")
    
    last_octet = int(parts[3])
    if last_octet < 2 or last_octet > 254:
        raise ValueError(f"Invalid client IP: {ip_address}")
    
    return last_octet - 2
