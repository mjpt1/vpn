"""
DNS Manager - Windows DNS configuration management
Handles DNS server configuration for VPN tunnel.
"""

import subprocess
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class DNSManager:
    """
    Windows DNS manager.
    
    Features:
    - Set/restore DNS servers
    - DNS leak prevention
    - Backup original DNS configuration
    """
    
    def __init__(self):
        """Initialize DNS manager."""
        self.original_dns: dict = {}  # interface -> [dns1, dns2, ...]
        
        logger.info("DNS manager initialized")
    
    def _run_command(self, command: str, check: bool = True) -> Tuple[int, str, str]:
        """Run shell command."""
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
        
        except Exception as e:
            logger.exception(f"Command error: {e}")
            raise
    
    def get_dns_servers(self, interface: str) -> List[str]:
        """
        Get current DNS servers for interface.
        
        Args:
            interface: Interface name
        
        Returns:
            List of DNS server IPs
        """
        try:
            command = f'netsh interface ip show dns "{interface}"'
            _, stdout, _ = self._run_command(command, check=False)
            
            dns_servers = []
            
            for line in stdout.split('\n'):
                if 'DNS Servers' in line or 'Statically Configured DNS Servers' in line:
                    # Extract IP from line
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip()
                        if ip and ip not in ['None', '']:
                            dns_servers.append(ip)
            
            return dns_servers
        
        except Exception as e:
            logger.exception(f"Error getting DNS servers: {e}")
            return []
    
    def backup_dns_config(self, interfaces: List[str]) -> bool:
        """
        Backup DNS configuration for interfaces.
        
        Args:
            interfaces: List of interface names
        
        Returns:
            True if backed up successfully
        """
        try:
            for interface in interfaces:
                dns_servers = self.get_dns_servers(interface)
                
                if dns_servers:
                    self.original_dns[interface] = dns_servers
                    logger.info(f"Backed up DNS for {interface}: {dns_servers}")
            
            return True
        
        except Exception as e:
            logger.exception(f"Error backing up DNS: {e}")
            return False
    
    def set_dns_servers(
        self,
        interface: str,
        primary_dns: str,
        secondary_dns: Optional[str] = None
    ) -> bool:
        """
        Set DNS servers for interface.
        
        Args:
            interface: Interface name
            primary_dns: Primary DNS server IP
            secondary_dns: Secondary DNS server IP (optional)
        
        Returns:
            True if set successfully
        """
        try:
            # Set primary DNS
            command = (
                f'netsh interface ip set dns name="{interface}" '
                f'static {primary_dns} primary'
            )
            
            self._run_command(command)
            
            logger.info(f"Set primary DNS on {interface}: {primary_dns}")
            
            # Set secondary DNS if provided
            if secondary_dns:
                command = (
                    f'netsh interface ip add dns name="{interface}" '
                    f'{secondary_dns} index=2'
                )
                
                self._run_command(command, check=False)
                logger.info(f"Set secondary DNS on {interface}: {secondary_dns}")
            
            return True
        
        except Exception as e:
            logger.exception(f"Error setting DNS: {e}")
            return False
    
    def set_vpn_dns(self, interface: str, dns_servers: List[str] = None) -> bool:
        """
        Set VPN DNS servers.
        
        Args:
            interface: VPN interface name
            dns_servers: List of DNS servers (default: Google DNS)
        
        Returns:
            True if set successfully
        """
        if not dns_servers:
            # Default to Google DNS
            dns_servers = ['8.8.8.8', '8.8.4.4']
        
        primary = dns_servers[0] if len(dns_servers) > 0 else '8.8.8.8'
        secondary = dns_servers[1] if len(dns_servers) > 1 else None
        
        return self.set_dns_servers(interface, primary, secondary)
    
    def restore_dns_config(self) -> bool:
        """
        Restore original DNS configuration.
        
        Returns:
            True if restored successfully
        """
        if not self.original_dns:
            logger.warning("No DNS configuration to restore")
            return True
        
        try:
            for interface, dns_servers in self.original_dns.items():
                logger.info(f"Restoring DNS for {interface}: {dns_servers}")
                
                if dns_servers:
                    # Set to DHCP (auto)
                    command = f'netsh interface ip set dns name="{interface}" dhcp'
                    self._run_command(command, check=False)
                    
                    # Or set static
                    # primary = dns_servers[0]
                    # secondary = dns_servers[1] if len(dns_servers) > 1 else None
                    # self.set_dns_servers(interface, primary, secondary)
            
            self.original_dns.clear()
            logger.info("DNS configuration restored")
            return True
        
        except Exception as e:
            logger.exception(f"Error restoring DNS: {e}")
            return False
    
    def flush_dns_cache(self) -> bool:
        """
        Flush DNS cache.
        
        Returns:
            True if flushed successfully
        """
        try:
            self._run_command('ipconfig /flushdns')
            logger.info("DNS cache flushed")
            return True
        
        except Exception as e:
            logger.exception(f"Error flushing DNS cache: {e}")
            return False
    
    def get_all_interfaces(self) -> List[str]:
        """
        Get all network interfaces.
        
        Returns:
            List of interface names
        """
        try:
            _, stdout, _ = self._run_command('netsh interface show interface', check=False)
            
            interfaces = []
            
            for line in stdout.split('\n'):
                if 'Connected' in line or 'Enabled' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interface_name = ' '.join(parts[3:])
                        interfaces.append(interface_name.strip())
            
            return interfaces
        
        except Exception as e:
            logger.exception(f"Error getting interfaces: {e}")
            return []
