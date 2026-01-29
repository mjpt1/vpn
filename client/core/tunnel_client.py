"""
Tunnel Client - Main VPN client logic
Handles secure connection, authentication, and data forwarding.
"""

import asyncio
import logging
import ssl
from typing import Optional, Callable
from pathlib import Path
import hashlib

from .encryption import EncryptionHandler
from .packet_processor import PacketProcessor
from .auto_reconnect import AutoReconnect, ReconnectState

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared.protocol import MessageType, CONNECTION_TIMEOUT, KEEPALIVE_INTERVAL
from shared.message_format import MessageFormat, PacketFramer, StreamBuffer
from shared.exceptions import (
    AuthenticationError,
    NetworkError,
    ConnectionLostError,
    TunnelError
)

logger = logging.getLogger(__name__)


class TunnelClient:
    """
    VPN tunnel client.
    
    Features:
    - Secure TLS connection to server
    - Authentication with username/password
    - Encrypted tunnel data forwarding
    - Keepalive mechanism
    - Auto-reconnect support
    """
    
    def __init__(
        self,
        server_host: str,
        server_port: int = 8443,
        username: str = "",
        password: str = "",
        verify_cert: bool = False,
        cert_file: Optional[str] = None
    ):
        """
        Initialize tunnel client.
        
        Args:
            server_host: Server hostname or IP
            server_port: Server port
            username: Username for authentication
            password: Password
            verify_cert: Verify server certificate
            cert_file: Path to CA certificate file
        """
        self.server_host = server_host
        self.server_port = server_port
        self.username = username
        self.password = password
        self.verify_cert = verify_cert
        self.cert_file = cert_file
        
        # Connection state
        self.is_connected = False
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        
        # Session info
        self.session_token: Optional[str] = None
        self.assigned_ip: Optional[str] = None
        
        # Encryption
        self.encryption: Optional[EncryptionHandler] = None
        self.packet_processor = PacketProcessor()
        
        # Stream buffer
        self.read_buffer = StreamBuffer()
        
        # Background tasks
        self.receive_task: Optional[asyncio.Task] = None
        self.keepalive_task: Optional[asyncio.Task] = None
        
        # Auto-reconnect
        self.auto_reconnect = AutoReconnect(
            connect_func=self._connect_internal,
            on_state_change=self._on_reconnect_state_change
        )
        
        # Callbacks
        self.on_connected: Optional[Callable[[str], None]] = None
        self.on_disconnected: Optional[Callable[[str], None]] = None
        self.on_data_received: Optional[Callable[[bytes], None]] = None
        
        # Statistics
        self.bytes_sent = 0
        self.bytes_received = 0
        self.packets_sent = 0
        self.packets_received = 0
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for TLS connection."""
        if not self.verify_cert:
            # Don't verify certificate (for testing with self-signed certs)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        
        # Verify certificate
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        if self.cert_file:
            context.load_verify_locations(self.cert_file)
        
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        
        return context
    
    async def connect(self) -> bool:
        """
        Connect to server.
        
        Returns:
            True if connected successfully
        """
        return await self._connect_internal()
    
    async def _connect_internal(self) -> bool:
        """Internal connection method (used by auto-reconnect)."""
        try:
            logger.info(f"Connecting to {self.server_host}:{self.server_port}...")
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
            
            # Connect to server
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.server_host,
                    self.server_port,
                    ssl=ssl_context
                ),
                timeout=CONNECTION_TIMEOUT
            )
            
            logger.info("TCP connection established")
            
            # Authenticate
            if not await self._authenticate():
                logger.error("Authentication failed")
                await self._cleanup_connection()
                return False
            
            logger.info(f"Authenticated successfully, assigned IP: {self.assigned_ip}")
            
            # Connection successful
            self.is_connected = True
            
            # Start background tasks
            self.receive_task = asyncio.create_task(self._receive_loop())
            self.keepalive_task = asyncio.create_task(self._keepalive_loop())
            
            # Notify auto-reconnect
            self.auto_reconnect.on_connected()
            
            # Notify callback
            if self.on_connected:
                try:
                    self.on_connected(self.assigned_ip)
                except Exception as e:
                    logger.exception(f"Error in on_connected callback: {e}")
            
            return True
        
        except asyncio.TimeoutError:
            logger.error("Connection timeout")
            return False
        
        except Exception as e:
            logger.exception(f"Connection error: {e}")
            return False
    
    async def _authenticate(self) -> bool:
        """
        Authenticate with server.
        
        Returns:
            True if authenticated
        """
        try:
            # Send authentication request
            # We send plaintext password because the channel is TLS encrypted
            # Note: The field is named 'password_hash' in protocol, but we send plaintext
            # because the server expects plaintext to verify against Argon2 hash.
            auth_request = MessageFormat.create_auth_request(
                username=self.username,
                password_hash=self.password,
                client_version="1.0.0"
            )
            
            self.writer.write(auth_request)
            await self.writer.drain()
            
            logger.debug("Authentication request sent")
            
            # Receive response
            response_data = await asyncio.wait_for(
                self.reader.read(4096),
                timeout=10
            )
            
            if not response_data:
                raise AuthenticationError("No response from server")
            
            message_type, payload = MessageFormat.unpack(response_data)
            
            if message_type == MessageType.AUTH_SUCCESS:
                # Extract session info
                self.session_token = payload.get('session_token')
                self.assigned_ip = payload.get('assigned_ip')
                
                if not self.session_token or not self.assigned_ip:
                    raise AuthenticationError("Invalid auth response")
                
                # Initialize encryption (will get key from server or derive)
                # For now, we'll use a temporary key
                # In production, server should send encryption key in AUTH_SUCCESS
                temp_key = hashlib.sha256(
                    (self.session_token + self.password).encode()
                ).digest()
                
                self.encryption = EncryptionHandler(master_key=temp_key)
                
                logger.info("Authentication successful")
                return True
            
            elif message_type == MessageType.AUTH_FAILURE:
                error_msg = payload.get('error_message', 'Unknown error')
                raise AuthenticationError(f"Authentication failed: {error_msg}")
            
            else:
                raise AuthenticationError(f"Unexpected response: {message_type}")
        
        except asyncio.TimeoutError:
            logger.error("Authentication timeout")
            return False
        
        except Exception as e:
            logger.exception(f"Authentication error: {e}")
            return False
    
    async def disconnect(self, reason: str = "User requested") -> None:
        """
        Disconnect from server.
        
        Args:
            reason: Disconnect reason
        """
        if not self.is_connected:
            return
        
        logger.info(f"Disconnecting: {reason}")
        
        try:
            # Send disconnect message
            if self.writer and not self.writer.is_closing():
                disconnect_msg = MessageFormat.create_disconnect(reason)
                self.writer.write(disconnect_msg)
                await self.writer.drain()
        except Exception as e:
            logger.error(f"Error sending disconnect: {e}")
        
        # Cleanup
        await self._cleanup_connection()
        
        # Notify callback
        if self.on_disconnected:
            try:
                self.on_disconnected(reason)
            except Exception as e:
                logger.exception(f"Error in on_disconnected callback: {e}")
    
    async def _cleanup_connection(self) -> None:
        """Clean up connection resources."""
        self.is_connected = False
        
        # Cancel background tasks
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
        
        if self.keepalive_task and not self.keepalive_task.done():
            self.keepalive_task.cancel()
        
        # Close writer
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
        
        # Clear references
        self.reader = None
        self.writer = None
        self.read_buffer.clear()
        
        logger.debug("Connection cleaned up")
    
    async def send_packet(self, packet: bytes) -> bool:
        """
        Send IP packet through tunnel.
        
        Args:
            packet: Raw IP packet
        
        Returns:
            True if sent successfully
        """
        if not self.is_connected or not self.encryption:
            return False
        
        try:
            # Process packet
            processed = self.packet_processor.process_outbound(packet)
            if not processed:
                return False
            
            # Encrypt
            encrypted = self.encryption.encrypt(processed)
            
            # Frame
            framed = PacketFramer.frame(encrypted)
            
            # Send
            self.writer.write(framed)
            await self.writer.drain()
            
            self.bytes_sent += len(framed)
            self.packets_sent += 1
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending packet: {e}")
            return False
    
    async def _receive_loop(self) -> None:
        """Background task to receive data from server."""
        try:
            while self.is_connected:
                data = await self.reader.read(4096)
                
                if not data:
                    logger.warning("Connection closed by server")
                    break
                
                self.bytes_received += len(data)
                self.read_buffer.append(data)
                
                # Process all complete frames
                while True:
                    frame = self.read_buffer.extract_frame()
                    if not frame:
                        break
                    
                    await self._process_received_frame(frame)
        
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        
        except Exception as e:
            logger.exception(f"Receive loop error: {e}")
        
        finally:
            if self.is_connected:
                # Connection lost
                await self._on_connection_lost()
    
    async def _process_received_frame(self, frame: bytes) -> None:
        """Process received encrypted frame."""
        try:
            if not self.encryption:
                return
            
            # Decrypt
            plaintext = self.encryption.decrypt(frame)
            
            # Process
            processed = self.packet_processor.process_inbound(plaintext)
            if not processed:
                return
            
            self.packets_received += 1
            
            # Notify callback
            if self.on_data_received:
                try:
                    self.on_data_received(processed)
                except Exception as e:
                    logger.exception(f"Error in on_data_received callback: {e}")
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
    
    async def _keepalive_loop(self) -> None:
        """Background task to send keepalive pings."""
        try:
            while self.is_connected:
                await asyncio.sleep(KEEPALIVE_INTERVAL)
                
                if not self.is_connected:
                    break
                
                # Send ping (for now, just a simple marker)
                # In production, use MessageFormat.create_ping()
                logger.debug("Keepalive ping")
        
        except asyncio.CancelledError:
            logger.debug("Keepalive loop cancelled")
        
        except Exception as e:
            logger.exception(f"Keepalive loop error: {e}")
    
    async def _on_connection_lost(self) -> None:
        """Handle connection loss."""
        logger.warning("Connection lost")
        
        await self._cleanup_connection()
        
        # Notify auto-reconnect
        self.auto_reconnect.on_disconnected()
        
        # Notify callback
        if self.on_disconnected:
            try:
                self.on_disconnected("Connection lost")
            except Exception as e:
                logger.exception(f"Error in callback: {e}")
    
    def _on_reconnect_state_change(self, state: ReconnectState) -> None:
        """Handle reconnect state changes."""
        logger.info(f"Reconnect state: {state.value}")
    
    def enable_auto_reconnect(self) -> None:
        """Enable automatic reconnection."""
        self.auto_reconnect.enable()
    
    def disable_auto_reconnect(self) -> None:
        """Disable automatic reconnection."""
        self.auto_reconnect.disable()
    
    def get_statistics(self) -> dict:
        """Get connection statistics."""
        stats = {
            'is_connected': self.is_connected,
            'server': f"{self.server_host}:{self.server_port}",
            'assigned_ip': self.assigned_ip,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
        }
        
        if self.encryption:
            stats['encryption'] = self.encryption.get_statistics()
        
        stats['packet_processor'] = self.packet_processor.get_statistics()
        stats['auto_reconnect'] = self.auto_reconnect.get_statistics()
        
        return stats
