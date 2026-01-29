"""
Auto-Reconnect Logic
Handles automatic reconnection with exponential backoff.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Awaitable
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared.protocol import (
    RECONNECT_INITIAL_DELAY,
    RECONNECT_MAX_DELAY,
    RECONNECT_BACKOFF_MULTIPLIER
)

logger = logging.getLogger(__name__)


class ReconnectState(Enum):
    """Reconnection state."""
    IDLE = "idle"
    WAITING = "waiting"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


class AutoReconnect:
    """
    Automatic reconnection handler with exponential backoff.
    
    Features:
    - Exponential backoff (1s, 2s, 4s, 8s, ... max 30s)
    - Connection health monitoring
    - Callback notifications
    """
    
    def __init__(
        self,
        connect_func: Callable[[], Awaitable[bool]],
        on_state_change: Optional[Callable[[ReconnectState], None]] = None
    ):
        """
        Initialize auto-reconnect.
        
        Args:
            connect_func: Async function to call for connection
            on_state_change: Optional callback for state changes
        """
        self.connect_func = connect_func
        self.on_state_change = on_state_change
        
        # State
        self.state = ReconnectState.IDLE
        self.is_enabled = False
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # Backoff parameters
        self.initial_delay = RECONNECT_INITIAL_DELAY
        self.max_delay = RECONNECT_MAX_DELAY
        self.backoff_multiplier = RECONNECT_BACKOFF_MULTIPLIER
        
        # Statistics
        self.current_delay = self.initial_delay
        self.reconnect_attempts = 0
        self.total_reconnects = 0
        self.last_connect_time: Optional[float] = None
        self.last_disconnect_time: Optional[float] = None
    
    def enable(self) -> None:
        """Enable auto-reconnect."""
        self.is_enabled = True
        logger.info("Auto-reconnect enabled")
    
    def disable(self) -> None:
        """Disable auto-reconnect."""
        self.is_enabled = False
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
        logger.info("Auto-reconnect disabled")
    
    async def start_reconnect(self) -> None:
        """Start reconnection process."""
        if not self.is_enabled:
            logger.debug("Auto-reconnect disabled, not reconnecting")
            return
        
        if self.reconnect_task and not self.reconnect_task.done():
            logger.debug("Reconnection already in progress")
            return
        
        # Record disconnect time
        self.last_disconnect_time = time.time()
        
        # Start reconnection task
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())
        logger.info("Starting auto-reconnect")
    
    async def _reconnect_loop(self) -> None:
        """Main reconnection loop with exponential backoff."""
        self.reconnect_attempts = 0
        self.current_delay = self.initial_delay
        
        while self.is_enabled:
            try:
                self.reconnect_attempts += 1
                
                # Update state to waiting
                self._change_state(ReconnectState.WAITING)
                
                # Wait before reconnecting (skip on first attempt)
                if self.reconnect_attempts > 1:
                    logger.info(
                        f"Waiting {self.current_delay}s before reconnect "
                        f"(attempt {self.reconnect_attempts})"
                    )
                    await asyncio.sleep(self.current_delay)
                
                # Try to connect
                self._change_state(ReconnectState.CONNECTING)
                logger.info(f"Reconnecting... (attempt {self.reconnect_attempts})")
                
                success = await self.connect_func()
                
                if success:
                    # Connection successful
                    self._change_state(ReconnectState.CONNECTED)
                    self.last_connect_time = time.time()
                    self.total_reconnects += 1
                    
                    logger.info(
                        f"Reconnected successfully after {self.reconnect_attempts} attempts"
                    )
                    
                    # Reset backoff
                    self.current_delay = self.initial_delay
                    self.reconnect_attempts = 0
                    break
                else:
                    # Connection failed, increase backoff
                    logger.warning(
                        f"Reconnect attempt {self.reconnect_attempts} failed"
                    )
                    self._increase_backoff()
                    self._change_state(ReconnectState.FAILED)
            
            except asyncio.CancelledError:
                logger.info("Reconnection cancelled")
                break
            
            except Exception as e:
                logger.exception(f"Error during reconnection: {e}")
                self._increase_backoff()
                self._change_state(ReconnectState.FAILED)
        
        # Final state update
        if not self.is_enabled:
            self._change_state(ReconnectState.IDLE)
    
    def _increase_backoff(self) -> None:
        """Increase backoff delay using exponential backoff."""
        self.current_delay = min(
            self.current_delay * self.backoff_multiplier,
            self.max_delay
        )
    
    def _change_state(self, new_state: ReconnectState) -> None:
        """Change reconnection state and notify callback."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            
            logger.debug(f"Reconnect state: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                try:
                    self.on_state_change(new_state)
                except Exception as e:
                    logger.exception(f"Error in state change callback: {e}")
    
    def on_connected(self) -> None:
        """Notify that connection was established externally."""
        self.last_connect_time = time.time()
        self.reconnect_attempts = 0
        self.current_delay = self.initial_delay
        self._change_state(ReconnectState.CONNECTED)
    
    def on_disconnected(self) -> None:
        """Notify that connection was lost."""
        self.last_disconnect_time = time.time()
        
        if self.is_enabled:
            asyncio.create_task(self.start_reconnect())
    
    def get_statistics(self) -> dict:
        """Get reconnection statistics."""
        uptime = None
        if self.last_connect_time and self.last_disconnect_time:
            if self.last_connect_time > self.last_disconnect_time:
                uptime = time.time() - self.last_connect_time
        
        return {
            'state': self.state.value,
            'is_enabled': self.is_enabled,
            'reconnect_attempts': self.reconnect_attempts,
            'total_reconnects': self.total_reconnects,
            'current_delay': self.current_delay,
            'uptime_seconds': uptime,
            'last_connect_time': self.last_connect_time,
            'last_disconnect_time': self.last_disconnect_time,
        }
    
    async def stop(self) -> None:
        """Stop reconnection."""
        self.disable()
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
        self._change_state(ReconnectState.IDLE)
