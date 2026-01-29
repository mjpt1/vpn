"""
Message Format - Serialization/Deserialization
Uses msgpack for efficient binary serialization of control messages.
"""

import msgpack
import struct
from typing import Any, Dict, Optional
from .protocol import MessageType, MAGIC_BYTES, PROTOCOL_VERSION
from .exceptions import ProtocolError


class MessageFormat:
    """
    Handles serialization and deserialization of control messages.
    
    Message Structure:
    [4 bytes: Magic] [2 bytes: Length] [1 byte: Type] [N bytes: Payload]
    
    Where Payload is msgpack-encoded dictionary.
    """
    
    HEADER_SIZE = 7  # 4 (magic) + 2 (length) + 1 (type)
    MAX_MESSAGE_SIZE = 65535  # 2^16 - 1
    
    @staticmethod
    def pack(message_type: MessageType, payload: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Pack a message into binary format.
        
        Args:
            message_type: Type of message
            payload: Optional dictionary payload
        
        Returns:
            Serialized message bytes
        
        Raises:
            ProtocolError: If message is too large
        """
        # Serialize payload with msgpack
        if payload is None:
            payload = {}
        
        # Add protocol version to all messages
        payload['version'] = PROTOCOL_VERSION
        
        payload_bytes = msgpack.packb(payload, use_bin_type=True)
        
        # Check size
        total_size = MessageFormat.HEADER_SIZE + len(payload_bytes)
        if total_size > MessageFormat.MAX_MESSAGE_SIZE:
            raise ProtocolError(f"Message too large: {total_size} bytes")
        
        # Pack: Magic (4) + Length (2) + Type (1) + Payload (N)
        message = bytearray()
        message.extend(MAGIC_BYTES)  # Magic
        message.extend(struct.pack('!H', len(payload_bytes)))  # Length (big-endian uint16)
        message.append(int(message_type))  # Type
        message.extend(payload_bytes)  # Payload
        
        return bytes(message)
    
    @staticmethod
    def unpack(data: bytes) -> tuple[MessageType, Dict[str, Any]]:
        """
        Unpack a binary message.
        
        Args:
            data: Serialized message bytes
        
        Returns:
            Tuple of (message_type, payload)
        
        Raises:
            ProtocolError: If message is invalid
        """
        if len(data) < MessageFormat.HEADER_SIZE:
            raise ProtocolError(f"Message too short: {len(data)} bytes")
        
        # Verify magic bytes
        magic = data[0:4]
        if magic != MAGIC_BYTES:
            raise ProtocolError(f"Invalid magic bytes: {magic.hex()}")
        
        # Extract length
        payload_length = struct.unpack('!H', data[4:6])[0]
        
        # Extract type
        message_type_val = data[6]
        try:
            message_type = MessageType(message_type_val)
        except ValueError:
            raise ProtocolError(f"Unknown message type: {message_type_val}")
        
        # Verify total length
        expected_length = MessageFormat.HEADER_SIZE + payload_length
        if len(data) < expected_length:
            raise ProtocolError(
                f"Incomplete message: expected {expected_length}, got {len(data)}"
            )
        
        # Extract and deserialize payload
        payload_bytes = data[7:7 + payload_length]
        try:
            payload = msgpack.unpackb(payload_bytes, raw=False)
        except Exception as e:
            raise ProtocolError(f"Failed to deserialize payload: {e}")
        
        return message_type, payload
    
    @staticmethod
    def create_auth_request(username: str, password_hash: str, client_version: str) -> bytes:
        """Create authentication request message."""
        payload = {
            'username': username,
            'password_hash': password_hash,
            'client_version': client_version,
        }
        return MessageFormat.pack(MessageType.AUTH_REQUEST, payload)
    
    @staticmethod
    def create_auth_response(session_token: str, assigned_ip: str) -> bytes:
        """Create authentication success response."""
        payload = {
            'session_token': session_token,
            'assigned_ip': assigned_ip,
        }
        return MessageFormat.pack(MessageType.AUTH_SUCCESS, payload)
    
    @staticmethod
    def create_auth_failure(error_code: int, error_message: str) -> bytes:
        """Create authentication failure response."""
        payload = {
            'error_code': error_code,
            'error_message': error_message,
        }
        return MessageFormat.pack(MessageType.AUTH_FAILURE, payload)
    
    @staticmethod
    def create_ping() -> bytes:
        """Create keepalive ping message."""
        import time
        payload = {'timestamp': time.time()}
        return MessageFormat.pack(MessageType.PING, payload)
    
    @staticmethod
    def create_pong(ping_timestamp: float) -> bytes:
        """Create keepalive pong response."""
        import time
        payload = {
            'ping_timestamp': ping_timestamp,
            'pong_timestamp': time.time(),
        }
        return MessageFormat.pack(MessageType.PONG, payload)
    
    @staticmethod
    def create_error(error_code: int, error_message: str) -> bytes:
        """Create error message."""
        payload = {
            'error_code': error_code,
            'error_message': error_message,
        }
        return MessageFormat.pack(MessageType.ERROR, payload)
    
    @staticmethod
    def create_disconnect(reason: str = "User requested") -> bytes:
        """Create disconnect message."""
        payload = {'reason': reason}
        return MessageFormat.pack(MessageType.DISCONNECT, payload)


# ============================================================
# Packet Framing for Data Stream
# ============================================================

class PacketFramer:
    """
    Handles framing of encrypted packets over TCP stream.
    
    Frame Format:
    [2 bytes: Length] [N bytes: Data]
    """
    
    LENGTH_SIZE = 2
    MAX_FRAME_SIZE = 65535
    
    @staticmethod
    def frame(data: bytes) -> bytes:
        """
        Frame data with length prefix.
        
        Args:
            data: Data to frame
        
        Returns:
            Framed data
        
        Raises:
            ValueError: If data is too large
        """
        if len(data) > PacketFramer.MAX_FRAME_SIZE:
            raise ValueError(f"Data too large: {len(data)} bytes")
        
        return struct.pack('!H', len(data)) + data
    
    @staticmethod
    def unframe(stream: bytes) -> tuple[Optional[bytes], bytes]:
        """
        Extract one frame from stream.
        
        Args:
            stream: Byte stream containing framed data
        
        Returns:
            Tuple of (frame_data, remaining_stream)
            If incomplete frame, returns (None, original_stream)
        """
        if len(stream) < PacketFramer.LENGTH_SIZE:
            return None, stream
        
        # Read length
        frame_length = struct.unpack('!H', stream[0:2])[0]
        
        # Check if full frame available
        total_size = PacketFramer.LENGTH_SIZE + frame_length
        if len(stream) < total_size:
            return None, stream
        
        # Extract frame
        frame_data = stream[2:total_size]
        remaining = stream[total_size:]
        
        return frame_data, remaining


# ============================================================
# Stream Buffer for Async Reading
# ============================================================

class StreamBuffer:
    """
    Buffer for handling partial message reads from async streams.
    """
    
    def __init__(self):
        """Initialize empty buffer."""
        self.buffer = bytearray()
    
    def append(self, data: bytes) -> None:
        """Add data to buffer."""
        self.buffer.extend(data)
    
    def extract_message(self) -> Optional[tuple[MessageType, Dict[str, Any]]]:
        """
        Try to extract one complete message from buffer.
        
        Returns:
            Tuple of (message_type, payload) or None if incomplete
        """
        if len(self.buffer) < MessageFormat.HEADER_SIZE:
            return None
        
        # Read payload length
        payload_length = struct.unpack('!H', self.buffer[4:6])[0]
        expected_length = MessageFormat.HEADER_SIZE + payload_length
        
        if len(self.buffer) < expected_length:
            return None
        
        # Extract message
        message_data = bytes(self.buffer[:expected_length])
        self.buffer = self.buffer[expected_length:]
        
        # Unpack
        return MessageFormat.unpack(message_data)
    
    def extract_frame(self) -> Optional[bytes]:
        """
        Try to extract one complete frame from buffer.
        
        Returns:
            Frame data or None if incomplete
        """
        frame_data, remaining = PacketFramer.unframe(bytes(self.buffer))
        if frame_data is not None:
            self.buffer = bytearray(remaining)
        return frame_data
    
    def clear(self) -> None:
        """Clear buffer."""
        self.buffer.clear()
    
    def __len__(self) -> int:
        """Return buffer size."""
        return len(self.buffer)
