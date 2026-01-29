"""
Configuration loader for VPN client.
"""

import yaml
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ClientConfig:
    """Client configuration loader."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to YAML config file
        """
        self.config_file = config_file or "client_config.yaml"
        self.config: dict = {}
        
        self._load_defaults()
        
        if Path(self.config_file).exists():
            self._load_from_file()
        else:
            logger.warning(f"Config file not found: {self.config_file}")
    
    def _load_defaults(self) -> None:
        """Load default configuration."""
        self.config = {
            'server': {
                'host': '',
                'port': 8443,
                'verify_cert': False,
                'cert_file': None
            },
            'auth': {
                'username': '',
                'password': ''
            },
            'network': {
                'interface_name': 'VPN-TAP',
                'mtu': 1400,
                'dns_servers': ['8.8.8.8', '8.8.4.4']
            },
            'vpn': {
                'auto_reconnect': True,
                'kill_switch': True,
                'allow_lan': True,
                'reconnect_max_backoff': 30
            },
            'logging': {
                'level': 'INFO',
                'file': 'vpn_client.log',
                'console': True
            }
        }
    
    def _load_from_file(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            
            # Deep merge
            self._deep_merge(self.config, file_config)
            
            logger.info(f"Configuration loaded from: {self.config_file}")
        
        except Exception as e:
            logger.exception(f"Error loading config: {e}")
    
    def _deep_merge(self, base: dict, override: dict) -> None:
        """Deep merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation path.
        
        Args:
            key_path: Dot-separated key path (e.g., "server.host")
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value by dot-notation path.
        
        Args:
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """
        Save configuration to file.
        
        Args:
            file_path: File path (default: self.config_file)
        
        Returns:
            True if saved successfully
        """
        target_file = file_path or self.config_file
        
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuration saved to: {target_file}")
            return True
        
        except Exception as e:
            logger.exception(f"Error saving config: {e}")
            return False
    
    def to_dict(self) -> dict:
        """Get configuration as dictionary."""
        return self.config.copy()
