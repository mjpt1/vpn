"""
Connection Manager - Manages VPN connection lifecycle
Central orchestrator for tunnel, network configuration, and state management.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .tunnel_client import TunnelClient

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """VPN connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class ConnectionManager:
    """
    Central connection manager.
    
    Responsibilities:
    - Manage connection lifecycle (connect, disconnect, reconnect)
    - State machine management
    - Coordinate tunnel client and network managers
    - Provide status and statistics
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connection manager.
        
        Args:
            config: Configuration dictionary with:
                - server_host: Server hostname/IP
                - server_port: Server port
                - username: Username
                - password: Password
                - verify_cert: Verify certificate
                - cert_file: Certificate file path
                - auto_reconnect: Enable auto-reconnect
        """
        self.config = config
        
        # State
        self.state = ConnectionState.DISCONNECTED
        self.error_message: Optional[str] = None
        
        # Components
        self.tunnel_client: Optional[TunnelClient] = None
        
        # Callbacks
        self.on_state_change: Optional[Callable[[ConnectionState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_ip_assigned: Optional[Callable[[str], None]] = None
        
        # Statistics
        self.connect_time: Optional[datetime] = None
        self.disconnect_time: Optional[datetime] = None
        self.connection_attempts = 0
        self.successful_connections = 0
        
        logger.info("Connection manager initialized")
    
    def _set_state(self, state: ConnectionState, error: Optional[str] = None) -> None:
        """
        Set connection state.
        
        Args:
            state: New state
            error: Error message (if any)
        """
        old_state = self.state
        self.state = state
        self.error_message = error
        
        logger.info(f"State: {old_state.value} -> {state.value}")
        
        if error:
            logger.error(f"Error: {error}")
        
        # Notify callback
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception as e:
                logger.exception(f"Error in state change callback: {e}")
        
        # Notify error callback
        if error and self.on_error:
            try:
                self.on_error(error)
            except Exception as e:
                logger.exception(f"Error in error callback: {e}")
    
    async def connect(self) -> bool:
        """
        Connect to VPN server.
        
        Returns:
            True if connection successful
        """
        if self.state not in [ConnectionState.DISCONNECTED, ConnectionState.ERROR]:
            logger.warning(f"Cannot connect from state: {self.state.value}")
            return False
        
        try:
            self._set_state(ConnectionState.CONNECTING)
            self.connection_attempts += 1
            
            # Create tunnel client
            self.tunnel_client = TunnelClient(
                server_host=self.config.get('server_host', ''),
                server_port=self.config.get('server_port', 8443),
                username=self.config.get('username', ''),
                password=self.config.get('password', ''),
                verify_cert=self.config.get('verify_cert', False),
                cert_file=self.config.get('cert_file')
            )
            
            # Set callbacks
            self.tunnel_client.on_connected = self._on_tunnel_connected
            self.tunnel_client.on_disconnected = self._on_tunnel_disconnected
            self.tunnel_client.on_data_received = self._on_tunnel_data
            
            # Enable auto-reconnect if configured
            if self.config.get('auto_reconnect', True):
                self.tunnel_client.enable_auto_reconnect()
            
            # Connect
            self._set_state(ConnectionState.AUTHENTICATING)
            
            success = await self.tunnel_client.connect()
            
            if success:
                self.connect_time = datetime.utcnow()
                self.successful_connections += 1
                self._set_state(ConnectionState.CONNECTED)
                
                # Setup network (TAP, routes, DNS, etc.)
                # Will implement in next step
                await self._setup_network()
                
                logger.info("Connected successfully")
                return True
            else:
                self._set_state(ConnectionState.ERROR, "Connection failed")
                return False
        
        except Exception as e:
            logger.exception(f"Connection error: {e}")
            self._set_state(ConnectionState.ERROR, str(e))
            return False
    
    async def disconnect(self, reason: str = "User requested") -> None:
        """
        Disconnect from VPN.
        
        Args:
            reason: Disconnect reason
        """
        if self.state == ConnectionState.DISCONNECTED:
            logger.warning("Already disconnected")
            return
        
        try:
            self._set_state(ConnectionState.DISCONNECTING)
            
            # Cleanup network configuration
            await self._cleanup_network()
            
            # Disconnect tunnel
            if self.tunnel_client:
                await self.tunnel_client.disconnect(reason)
                self.tunnel_client = None
            
            self.disconnect_time = datetime.utcnow()
            self._set_state(ConnectionState.DISCONNECTED)
            
            logger.info("Disconnected successfully")
        
        except Exception as e:
            logger.exception(f"Disconnect error: {e}")
            self._set_state(ConnectionState.ERROR, str(e))
    
    async def _setup_network(self) -> None:
        """
        Setup network configuration.
        
        This will configure:
        - TAP interface
        - Routing table
        - DNS settings
        - Firewall rules (kill switch)
        """
        logger.info("Setting up network configuration...")
        
        try:
            # Get assigned IP
            if not self.tunnel_client or not self.tunnel_client.assigned_ip:
                raise Exception("No assigned IP")
            
            assigned_ip = self.tunnel_client.assigned_ip
            
            logger.info(f"Assigned IP: {assigned_ip}")
            
            # Notify callback
            if self.on_ip_assigned:
                try:
                    self.on_ip_assigned(assigned_ip)
                except Exception as e:
                    logger.exception(f"Error in IP assigned callback: {e}")
            
            # TODO: Implement network managers
            # - TAP interface creation and IP assignment
            # - Add routes to tunnel
            # - Configure DNS
            # - Enable kill switch
            
            logger.info("Network configuration completed")
        
        except Exception as e:
            logger.exception(f"Network setup error: {e}")
            raise
    
    async def _cleanup_network(self) -> None:
        """
        Cleanup network configuration.
        
        This will:
        - Remove routes
        - Restore DNS settings
        - Disable kill switch
        - Remove TAP interface
        """
        logger.info("Cleaning up network configuration...")
        
        try:
            # TODO: Implement network cleanup
            # - Disable kill switch
            # - Restore DNS
            # - Remove routes
            # - Delete TAP interface
            
            logger.info("Network cleanup completed")
        
        except Exception as e:
            logger.exception(f"Network cleanup error: {e}")
    
    def _on_tunnel_connected(self, assigned_ip: str) -> None:
        """Handle tunnel connection."""
        logger.info(f"Tunnel connected, IP: {assigned_ip}")
    
    def _on_tunnel_disconnected(self, reason: str) -> None:
        """Handle tunnel disconnection."""
        logger.warning(f"Tunnel disconnected: {reason}")
        
        # If we're in CONNECTED state, this is unexpected
        if self.state == ConnectionState.CONNECTED:
            self._set_state(ConnectionState.RECONNECTING)
    
    def _on_tunnel_data(self, packet: bytes) -> None:
        """
        Handle received packet from tunnel.
        
        Args:
            packet: IP packet
        """
        # TODO: Send packet to TAP interface
        pass
    
    async def send_packet(self, packet: bytes) -> bool:
        """
        Send packet through tunnel.
        
        Args:
            packet: IP packet from TAP interface
        
        Returns:
            True if sent successfully
        """
        if not self.tunnel_client or self.state != ConnectionState.CONNECTED:
            return False
        
        return await self.tunnel_client.send_packet(packet)
    
    def get_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.state
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.state == ConnectionState.CONNECTED
    
    def get_assigned_ip(self) -> Optional[str]:
        """Get assigned VPN IP."""
        if self.tunnel_client:
            return self.tunnel_client.assigned_ip
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics."""
        stats = {
            'state': self.state.value,
            'error': self.error_message,
            'connection_attempts': self.connection_attempts,
            'successful_connections': self.successful_connections,
        }
        
        if self.connect_time:
            stats['connect_time'] = self.connect_time.isoformat()
            
            if self.state == ConnectionState.CONNECTED:
                uptime = (datetime.utcnow() - self.connect_time).total_seconds()
                stats['uptime_seconds'] = int(uptime)
        
        if self.disconnect_time:
            stats['disconnect_time'] = self.disconnect_time.isoformat()
        
        # Tunnel statistics
        if self.tunnel_client:
            stats['tunnel'] = self.tunnel_client.get_statistics()
        
        return stats
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary."""
        if self.state == ConnectionState.CONNECTED:
            ip = self.get_assigned_ip()
            if self.connect_time:
                uptime = int((datetime.utcnow() - self.connect_time).total_seconds())
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                return f"متصل • IP: {ip} • مدت: {hours}h {minutes}m"
            return f"متصل • IP: {ip}"
        
        elif self.state == ConnectionState.CONNECTING:
            return "در حال اتصال..."
        
        elif self.state == ConnectionState.AUTHENTICATING:
            return "در حال احراز هویت..."
        
        elif self.state == ConnectionState.RECONNECTING:
            return "در حال اتصال مجدد..."
        
        elif self.state == ConnectionState.DISCONNECTING:
            return "در حال قطع اتصال..."
        
        elif self.state == ConnectionState.ERROR:
            return f"خطا: {self.error_message}"
        
        else:  # DISCONNECTED
            return "قطع شده"
