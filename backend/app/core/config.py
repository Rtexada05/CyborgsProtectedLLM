"""
Configuration management for the protected chat system
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists.
# Override inherited shell values so local test settings take effect reliably.
load_dotenv(override=True)


class Settings:
    """Application settings and configuration"""
    
    # Hugging Face Configuration
    HF_MODEL_NAME: str = os.getenv("HF_MODEL_NAME", "microsoft/DialoGPT-medium")
    HF_PROVIDER: Optional[str] = os.getenv("HF_PROVIDER")
    HF_FALLBACK_PROVIDERS: str = os.getenv("HF_FALLBACK_PROVIDERS", "novita")
    HF_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("HF_REQUEST_TIMEOUT_SECONDS", "20"))
    API_KEY: Optional[str] = os.getenv("API_KEY")
    CLIENT_API_KEY: Optional[str] = os.getenv("CLIENT_API_KEY")
    ADMIN_API_KEY: Optional[str] = os.getenv("ADMIN_API_KEY")
    
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
    CHAT_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("CHAT_REQUEST_TIMEOUT_SECONDS", "30"))
    SPIKE_ALERT_WINDOW_SECONDS: int = int(os.getenv("SPIKE_ALERT_WINDOW_SECONDS", "60"))
    SPIKE_ALERT_THRESHOLD_REQUESTS: int = int(os.getenv("SPIKE_ALERT_THRESHOLD_REQUESTS", "50"))
    SPIKE_ALERT_COOLDOWN_SECONDS: int = int(os.getenv("SPIKE_ALERT_COOLDOWN_SECONDS", "300"))

    # RAG / Vector Database Configuration
    VECTOR_DB_PROVIDER: str = os.getenv("VECTOR_DB_PROVIDER", "qdrant")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "rag_chunks")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() == "true"
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "8"))
    RAG_MAX_CHUNKS_TO_MODEL: int = int(os.getenv("RAG_MAX_CHUNKS_TO_MODEL", "3"))
    RAG_MAX_CHUNKS_PER_SOURCE: int = int(os.getenv("RAG_MAX_CHUNKS_PER_SOURCE", "2"))
    RAG_MAX_CONTEXT_CHARS: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "4000"))
    RAG_ENABLE_UPLOAD_INDEXING: bool = os.getenv("RAG_ENABLE_UPLOAD_INDEXING", "true").lower() == "true"
    RAG_UPLOAD_TTL_SECONDS: int = int(os.getenv("RAG_UPLOAD_TTL_SECONDS", str(24 * 60 * 60)))
    RAG_QUARANTINE_ON_POISON_SCAN: bool = os.getenv("RAG_QUARANTINE_ON_POISON_SCAN", "true").lower() == "true"
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "local-hash-embedding-v1")
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
    EMBEDDING_TIMEOUT_SECONDS: float = float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "5"))
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "128"))
    
    # Conversation Memory Configuration
    MEMORY_ENABLED: bool = os.getenv("MEMORY_ENABLED", "true").lower() == "true"
    MEMORY_DB_PATH: str = os.getenv("MEMORY_DB_PATH", "backend/data/chat_memory.sqlite")
    EVAL_DB_PATH: str = os.getenv("EVAL_DB_PATH", "backend/data/evaluation.sqlite")
    MEMORY_MAX_TURNS_TO_MODEL: int = int(os.getenv("MEMORY_MAX_TURNS_TO_MODEL", "12"))
    MEMORY_MAX_CONTEXT_CHARS: int = int(os.getenv("MEMORY_MAX_CONTEXT_CHARS", "6000"))
    MEMORY_INCLUDE_BLOCKED: bool = os.getenv("MEMORY_INCLUDE_BLOCKED", "true").lower() == "true"
    MEMORY_INCLUDE_SANITIZED: bool = os.getenv("MEMORY_INCLUDE_SANITIZED", "true").lower() == "true"
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()
