"""
Configuration management for the protected chat system
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Settings:
    """Application settings and configuration"""
    
    # Hugging Face Configuration
    HF_MODEL_NAME: str = os.getenv("HF_MODEL_NAME", "microsoft/DialoGPT-medium")
    API_KEY: Optional[str] = os.getenv("API_KEY")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security Configuration
    DEFAULT_SECURITY_MODE: str = os.getenv("DEFAULT_SECURITY_MODE", "Normal")
    MAX_PROMPT_LENGTH: int = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
    ENABLE_METRICS_LOGGING: bool = os.getenv("ENABLE_METRICS_LOGGING", "true").lower() == "true"
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()
