"""
Log Viewer Widget - Display formatted logs
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QGroupBox, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LogViewer(QWidget):
    """
    Log viewer widget with color-coded messages.
    
    Features:
    - Color-coded log levels
    - Auto-scroll
    - Clear button
    - Maximum lines limit
    """
    
    MAX_LINES = 1000  # Maximum number of log lines
    
    # Log level colors
    COLORS = {
        'DEBUG': '#808080',
        'INFO': '#4ec9b0',
        'WARNING': '#dcdcaa',
        'ERROR': '#f48771',
        'CRITICAL': '#f48771'
    }
    
    def __init__(self, parent=None):
        """Initialize log viewer."""
        super().__init__(parent)
        
        self._init_ui()
        self._line_count = 0
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box
        group = QGroupBox("لاگ‌ها")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        
        # Text edit
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("logViewer")
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumHeight(150)
        self.text_edit.setMaximumHeight(300)
        group_layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.clear_button = QPushButton("پاک کردن")
        self.clear_button.clicked.connect(self.clear_logs)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        self.auto_scroll_button = QPushButton("اسکرول خودکار: فعال")
        self.auto_scroll_button.setCheckable(True)
        self.auto_scroll_button.setChecked(True)
        self.auto_scroll_button.clicked.connect(self._toggle_auto_scroll)
        button_layout.addWidget(self.auto_scroll_button)
        
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group)
    
    @Slot(str, str)
    def add_log(self, level: str, message: str) -> None:
        """
        Add log message.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
        """
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Get color
        color = self.COLORS.get(level.upper(), '#cccccc')
        
        # Format message
        formatted = f'<span style="color: #808080;">[{timestamp}]</span> '
        formatted += f'<span style="color: {color};">[{level}]</span> '
        formatted += f'<span style="color: #d4d4d4;">{message}</span>'
        
        # Append to text edit
        self.text_edit.append(formatted)
        
        # Increment line count
        self._line_count += 1
        
        # Limit number of lines
        if self._line_count > self.MAX_LINES:
            # Remove first line
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove newline
            self._line_count -= 1
        
        # Auto-scroll to bottom
        if self.auto_scroll_button.isChecked():
            self.text_edit.moveCursor(QTextCursor.End)
    
    @Slot()
    def clear_logs(self) -> None:
        """Clear all logs."""
        self.text_edit.clear()
        self._line_count = 0
        self.add_log('INFO', 'لاگ‌ها پاک شد')
    
    @Slot()
    def _toggle_auto_scroll(self) -> None:
        """Toggle auto-scroll."""
        if self.auto_scroll_button.isChecked():
            self.auto_scroll_button.setText("اسکرول خودکار: فعال")
        else:
            self.auto_scroll_button.setText("اسکرول خودکار: غیرفعال")
