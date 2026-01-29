"""
Configuration Loader
Loads and validates server configuration from YAML file.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads and manages server configuration.
    """
    
    DEFAULT_CONFIG = {
        'server': {
            'host': '0.0.0.0',
            'port': 8443,
            'max_clients': 100,
        },
        'database': {
            'path': 'vpn_server.db',
        },
        'tls': {
            'cert_file': 'certs/server.crt',
            'key_file': 'certs/server.key',
        },
        'tunnel': {
            'interface_name': 'iran_vpn0',
            'ip_range': '10.8.0.0/24',
            'mtu': 1420,
        },
        'security': {
            'session_timeout_hours': 24,
            'keepalive_interval': 15,
            'max_sessions_per_user': 3,
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/server.log',
            'json_format': False,
        },
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize config loader.
        
        Args:
            config_file: Path to YAML config file
        """
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file:
            self.load(config_file)
    
    def load(self, config_file: str) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to YAML config file
        """
        path = Path(config_file)
        
        if not path.exists():
            logger.warning(f"Config file not found: {config_file}, using defaults")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
            
            # Merge with defaults (deep update)
            self._deep_update(self.config, loaded_config)
            
            logger.info(f"Configuration loaded from: {config_file}")
        
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
    
    def _deep_update(self, base: Dict, update: Dict) -> None:
        """Recursively update nested dictionaries."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation path.
        
        Args:
            key_path: Dot-separated key path (e.g., 'server.host')
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
    
    def save(self, config_file: str) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            config_file: Output file path
        """
        path = Path(config_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to: {config_file}")
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self.get(key)
    
    def to_dict(self) -> Dict:
        """Return configuration as dictionary."""
        return self.config.copy()
