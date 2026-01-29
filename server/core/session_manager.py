"""
Session Manager - Manages active client sessions in memory
"""

import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime

from ..database.models import Session as SessionModel
from ..core.encryption import EncryptionHandler
from ..core.packet_processor import PacketProcessor

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from shared.message_format import StreamBuffer
from shared.exceptions import SessionError

logger = logging.getLogger(__name__)


class ClientSession:
    """
    Represents an active client session.
    
    Holds all runtime state for a connected client.
    """
    
    def __init__(
        self,
        session_model: SessionModel,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        encryption_key: bytes
    ):
        """
        Initialize client session.
        
        Args:
            session_model: Database session model
            reader: Async stream reader
            writer: Async stream writer
            encryption_key: Master encryption key
        """
        self.session_id = session_model.id
        self.session_token = session_model.session_token
        self.user_id = session_model.user_id
        self.assigned_ip = session_model.assigned_ip
        self.client_ip = session_model.client_real_ip
        
        # Network streams
        self.reader = reader
        self.writer = writer
        
        # Encryption
        self.encryption = EncryptionHandler(master_key=encryption_key)
        
        # Packet processing
        self.packet_processor = PacketProcessor()
        
        # Stream buffer for partial reads
        self.read_buffer = StreamBuffer()
        
        # State
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_active = True
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        
        # Keepalive
        self.last_ping_time: Optional[float] = None
        self.last_pong_time: Optional[float] = None
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def add_traffic(self, sent: int, received: int) -> None:
        """Update traffic counters."""
        self.bytes_sent += sent
        self.bytes_received += received
    
    async def send_data(self, data: bytes) -> None:
        """
        Send data to client.
        
        Args:
            data: Data to send
        """
        self.writer.write(data)
        await self.writer.drain()
        self.bytes_sent += len(data)
        self.update_activity()
    
    async def recv_data(self, size: int = 4096) -> Optional[bytes]:
        """
        Receive data from client.
        
        Args:
            size: Maximum bytes to read
        
        Returns:
            Received data or None if connection closed
        """
        try:
            data = await self.reader.read(size)
            if not data:
                return None
            self.bytes_received += len(data)
            self.update_activity()
            return data
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            return None
    
    def close(self) -> None:
        """Close connection."""
        if not self.writer.is_closing():
            self.writer.close()
        self.is_active = False
    
    def get_statistics(self) -> dict:
        """Get session statistics."""
        uptime = (datetime.utcnow() - self.connected_at).total_seconds()
        
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'assigned_ip': self.assigned_ip,
            'client_ip': self.client_ip,
            'uptime_seconds': int(uptime),
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active,
        }


class SessionManager:
    """
    Manages all active client sessions.
    
    Responsibilities:
    - Track active sessions
    - Session lifecycle management
    - Session lookup by various keys
    """
    
    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, ClientSession] = {}  # token -> session
        self.sessions_by_ip: Dict[str, ClientSession] = {}  # IP -> session
        self._lock = asyncio.Lock()
    
    async def add_session(self, session: ClientSession) -> None:
        """
        Add a new session.
        
        Args:
            session: Client session to add
        """
        async with self._lock:
            self.sessions[session.session_token] = session
            self.sessions_by_ip[session.assigned_ip] = session
            logger.info(
                f"Session added: token={session.session_token[:16]}..., "
                f"ip={session.assigned_ip}"
            )
    
    async def remove_session(self, session_token: str) -> Optional[ClientSession]:
        """
        Remove a session.
        
        Args:
            session_token: Session token
        
        Returns:
            Removed session or None if not found
        """
        async with self._lock:
            session = self.sessions.pop(session_token, None)
            if session:
                self.sessions_by_ip.pop(session.assigned_ip, None)
                session.close()
                logger.info(f"Session removed: token={session_token[:16]}...")
            return session
    
    def get_session(self, session_token: str) -> Optional[ClientSession]:
        """Get session by token."""
        return self.sessions.get(session_token)
    
    def get_session_by_ip(self, ip_address: str) -> Optional[ClientSession]:
        """Get session by assigned IP."""
        return self.sessions_by_ip.get(ip_address)
    
    def get_all_sessions(self) -> list[ClientSession]:
        """Get all active sessions."""
        return list(self.sessions.values())
    
    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.sessions)
    
    async def cleanup_inactive_sessions(self, timeout_seconds: int = 300) -> int:
        """
        Clean up inactive sessions.
        
        Args:
            timeout_seconds: Timeout in seconds
        
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        to_remove = []
        
        for token, session in self.sessions.items():
            idle_time = (now - session.last_activity).total_seconds()
            if idle_time > timeout_seconds or not session.is_active:
                to_remove.append(token)
        
        for token in to_remove:
            await self.remove_session(token)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive sessions")
        
        return len(to_remove)
    
    def get_statistics(self) -> dict:
        """Get overall statistics."""
        sessions = self.get_all_sessions()
        
        total_bytes_sent = sum(s.bytes_sent for s in sessions)
        total_bytes_received = sum(s.bytes_received for s in sessions)
        
        return {
            'active_sessions': len(sessions),
            'total_bytes_sent': total_bytes_sent,
            'total_bytes_received': total_bytes_received,
        }
