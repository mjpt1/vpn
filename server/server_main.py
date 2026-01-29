"""
VPN Server Main Entry Point
Starts the tunnel server and handles graceful shutdown.
"""

import asyncio
import signal
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.core.tunnel_server import TunnelServer
from server.utils.logger import setup_logger
from server.utils.config_loader import ConfigLoader
from server.database.user_repo import UserRepository
from server.database.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import logging

logger = None  # Will be initialized after config load


def create_default_user(db_path: str) -> None:
    """
    Create default admin user if database is empty.
    
    Args:
        db_path: Database file path
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    try:
        user_repo = UserRepository(db_session)
        
        # Check if any users exist
        users = user_repo.list_users()
        if not users:
            # Create default admin user
            user_repo.create_user(
                username="admin",
                password="admin123",  # CHANGE THIS IN PRODUCTION!
                email="admin@localhost",
                is_admin=True,
                max_sessions=5
            )
            logger.info("Default admin user created (username: admin, password: admin123)")
            logger.warning("SECURITY: Change default password immediately!")
    
    finally:
        db_session.close()


async def main_async(config: ConfigLoader) -> None:
    """
    Main async function.
    
    Args:
        config: Configuration loader
    """
    # Create server
    server = TunnelServer(
        host=config.get('server.host', '0.0.0.0'),
        port=config.get('server.port', 8443),
        db_path=config.get('database.path', 'vpn_server.db'),
        cert_file=config.get('tls.cert_file'),
        key_file=config.get('tls.key_file'),
    )
    
    # Setup signal handlers for graceful shutdown
    # Note: Windows doesn't support add_signal_handler, use signal.signal instead
    import platform
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(server.stop())
    
    if platform.system() == 'Windows':
        # Windows signal handling
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        # Unix signal handling
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s, None))
    
    try:
        # Start server
        await server.start()
        
        # Keep running
        while server.running:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    
    except Exception as e:
        logger.exception(f"Server error: {e}")
    
    finally:
        await server.stop()


def main() -> None:
    """Main entry point."""
    global logger
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Iran VPN Gateway Server')
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    parser.add_argument(
        '--create-user',
        action='store_true',
        help='Create default admin user and exit'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Override log level from config'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = ConfigLoader(args.config)
    
    # Setup logging
    log_level = args.log_level or config.get('logging.level', 'INFO')
    logger = setup_logger(
        name='vpn_server',
        log_level=log_level,
        log_file=config.get('logging.file'),
        json_format=config.get('logging.json_format', False)
    )
    
    logger.info("=" * 60)
    logger.info("Iran VPN Gateway Server v1.0.0")
    logger.info("=" * 60)
    
    # Create database and default user if needed
    db_path = config.get('database.path', 'vpn_server.db')
    create_default_user(db_path)
    
    # If --create-user flag, exit after creating user
    if args.create_user:
        logger.info("Default user creation complete, exiting")
        sys.exit(0)
    
    # Display configuration
    logger.info(f"Configuration:")
    logger.info(f"  Host: {config.get('server.host')}")
    logger.info(f"  Port: {config.get('server.port')}")
    logger.info(f"  Database: {db_path}")
    logger.info(f"  TLS Cert: {config.get('tls.cert_file', 'Not configured')}")
    logger.info(f"  Max Clients: {config.get('server.max_clients')}")
    
    # Run server
    try:
        asyncio.run(main_async(config))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    
    logger.info("Server shutdown complete")


if __name__ == '__main__':
    main()
