"""
Connection Button Widget - Animated connect/disconnect button
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QTimer
from PySide6.QtGui import QColor
import logging

logger = logging.getLogger(__name__)


class ConnectionButton(QPushButton):
    """
    Custom connection button with animations.
    
    States:
    - Disconnected: Blue "اتصال"
    - Connecting: Orange "در حال اتصال..." (pulsing)
    - Connected: Red "قطع اتصال"
    """
    
    def __init__(self, parent=None):
        """Initialize connection button."""
        super().__init__(parent)
        
        self.setObjectName("connectButton")
        self.setMinimumSize(200, 60)
        self.setCursor(Qt.PointingHandCursor)
        
        # State
        self._is_connected = False
        self._is_connecting = False
        
        # Animation
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_state = 0
        
        self._update_ui()
    
    def set_disconnected(self) -> None:
        """Set button to disconnected state."""
        self._is_connected = False
        self._is_connecting = False
        self._stop_animation()
        self._update_ui()
    
    def set_connecting(self) -> None:
        """Set button to connecting state."""
        self._is_connected = False
        self._is_connecting = True
        self._start_animation()
        self._update_ui()
    
    def set_connected(self) -> None:
        """Set button to connected state."""
        self._is_connected = True
        self._is_connecting = False
        self._stop_animation()
        self._update_ui()
    
    def _update_ui(self) -> None:
        """Update button text and style."""
        if self._is_connecting:
            self.setText("در حال اتصال...")
            self.setProperty("connecting", "true")
            self.setProperty("connected", "false")
        elif self._is_connected:
            self.setText("قطع اتصال")
            self.setProperty("connecting", "false")
            self.setProperty("connected", "true")
        else:
            self.setText("اتصال")
            self.setProperty("connecting", "false")
            self.setProperty("connected", "false")
        
        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
    
    def _start_animation(self) -> None:
        """Start pulsing animation."""
        self._pulse_timer.start(500)  # 500ms
    
    def _stop_animation(self) -> None:
        """Stop pulsing animation."""
        self._pulse_timer.stop()
        self.setEnabled(True)
    
    def _pulse(self) -> None:
        """Pulse animation effect."""
        self._pulse_state = (self._pulse_state + 1) % 4
        
        if self._pulse_state % 2 == 0:
            self.setText("در حال اتصال...")
        else:
            self.setText("در حال اتصال")
