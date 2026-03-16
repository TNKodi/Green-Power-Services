"""
Configuration management for the ThingsBoard Power Forecast API.
Loads environment variables and provides centralized configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Application Settings
    APP_NAME: str = "thingsboard-power-forecast-api"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ThingsBoard Settings
    TB_HOST: str = os.getenv("TB_HOST", "http://localhost:8080")
    TB_USERNAME: str = os.getenv("TB_USERNAME", "")
    TB_PASSWORD: str = os.getenv("TB_PASSWORD", "")
    
    # JWT Token Settings
    TB_TOKEN: str | None = None  # Will be set at runtime
    TB_TOKEN_EXPIRY: int = 3600  # Token expiry time in seconds (1 hour)
    
    # Asset Configuration
    DEFAULT_TARGET_LEVEL: int = int(os.getenv("TARGET_LEVEL", "3"))
    
    # Timezone
    TZ_LOCAL: str = os.getenv("TZ_LOCAL", "Asia/Colombo")
    
    # API Settings
    API_PREFIX: str = "/api"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> None:
        """Validate that all required settings are present."""
        if not cls.TB_HOST:
            raise ValueError("TB_HOST environment variable is required")
        if not cls.TB_USERNAME:
            raise ValueError("TB_USERNAME environment variable is required")
        if not cls.TB_PASSWORD:
            raise ValueError("TB_PASSWORD environment variable is required")


# Create global settings instance
settings = Settings()
