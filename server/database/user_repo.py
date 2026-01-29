"""
User Repository - CRUD operations for User model
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository for User database operations.
    """
    
    def __init__(self, db_session: DBSession):
        """
        Initialize user repository.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.ph = PasswordHasher()  # Argon2 password hasher
    
    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        is_admin: bool = False,
        max_sessions: int = 3
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            email: Optional email address
            is_admin: Admin flag
            max_sessions: Maximum concurrent sessions
        
        Returns:
            Created User object
        
        Raises:
            ValueError: If username already exists
        """
        # Check if user exists
        existing = self.get_by_username(username)
        if existing:
            raise ValueError(f"Username '{username}' already exists")
        
        # Hash password
        password_hash = self.ph.hash(password)
        
        # Create user
        user = User(
            username=username,
            password_hash=password_hash,
            email=email,
            is_admin=is_admin,
            max_sessions=max_sessions,
            is_active=True,
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Created user: {username} (id={user.id})")
        return user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with password.
        
        Args:
            username: Username
            password: Plain text password
        
        Returns:
            User object if authenticated, None otherwise
        """
        user = self.get_by_username(username)
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication failed: user '{username}' is disabled")
            return None
        
        try:
            # Verify password
            self.ph.verify(user.password_hash, password)
            
            # Update last login
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"User authenticated: {username}")
            return user
        
        except VerifyMismatchError:
            logger.warning(f"Authentication failed: invalid password for '{username}'")
            return None
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password
        
        Returns:
            True if updated, False if user not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.password_hash = self.ph.hash(new_password)
        self.db.commit()
        
        logger.info(f"Password updated for user: {user.username}")
        return True
    
    def disable_user(self, user_id: int) -> bool:
        """Disable user account."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        
        logger.info(f"User disabled: {user.username}")
        return True
    
    def enable_user(self, user_id: int) -> bool:
        """Enable user account."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.is_active = True
        self.db.commit()
        
        logger.info(f"User enabled: {user.username}")
        return True
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete user (cascades to sessions and logs).
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        username = user.username
        self.db.delete(user)
        self.db.commit()
        
        logger.info(f"User deleted: {username}")
        return True
    
    def list_users(self, active_only: bool = False) -> list[User]:
        """
        List all users.
        
        Args:
            active_only: If True, return only active users
        
        Returns:
            List of User objects
        """
        query = self.db.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.all()
    
    def get_active_session_count(self, user_id: int) -> int:
        """Get count of active sessions for user."""
        from .models import Session as SessionModel
        
        count = self.db.query(SessionModel).filter(
            SessionModel.user_id == user_id,
            SessionModel.is_active == True
        ).count()
        
        return count
    
    def can_create_session(self, user_id: int) -> bool:
        """
        Check if user can create a new session.
        
        Args:
            user_id: User ID
        
        Returns:
            True if can create session, False otherwise
        """
        user = self.get_by_id(user_id)
        if not user or not user.is_active:
            return False
        
        active_sessions = self.get_active_session_count(user_id)
        return active_sessions < user.max_sessions
