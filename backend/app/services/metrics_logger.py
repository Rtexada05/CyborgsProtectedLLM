"""
Metrics Logger - logs events and metrics for monitoring
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from collections import deque

from ..core.config import settings


class MetricsLogger:
    """In-memory metrics and event logging"""
    
    def __init__(self):
        # In-memory storage for events (in production, use proper logging/database)
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.metrics = {
            "total_requests": 0,
            "blocked_requests": 0,
            "sanitized_requests": 0,
            "allowed_requests": 0,
            "high_risk_requests": 0,
            "medium_risk_requests": 0,
            "low_risk_requests": 0,
        }
        self.start_time = datetime.now()
        self._lock = asyncio.Lock()

    async def log_event(self, event_data: Dict[str, Any]) -> None:
        """Log an event with timestamp"""
        
        async with self._lock:
            # Add timestamp if not present
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.now()
            
            # Add to events list
            self.events.append(event_data)
            
            # Update metrics
            await self._update_metrics(event_data)
    
    async def _update_metrics(self, event_data: Dict[str, Any]) -> None:
        """Update metrics based on event data"""
        
        event_type = event_data.get("event_type", "")
        
        if event_type == "chat_request":
            self.metrics["total_requests"] += 1
            
            decision = event_data.get("decision", "")
            if decision == "BLOCK":
                self.metrics["blocked_requests"] += 1
            elif decision == "SANITIZE":
                self.metrics["sanitized_requests"] += 1
            elif decision == "ALLOW":
                self.metrics["allowed_requests"] += 1
            
            risk_level = event_data.get("risk_level", "")
            if risk_level == "HIGH":
                self.metrics["high_risk_requests"] += 1
            elif risk_level == "MEDIUM":
                self.metrics["medium_risk_requests"] += 1
            elif risk_level == "LOW":
                self.metrics["low_risk_requests"] += 1
    
    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        
        async with self._lock:
            # Return most recent events
            recent_events = list(self.events)[-limit:]
            
            # Convert datetime objects to strings for JSON serialization
            for event in recent_events:
                if isinstance(event.get("timestamp"), datetime):
                    event["timestamp"] = event["timestamp"].isoformat()
            
            return recent_events
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        
        async with self._lock:
            uptime = datetime.now() - self.start_time
            
            # Calculate rates
            total_requests = self.metrics["total_requests"]
            uptime_hours = uptime.total_seconds() / 3600
            requests_per_hour = total_requests / uptime_hours if uptime_hours > 0 else 0
            
            # Calculate percentages
            blocked_rate = (self.metrics["blocked_requests"] / total_requests * 100) if total_requests > 0 else 0
            sanitized_rate = (self.metrics["sanitized_requests"] / total_requests * 100) if total_requests > 0 else 0
            allowed_rate = (self.metrics["allowed_requests"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self.metrics,
                "uptime_seconds": uptime.total_seconds(),
                "uptime_formatted": str(uptime).split(".")[0],  # Remove microseconds
                "requests_per_hour": round(requests_per_hour, 2),
                "blocked_rate_percent": round(blocked_rate, 2),
                "sanitized_rate_percent": round(sanitized_rate, 2),
                "allowed_rate_percent": round(allowed_rate, 2),
                "high_risk_rate_percent": round(
                    (self.metrics["high_risk_requests"] / total_requests * 100) if total_requests > 0 else 0, 2
                ),
                "medium_risk_rate_percent": round(
                    (self.metrics["medium_risk_requests"] / total_requests * 100) if total_requests > 0 else 0, 2
                ),
                "low_risk_rate_percent": round(
                    (self.metrics["low_risk_requests"] / total_requests * 100) if total_requests > 0 else 0, 2
                ),
            }
    
    async def get_user_activity(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get activity summary for a specific user"""
        
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            user_events = [
                event for event in self.events
                if event.get("user_id") == user_id and 
                   event.get("timestamp", datetime.now()) > cutoff_time
            ]
            
            total_requests = len(user_events)
            blocked_requests = len([e for e in user_events if e.get("decision") == "BLOCK"])
            sanitized_requests = len([e for e in user_events if e.get("decision") == "SANITIZE"])
            allowed_requests = len([e for e in user_events if e.get("decision") == "ALLOW"])
            
            return {
                "user_id": user_id,
                "time_period_hours": hours,
                "total_requests": total_requests,
                "blocked_requests": blocked_requests,
                "sanitized_requests": sanitized_requests,
                "allowed_requests": allowed_requests,
                "blocked_rate_percent": round(
                    (blocked_requests / total_requests * 100) if total_requests > 0 else 0, 2
                ),
                "last_activity": max(
                    [e.get("timestamp") for e in user_events],
                    default=None
                )
            }
    
    async def get_risk_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get risk level trends over time"""
        
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_events = [
                event for event in self.events
                if event.get("timestamp", datetime.now()) > cutoff_time and
                   event.get("event_type") == "chat_request"
            ]
            
            # Group by hour
            hourly_data = {}
            for event in recent_events:
                hour_key = event.get("timestamp").strftime("%Y-%m-%d %H:00")
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
                
                risk_level = event.get("risk_level", "LOW")
                hourly_data[hour_key][risk_level] += 1
            
            return {
                "time_period_hours": hours,
                "hourly_breakdown": hourly_data,
                "total_analyzed": len(recent_events)
            }
    
    async def clear_old_events(self, hours_to_keep: int = 168) -> int:  # 1 week default
        """Clear events older than specified hours"""
        
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
            initial_count = len(self.events)
            
            # Filter out old events
            self.events = deque(
                [event for event in self.events 
                 if event.get("timestamp", datetime.now()) > cutoff_time],
                maxlen=1000
            )
            
            cleared_count = initial_count - len(self.events)
            return cleared_count


# Global shared instance
shared_metrics_logger = MetricsLogger()
