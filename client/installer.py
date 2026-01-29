"""
Installation Script for VPN Client
Handles deployment and initial setup.
"""

import os
import sys
import shutil
import winreg
import logging
from pathlib import Path
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VPNInstaller:
    """VPN Client installer."""
    
    def __init__(self, install_dir: Path = None):
        """
        Initialize installer.
        
        Args:
            install_dir: Installation directory (default: Program Files)
        """
        if install_dir is None:
            # Default to Program Files
            program_files = Path(os.environ.get('ProgramFiles', 'C:\\Program Files'))
            install_dir = program_files / "VPN Client"
        
        self.install_dir = install_dir
        self.exe_path = None
        
        logger.info(f"Installation directory: {self.install_dir}")
    
    def check_admin(self) -> bool:
        """Check if running as admin."""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def require_admin(self) -> None:
        """Exit if not running as admin."""
        if not self.check_admin():
            logger.error("Installation requires Administrator privileges!")
            logger.info("Please run this installer as Administrator.")
            sys.exit(1)
    
    def create_directories(self) -> bool:
        """Create installation directories."""
        logger.info("Creating installation directories...")
        
        try:
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            (self.install_dir / "logs").mkdir(exist_ok=True)
            (self.install_dir / "data").mkdir(exist_ok=True)
            
            logger.info(f"✓ Created {self.install_dir}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            return False
    
    def copy_files(self, exe_path: Path) -> bool:
        """
        Copy executable and supporting files.
        
        Args:
            exe_path: Path to VPN_Client.exe
        
        Returns:
            True if successful
        """
        logger.info("Copying files...")
        
        if not exe_path.exists():
            logger.error(f"EXE not found: {exe_path}")
            return False
        
        try:
            # Copy executable
            dest_exe = self.install_dir / exe_path.name
            shutil.copy2(exe_path, dest_exe)
            logger.info(f"✓ Copied {exe_path.name}")
            
            self.exe_path = dest_exe
            
            # Copy entire dist folder
            exe_parent = exe_path.parent
            src_libs = exe_parent / "_internal"
            
            if src_libs.exists():
                dest_libs = self.install_dir / "_internal"
                if dest_libs.exists():
                    shutil.rmtree(dest_libs)
                shutil.copytree(src_libs, dest_libs)
                logger.info("✓ Copied libraries")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to copy files: {e}")
            return False
    
    def create_shortcuts(self) -> bool:
        """Create Start Menu and Desktop shortcuts."""
        logger.info("Creating shortcuts...")
        
        if not self.exe_path:
            logger.error("EXE path not set")
            return False
        
        try:
            import win32com.client
            
            # Create Start Menu shortcut
            start_menu = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            start_menu_dir = start_menu / "VPN Client"
            start_menu_dir.mkdir(exist_ok=True)
            
            shortcut_path = start_menu_dir / "VPN Client.lnk"
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.TargetPath = str(self.exe_path)
            shortcut.WorkingDirectory = str(self.install_dir)
            shortcut.IconLocation = str(self.exe_path)
            shortcut.save()
            
            logger.info(f"✓ Created Start Menu shortcut")
            
            # Create Desktop shortcut
            desktop = Path(os.environ['USERPROFILE']) / "Desktop"
            desktop_shortcut = desktop / "VPN Client.lnk"
            
            shortcut = shell.CreateShortCut(str(desktop_shortcut))
            shortcut.TargetPath = str(self.exe_path)
            shortcut.WorkingDirectory = str(self.install_dir)
            shortcut.IconLocation = str(self.exe_path)
            shortcut.save()
            
            logger.info(f"✓ Created Desktop shortcut")
            
            return True
        
        except ImportError:
            logger.warning("win32com not available, skipping shortcuts")
            logger.info("Install with: pip install pywin32")
            return False
        
        except Exception as e:
            logger.error(f"Failed to create shortcuts: {e}")
            return False
    
    def register_uninstaller(self) -> bool:
        """Register in Programs and Features for uninstall."""
        logger.info("Registering uninstaller...")
        
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VPN_Client"
            
            # Create registry key
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            
            # Set registry values
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "VPN Client - Iran Gateway")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "VPN Gateway")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, str(self.exe_path))
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(self.install_dir))
            winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, "http://vpn.example.com")
            
            winreg.CloseKey(key)
            
            logger.info("✓ Registered in Programs and Features")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register uninstaller: {e}")
            return False
    
    def create_config_template(self) -> bool:
        """Create configuration template."""
        logger.info("Creating configuration template...")
        
        try:
            config_path = self.install_dir / "client_config.yaml"
            
            if config_path.exists():
                logger.info("Configuration file already exists, skipping")
                return True
            
            # Create template
            template = """# VPN Client Configuration
# Edit this file before running VPN Client

server:
  host: ""           # VPN server IP or hostname (REQUIRED)
  port: 8443                  # VPN server port
  verify_cert: false          # Verify TLS certificate
  cert_file: null             # Path to CA certificate file

auth:
  username: ""                # Your username (REQUIRED)
  password: ""                # Your password (REQUIRED)

network:
  interface_name: "VPN-TAP"   # TAP interface name
  mtu: 1400                   # MTU size
  dns_servers:
    - "8.8.8.8"
    - "8.8.4.4"

vpn:
  auto_reconnect: true        # Automatically reconnect
  kill_switch: true           # Block all traffic if VPN disconnects
  allow_lan: true             # Allow LAN access with kill switch
  reconnect_max_backoff: 30   # Max reconnect backoff (seconds)

logging:
  level: "INFO"               # Log level: DEBUG, INFO, WARNING, ERROR
  file: "vpn_client.log"      # Log file path
  console: true               # Log to console
"""
            
            config_path.write_text(template)
            logger.info(f"✓ Created configuration template: {config_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to create config: {e}")
            return False
    
    def install(self, exe_path: Path) -> bool:
        """
        Run full installation.
        
        Args:
            exe_path: Path to VPN_Client.exe
        
        Returns:
            True if successful
        """
        logger.info("=" * 60)
        logger.info("VPN Client Installation")
        logger.info("=" * 60)
        
        # Check admin
        self.require_admin()
        
        # Create directories
        if not self.create_directories():
            return False
        
        # Copy files
        if not self.copy_files(exe_path):
            return False
        
        # Create configuration
        self.create_config_template()
        
        # Create shortcuts
        self.create_shortcuts()
        
        # Register uninstaller
        self.register_uninstaller()
        
        logger.info("=" * 60)
        logger.info("Installation Complete!")
        logger.info("=" * 60)
        logger.info(f"\nVPN Client installed to: {self.install_dir}")
        logger.info(f"Executable: {self.exe_path}")
        logger.info(f"\nYou can now run VPN Client from:")
        logger.info(f"  - Start Menu → VPN Client")
        logger.info(f"  - Desktop shortcut")
        logger.info(f"  - {self.exe_path}")
        logger.info("\nNext steps:")
        logger.info(f"  1. Edit: {self.install_dir / 'client_config.yaml'}")
        logger.info(f"  2. Set server IP and credentials")
        logger.info(f"  3. Run VPN Client")
        
        return True


def main():
    """Main installation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="VPN Client Installer")
    parser.add_argument("exe", help="Path to VPN_Client.exe")
    parser.add_argument(
        "--install-dir",
        help="Installation directory (default: Program Files)"
    )
    
    args = parser.parse_args()
    
    exe_path = Path(args.exe)
    install_dir = Path(args.install_dir) if args.install_dir else None
    
    installer = VPNInstaller(install_dir)
    
    success = installer.install(exe_path)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
