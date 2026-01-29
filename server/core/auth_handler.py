"""
Authentication Handler - User authentication and session management
"""

import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session as DBSession

from ..database.user_repo import UserRepository
from ..database.session_repo import SessionRepository
from ..database.models import User, Session as SessionModel
from ..core.encryption import EncryptionHandler

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from shared.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    SessionLimitError,
)

logger = logging.getLogger(__name__)


class AuthHandler:
    """
    Handles authentication and session management.
    
    Responsibilities:
    - User authentication
    - Session creation and validation
    - Token management
    - IP assignment
    """
    
    def __init__(self, db_session: DBSession):
        """
        Initialize authentication handler.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.user_repo = UserRepository(db_session)
        self.session_repo = SessionRepository(db_session)
        
        # Track assigned IPs
        self.assigned_ips: set[str] = set()
        self._load_assigned_ips()
    
    def _load_assigned_ips(self) -> None:
        """Load currently assigned IPs from active sessions."""
        active_sessions = self.session_repo.get_active_sessions()
        self.assigned_ips = {session.assigned_ip for session in active_sessions}
        logger.info(f"Loaded {len(self.assigned_ips)} assigned IPs")
    
    def authenticate_user(
        self,
        username: str,
        password: str,
        client_ip: str,
        client_version: str
    ) -> Tuple[SessionModel, str]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username
            password: Password (plain text)
            client_ip: Client's real IP address
            client_version: Client software version
        
        Returns:
            Tuple of (Session object, encryption_key_hex)
        
        Raises:
            InvalidCredentialsError: If authentication fails
            SessionLimitError: If user has too many sessions
        """
        # Authenticate user
        user = self.user_repo.authenticate(username, password)
        if not user:
            raise InvalidCredentialsError(f"Invalid username or password")
        
        # Check session limit
        if not self.user_repo.can_create_session(user.id):
            raise SessionLimitError(
                f"Maximum sessions ({user.max_sessions}) reached"
            )
        
        # Assign virtual IP
        assigned_ip = self._assign_ip()
        
        # Generate encryption key
        encryption_key = EncryptionHandler.generate_master_key()
        encryption_key_hex = encryption_key.hex()
        
        # Create session
        try:
            session = self.session_repo.create_session(
                user_id=user.id,
                assigned_ip=assigned_ip,
                client_real_ip=client_ip,
                client_version=client_version,
                encryption_key=encryption_key_hex,
                expiry_hours=24,
            )
            
            logger.info(
                f"User authenticated: {username}, IP={assigned_ip}, "
                f"token={session.session_token[:16]}..."
            )
            
            return session, encryption_key_hex
        
        except Exception as e:
            # Release IP if session creation fails
            self.assigned_ips.discard(assigned_ip)
            raise AuthenticationError(f"Failed to create session: {e}")
    
    def validate_token(self, session_token: str) -> Optional[SessionModel]:
        """
        Validate session token.
        
        Args:
            session_token: Session token
        
        Returns:
            Session object if valid, None otherwise
        
        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token has expired
        """
        session = self.session_repo.validate_session(session_token)
        
        if session is None:
            # Check if session exists but is expired or inactive
            session_obj = self.session_repo.get_by_token(session_token)
            if session_obj:
                if session_obj.is_expired():
                    raise TokenExpiredError()
                else:
                    raise InvalidTokenError("Session is inactive")
            else:
                raise InvalidTokenError("Invalid session token")
        
        return session
    
    def terminate_session(self, session_token: str, reason: str = "User logout") -> bool:
        """
        Terminate a session.
        
        Args:
            session_token: Session token
            reason: Termination reason
        
        Returns:
            True if terminated, False if not found
        """
        session = self.session_repo.get_by_token(session_token)
        if not session:
            return False
        
        # Release IP
        self.assigned_ips.discard(session.assigned_ip)
        
        # Terminate in database
        result = self.session_repo.terminate_session(session.id, reason)
        
        if result:
            logger.info(f"Session terminated: {session_token[:16]}..., reason={reason}")
        
        return result
    
    def _assign_ip(self) -> str:
        """
        Assign next available IP address.
        
        Returns:
            Assigned IP address (e.g., "10.8.0.5")
        
        Raises:
            RuntimeError: If no IPs available
        """
        from shared.protocol import get_next_client_ip
        
        # Try to find available IP
        for i in range(253):  # .2 to .254
            ip = get_next_client_ip(i)
            if ip not in self.assigned_ips:
                self.assigned_ips.add(ip)
                return ip
        
        raise RuntimeError("No available IP addresses")
    
    def release_ip(self, ip_address: str) -> None:
        """Release an IP address."""
        self.assigned_ips.discard(ip_address)
        logger.debug(f"Released IP: {ip_address}")
    
    def get_session_by_ip(self, ip_address: str) -> Optional[SessionModel]:
        """Get active session by assigned IP."""
        sessions = self.session_repo.get_active_sessions()
        for session in sessions:
            if session.assigned_ip == ip_address:
                return session
        return None
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        count = self.session_repo.cleanup_expired_sessions()
        
        # Reload assigned IPs
        self._load_assigned_ips()
        
        return count
    
    def get_active_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self.session_repo.get_active_sessions())
    
    def get_statistics(self) -> dict:
        """Get authentication statistics."""
        active_sessions = self.session_repo.get_active_sessions()
        
        total_bytes_sent = sum(s.bytes_sent for s in active_sessions)
        total_bytes_received = sum(s.bytes_received for s in active_sessions)
        
        return {
            'active_sessions': len(active_sessions),
            'assigned_ips': len(self.assigned_ips),
            'total_bytes_sent': total_bytes_sent,
            'total_bytes_received': total_bytes_received,
        }
