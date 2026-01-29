"""
Packet Processor - Handles IP packet reading/writing from TUN interface
"""

import struct
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PacketProcessor:
    """
    Processes IP packets to/from TUN interface.
    
    Handles:
    - IP packet validation
    - Packet size verification
    - Basic IP header parsing
    """
    
    MIN_IP_HEADER_SIZE = 20
    MAX_PACKET_SIZE = 1500  # MTU
    
    def __init__(self):
        """Initialize packet processor."""
        self.packets_processed = 0
        self.bytes_processed = 0
        self.invalid_packets = 0
    
    def validate_packet(self, packet: bytes) -> bool:
        """
        Validate IP packet.
        
        Args:
            packet: Raw IP packet
        
        Returns:
            True if valid, False otherwise
        """
        # Check minimum size
        if len(packet) < self.MIN_IP_HEADER_SIZE:
            logger.warning(f"Packet too small: {len(packet)} bytes")
            self.invalid_packets += 1
            return False
        
        # Check maximum size
        if len(packet) > self.MAX_PACKET_SIZE:
            logger.warning(f"Packet too large: {len(packet)} bytes")
            self.invalid_packets += 1
            return False
        
        # Parse IP version
        version = (packet[0] >> 4) & 0x0F
        if version not in (4, 6):
            logger.warning(f"Invalid IP version: {version}")
            self.invalid_packets += 1
            return False
        
        return True
    
    def process_outbound(self, packet: bytes) -> Optional[bytes]:
        """
        Process outbound packet (from TUN to tunnel).
        
        Args:
            packet: Raw IP packet from TUN interface
        
        Returns:
            Processed packet or None if invalid
        """
        if not self.validate_packet(packet):
            return None
        
        self.packets_processed += 1
        self.bytes_processed += len(packet)
        
        # In production, could add:
        # - Packet fragmentation handling
        # - QoS marking
        # - Traffic shaping
        
        return packet
    
    def process_inbound(self, packet: bytes) -> Optional[bytes]:
        """
        Process inbound packet (from tunnel to TUN).
        
        Args:
            packet: Raw IP packet from tunnel
        
        Returns:
            Processed packet or None if invalid
        """
        if not self.validate_packet(packet):
            return None
        
        self.packets_processed += 1
        self.bytes_processed += len(packet)
        
        return packet
    
    def extract_ip_info(self, packet: bytes) -> Optional[dict]:
        """
        Extract basic IP information from packet.
        
        Args:
            packet: Raw IP packet
        
        Returns:
            Dictionary with IP info or None if invalid
        """
        if not self.validate_packet(packet):
            return None
        
        version = (packet[0] >> 4) & 0x0F
        
        if version == 4:
            return self._parse_ipv4(packet)
        elif version == 6:
            return self._parse_ipv6(packet)
        
        return None
    
    def _parse_ipv4(self, packet: bytes) -> dict:
        """Parse IPv4 packet header."""
        if len(packet) < 20:
            return {}
        
        # Parse IPv4 header
        version_ihl = packet[0]
        ihl = (version_ihl & 0x0F) * 4  # Header length in bytes
        
        total_length = struct.unpack('!H', packet[2:4])[0]
        protocol = packet[9]
        
        src_ip = '.'.join(str(b) for b in packet[12:16])
        dst_ip = '.'.join(str(b) for b in packet[16:20])
        
        return {
            'version': 4,
            'header_length': ihl,
            'total_length': total_length,
            'protocol': protocol,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
        }
    
    def _parse_ipv6(self, packet: bytes) -> dict:
        """Parse IPv6 packet header."""
        if len(packet) < 40:
            return {}
        
        # Parse IPv6 header
        version_class_flow = struct.unpack('!I', packet[0:4])[0]
        payload_length = struct.unpack('!H', packet[4:6])[0]
        next_header = packet[6]
        
        src_ip = ':'.join(packet[8:24].hex()[i:i+4] for i in range(0, 32, 4))
        dst_ip = ':'.join(packet[24:40].hex()[i:i+4] for i in range(0, 32, 4))
        
        return {
            'version': 6,
            'payload_length': payload_length,
            'next_header': next_header,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
        }
    
    def get_statistics(self) -> dict:
        """Get packet processing statistics."""
        return {
            'packets_processed': self.packets_processed,
            'bytes_processed': self.bytes_processed,
            'invalid_packets': self.invalid_packets,
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.packets_processed = 0
        self.bytes_processed = 0
        self.invalid_packets = 0
