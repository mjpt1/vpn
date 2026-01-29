"""
Tunnel Server - Main VPN server logic
Handles client connections, authentication, and tunnel management.
"""

import asyncio
import logging
import ssl
from typing import Optional
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession

from ..database.models import Base
from ..core.auth_handler import AuthHandler
from ..core.session_manager import SessionManager, ClientSession
from ..core.encryption import EncryptionHandler

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from shared.protocol import MessageType, KEEPALIVE_INTERVAL
from shared.message_format import MessageFormat, PacketFramer
from shared.exceptions import AuthenticationError, ProtocolError

logger = logging.getLogger(__name__)


class TunnelServer:
    """
    Main VPN tunnel server.
    
    Handles:
    - Client connections (reverse connection)
    - TLS encryption
    - Authentication
    - Tunnel data forwarding
    - Keepalive mechanism
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8443,
        db_path: str = "vpn_server.db",
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None
    ):
        """
        Initialize tunnel server.
        
        Args:
            host: Bind address
            port: Bind port
            db_path: SQLite database path
            cert_file: TLS certificate file path
            key_file: TLS private key file path
        """
        self.host = host
        self.port = port
        
        # Database setup
        self.db_engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.db_engine)
        self.DBSession = sessionmaker(bind=self.db_engine)
        
        # Components
        self.session_manager = SessionManager()
        
        # TLS configuration
        self.cert_file = cert_file
        self.key_file = key_file
        self.ssl_context = None
        
        # Server state
        self.running = False
        self.server: Optional[asyncio.Server] = None
        
        # Background tasks
        self.background_tasks: list[asyncio.Task] = []
        
        logger.info(f"TunnelServer initialized: {host}:{port}")
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for TLS."""
        if not self.cert_file or not self.key_file:
            logger.warning("No TLS certificate provided, running without TLS")
            return None
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(self.cert_file, self.key_file)
        
        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        # context.set_ciphers('TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384')
        
        logger.info("TLS context created")
        return context
    
    async def start(self) -> None:
        """Start the server."""
        if self.running:
            logger.warning("Server already running")
            return
        
        # Create SSL context
        self.ssl_context = self._create_ssl_context()
        
        # Start TCP server
        self.server = await asyncio.start_server(
            self._handle_client_connection,
            self.host,
            self.port,
            ssl=self.ssl_context
        )
        
        self.running = True
        
        # Start background tasks
        self.background_tasks.append(
            asyncio.create_task(self._cleanup_task())
        )
        self.background_tasks.append(
            asyncio.create_task(self._statistics_task())
        )
        
        addr = self.server.sockets[0].getsockname()
        logger.info(f"Server started on {addr}")
        logger.info("Waiting for connections...")
    
    async def stop(self) -> None:
        """Stop the server."""
        if not self.running:
            return
        
        logger.info("Stopping server...")
        self.running = False
        
        # Stop accepting new connections
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Disconnect all clients
        sessions = self.session_manager.get_all_sessions()
        for session in sessions:
            await self.session_manager.remove_session(session.session_token)
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("Server stopped")
    
    async def _handle_client_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle new client connection.
        
        Args:
            reader: Stream reader
            writer: Stream writer
        """
        client_addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {client_addr}")
        
        session: Optional[ClientSession] = None
        db_session: Optional[DBSession] = None
        
        try:
            # Create database session
            db_session = self.DBSession()
            auth_handler = AuthHandler(db_session)
            
            # Authenticate client
            session_token = await self._authenticate_client(
                reader, writer, auth_handler, client_addr[0]
            )
            
            if not session_token:
                logger.warning(f"Authentication failed for {client_addr}")
                return
            
            # Get session from database
            session_model = auth_handler.session_repo.get_by_token(session_token)
            if not session_model:
                logger.error(f"Session not found after authentication: {session_token}")
                return
            
            # Create client session
            encryption_key = bytes.fromhex(session_model.encryption_key)
            session = ClientSession(
                session_model=session_model,
                reader=reader,
                writer=writer,
                encryption_key=encryption_key
            )
            
            await self.session_manager.add_session(session)
            
            logger.info(
                f"Client authenticated: {session_model.assigned_ip}, "
                f"token={session_token[:16]}..."
            )
            
            # Handle tunnel data
            await self._handle_tunnel_data(session, db_session)
        
        except Exception as e:
            logger.exception(f"Error handling client: {e}")
        
        finally:
            # Cleanup
            if session:
                await self.session_manager.remove_session(session.session_token)
                
                # Update database
                if db_session:
                    auth_handler = AuthHandler(db_session)
                    auth_handler.terminate_session(
                        session.session_token,
                        "Connection closed"
                    )
            
            if db_session:
                db_session.close()
            
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            
            logger.info(f"Client disconnected: {client_addr}")
    
    async def _authenticate_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        auth_handler: AuthHandler,
        client_ip: str
    ) -> Optional[str]:
        """
        Authenticate client.
        
        Returns:
            Session token if successful, None otherwise
        """
        try:
            # Read authentication request
            data = await asyncio.wait_for(reader.read(4096), timeout=10)
            if not data:
                return None
            
            message_type, payload = MessageFormat.unpack(data)
            
            if message_type != MessageType.AUTH_REQUEST:
                logger.warning(f"Expected AUTH_REQUEST, got {message_type}")
                return None
            
            # Extract credentials
            username = payload.get('username')
            password_hash = payload.get('password_hash')
            client_version = payload.get('client_version', 'unknown')
            
            if not username or not password_hash:
                raise AuthenticationError("Missing credentials")
            
            # Authenticate (password_hash is pre-hashed on client)
            # For now, we'll use it as-is (in production, verify the hash)
            session_model, encryption_key_hex = auth_handler.authenticate_user(
                username=username,
                password=password_hash,  # This should be verified properly
                client_ip=client_ip,
                client_version=client_version
            )
            
            # Send success response
            response = MessageFormat.create_auth_response(
                session_token=session_model.session_token,
                assigned_ip=session_model.assigned_ip
            )
            
            writer.write(response)
            await writer.drain()
            
            return session_model.session_token
        
        except AuthenticationError as e:
            # Send failure response
            response = MessageFormat.create_auth_failure(
                error_code=e.error_code,
                error_message=str(e)
            )
            writer.write(response)
            await writer.drain()
            return None
        
        except Exception as e:
            logger.exception(f"Authentication error: {e}")
            return None
    
    async def _handle_tunnel_data(
        self,
        session: ClientSession,
        db_session: DBSession
    ) -> None:
        """
        Handle tunnel data forwarding.
        
        Args:
            session: Client session
            db_session: Database session
        """
        logger.info(f"Tunnel established for {session.assigned_ip}")
        
        try:
            while session.is_active:
                # Read encrypted packet
                data = await session.recv_data(4096)
                if not data:
                    break
                
                session.read_buffer.append(data)
                
                # Process all complete frames in buffer
                while True:
                    frame = session.read_buffer.extract_frame()
                    if not frame:
                        break
                    
                    try:
                        # Decrypt packet
                        plaintext = session.encryption.decrypt(frame)
                        
                        # Process packet (here we would write to TUN interface)
                        # For now, just log it
                        processed = session.packet_processor.process_inbound(plaintext)
                        
                        if processed:
                            # In real implementation:
                            # - Write to TUN interface
                            # - Forward to internet
                            # - Receive response
                            # - Encrypt and send back
                            
                            # For demo, echo back (encrypted)
                            encrypted_response = session.encryption.encrypt(processed)
                            framed_response = PacketFramer.frame(encrypted_response)
                            await session.send_data(framed_response)
                            
                            # Update statistics
                            session_repo = auth_handler.session_repo
                            session_repo.update_traffic(
                                session.session_id,
                                len(framed_response),
                                len(frame)
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing packet: {e}")
                        continue
        
        except Exception as e:
            logger.exception(f"Tunnel error: {e}")
        
        finally:
            logger.info(f"Tunnel closed for {session.assigned_ip}")
    
    async def _cleanup_task(self) -> None:
        """Background task to cleanup expired sessions."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Cleanup inactive sessions
                count = await self.session_manager.cleanup_inactive_sessions(
                    timeout_seconds=300  # 5 minutes
                )
                
                # Cleanup database sessions
                db_session = self.DBSession()
                try:
                    auth_handler = AuthHandler(db_session)
                    db_count = auth_handler.cleanup_expired_sessions()
                    
                    if count > 0 or db_count > 0:
                        logger.info(
                            f"Cleanup: {count} memory sessions, {db_count} DB sessions"
                        )
                finally:
                    db_session.close()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Cleanup task error: {e}")
    
    async def _statistics_task(self) -> None:
        """Background task to log statistics."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                stats = self.session_manager.get_statistics()
                logger.info(f"Statistics: {stats}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Statistics task error: {e}")


# Fix the undefined auth_handler reference
async def _handle_tunnel_data_fixed(
    self,
    session: ClientSession,
    db_session: DBSession
) -> None:
    """Fixed version of _handle_tunnel_data with proper auth_handler scope."""
    from ..core.auth_handler import AuthHandler
    
    logger.info(f"Tunnel established for {session.assigned_ip}")
    auth_handler = AuthHandler(db_session)
    
    try:
        while session.is_active:
            data = await session.recv_data(4096)
            if not data:
                break
            
            session.read_buffer.append(data)
            
            while True:
                frame = session.read_buffer.extract_frame()
                if not frame:
                    break
                
                try:
                    plaintext = session.encryption.decrypt(frame)
                    processed = session.packet_processor.process_inbound(plaintext)
                    
                    if processed:
                        encrypted_response = session.encryption.encrypt(processed)
                        framed_response = PacketFramer.frame(encrypted_response)
                        await session.send_data(framed_response)
                        
                        auth_handler.session_repo.update_traffic(
                            session.session_id,
                            len(framed_response),
                            len(frame)
                        )
                
                except Exception as e:
                    logger.error(f"Error processing packet: {e}")
                    continue
    
    except Exception as e:
        logger.exception(f"Tunnel error: {e}")
    
    finally:
        logger.info(f"Tunnel closed for {session.assigned_ip}")

# Monkey-patch the fixed version
TunnelServer._handle_tunnel_data = _handle_tunnel_data_fixed
