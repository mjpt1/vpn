"""
VPN Client - Main entry point (No GUI)
Command-line VPN client for testing and automation.
"""

import asyncio
import signal
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from client.core.connection_manager import ConnectionManager, ConnectionState
from client.utils.config_loader import ClientConfig
from client.utils.logger import setup_logger

import logging

logger = None


class VPNClient:
    """
    Main VPN client application.
    
    No GUI - command-line interface only.
    """
    
    def __init__(self, config_file: str = "client_config.yaml"):
        """
        Initialize VPN client.
        
        Args:
            config_file: Configuration file path
        """
        self.config = ClientConfig(config_file)
        self.connection_manager: ConnectionManager = None
        self.is_running = False
        
        # Setup logger
        global logger
        logger = setup_logger(
            level=self.config.get('logging.level', 'INFO'),
            log_file=self.config.get('logging.file'),
            console=self.config.get('logging.console', True)
        )
        
        logger.info("VPN Client initialized")
    
    async def start(self) -> None:
        """Start VPN client."""
        logger.info("Starting VPN client...")
        
        # Validate configuration
        if not self._validate_config():
            logger.error("Invalid configuration")
            return
        
        # Create connection manager
        self.connection_manager = ConnectionManager(self.config.to_dict())
        
        # Set callbacks
        self.connection_manager.on_state_change = self._on_state_change
        self.connection_manager.on_error = self._on_error
        self.connection_manager.on_ip_assigned = self._on_ip_assigned
        
        # Connect
        success = await self.connection_manager.connect()
        
        if success:
            logger.info("✓ Connected to VPN successfully")
            self.is_running = True
            
            # Keep running
            await self._main_loop()
        else:
            logger.error("✗ Failed to connect to VPN")
    
    def _validate_config(self) -> bool:
        """Validate configuration."""
        server_host = self.config.get('server.host')
        username = self.config.get('auth.username')
        password = self.config.get('auth.password')
        
        if not server_host:
            logger.error("Server host not configured")
            return False
        
        if not username or not password:
            logger.error("Username/password not configured")
            return False
        
        return True
    
    async def _main_loop(self) -> None:
        """Main loop to keep client running."""
        try:
            logger.info("VPN client running. Press Ctrl+C to stop.")
            
            while self.is_running:
                await asyncio.sleep(5)
                
                # Print statistics every 30 seconds
                if hasattr(self, '_stats_counter'):
                    self._stats_counter += 5
                else:
                    self._stats_counter = 5
                
                if self._stats_counter >= 30:
                    self._print_statistics()
                    self._stats_counter = 0
        
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
    
    def _on_state_change(self, state: ConnectionState) -> None:
        """Handle state changes."""
        logger.info(f"State changed: {state.value}")
        
        if state == ConnectionState.DISCONNECTED:
            self.is_running = False
    
    def _on_error(self, error: str) -> None:
        """Handle errors."""
        logger.error(f"Error: {error}")
    
    def _on_ip_assigned(self, ip: str) -> None:
        """Handle IP assignment."""
        logger.info(f"✓ Assigned VPN IP: {ip}")
    
    def _print_statistics(self) -> None:
        """Print connection statistics."""
        if not self.connection_manager:
            return
        
        stats = self.connection_manager.get_statistics()
        
        logger.info("=== Statistics ===")
        logger.info(f"State: {stats.get('state')}")
        
        if 'uptime_seconds' in stats:
            uptime = stats['uptime_seconds']
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            logger.info(f"Uptime: {hours}h {minutes}m")
        
        if 'tunnel' in stats:
            tunnel = stats['tunnel']
            logger.info(f"Bytes sent: {tunnel.get('bytes_sent', 0)}")
            logger.info(f"Bytes received: {tunnel.get('bytes_received', 0)}")
            logger.info(f"Packets sent: {tunnel.get('packets_sent', 0)}")
            logger.info(f"Packets received: {tunnel.get('packets_received', 0)}")
        
        logger.info("==================")
    
    async def stop(self) -> None:
        """Stop VPN client."""
        logger.info("Stopping VPN client...")
        
        self.is_running = False
        
        if self.connection_manager:
            await self.connection_manager.disconnect("Client shutdown")
        
        logger.info("VPN client stopped")


async def main_async(args: argparse.Namespace) -> None:
    """Async main function."""
    client = VPNClient(args.config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(client.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start client
    await client.start()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="VPN Client (No GUI)")
    
    parser.add_argument(
        '--config',
        default='client_config.yaml',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create default configuration file'
    )
    
    args = parser.parse_args()
    
    # Create default config if requested
    if args.create_config:
        config = ClientConfig(args.config)
        if config.save():
            print(f"✓ Configuration file created: {args.config}")
            print("\nPlease edit the configuration file and set:")
            print("  - server.host: Your VPN server IP/hostname")
            print("  - auth.username: Your username")
            print("  - auth.password: Your password")
        else:
            print(f"✗ Failed to create configuration file")
        return
    
    # Check if config exists
    if not Path(args.config).exists():
        print(f"✗ Configuration file not found: {args.config}")
        print(f"\nCreate default configuration:")
        print(f"  python client_main.py --create-config")
        sys.exit(1)
    
    # Run client
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
