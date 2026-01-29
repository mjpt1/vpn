"""
GUI Application - Simple VPN Client Interface
"""

import sys
import logging
import asyncio
from pathlib import Path
from threading import Thread

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vpn_gui")

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from client.core.tunnel_client import TunnelClient
    logger.info("✓ VPN Core loaded successfully")
except ImportError as e:
    logger.error(f"✗ Core import failed: {e}")

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, 
        QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox,
        QMessageBox, QStatusBar, QTabWidget, QFormLayout
    )
    from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot
    from PySide6.QtGui import QIcon
    logger.info("✓ PySide6 loaded successfully")
except ImportError as e:
    logger.error(f"✗ PySide6 import failed: {e}")
    sys.exit(1)


class VPNWorker(QThread):
    """Worker thread for VPN connection."""
    
    connected = Signal(str)
    disconnected = Signal(str)
    error_occurred = Signal(str)
    log_message = Signal(str)
    
    def __init__(self, host, port, username, password):
        super().__init__()
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.client = None
        self._is_running = True
        self.loop = None

    def run(self):
        """Run the VPN client in a separate thread."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.loop.run_until_complete(self._run_async())
            self.loop.close()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            
    async def _run_async(self):
        """Async entry point."""
        try:
            self.client = TunnelClient(
                server_host=self.host,
                server_port=self.port,
                username=self.username,
                password=self.password,
                verify_cert=False  # Self-signed certs for testing
            )
            
            # Setup callbacks (need to bridge to signals)
            # Note: callbacks are called from async loop, so emit signal is safe in Qt?
            # Qt signals are thread-safe.
            
            self.log_message.emit(f"Connecting to {self.host}:{self.port}...")
            
            success = await self.client.connect()
            
            if success:
                self.connected.emit(self.client.assigned_ip or "Unknown IP")
                self.log_message.emit("✓ Connected successfully!")
                
                # Keep running until stopped
                while self._is_running and self.client.is_connected:
                    await asyncio.sleep(1)
            else:
                self.error_occurred.emit("Connection failed (check server logs)")
                
        except Exception as e:
            logger.exception("VPN Worker Error")
            self.error_occurred.emit(str(e))
        finally:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.disconnected.emit("Stopped")

    def stop(self):
        """Stop the worker thread."""
        self._is_running = False


class MainWindow(QMainWindow):
    """Main VPN Client Window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VPN Client")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("VPN Client")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Server configuration
        config_layout = QFormLayout()
        
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("vpn.example.com")
        config_layout.addRow("VPN Server:", self.server_input)
        
        self.port_input = QLineEdit()
        self.port_input.setText("443")
        config_layout.addRow("Port:", self.port_input)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username")
        config_layout.addRow("Username:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("password")
        config_layout.addRow("Password:", self.password_input)
        
        layout.addLayout(config_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        button_layout.addWidget(self.disconnect_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)
        
        # Add stretch
        layout.addStretch()
        
        central_widget.setLayout(layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        self.worker = None
        
        logger.info("✓ Main window created successfully")
    
    def on_connect(self):
        """Handle connect button."""
        server = self.server_input.text()
        port = self.port_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not server or not port or not username or not password:
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
            
        self.status_label.setText(f"Status: Connecting to {server}...")
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.server_input.setEnabled(False)
        self.port_input.setEnabled(False)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
        
        # Start worker thread
        self.worker = VPNWorker(server, port, username, password)
        self.worker.connected.connect(self.on_connected)
        self.worker.disconnected.connect(self.on_disconnected_worker)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.log_message.connect(self.update_status)
        self.worker.start()
    
    def on_disconnect(self):
        """Handle disconnect button."""
        if self.worker:
            self.status_label.setText("Status: Disconnecting...")
            self.worker.stop()
            # Wait for thread will be done in on_disconnected_worker
    
    @Slot(str)
    def on_connected(self, ip_address):
        """Called when connected successfully."""
        self.status_label.setText(f"Status: Connected (IP: {ip_address})")
        QMessageBox.information(self, "Connected", f"Successfully connected!\nYour IP: {ip_address}")

    @Slot(str)
    def on_disconnected_worker(self, reason):
        """Called when worker thread finishes."""
        self.reset_ui()
        self.status_label.setText(f"Status: Disconnected ({reason})")

    @Slot(str)
    def on_error(self, error_msg):
        """Called when error occurs."""
        self.reset_ui()
        self.status_label.setText("Status: Error")
        QMessageBox.critical(self, "Connection Error", f"Error: {error_msg}")

    @Slot(str)
    def update_status(self, msg):
        """Update status bar."""
        self.statusBar().showMessage(msg)

    def reset_ui(self):
        """Reset UI to initial state."""
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.server_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.username_input.setEnabled(True)
        self.password_input.setEnabled(True)


def main() -> int:
    """Main entry point."""
    logger.info("Starting VPN GUI Client...")
    
    try:
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("✓ GUI window created and shown")
        
        # Run application
        return app.exec()
    
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
