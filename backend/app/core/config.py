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
    HF_PROVIDER: Optional[str] = os.getenv("HF_PROVIDER")
    API_KEY: Optional[str] = os.getenv("API_KEY")
    CLIENT_API_KEY: Optional[str] = os.getenv("CLIENT_API_KEY")
    
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
    MAX_RESPONSE_TOKENS: int = int(os.getenv("MAX_RESPONSE_TOKENS", "512"))
    ENABLE_TRAFFIC_GUARD: bool = os.getenv("ENABLE_TRAFFIC_GUARD", "true").lower() == "true"
    TRUST_PROXY_HEADERS: bool = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
    RATE_LIMIT_IP_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_IP_PER_MINUTE", "30"))
    RATE_LIMIT_API_KEY_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_API_KEY_PER_MINUTE", "60"))
    ENABLE_USER_QUOTAS: bool = os.getenv("ENABLE_USER_QUOTAS", "false").lower() == "true"
    USER_QUOTA_PER_MINUTE: int = int(os.getenv("USER_QUOTA_PER_MINUTE", "20"))
    USER_QUOTA_PER_DAY: int = int(os.getenv("USER_QUOTA_PER_DAY", "500"))
    CHAT_MAX_IN_FLIGHT: int = int(os.getenv("CHAT_MAX_IN_FLIGHT", "8"))
    CHAT_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("CHAT_REQUEST_TIMEOUT_SECONDS", "12"))
    SPIKE_ALERT_WINDOW_SECONDS: int = int(os.getenv("SPIKE_ALERT_WINDOW_SECONDS", "60"))
    SPIKE_ALERT_THRESHOLD_REQUESTS: int = int(os.getenv("SPIKE_ALERT_THRESHOLD_REQUESTS", "50"))
    SPIKE_ALERT_COOLDOWN_SECONDS: int = int(os.getenv("SPIKE_ALERT_COOLDOWN_SECONDS", "300"))
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()
