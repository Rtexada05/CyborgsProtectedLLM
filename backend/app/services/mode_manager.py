"""
Global Mode Manager - Centralized security mode management
"""

from typing import Optional
from ..core.security_modes import SecurityMode


class ModeManager:
    """Manages global security mode for the entire application"""
    
    def __init__(self):
        self._current_mode: SecurityMode = SecurityMode.NORMAL
    
    def get_mode(self) -> SecurityMode:
        """Get the current global security mode"""
        return self._current_mode
    
    def set_mode(self, mode: SecurityMode) -> SecurityMode:
        """Set the global security mode and return the new mode"""
        self._current_mode = mode
        return self._current_mode
    
    def get_mode_info(self) -> dict:
        """Get detailed information about current mode"""
        return {
            "mode": self._current_mode,
            "mode_value": self._current_mode.value,
            "description": f"Security mode is set to {self._current_mode.value}"
        }


# Global instance for shared access across the application
shared_mode_manager = ModeManager()
