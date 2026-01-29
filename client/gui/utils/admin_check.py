"""
Administrator Elevation - Force GUI to run as Administrator
Detects if running as admin, and if not, re-launches with elevation.
"""

import os
import sys
import ctypes
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


def is_running_as_admin() -> bool:
    """
    Check if current process is running as Administrator.
    
    Returns:
        True if running as admin, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logger.warning(f"Could not check admin status: {e}")
        return False


def elevate_privileges() -> bool:
    """
    Re-launch current script with Administrator privileges.
    
    Returns:
        True if re-launched (process will exit after this)
        False if already admin
    """
    if is_running_as_admin():
        logger.info("✓ Already running as Administrator")
        return False
    
    try:
        logger.info("Re-launching with Administrator privileges...")
        
        # Get current executable
        if hasattr(sys, 'frozen') and sys.frozen == 'windows_exe':
            # Running as PyInstaller executable
            exe_path = sys.executable
            args = sys.argv[1:]  # Skip executable name
        else:
            # Running as Python script
            exe_path = sys.executable
            args = [__file__] + sys.argv[1:]  # Include script name
        
        # Build command
        cmd = [exe_path] + args
        
        # Re-launch with elevation using ShellExecuteEx
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",  # Operation: run as admin
            exe_path,
            " ".join(f'"{arg}"' for arg in args),  # Arguments
            None,
            1  # SW_SHOW
        )
        
        # Exit current process
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Failed to elevate privileges: {e}")
        return False


def check_and_elevate() -> None:
    """
    Check if running as admin, and elevate if necessary.
    
    This function will:
    - Check if running as admin
    - If not, re-launch with admin privileges and exit
    - If yes, continue execution
    """
    if not is_running_as_admin():
        elevate_privileges()
        # If elevation was successful, this line won't be reached
        # If elevation failed, we continue anyway
        logger.warning("Running without Administrator privileges (some features may not work)")


def require_admin(func):
    """
    Decorator to check for admin privileges before running function.
    
    Usage:
        @require_admin
        def my_function():
            pass
    """
    def wrapper(*args, **kwargs):
        check_and_elevate()
        return func(*args, **kwargs)
    
    return wrapper
