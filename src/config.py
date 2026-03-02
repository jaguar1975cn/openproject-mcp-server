"""Configuration management for OpenProject MCP Server."""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging as early as possible
from utils.logging import configure_logging
configure_logging(os.getenv("MCP_LOG_LEVEL", "INFO"))


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # OpenProject configuration
        self.openproject_url: str = self._get_required_env("OPENPROJECT_URL")
        self.openproject_api_key: str = self._get_required_env("OPENPROJECT_API_KEY")
        
        # MCP server configuration
        self.mcp_host: str = os.getenv("MCP_HOST", "localhost")
        self.mcp_port: int = int(os.getenv("MCP_PORT", "8080"))
        self.log_level: str = os.getenv("MCP_LOG_LEVEL", "INFO")

        # SSL configuration
        self.openproject_verify_ssl: bool = os.getenv("OPENPROJECT_VERIFY_SSL", "true").lower() != "false"
        
        # Validate configuration
        self._validate_config()
    
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        if not self.openproject_url.startswith(("http://", "https://")):
            raise ValueError("OPENPROJECT_URL must start with http:// or https://")
        
        if len(self.openproject_api_key) < 20:
            raise ValueError("OPENPROJECT_API_KEY appears to be too short")
        
        if not (1 <= self.mcp_port <= 65535):
            raise ValueError("MCP_PORT must be between 1 and 65535")


# Global settings instance
settings = Settings()
