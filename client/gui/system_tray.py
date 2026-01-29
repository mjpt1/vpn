"""
System Tray Icon - Minimize to tray functionality
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal
import logging

logger = logging.getLogger(__name__)


class SystemTrayIcon(QSystemTrayIcon):
    """
    System tray icon for VPN client.
    
    Features:
    - Show/hide main window
    - Quick connect/disconnect
    - Status indicator
    """
    
    # Signals
    show_window = Signal()
    connect_requested = Signal()
    disconnect_requested = Signal()
    quit_requested = Signal()
    
    def __init__(self, parent=None):
        """Initialize system tray icon."""
        super().__init__(parent)
        
        # Set icon (using default for now)
        # TODO: Add custom icons
        self.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        
        # Create menu
        self._create_menu()
        
        # Connect signals
        self.activated.connect(self._on_activated)
        
        # Tooltip
        self.setToolTip("VPN Client - قطع شده")
        
        logger.info("System tray icon initialized")
    
    def _create_menu(self) -> None:
        """Create context menu."""
        menu = QMenu()
        
        # Show window
        show_action = QAction("نمایش پنجره", self)
        show_action.triggered.connect(self.show_window.emit)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Connect
        self.connect_action = QAction("اتصال", self)
        self.connect_action.triggered.connect(self.connect_requested.emit)
        menu.addAction(self.connect_action)
        
        # Disconnect
        self.disconnect_action = QAction("قطع اتصال", self)
        self.disconnect_action.triggered.connect(self.disconnect_requested.emit)
        self.disconnect_action.setEnabled(False)
        menu.addAction(self.disconnect_action)
        
        menu.addSeparator()
        
        # Quit
        quit_action = QAction("خروج", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
    
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window.emit()
    
    def set_connected(self) -> None:
        """Set tray icon to connected state."""
        self.setToolTip("VPN Client - متصل")
        self.connect_action.setEnabled(False)
        self.disconnect_action.setEnabled(True)
    
    def set_disconnected(self) -> None:
        """Set tray icon to disconnected state."""
        self.setToolTip("VPN Client - قطع شده")
        self.connect_action.setEnabled(True)
        self.disconnect_action.setEnabled(False)
    
    def set_connecting(self) -> None:
        """Set tray icon to connecting state."""
        self.setToolTip("VPN Client - در حال اتصال...")
        self.connect_action.setEnabled(False)
        self.disconnect_action.setEnabled(False)
    
    def show_message_info(self, title: str, message: str) -> None:
        """Show info notification."""
        self.showMessage(title, message, QSystemTrayIcon.Information, 3000)
    
    def show_message_warning(self, title: str, message: str) -> None:
        """Show warning notification."""
        self.showMessage(title, message, QSystemTrayIcon.Warning, 5000)
    
    def show_message_error(self, title: str, message: str) -> None:
        """Show error notification."""
        self.showMessage(title, message, QSystemTrayIcon.Critical, 5000)
