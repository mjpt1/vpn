"""
Status Widget - Display connection status and IP
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class StatusWidget(QWidget):
    """
    Connection status display widget.
    
    Shows:
    - Connection state
    - Assigned IP
    - Uptime
    - Server info
    """
    
    def __init__(self, parent=None):
        """Initialize status widget."""
        super().__init__(parent)
        
        self._init_ui()
        
        # Uptime tracking
        self._uptime_seconds = 0
        self._uptime_timer = QTimer()
        self._uptime_timer.timeout.connect(self._update_uptime)
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status label
        self.status_label = QLabel("قطع شده")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        # IP label
        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(8)
        
        ip_title = QLabel("IP:")
        ip_title.setStyleSheet("color: #999999;")
        ip_layout.addWidget(ip_title)
        
        self.ip_label = QLabel("---")
        self.ip_label.setObjectName("ipLabel")
        ip_layout.addWidget(self.ip_label)
        
        ip_layout.addStretch()
        layout.addLayout(ip_layout)
        
        # Server label
        server_layout = QHBoxLayout()
        server_layout.setSpacing(8)
        
        server_title = QLabel("سرور:")
        server_title.setStyleSheet("color: #999999;")
        server_layout.addWidget(server_title)
        
        self.server_label = QLabel("---")
        self.server_label.setStyleSheet("color: #cccccc;")
        server_layout.addWidget(self.server_label)
        
        server_layout.addStretch()
        layout.addLayout(server_layout)
        
        # Uptime label
        uptime_layout = QHBoxLayout()
        uptime_layout.setSpacing(8)
        
        uptime_title = QLabel("مدت اتصال:")
        uptime_title.setStyleSheet("color: #999999;")
        uptime_layout.addWidget(uptime_title)
        
        self.uptime_label = QLabel("---")
        self.uptime_label.setStyleSheet("color: #cccccc;")
        uptime_layout.addWidget(self.uptime_label)
        
        uptime_layout.addStretch()
        layout.addLayout(uptime_layout)
        
        layout.addStretch()
    
    def set_status(self, status: str, color: str = None) -> None:
        """
        Set status text.
        
        Args:
            status: Status text
            color: Optional color
        """
        self.status_label.setText(status)
        
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
    
    def set_disconnected(self) -> None:
        """Set disconnected state."""
        self.set_status("قطع شده", "#999999")
        self.ip_label.setText("---")
        self.uptime_label.setText("---")
        self._stop_uptime()
    
    def set_connecting(self) -> None:
        """Set connecting state."""
        self.set_status("در حال اتصال...", "#ca5010")
        self.ip_label.setText("---")
        self.uptime_label.setText("---")
        self._stop_uptime()
    
    def set_connected(self, ip: str = None) -> None:
        """Set connected state."""
        self.set_status("متصل", "#4ec9b0")
        
        if ip:
            self.ip_label.setText(ip)
        
        self._start_uptime()
    
    def set_error(self, error: str) -> None:
        """Set error state."""
        self.set_status(f"خطا: {error}", "#f48771")
        self.ip_label.setText("---")
        self.uptime_label.setText("---")
        self._stop_uptime()
    
    def set_server(self, server: str) -> None:
        """Set server info."""
        self.server_label.setText(server)
    
    def set_ip(self, ip: str) -> None:
        """Set IP address."""
        self.ip_label.setText(ip)
    
    def _start_uptime(self) -> None:
        """Start uptime counter."""
        self._uptime_seconds = 0
        self._update_uptime()
        self._uptime_timer.start(1000)  # Update every second
    
    def _stop_uptime(self) -> None:
        """Stop uptime counter."""
        self._uptime_timer.stop()
        self._uptime_seconds = 0
    
    def _update_uptime(self) -> None:
        """Update uptime display."""
        hours = self._uptime_seconds // 3600
        minutes = (self._uptime_seconds % 3600) // 60
        seconds = self._uptime_seconds % 60
        
        if hours > 0:
            uptime_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_text = f"{minutes:02d}:{seconds:02d}"
        
        self.uptime_label.setText(uptime_text)
        self._uptime_seconds += 1
