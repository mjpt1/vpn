"""
Firewall Manager - Windows Firewall kill switch
Blocks all traffic except VPN when connection drops.
"""

import subprocess
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class FirewallManager:
    """
    Windows Firewall manager for VPN kill switch.
    
    Features:
    - Enable/disable kill switch
    - Block all traffic except VPN server
    - Allow LAN traffic
    - Automatic cleanup on disconnect
    """
    
    RULE_PREFIX = "VPN_KillSwitch"
    
    def __init__(self):
        """Initialize firewall manager."""
        self.is_enabled = False
        self.vpn_server_ip: Optional[str] = None
        self.vpn_server_port: Optional[int] = None
        self.created_rules: List[str] = []
        
        logger.info("Firewall manager initialized")
    
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
    
    def _add_firewall_rule(
        self,
        name: str,
        direction: str,
        action: str,
        protocol: str = "any",
        remote_ip: Optional[str] = None,
        remote_port: Optional[int] = None,
        local_port: Optional[int] = None
    ) -> bool:
        """
        Add Windows Firewall rule.
        
        Args:
            name: Rule name
            direction: "in" or "out"
            action: "allow" or "block"
            protocol: "tcp", "udp", "any"
            remote_ip: Remote IP address
            remote_port: Remote port
            local_port: Local port
        
        Returns:
            True if added successfully
        """
        try:
            rule_name = f"{self.RULE_PREFIX}_{name}"
            
            command = (
                f'netsh advfirewall firewall add rule '
                f'name="{rule_name}" '
                f'dir={direction} '
                f'action={action} '
                f'protocol={protocol}'
            )
            
            if remote_ip:
                command += f' remoteip={remote_ip}'
            
            if remote_port:
                command += f' remoteport={remote_port}'
            
            if local_port:
                command += f' localport={local_port}'
            
            self._run_command(command)
            
            self.created_rules.append(rule_name)
            
            logger.debug(f"Added firewall rule: {rule_name}")
            return True
        
        except Exception as e:
            logger.exception(f"Error adding firewall rule: {e}")
            return False
    
    def _delete_firewall_rule(self, name: str) -> bool:
        """Delete firewall rule."""
        try:
            rule_name = f"{self.RULE_PREFIX}_{name}"
            
            command = f'netsh advfirewall firewall delete rule name="{rule_name}"'
            self._run_command(command, check=False)
            
            if rule_name in self.created_rules:
                self.created_rules.remove(rule_name)
            
            logger.debug(f"Deleted firewall rule: {rule_name}")
            return True
        
        except Exception as e:
            logger.exception(f"Error deleting firewall rule: {e}")
            return False
    
    def enable_kill_switch(
        self,
        vpn_server_ip: str,
        vpn_server_port: int = 8443,
        allow_lan: bool = True
    ) -> bool:
        """
        Enable VPN kill switch.
        
        Blocks all traffic except:
        - VPN server connection
        - LAN traffic (optional)
        - Loopback
        
        Args:
            vpn_server_ip: VPN server IP
            vpn_server_port: VPN server port
            allow_lan: Allow LAN traffic
        
        Returns:
            True if enabled successfully
        """
        if self.is_enabled:
            logger.warning("Kill switch already enabled")
            return True
        
        try:
            logger.info("Enabling VPN kill switch...")
            
            self.vpn_server_ip = vpn_server_ip
            self.vpn_server_port = vpn_server_port
            
            # 1. Allow loopback
            self._add_firewall_rule(
                "Allow_Loopback_Out",
                "out",
                "allow",
                remote_ip="127.0.0.1"
            )
            
            self._add_firewall_rule(
                "Allow_Loopback_In",
                "in",
                "allow",
                remote_ip="127.0.0.1"
            )
            
            # 2. Allow VPN server connection
            self._add_firewall_rule(
                "Allow_VPN_Server_Out",
                "out",
                "allow",
                protocol="tcp",
                remote_ip=vpn_server_ip,
                remote_port=vpn_server_port
            )
            
            self._add_firewall_rule(
                "Allow_VPN_Server_In",
                "in",
                "allow",
                protocol="tcp",
                remote_ip=vpn_server_ip
            )
            
            # 3. Allow LAN traffic (optional)
            if allow_lan:
                # Allow private IP ranges
                for subnet in ["192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8"]:
                    self._add_firewall_rule(
                        f"Allow_LAN_{subnet.replace('/', '_')}_Out",
                        "out",
                        "allow",
                        remote_ip=subnet
                    )
                    
                    self._add_firewall_rule(
                        f"Allow_LAN_{subnet.replace('/', '_')}_In",
                        "in",
                        "allow",
                        remote_ip=subnet
                    )
            
            # 4. Block all other outbound traffic
            self._add_firewall_rule(
                "Block_All_Out",
                "out",
                "block"
            )
            
            # 5. Block all other inbound traffic
            self._add_firewall_rule(
                "Block_All_In",
                "in",
                "block"
            )
            
            self.is_enabled = True
            logger.info("VPN kill switch enabled")
            return True
        
        except Exception as e:
            logger.exception(f"Error enabling kill switch: {e}")
            # Cleanup on error
            self.disable_kill_switch()
            return False
    
    def disable_kill_switch(self) -> bool:
        """
        Disable VPN kill switch.
        
        Returns:
            True if disabled successfully
        """
        if not self.is_enabled and not self.created_rules:
            return True
        
        try:
            logger.info("Disabling VPN kill switch...")
            
            # Delete all created rules
            for rule_name in list(self.created_rules):
                # Extract short name
                short_name = rule_name.replace(f"{self.RULE_PREFIX}_", "")
                self._delete_firewall_rule(short_name)
            
            self.is_enabled = False
            self.created_rules.clear()
            
            logger.info("VPN kill switch disabled")
            return True
        
        except Exception as e:
            logger.exception(f"Error disabling kill switch: {e}")
            return False
    
    def cleanup_all_rules(self) -> None:
        """Remove all VPN kill switch rules."""
        try:
            # Delete all rules with our prefix
            command = f'netsh advfirewall firewall delete rule name="{self.RULE_PREFIX}_*"'
            self._run_command(command, check=False)
            
            self.created_rules.clear()
            self.is_enabled = False
            
            logger.info("All VPN firewall rules removed")
        
        except Exception as e:
            logger.exception(f"Error cleaning up rules: {e}")
    
    def get_status(self) -> dict:
        """Get kill switch status."""
        return {
            'enabled': self.is_enabled,
            'vpn_server': f"{self.vpn_server_ip}:{self.vpn_server_port}" if self.vpn_server_ip else None,
            'active_rules': len(self.created_rules),
            'rules': self.created_rules
        }
