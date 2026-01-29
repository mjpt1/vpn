"""
TAP Interface Manager - Windows TAP-Windows6 adapter management
Handles virtual network interface creation and configuration.
"""

import subprocess
import logging
import re
from typing import Optional, List, Tuple
import time

logger = logging.getLogger(__name__)


class TAPInterface:
    """
    Windows TAP interface manager.
    
    Uses TAP-Windows6 driver (OpenVPN's TAP driver).
    
    Requirements:
    - TAP-Windows6 driver must be installed
    - Administrator privileges required
    """
    
    def __init__(self, interface_name: str = "VPN-TAP"):
        """
        Initialize TAP interface manager.
        
        Args:
            interface_name: Name for the TAP interface
        """
        self.interface_name = interface_name
        self.adapter_guid: Optional[str] = None
        self.adapter_name: Optional[str] = None
        self.is_created = False
        
        logger.info(f"TAP interface manager initialized: {interface_name}")
    
    def _run_command(self, command: str, check: bool = True) -> Tuple[int, str, str]:
        """
        Run shell command.
        
        Args:
            command: Command to run
            check: Raise exception on error
        
        Returns:
            (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if check and result.returncode != 0:
                logger.error(f"Command failed: {command}")
                logger.error(f"Error: {result.stderr}")
                raise Exception(f"Command failed: {result.stderr}")
            
            return result.returncode, result.stdout, result.stderr
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {command}")
            raise Exception("Command timeout")
        
        except Exception as e:
            logger.exception(f"Command error: {e}")
            raise
    
    def find_tap_adapters(self) -> List[dict]:
        """
        Find all TAP adapters.
        
        Returns:
            List of adapter info dicts
        """
        try:
            # Use netsh to list adapters
            _, stdout, _ = self._run_command(
                'netsh interface show interface',
                check=False
            )
            
            adapters = []
            
            for line in stdout.split('\n'):
                if 'TAP' in line.upper():
                    parts = line.split()
                    if len(parts) >= 4:
                        adapters.append({
                            'name': parts[-1],
                            'state': parts[2],
                        })
            
            logger.info(f"Found {len(adapters)} TAP adapters")
            return adapters
        
        except Exception as e:
            logger.exception(f"Error finding TAP adapters: {e}")
            return []
    
    def create_or_find_adapter(self) -> bool:
        """
        Create or find existing TAP adapter.
        
        Returns:
            True if adapter available
        """
        try:
            # Find existing TAP adapters
            adapters = self.find_tap_adapters()
            
            if adapters:
                # Use first available TAP adapter
                self.adapter_name = adapters[0]['name']
                logger.info(f"Using existing TAP adapter: {self.adapter_name}")
                
                # Rename if needed
                if self.adapter_name != self.interface_name:
                    self._rename_adapter(self.adapter_name, self.interface_name)
                    self.adapter_name = self.interface_name
                
                self.is_created = True
                return True
            
            else:
                # No TAP adapter found
                logger.error("No TAP adapter found. Please install TAP-Windows6 driver.")
                logger.error("Download from: https://openvpn.net/community-downloads/")
                return False
        
        except Exception as e:
            logger.exception(f"Error creating/finding adapter: {e}")
            return False
    
    def _rename_adapter(self, old_name: str, new_name: str) -> None:
        """Rename network adapter."""
        try:
            command = f'netsh interface set interface name="{old_name}" newname="{new_name}"'
            self._run_command(command)
            logger.info(f"Renamed adapter: {old_name} -> {new_name}")
        
        except Exception as e:
            logger.warning(f"Could not rename adapter: {e}")
    
    def configure_ip(self, ip_address: str, netmask: str = "255.255.255.0") -> bool:
        """
        Configure IP address on TAP interface.
        
        Args:
            ip_address: IP address (e.g., "10.8.0.2")
            netmask: Subnet mask
        
        Returns:
            True if configured successfully
        """
        if not self.is_created:
            logger.error("TAP adapter not created")
            return False
        
        try:
            # Set IP address
            command = (
                f'netsh interface ip set address name="{self.adapter_name}" '
                f'static {ip_address} {netmask}'
            )
            
            self._run_command(command)
            
            logger.info(f"Configured IP: {ip_address}/{netmask}")
            
            # Wait for interface to be ready
            time.sleep(2)
            
            return True
        
        except Exception as e:
            logger.exception(f"Error configuring IP: {e}")
            return False
    
    def set_mtu(self, mtu: int = 1400) -> bool:
        """
        Set MTU on TAP interface.
        
        Args:
            mtu: MTU value
        
        Returns:
            True if set successfully
        """
        if not self.is_created:
            logger.error("TAP adapter not created")
            return False
        
        try:
            # Windows uses netsh to set MTU
            command = (
                f'netsh interface ipv4 set subinterface "{self.adapter_name}" '
                f'mtu={mtu} store=persistent'
            )
            
            self._run_command(command)
            
            logger.info(f"Set MTU: {mtu}")
            return True
        
        except Exception as e:
            logger.exception(f"Error setting MTU: {e}")
            return False
    
    def enable(self) -> bool:
        """
        Enable TAP interface.
        
        Returns:
            True if enabled successfully
        """
        if not self.is_created:
            logger.error("TAP adapter not created")
            return False
        
        try:
            command = f'netsh interface set interface "{self.adapter_name}" enabled'
            self._run_command(command)
            
            logger.info("TAP interface enabled")
            time.sleep(1)
            
            return True
        
        except Exception as e:
            logger.exception(f"Error enabling interface: {e}")
            return False
    
    def disable(self) -> bool:
        """
        Disable TAP interface.
        
        Returns:
            True if disabled successfully
        """
        if not self.is_created:
            return True
        
        try:
            command = f'netsh interface set interface "{self.adapter_name}" disabled'
            self._run_command(command, check=False)
            
            logger.info("TAP interface disabled")
            return True
        
        except Exception as e:
            logger.exception(f"Error disabling interface: {e}")
            return False
    
    def delete(self) -> bool:
        """
        Delete TAP interface (disable only, as Windows TAP adapters persist).
        
        Returns:
            True if deleted successfully
        """
        result = self.disable()
        
        if result:
            self.is_created = False
            self.adapter_name = None
        
        return result
    
    def get_status(self) -> dict:
        """Get interface status."""
        if not self.is_created:
            return {'status': 'not_created'}
        
        try:
            # Get interface info
            command = f'netsh interface show interface "{self.adapter_name}"'
            _, stdout, _ = self._run_command(command, check=False)
            
            status = {
                'name': self.adapter_name,
                'created': self.is_created,
                'details': stdout.strip()
            }
            
            return status
        
        except Exception as e:
            logger.exception(f"Error getting status: {e}")
            return {'status': 'error', 'error': str(e)}
