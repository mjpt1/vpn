"""
Main Window - VPN Client GUI
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QStatusBar, QMessageBox, QPushButton,
    QLabel, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Slot, QSize
from PySide6.QtGui import QAction, QIcon, QFont
from pathlib import Path
import logging
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from client.core import ConnectionManager, ConnectionState
from client.utils import ClientConfig

from .widgets import ConnectionButton, StatusWidget, StatsWidget, LogViewer
from .utils.signal_bridge import VPNSignals, SignalBridge
from .utils.async_runner import AsyncRunner

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main VPN client window.
    
    Features:
    - Connection control
    - Status display
    - Statistics
    - Log viewer
    - Settings
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize main window.
        
        Args:
            config: Client configuration
        """
        super().__init__()
        
        self.config = config
        
        # Async runner for Core
        self.async_runner = AsyncRunner()
        
        # Signals
        self.signals = VPNSignals()
        self.signal_bridge = SignalBridge(self.signals)
        
        # Connection manager (will be created when needed)
        self.connection_manager: ConnectionManager = None
        
        # UI
        self._init_ui()
        self._connect_signals()
        
        # Statistics timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_statistics)
        
        # Start async runner
        self.async_runner.start()
        
        logger.info("Main window initialized")
    
    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle("VPN Client - Iran Gateway")
        self.setMinimumSize(600, 700)
        self.resize(700, 800)
        
        # Load stylesheet
        self._load_stylesheet()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("VPN Gateway")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Connection button
        self.connect_button = ConnectionButton()
        self.connect_button.clicked.connect(self._on_connect_button_clicked)
        main_layout.addWidget(self.connect_button, alignment=Qt.AlignCenter)
        
        # Status widget
        self.status_widget = StatusWidget()
        self.status_widget.set_server(
            f"{self.config.get('server.host', '')}:{self.config.get('server.port', 8443)}"
        )
        main_layout.addWidget(self.status_widget)
        
        # Splitter for stats and logs
        splitter = QSplitter(Qt.Vertical)
        
        # Statistics widget
        self.stats_widget = StatsWidget()
        splitter.addWidget(self.stats_widget)
        
        # Log viewer
        self.log_viewer = LogViewer()
        splitter.addWidget(self.log_viewer)
        
        # Set splitter sizes
        splitter.setSizes([200, 300])
        
        main_layout.addWidget(splitter, stretch=1)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("آماده")
        
        # Initial state
        self._set_ui_disconnected()
    
    def _load_stylesheet(self) -> None:
        """Load dark theme stylesheet."""
        try:
            style_path = Path(__file__).parent / "styles" / "dark_theme.qss"
            
            if style_path.exists():
                with open(style_path, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                logger.info("Stylesheet loaded")
            else:
                logger.warning(f"Stylesheet not found: {style_path}")
        
        except Exception as e:
            logger.exception(f"Error loading stylesheet: {e}")
    
    def _create_menu_bar(self) -> None:
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("فایل")
        
        settings_action = QAction("تنظیمات", self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("راهنما")
        
        about_action = QAction("درباره", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.connection_success.connect(self._on_connection_success)
        self.signals.connection_failed.connect(self._on_connection_failed)
        self.signals.disconnected.connect(self._on_disconnected)
        self.signals.ip_assigned.connect(self._on_ip_assigned)
        self.signals.log_message.connect(self._on_log_message)
        self.signals.stats_updated.connect(self._on_stats_updated)
        self.signals.status_message.connect(self._on_status_message)
    
    @Slot()
    def _on_connect_button_clicked(self) -> None:
        """Handle connect button click."""
        if self.connection_manager and self.connection_manager.is_connected():
            # Disconnect
            self._disconnect()
        else:
            # Connect
            self._connect()
    
    def _connect(self) -> None:
        """Connect to VPN."""
        try:
            logger.info("Connecting to VPN...")
            self.log_viewer.add_log('INFO', 'در حال اتصال به سرور...')
            
            # Update UI
            self._set_ui_connecting()
            
            # Create connection manager
            self.connection_manager = ConnectionManager(self.config.to_dict())
            
            # Set callbacks
            self.connection_manager.on_state_change = self.signal_bridge.on_state_change
            self.connection_manager.on_error = self.signal_bridge.on_error
            self.connection_manager.on_ip_assigned = self.signal_bridge.on_ip_assigned
            
            # Connect in async thread
            future = self.async_runner.run_coroutine(
                self.connection_manager.connect()
            )
            
            # Add done callback
            future.add_done_callback(self._on_connect_done)
        
        except Exception as e:
            logger.exception(f"Connection error: {e}")
            self.log_viewer.add_log('ERROR', f'خطا در اتصال: {e}')
            self._set_ui_disconnected()
    
    def _on_connect_done(self, future) -> None:
        """Handle connection completion."""
        try:
            result = future.result()
            
            if result:
                logger.info("Connection successful")
                self.signals.connection_success.emit()
            else:
                logger.error("Connection failed")
                self.signals.connection_failed.emit("اتصال ناموفق")
        
        except Exception as e:
            logger.exception(f"Connection error: {e}")
            self.signals.connection_failed.emit(str(e))
    
    def _disconnect(self) -> None:
        """Disconnect from VPN."""
        try:
            logger.info("Disconnecting from VPN...")
            self.log_viewer.add_log('INFO', 'در حال قطع اتصال...')
            
            if self.connection_manager:
                # Disconnect in async thread
                future = self.async_runner.run_coroutine(
                    self.connection_manager.disconnect("کاربر درخواست قطع اتصال داد")
                )
                
                future.add_done_callback(self._on_disconnect_done)
        
        except Exception as e:
            logger.exception(f"Disconnect error: {e}")
            self._set_ui_disconnected()
    
    def _on_disconnect_done(self, future) -> None:
        """Handle disconnection completion."""
        try:
            future.result()
            logger.info("Disconnected successfully")
            self.signals.disconnected.emit("قطع اتصال توسط کاربر")
        
        except Exception as e:
            logger.exception(f"Disconnect error: {e}")
    
    @Slot(str)
    def _on_state_changed(self, state: str) -> None:
        """Handle state change."""
        logger.debug(f"State: {state}")
        
        if state == "connected":
            self._set_ui_connected()
            self.stats_timer.start(2000)  # Update stats every 2 seconds
        elif state == "connecting" or state == "authenticating":
            self._set_ui_connecting()
        elif state == "disconnected":
            self._set_ui_disconnected()
            self.stats_timer.stop()
        elif state == "error":
            self._set_ui_disconnected()
            self.stats_timer.stop()
    
    @Slot()
    def _on_connection_success(self) -> None:
        """Handle connection success."""
        self.log_viewer.add_log('INFO', '✓ اتصال برقرار شد')
        self.status_bar.showMessage("متصل", 3000)
    
    @Slot(str)
    def _on_connection_failed(self, error: str) -> None:
        """Handle connection failure."""
        self.log_viewer.add_log('ERROR', f'✗ خطا در اتصال: {error}')
        self.status_bar.showMessage(f"خطا: {error}", 5000)
        
        QMessageBox.warning(
            self,
            "خطا در اتصال",
            f"اتصال به سرور ناموفق بود:\n\n{error}",
            QMessageBox.Ok
        )
    
    @Slot(str)
    def _on_disconnected(self, reason: str) -> None:
        """Handle disconnection."""
        self.log_viewer.add_log('INFO', f'قطع اتصال: {reason}')
        self.status_bar.showMessage("قطع شده", 3000)
    
    @Slot(str)
    def _on_ip_assigned(self, ip: str) -> None:
        """Handle IP assignment."""
        self.status_widget.set_ip(ip)
        self.log_viewer.add_log('INFO', f'IP دریافتی: {ip}')
    
    @Slot(str, str)
    def _on_log_message(self, level: str, message: str) -> None:
        """Handle log message."""
        self.log_viewer.add_log(level, message)
    
    @Slot(dict)
    def _on_stats_updated(self, stats: dict) -> None:
        """Handle statistics update."""
        self.stats_widget.update_stats(stats)
    
    @Slot(str)
    def _on_status_message(self, message: str) -> None:
        """Handle status message."""
        self.status_bar.showMessage(message, 3000)
    
    def _update_statistics(self) -> None:
        """Update statistics (called by timer)."""
        if self.connection_manager and self.connection_manager.is_connected():
            try:
                stats = self.connection_manager.get_statistics()
                self.signals.stats_updated.emit(stats)
            except Exception as e:
                logger.exception(f"Error updating stats: {e}")
    
    def _set_ui_disconnected(self) -> None:
        """Set UI to disconnected state."""
        self.connect_button.set_disconnected()
        self.status_widget.set_disconnected()
        self.stats_widget.reset_stats()
    
    def _set_ui_connecting(self) -> None:
        """Set UI to connecting state."""
        self.connect_button.set_connecting()
        self.status_widget.set_connecting()
    
    def _set_ui_connected(self) -> None:
        """Set UI to connected state."""
        self.connect_button.set_connected()
        self.status_widget.set_connected()
    
    @Slot()
    def _show_settings(self) -> None:
        """Show settings dialog."""
        # TODO: Implement settings dialog
        QMessageBox.information(
            self,
            "تنظیمات",
            "پنجره تنظیمات در نسخه بعدی اضافه خواهد شد.",
            QMessageBox.Ok
        )
    
    @Slot()
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "درباره VPN Client",
            "<h3>VPN Client - Iran Gateway</h3>"
            "<p>نسخه 1.0.0</p>"
            "<p>کلاینت VPN برای اتصال به سرور ایران</p>"
            "<p>توسعه یافته با Python و PySide6</p>"
        )
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self.connection_manager and self.connection_manager.is_connected():
            reply = QMessageBox.question(
                self,
                "خروج",
                "VPN متصل است. آیا می‌خواهید قطع کنید و خارج شوید؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Disconnect
                try:
                    future = self.async_runner.run_coroutine(
                        self.connection_manager.disconnect("بستن برنامه")
                    )
                    future.result(timeout=5)
                except Exception as e:
                    logger.exception(f"Error disconnecting: {e}")
                
                # Stop async runner
                self.async_runner.stop()
                
                event.accept()
            else:
                event.ignore()
        else:
            # Stop async runner
            self.async_runner.stop()
            event.accept()
