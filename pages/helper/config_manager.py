"""
Secure configuration and credential management module.
"""
import os
import yaml
import bcrypt
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Secure configuration manager with environment variable support."""
    
    def __init__(self, config_path: str = "login_config.yml"):
        self.config_path = config_path
        self.config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file with error handling."""
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Configuration file not found: {self.config_path}")
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
                
            if not self.config:
                logger.error("Configuration file is empty or invalid")
                raise ValueError("Configuration file is empty or invalid")
                
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def get_credentials(self) -> Dict[str, Any]:
        """Get credentials with security checks."""
        if not self.config or 'credentials' not in self.config:
            logger.error("No credentials found in configuration")
            raise ValueError("No credentials found in configuration")
        
        return self.config['credentials']
    
    def get_cookie_config(self) -> Dict[str, Any]:
        """Get cookie configuration."""
        if not self.config or 'cookie' not in self.config:
            logger.warning("No cookie configuration found, using defaults")
            return {
                'name': 'missing_person_auth',
                'key': 'default_secret_key_change_in_production',
                'expiry_days': 30
            }
        
        return self.config['cookie']
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user information securely.
        
        Args:
            username: Username to look up
            
        Returns:
            User information dict or None if not found
        """
        try:
            credentials = self.get_credentials()
            usernames = credentials.get('usernames', {})
            
            if username not in usernames:
                logger.warning(f"User not found: {username}")
                return None
            
            user_info = usernames[username].copy()
            
            # Remove sensitive data from returned info
            user_info.pop('password', None)
            
            return user_info
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def verify_password(self, username: str, password: str) -> bool:
        """
        Verify password for a user.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            credentials = self.get_credentials()
            usernames = credentials.get('usernames', {})
            
            if username not in usernames:
                logger.warning(f"Authentication failed: user not found - {username}")
                return False
            
            stored_hash = usernames[username].get('password')
            if not stored_hash:
                logger.error(f"No password hash found for user: {username}")
                return False
            
            # Verify password using bcrypt
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')
            
            password_bytes = password.encode('utf-8')
            
            is_valid = bcrypt.checkpw(password_bytes, stored_hash)
            
            if not is_valid:
                logger.warning(f"Authentication failed: invalid password for user - {username}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password as string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()


class EnvironmentConfig:
    """Environment variable configuration manager."""
    
    @staticmethod
    def get_smtp_config() -> Dict[str, Optional[str]]:
        """
        Get SMTP configuration from environment variables.
        
        Returns:
            Dictionary with SMTP configuration
        """
        return {
            'host': os.getenv('SMTP_HOST'),
            'port': os.getenv('SMTP_PORT'),
            'user': os.getenv('SMTP_USER'),
            'password': os.getenv('SMTP_PASSWORD'),
        }
    
    @staticmethod
    def get_database_config() -> Dict[str, str]:
        """
        Get database configuration from environment variables.
        
        Returns:
            Dictionary with database configuration
        """
        return {
            'url': os.getenv('DATABASE_URL', 'sqlite:///sqlite_database.db'),
        }
    
    @staticmethod
    def get_security_config() -> Dict[str, Any]:
        """
        Get security configuration from environment variables.
        
        Returns:
            Dictionary with security configuration
        """
        return {
            'secret_key': os.getenv('SECRET_KEY'),
            'session_timeout': int(os.getenv('SESSION_TIMEOUT', '1800')),
            'max_login_attempts': int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')),
            'rate_limit_enabled': os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
        }
    
    @staticmethod
    def validate_required_env_vars(required_vars: list) -> Tuple[bool, list]:
        """
        Validate that required environment variables are set.
        
        Args:
            required_vars: List of required environment variable names
            
        Returns:
            Tuple of (is_valid, missing_vars)
        """
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        return len(missing_vars) == 0, missing_vars


class SecretManager:
    """Basic secret management utilities."""
    
    @staticmethod
    def generate_secret_key(length: int = 32) -> str:
        """
        Generate a cryptographically secure secret key.
        
        Args:
            length: Length of the secret key
            
        Returns:
            Hex-encoded secret key
        """
        import secrets
        return secrets.token_hex(length)
    
    @staticmethod
    def validate_secret_strength(secret: str, min_length: int = 16) -> bool:
        """
        Validate the strength of a secret/key.
        
        Args:
            secret: Secret to validate
            min_length: Minimum required length
            
        Returns:
            True if secret meets strength requirements
        """
        if not secret or len(secret) < min_length:
            return False
        
        # Check for sufficient entropy (basic check)
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in secret)
        
        return (has_upper + has_lower + has_digit + has_special) >= 2


def setup_secure_config():
    """
    Setup secure configuration with environment variable support.
    Creates example .env file if it doesn't exist.
    """
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        logger.info("Created .env file from .env.example")
    
    # Check for critical security issues
    config = EnvironmentConfig.get_security_config()
    
    if not config['secret_key']:
        logger.warning("SECRET_KEY not set in environment variables")
        logger.warning("Generate a secure key using: python -c 'from pages.helper.config_manager import SecretManager; print(SecretManager.generate_secret_key())'")
    
    return config


# Global configuration manager instance
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager