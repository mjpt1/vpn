"""
Signal Bridge - Thread-safe bridge between async Core and Qt GUI
Converts asyncio callbacks to Qt signals.
"""

from PySide6.QtCore import QObject, Signal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VPNSignals(QObject):
    """
    Qt Signals for VPN events.
    
    These signals are thread-safe and can be emitted from asyncio tasks.
    """
    
    # Connection state signals
    state_changed = Signal(str)  # state name
    connection_success = Signal()
    connection_failed = Signal(str)  # error message
    disconnected = Signal(str)  # reason
    
    # Network signals
    ip_assigned = Signal(str)  # IP address
    
    # Statistics signals
    stats_updated = Signal(dict)  # statistics dict
    
    # Log signals
    log_message = Signal(str, str)  # (level, message)
    
    # Progress signals
    progress_update = Signal(int)  # 0-100
    status_message = Signal(str)  # status text
    
    def __init__(self):
        """Initialize signals."""
        super().__init__()
        logger.debug("VPN signals initialized")


class SignalBridge:
    """
    Bridge between Core callbacks and Qt signals.
    
    Provides callback functions that emit Qt signals.
    """
    
    def __init__(self, signals: VPNSignals):
        """
        Initialize signal bridge.
        
        Args:
            signals: VPN signals object
        """
        self.signals = signals
        logger.info("Signal bridge initialized")
    
    # Connection Manager callbacks
    
    def on_state_change(self, state) -> None:
        """Handle state change."""
        state_name = state.value if hasattr(state, 'value') else str(state)
        logger.debug(f"State changed: {state_name}")
        self.signals.state_changed.emit(state_name)
    
    def on_connected(self, assigned_ip: str) -> None:
        """Handle connection success."""
        logger.info(f"Connected: {assigned_ip}")
        self.signals.connection_success.emit()
        self.signals.ip_assigned.emit(assigned_ip)
    
    def on_disconnected(self, reason: str) -> None:
        """Handle disconnection."""
        logger.info(f"Disconnected: {reason}")
        self.signals.disconnected.emit(reason)
    
    def on_error(self, error: str) -> None:
        """Handle error."""
        logger.error(f"Error: {error}")
        self.signals.connection_failed.emit(error)
    
    def on_ip_assigned(self, ip: str) -> None:
        """Handle IP assignment."""
        logger.info(f"IP assigned: {ip}")
        self.signals.ip_assigned.emit(ip)
    
    # Log handler
    
    def on_log_message(self, level: str, message: str) -> None:
        """Handle log message."""
        self.signals.log_message.emit(level, message)
    
    # Statistics
    
    def on_stats_update(self, stats: dict) -> None:
        """Handle statistics update."""
        self.signals.stats_updated.emit(stats)
    
    # Progress
    
    def on_progress(self, progress: int) -> None:
        """Handle progress update."""
        self.signals.progress_update.emit(progress)
    
    def on_status(self, message: str) -> None:
        """Handle status message."""
        self.signals.status_message.emit(message)
