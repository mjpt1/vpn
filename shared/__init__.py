"""
Shared Components - Iran VPN Gateway
Common code used by both server and client components.
"""

__version__ = "1.0.0"
__author__ = "Iran VPN Gateway Project"

from .protocol import *
from .exceptions import *

__all__ = [
    'PacketType',
    'MessageType',
    'ConnectionState',
    'PROTOCOL_VERSION',
    'VPNException',
    'AuthenticationError',
    'TunnelError',
    'EncryptionError',
    'NetworkError',
]
