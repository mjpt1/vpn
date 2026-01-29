"""
Routing Manager - Windows routing table management
Handles route addition/removal for VPN traffic.
"""

import subprocess
import logging
from typing import Optional, List, Tuple
import ipaddress

logger = logging.getLogger(__name__)


class RoutingManager:
    """
    Windows routing table manager.
    
    Features:
    - Add/remove routes
    - Default gateway backup/restore
    - Split tunneling support
    """
    
    def __init__(self):
        """Initialize routing manager."""
        self.original_gateway: Optional[str] = None
        self.original_interface: Optional[str] = None
        self.added_routes: List[str] = []
        
        logger.info("Routing manager initialized")
    
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
    
    def get_default_gateway(self) -> Optional[Tuple[str, str]]:
        """
        Get current default gateway.
        
        Returns:
            (gateway_ip, interface_name) or None
        """
        try:
            # Use route print to get default gateway
            _, stdout, _ = self._run_command('route print 0.0.0.0', check=False)
            
            for line in stdout.split('\n'):
                if '0.0.0.0' in line and '0.0.0.0' in line.split()[0]:
                    parts = line.split()
                    if len(parts) >= 4:
                        gateway = parts[2]
                        # Interface is usually in the last column
                        return gateway, None
            
            logger.warning("Could not find default gateway")
            return None
        
        except Exception as e:
            logger.exception(f"Error getting default gateway: {e}")
            return None
    
    def backup_default_gateway(self) -> bool:
        """
        Backup current default gateway.
        
        Returns:
            True if backed up successfully
        """
        try:
            result = self.get_default_gateway()
            
            if result:
                self.original_gateway, self.original_interface = result
                logger.info(f"Backed up default gateway: {self.original_gateway}")
                return True
            
            return False
        
        except Exception as e:
            logger.exception(f"Error backing up gateway: {e}")
            return False
    
    def add_route(
        self,
        destination: str,
        gateway: str,
        interface: Optional[str] = None,
        metric: int = 1
    ) -> bool:
        """
        Add route to routing table.
        
        Args:
            destination: Destination network (e.g., "0.0.0.0" or "192.168.1.0/24")
            gateway: Gateway IP
            interface: Interface name (optional)
            metric: Route metric
        
        Returns:
            True if added successfully
        """
        try:
            # Parse destination
            if '/' in destination:
                network = ipaddress.ip_network(destination, strict=False)
                dest_ip = str(network.network_address)
                netmask = str(network.netmask)
            else:
                dest_ip = destination
                netmask = "255.255.255.255" if destination != "0.0.0.0" else "0.0.0.0"
            
            # Build command
            command = f'route add {dest_ip} mask {netmask} {gateway} metric {metric}'
            
            if interface:
                command += f' if "{interface}"'
            
            self._run_command(command)
            
            # Track added route
            self.added_routes.append(dest_ip)
            
            logger.info(f"Added route: {dest_ip}/{netmask} via {gateway}")
            return True
        
        except Exception as e:
            logger.exception(f"Error adding route: {e}")
            return False
    
    def delete_route(self, destination: str) -> bool:
        """
        Delete route from routing table.
        
        Args:
            destination: Destination network
        
        Returns:
            True if deleted successfully
        """
        try:
            # Parse destination
            if '/' in destination:
                network = ipaddress.ip_network(destination, strict=False)
                dest_ip = str(network.network_address)
            else:
                dest_ip = destination
            
            command = f'route delete {dest_ip}'
            self._run_command(command, check=False)
            
            # Remove from tracked routes
            if dest_ip in self.added_routes:
                self.added_routes.remove(dest_ip)
            
            logger.info(f"Deleted route: {dest_ip}")
            return True
        
        except Exception as e:
            logger.exception(f"Error deleting route: {e}")
            return False
    
    def set_default_gateway(self, gateway: str, interface: Optional[str] = None) -> bool:
        """
        Set default gateway (0.0.0.0/0).
        
        Args:
            gateway: Gateway IP
            interface: Interface name
        
        Returns:
            True if set successfully
        """
        try:
            # First backup current gateway
            if not self.original_gateway:
                self.backup_default_gateway()
            
            # Delete old default route
            self._run_command('route delete 0.0.0.0', check=False)
            
            # Add new default route
            return self.add_route('0.0.0.0', gateway, interface, metric=1)
        
        except Exception as e:
            logger.exception(f"Error setting default gateway: {e}")
            return False
    
    def restore_default_gateway(self) -> bool:
        """
        Restore original default gateway.
        
        Returns:
            True if restored successfully
        """
        if not self.original_gateway:
            logger.warning("No original gateway to restore")
            return True
        
        try:
            # Delete current default route
            self._run_command('route delete 0.0.0.0', check=False)
            
            # Restore original
            success = self.add_route(
                '0.0.0.0',
                self.original_gateway,
                self.original_interface,
                metric=1
            )
            
            if success:
                logger.info(f"Restored default gateway: {self.original_gateway}")
                self.original_gateway = None
                self.original_interface = None
            
            return success
        
        except Exception as e:
            logger.exception(f"Error restoring gateway: {e}")
            return False
    
    def cleanup_all_routes(self) -> None:
        """Remove all routes added by VPN."""
        logger.info("Cleaning up routes...")
        
        # Delete all tracked routes
        for route in list(self.added_routes):
            self.delete_route(route)
        
        # Restore default gateway
        self.restore_default_gateway()
        
        logger.info("Route cleanup completed")
    
    def get_routing_table(self) -> str:
        """
        Get current routing table.
        
        Returns:
            Routing table as string
        """
        try:
            _, stdout, _ = self._run_command('route print', check=False)
            return stdout
        
        except Exception as e:
            logger.exception(f"Error getting routing table: {e}")
            return ""
