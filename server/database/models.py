"""
Database Models - SQLAlchemy ORM
Defines User, Session, and ConnectionLog tables.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """
    User table - stores VPN user accounts.
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)  # Argon2 hash
    email = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Limits
    max_sessions = Column(Integer, default=3, nullable=False)
    bandwidth_limit_mb = Column(Integer, default=0, nullable=False)  # 0 = unlimited
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    sessions = relationship('Session', back_populates='user', cascade='all, delete-orphan')
    connection_logs = relationship('ConnectionLog', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', active={self.is_active})>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'max_sessions': self.max_sessions,
            'bandwidth_limit_mb': self.bandwidth_limit_mb,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class Session(Base):
    """
    Session table - stores active VPN sessions.
    """
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Connection info
    assigned_ip = Column(String(15), nullable=False)  # Virtual IP (e.g., 10.8.0.5)
    client_real_ip = Column(String(45), nullable=True)  # Client's real IP
    client_version = Column(String(20), nullable=True)
    
    # Encryption
    encryption_key = Column(String(64), nullable=False)  # Hex-encoded master key
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Statistics
    bytes_sent = Column(BigInteger, default=0, nullable=False)
    bytes_received = Column(BigInteger, default=0, nullable=False)
    packets_sent = Column(BigInteger, default=0, nullable=False)
    packets_received = Column(BigInteger, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    disconnected_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('User', back_populates='sessions')
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, ip='{self.assigned_ip}', active={self.is_active})>"
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at
    
    def extend_expiry(self, hours: int = 24) -> None:
        """Extend session expiry time."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def add_traffic(self, bytes_sent: int, bytes_received: int) -> None:
        """Update traffic statistics."""
        self.bytes_sent += bytes_sent
        self.bytes_received += bytes_received
        self.packets_sent += 1  # Simplified
        self.packets_received += 1
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'session_token': self.session_token,
            'user_id': self.user_id,
            'assigned_ip': self.assigned_ip,
            'client_real_ip': self.client_real_ip,
            'client_version': self.client_version,
            'is_active': self.is_active,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class ConnectionLog(Base):
    """
    Connection log table - audit trail of connections.
    """
    __tablename__ = 'connection_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Connection info
    client_ip = Column(String(45), nullable=True)
    assigned_ip = Column(String(15), nullable=True)
    
    # Timestamps
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    disconnected_at = Column(DateTime, nullable=True)
    
    # Statistics (snapshot at disconnect)
    bytes_sent = Column(BigInteger, default=0, nullable=False)
    bytes_received = Column(BigInteger, default=0, nullable=False)
    duration_seconds = Column(Integer, default=0, nullable=False)
    
    # Status
    disconnect_reason = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship('User', back_populates='connection_logs')
    
    def __repr__(self):
        return f"<ConnectionLog(id={self.id}, user_id={self.user_id}, connected={self.connected_at})>"
    
    def calculate_duration(self) -> None:
        """Calculate connection duration."""
        if self.disconnected_at:
            delta = self.disconnected_at - self.connected_at
            self.duration_seconds = int(delta.total_seconds())
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'client_ip': self.client_ip,
            'assigned_ip': self.assigned_ip,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'disconnected_at': self.disconnected_at.isoformat() if self.disconnected_at else None,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'duration_seconds': self.duration_seconds,
            'disconnect_reason': self.disconnect_reason,
        }
