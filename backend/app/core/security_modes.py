"""
Security modes and configurations for the protected chat system
"""

from enum import Enum
from typing import Dict, Any


class SecurityMode(str, Enum):
    """Security modes for the chat system"""
    OFF = "Off"
    WEAK = "Weak"
    NORMAL = "Normal"
    STRONG = "Strong"


class SecurityConfig:
    """Configuration for each security mode"""
    
    MODE_CONFIGS: Dict[SecurityMode, Dict[str, Any]] = {
        SecurityMode.OFF: {
            "enable_input_validation": False,
            "enable_steganography_detection": False,
            "enable_rag_validation": False,
            "enable_tool_gatekeeping": False,
            "max_risk_level": "HIGH",
            "auto_block_threshold": 1.0,
        },
        SecurityMode.WEAK: {
            "enable_input_validation": True,
            "enable_steganography_detection": False,
            "enable_rag_validation": False,
            "enable_tool_gatekeeping": True,
            "max_risk_level": "MEDIUM",
            "auto_block_threshold": 0.8,
        },
        SecurityMode.NORMAL: {
            "enable_input_validation": True,
            "enable_steganography_detection": True,
            "enable_rag_validation": True,
            "enable_tool_gatekeeping": True,
            "max_risk_level": "MEDIUM",
            "auto_block_threshold": 0.6,
        },
        SecurityMode.STRONG: {
            "enable_input_validation": True,
            "enable_steganography_detection": True,
            "enable_rag_validation": True,
            "enable_tool_gatekeeping": True,
            "max_risk_level": "LOW",
            "auto_block_threshold": 0.3,
        }
    }
    
    @classmethod
    def get_config(cls, mode: SecurityMode) -> Dict[str, Any]:
        """Get configuration for a specific security mode"""
        return cls.MODE_CONFIGS.get(mode, cls.MODE_CONFIGS[SecurityMode.NORMAL])
    
    @classmethod
    def is_feature_enabled(cls, mode: SecurityMode, feature: str) -> bool:
        """Check if a feature is enabled for a given security mode"""
        config = cls.get_config(mode)
        return config.get(feature, False)
