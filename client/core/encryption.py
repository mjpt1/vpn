"""
Client Encryption Handler - Identical to Server
Uses same ChaCha20-Poly1305 implementation for compatibility.
"""

import os
import struct
import time
from typing import Optional, Tuple
from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared.protocol import KEY_SIZE, NONCE_SIZE, TAG_SIZE, KDF_INFO
from shared.exceptions import EncryptionError, DecryptionError, ReplayAttackError


class EncryptionHandler:
    """
    Client-side encryption handler (identical to server).
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """Initialize encryption with master key."""
        if master_key is None:
            self.master_key = os.urandom(KEY_SIZE)
        else:
            if len(master_key) != KEY_SIZE:
                raise ValueError(f"Master key must be {KEY_SIZE} bytes")
            self.master_key = master_key
        
        self.session_key = self._derive_key(self.master_key, b"session_key")
        
        self.send_counter: int = 0
        self.recv_counter: int = 0
        
        self.replay_window_size = 64
        self.highest_recv_counter = 0
        self.recv_bitmap = 0
        
        self.packets_encrypted = 0
        self.packets_decrypted = 0
        self.replay_attacks_blocked = 0
    
    def _derive_key(self, master_key: bytes, context: bytes) -> bytes:
        """Derive key using HKDF-SHA256."""
        salt = KDF_INFO
        derived_key = HKDF(
            master=master_key,
            key_len=KEY_SIZE,
            salt=salt,
            hashmod=SHA256,
            context=context
        )
        return derived_key
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt data with ChaCha20-Poly1305.
        
        Returns: [8 bytes: nonce_counter] [N bytes: ciphertext] [16 bytes: tag]
        """
        try:
            nonce_counter = self.send_counter
            timestamp = int(time.time()) & 0xFFFFFFFF
            
            nonce = struct.pack('!Q', nonce_counter) + struct.pack('!I', timestamp)
            
            cipher = ChaCha20_Poly1305.new(key=self.session_key, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)
            
            self.send_counter += 1
            self.packets_encrypted += 1
            
            return struct.pack('!Q', nonce_counter) + ciphertext + tag
        
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_packet: bytes) -> bytes:
        """Decrypt ChaCha20-Poly1305 encrypted packet."""
        try:
            if len(encrypted_packet) < 24:
                raise DecryptionError("Packet too short")
            
            nonce_counter = struct.unpack('!Q', encrypted_packet[0:8])[0]
            ciphertext = encrypted_packet[8:-16]
            tag = encrypted_packet[-16:]
            
            if not self._check_replay(nonce_counter):
                self.replay_attacks_blocked += 1
                raise ReplayAttackError(f"Replay detected: counter={nonce_counter}")
            
            timestamp = 0
            nonce = struct.pack('!Q', nonce_counter) + struct.pack('!I', timestamp)
            
            cipher = ChaCha20_Poly1305.new(key=self.session_key, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            
            self._update_replay_window(nonce_counter)
            self.packets_decrypted += 1
            
            return plaintext
        
        except ReplayAttackError:
            raise
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}")
    
    def _check_replay(self, counter: int) -> bool:
        """Check if packet counter is valid (not replayed)."""
        if counter + self.replay_window_size < self.highest_recv_counter:
            return False
        
        if counter > self.highest_recv_counter:
            return True
        
        diff = self.highest_recv_counter - counter
        if diff >= self.replay_window_size:
            return False
        
        if self.recv_bitmap & (1 << diff):
            return False
        
        return True
    
    def _update_replay_window(self, counter: int) -> None:
        """Update replay protection window."""
        if counter > self.highest_recv_counter:
            diff = counter - self.highest_recv_counter
            if diff < self.replay_window_size:
                self.recv_bitmap = (self.recv_bitmap << diff) | 1
            else:
                self.recv_bitmap = 1
            self.highest_recv_counter = counter
        else:
            diff = self.highest_recv_counter - counter
            self.recv_bitmap |= (1 << diff)
    
    def get_statistics(self) -> dict:
        """Get encryption statistics."""
        return {
            'packets_encrypted': self.packets_encrypted,
            'packets_decrypted': self.packets_decrypted,
            'replay_attacks_blocked': self.replay_attacks_blocked,
            'send_counter': self.send_counter,
            'recv_counter': self.recv_counter,
        }
