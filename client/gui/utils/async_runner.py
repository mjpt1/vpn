"""
Async Runner - Bridge between asyncio and Qt event loop
"""

import asyncio
import logging
from threading import Thread
from typing import Callable, Coroutine, Any
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class AsyncRunner:
    """
    Run asyncio code in a separate thread.
    
    Allows Qt GUI to remain responsive while asyncio code runs.
    """
    
    def __init__(self):
        """Initialize async runner."""
        self.loop: asyncio.AbstractEventLoop = None
        self.thread: Thread = None
        self.is_running = False
        
        logger.info("Async runner initialized")
    
    def start(self) -> None:
        """Start asyncio event loop in a separate thread."""
        if self.is_running:
            logger.warning("Async runner already running")
            return
        
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Wait for loop to start
        while self.loop is None:
            pass
        
        self.is_running = True
        logger.info("Async runner started")
    
    def stop(self) -> None:
        """Stop asyncio event loop."""
        if not self.is_running:
            return
        
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.is_running = False
        logger.info("Async runner stopped")
    
    def _run_loop(self) -> None:
        """Run event loop (in separate thread)."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()
    
    def run_coroutine(self, coro: Coroutine) -> asyncio.Future:
        """
        Schedule coroutine to run in async loop.
        
        Args:
            coro: Coroutine to run
        
        Returns:
            Future object
        """
        if not self.is_running or not self.loop:
            raise RuntimeError("Async runner not running")
        
        return asyncio.run_coroutine_threadsafe(coro, self.loop)
    
    def run_callback(self, callback: Callable, *args) -> None:
        """
        Schedule callback to run in async loop.
        
        Args:
            callback: Callback function
            *args: Arguments
        """
        if not self.is_running or not self.loop:
            raise RuntimeError("Async runner not running")
        
        self.loop.call_soon_threadsafe(callback, *args)
