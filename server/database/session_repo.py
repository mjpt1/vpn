"""
Session Repository - CRUD operations for Session model
"""

import logging
import secrets
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession

from .models import Session as SessionModel, ConnectionLog
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from shared.exceptions import SessionError, SessionLimitError

logger = logging.getLogger(__name__)


class SessionRepository:
    """
    Repository for Session database operations.
    """
    
    def __init__(self, db_session: DBSession):
        """
        Initialize session repository.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def create_session(
        self,
        user_id: int,
        assigned_ip: str,
        client_real_ip: str,
        client_version: str,
        encryption_key: str,
        expiry_hours: int = 24
    ) -> SessionModel:
        """
        Create a new session.
        
        Args:
            user_id: User ID
            assigned_ip: Virtual IP assigned to client
            client_real_ip: Client's real IP address
            client_version: Client software version
            encryption_key: Hex-encoded encryption key
            expiry_hours: Session expiry in hours
        
        Returns:
            Created Session object
        
        Raises:
            SessionLimitError: If user has too many active sessions
        """
        # Check session limit
        active_count = self.get_active_session_count(user_id)
        from .user_repo import UserRepository
        user_repo = UserRepository(self.db)
        user = user_repo.get_by_id(user_id)
        
        if user and active_count >= user.max_sessions:
            raise SessionLimitError(
                f"User has reached maximum session limit ({user.max_sessions})"
            )
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Create session
        session = SessionModel(
            session_token=session_token,
            user_id=user_id,
            assigned_ip=assigned_ip,
            client_real_ip=client_real_ip,
            client_version=client_version,
            encryption_key=encryption_key,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        logger.info(f"Session created: user_id={user_id}, ip={assigned_ip}, token={session_token[:16]}...")
        return session
    
    def get_by_token(self, session_token: str) -> Optional[SessionModel]:
        """Get session by token."""
        return self.db.query(SessionModel).filter(
            SessionModel.session_token == session_token
        ).first()
    
    def get_by_id(self, session_id: int) -> Optional[SessionModel]:
        """Get session by ID."""
        return self.db.query(SessionModel).filter(
            SessionModel.id == session_id
        ).first()
    
    def get_active_sessions(self, user_id: Optional[int] = None) -> List[SessionModel]:
        """
        Get active sessions.
        
        Args:
            user_id: Optional user ID to filter by
        
        Returns:
            List of active sessions
        """
        query = self.db.query(SessionModel).filter(SessionModel.is_active == True)
        
        if user_id is not None:
            query = query.filter(SessionModel.user_id == user_id)
        
        return query.all()
    
    def get_active_session_count(self, user_id: int) -> int:
        """Get count of active sessions for user."""
        count = self.db.query(SessionModel).filter(
            SessionModel.user_id == user_id,
            SessionModel.is_active == True
        ).count()
        return count
    
    def validate_session(self, session_token: str) -> Optional[SessionModel]:
        """
        Validate session token.
        
        Args:
            session_token: Session token to validate
        
        Returns:
            Session object if valid, None otherwise
        """
        session = self.get_by_token(session_token)
        
        if not session:
            logger.warning(f"Session not found: {session_token[:16]}...")
            return None
        
        if not session.is_active:
            logger.warning(f"Session inactive: {session_token[:16]}...")
            return None
        
        if session.is_expired():
            logger.warning(f"Session expired: {session_token[:16]}...")
            self.terminate_session(session.id, "Session expired")
            return None
        
        # Update last activity
        session.update_activity()
        self.db.commit()
        
        return session
    
    def extend_session(self, session_id: int, hours: int = 24) -> bool:
        """
        Extend session expiry time.
        
        Args:
            session_id: Session ID
            hours: Hours to extend
        
        Returns:
            True if extended, False if session not found
        """
        session = self.get_by_id(session_id)
        if not session:
            return False
        
        session.extend_expiry(hours)
        self.db.commit()
        
        logger.info(f"Session extended: id={session_id}, new_expiry={session.expires_at}")
        return True
    
    def update_traffic(
        self,
        session_id: int,
        bytes_sent: int,
        bytes_received: int
    ) -> bool:
        """
        Update session traffic statistics.
        
        Args:
            session_id: Session ID
            bytes_sent: Bytes sent
            bytes_received: Bytes received
        
        Returns:
            True if updated, False if session not found
        """
        session = self.get_by_id(session_id)
        if not session:
            return False
        
        session.add_traffic(bytes_sent, bytes_received)
        session.update_activity()
        self.db.commit()
        
        return True
    
    def terminate_session(self, session_id: int, reason: str = "User disconnected") -> bool:
        """
        Terminate a session.
        
        Args:
            session_id: Session ID
            reason: Disconnect reason
        
        Returns:
            True if terminated, False if not found
        """
        session = self.get_by_id(session_id)
        if not session:
            return False
        
        # Mark inactive
        session.is_active = False
        session.disconnected_at = datetime.utcnow()
        
        # Create connection log
        log = ConnectionLog(
            user_id=session.user_id,
            client_ip=session.client_real_ip,
            assigned_ip=session.assigned_ip,
            connected_at=session.created_at,
            disconnected_at=session.disconnected_at,
            bytes_sent=session.bytes_sent,
            bytes_received=session.bytes_received,
            disconnect_reason=reason,
        )
        log.calculate_duration()
        
        self.db.add(log)
        self.db.commit()
        
        logger.info(f"Session terminated: id={session_id}, reason={reason}")
        return True
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = self.db.query(SessionModel).filter(
            SessionModel.is_active == True,
            SessionModel.expires_at < datetime.utcnow()
        ).all()
        
        count = 0
        for session in expired_sessions:
            self.terminate_session(session.id, "Session expired")
            count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        
        return count
    
    def get_session_statistics(self, session_id: int) -> Optional[dict]:
        """Get session statistics."""
        session = self.get_by_id(session_id)
        if not session:
            return None
        
        # Calculate duration
        if session.is_active:
            duration = datetime.utcnow() - session.created_at
        else:
            duration = session.disconnected_at - session.created_at
        
        return {
            'session_id': session.id,
            'user_id': session.user_id,
            'assigned_ip': session.assigned_ip,
            'is_active': session.is_active,
            'bytes_sent': session.bytes_sent,
            'bytes_received': session.bytes_received,
            'total_bytes': session.bytes_sent + session.bytes_received,
            'packets_sent': session.packets_sent,
            'packets_received': session.packets_received,
            'duration_seconds': int(duration.total_seconds()),
            'created_at': session.created_at,
            'last_activity': session.last_activity,
        }
