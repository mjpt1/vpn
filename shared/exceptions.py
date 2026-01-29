"""
Custom Exceptions
Defines all custom exceptions used throughout the VPN system.
"""


class VPNException(Exception):
    """Base exception for all VPN-related errors."""
    
    def __init__(self, message: str, error_code: int = 0):
        """
        Initialize VPN exception.
        
        Args:
            message: Error message
            error_code: Optional error code from ErrorCode enum
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[Code {self.error_code}] {self.message}"
        return self.message


class AuthenticationError(VPNException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", error_code: int = 0x10):
        super().__init__(message, error_code)


class InvalidCredentialsError(AuthenticationError):
    """Raised when username/password is incorrect."""
    
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, error_code=0x11)


class InvalidTokenError(AuthenticationError):
    """Raised when session token is invalid."""
    
    def __init__(self, message: str = "Invalid session token"):
        super().__init__(message, error_code=0x12)


class TokenExpiredError(AuthenticationError):
    """Raised when session token has expired."""
    
    def __init__(self, message: str = "Session token expired"):
        super().__init__(message, error_code=0x13)


class TunnelError(VPNException):
    """Raised when tunnel operation fails."""
    
    def __init__(self, message: str = "Tunnel error", error_code: int = 0x30):
        super().__init__(message, error_code)


class TunnelCreationError(TunnelError):
    """Raised when TUN/TAP interface creation fails."""
    
    def __init__(self, message: str = "Failed to create tunnel interface"):
        super().__init__(message, error_code=0x30)


class IPAllocationError(TunnelError):
    """Raised when IP allocation fails."""
    
    def __init__(self, message: str = "Failed to allocate IP address"):
        super().__init__(message, error_code=0x31)


class RoutingError(TunnelError):
    """Raised when routing configuration fails."""
    
    def __init__(self, message: str = "Routing configuration failed"):
        super().__init__(message, error_code=0x32)


class EncryptionError(VPNException):
    """Raised when encryption/decryption fails."""
    
    def __init__(self, message: str = "Encryption error", error_code: int = 0x40):
        super().__init__(message, error_code)


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    
    def __init__(self, message: str = "Decryption failed"):
        super().__init__(message, error_code=0x41)


class KeyExchangeError(EncryptionError):
    """Raised when key exchange fails."""
    
    def __init__(self, message: str = "Key exchange failed"):
        super().__init__(message, error_code=0x42)


class ReplayAttackError(EncryptionError):
    """Raised when replay attack is detected."""
    
    def __init__(self, message: str = "Replay attack detected"):
        super().__init__(message, error_code=0x43)


class NetworkError(VPNException):
    """Raised when network operation fails."""
    
    def __init__(self, message: str = "Network error", error_code: int = 0x50):
        super().__init__(message, error_code)


class ConnectionLostError(NetworkError):
    """Raised when connection is lost."""
    
    def __init__(self, message: str = "Connection lost"):
        super().__init__(message, error_code=0x51)


class TimeoutError(NetworkError):
    """Raised when operation times out."""
    
    def __init__(self, message: str = "Operation timed out"):
        super().__init__(message, error_code=0x52)


class SessionError(VPNException):
    """Raised when session operation fails."""
    
    def __init__(self, message: str = "Session error", error_code: int = 0x20):
        super().__init__(message, error_code)


class SessionNotFoundError(SessionError):
    """Raised when session is not found."""
    
    def __init__(self, message: str = "Session not found"):
        super().__init__(message, error_code=0x20)


class SessionExpiredError(SessionError):
    """Raised when session has expired."""
    
    def __init__(self, message: str = "Session expired"):
        super().__init__(message, error_code=0x21)


class SessionLimitError(SessionError):
    """Raised when session limit is reached."""
    
    def __init__(self, message: str = "Session limit reached"):
        super().__init__(message, error_code=0x22)


class ProtocolError(VPNException):
    """Raised when protocol violation occurs."""
    
    def __init__(self, message: str = "Protocol error", error_code: int = 0x01):
        super().__init__(message, error_code)


class ProtocolVersionMismatchError(ProtocolError):
    """Raised when protocol versions don't match."""
    
    def __init__(self, client_version: str, server_version: str):
        message = f"Protocol version mismatch: client={client_version}, server={server_version}"
        super().__init__(message, error_code=0x02)


class ServerError(VPNException):
    """Raised when server encounters an error."""
    
    def __init__(self, message: str = "Server error", error_code: int = 0x60):
        super().__init__(message, error_code)


class ServerOverloadedError(ServerError):
    """Raised when server is overloaded."""
    
    def __init__(self, message: str = "Server is overloaded, please try again later"):
        super().__init__(message, error_code=0x60)


class MaintenanceModeError(ServerError):
    """Raised when server is in maintenance mode."""
    
    def __init__(self, message: str = "Server is in maintenance mode"):
        super().__init__(message, error_code=0x61)
