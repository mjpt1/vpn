"""
Packet Processor - Client Side
"""

import struct
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PacketProcessor:
    """Process IP packets (client-side)."""
    
    MIN_IP_HEADER_SIZE = 20
    MAX_PACKET_SIZE = 1500
    
    def __init__(self):
        """Initialize packet processor."""
        self.packets_processed = 0
        self.bytes_processed = 0
        self.invalid_packets = 0
    
    def validate_packet(self, packet: bytes) -> bool:
        """Validate IP packet."""
        if len(packet) < self.MIN_IP_HEADER_SIZE:
            logger.warning(f"Packet too small: {len(packet)} bytes")
            self.invalid_packets += 1
            return False
        
        if len(packet) > self.MAX_PACKET_SIZE:
            logger.warning(f"Packet too large: {len(packet)} bytes")
            self.invalid_packets += 1
            return False
        
        version = (packet[0] >> 4) & 0x0F
        if version not in (4, 6):
            logger.warning(f"Invalid IP version: {version}")
            self.invalid_packets += 1
            return False
        
        return True
    
    def process_outbound(self, packet: bytes) -> Optional[bytes]:
        """Process outbound packet (from TAP to tunnel)."""
        if not self.validate_packet(packet):
            return None
        
        self.packets_processed += 1
        self.bytes_processed += len(packet)
        
        return packet
    
    def process_inbound(self, packet: bytes) -> Optional[bytes]:
        """Process inbound packet (from tunnel to TAP)."""
        if not self.validate_packet(packet):
            return None
        
        self.packets_processed += 1
        self.bytes_processed += len(packet)
        
        return packet
    
    def get_statistics(self) -> dict:
        """Get packet processing statistics."""
        return {
            'packets_processed': self.packets_processed,
            'bytes_processed': self.bytes_processed,
            'invalid_packets': self.invalid_packets,
        }
