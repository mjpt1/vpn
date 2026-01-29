"""
Statistics Widget - Display traffic statistics
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class StatsWidget(QWidget):
    """
    Statistics display widget.
    
    Shows:
    - Bytes sent/received
    - Packets sent/received
    - Connection attempts
    """
    
    def __init__(self, parent=None):
        """Initialize statistics widget."""
        super().__init__(parent)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box
        group = QGroupBox("آمار اتصال")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        # Upload
        upload_layout = QHBoxLayout()
        upload_layout.setSpacing(8)
        
        upload_title = QLabel("↑ ارسال:")
        upload_title.setStyleSheet("color: #4ec9b0;")
        upload_layout.addWidget(upload_title)
        
        self.upload_label = QLabel("0 B")
        upload_layout.addWidget(self.upload_label)
        
        upload_layout.addStretch()
        group_layout.addLayout(upload_layout)
        
        # Download
        download_layout = QHBoxLayout()
        download_layout.setSpacing(8)
        
        download_title = QLabel("↓ دریافت:")
        download_title.setStyleSheet("color: #4ec9b0;")
        download_layout.addWidget(download_title)
        
        self.download_label = QLabel("0 B")
        download_layout.addWidget(self.download_label)
        
        download_layout.addStretch()
        group_layout.addLayout(download_layout)
        
        # Separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #3f3f46;")
        group_layout.addWidget(separator)
        
        # Packets sent
        packets_sent_layout = QHBoxLayout()
        packets_sent_layout.setSpacing(8)
        
        packets_sent_title = QLabel("بسته ارسالی:")
        packets_sent_title.setStyleSheet("color: #999999;")
        packets_sent_layout.addWidget(packets_sent_title)
        
        self.packets_sent_label = QLabel("0")
        packets_sent_layout.addWidget(self.packets_sent_label)
        
        packets_sent_layout.addStretch()
        group_layout.addLayout(packets_sent_layout)
        
        # Packets received
        packets_recv_layout = QHBoxLayout()
        packets_recv_layout.setSpacing(8)
        
        packets_recv_title = QLabel("بسته دریافتی:")
        packets_recv_title.setStyleSheet("color: #999999;")
        packets_recv_layout.addWidget(packets_recv_title)
        
        self.packets_recv_label = QLabel("0")
        packets_recv_layout.addWidget(self.packets_recv_label)
        
        packets_recv_layout.addStretch()
        group_layout.addLayout(packets_recv_layout)
        
        layout.addWidget(group)
    
    def update_stats(self, stats: dict) -> None:
        """
        Update statistics display.
        
        Args:
            stats: Statistics dictionary from ConnectionManager
        """
        if 'tunnel' in stats:
            tunnel_stats = stats['tunnel']
            
            # Bytes
            bytes_sent = tunnel_stats.get('bytes_sent', 0)
            bytes_recv = tunnel_stats.get('bytes_received', 0)
            
            self.upload_label.setText(self._format_bytes(bytes_sent))
            self.download_label.setText(self._format_bytes(bytes_recv))
            
            # Packets
            packets_sent = tunnel_stats.get('packets_sent', 0)
            packets_recv = tunnel_stats.get('packets_received', 0)
            
            self.packets_sent_label.setText(f"{packets_sent:,}")
            self.packets_recv_label.setText(f"{packets_recv:,}")
    
    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        self.upload_label.setText("0 B")
        self.download_label.setText("0 B")
        self.packets_sent_label.setText("0")
        self.packets_recv_label.setText("0")
    
    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """
        Format bytes to human-readable string.
        
        Args:
            bytes_value: Number of bytes
        
        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
