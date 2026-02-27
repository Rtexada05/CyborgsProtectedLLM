"""
Metrics Logger - logs events and metrics for monitoring
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import asyncio
from collections import deque


class MetricsLogger:
    """In-memory metrics and event logging"""
    
    def __init__(self):
        # In-memory storage for events (in production, use proper logging/database)
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.decisions = deque(maxlen=1000)
        self.trace_ids_seen = set()
        self.start_time = datetime.now()
        self._lock = asyncio.Lock()

    def _parse_timestamp(self, timestamp: Any) -> datetime:
        """Normalize timestamp values to datetime for internal comparisons."""
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                return datetime.now()
        return datetime.now()

    def _serialize_timestamp(self, timestamp: Any) -> str:
        """Serialize timestamp values as ISO-8601 strings for API responses."""
        return self._parse_timestamp(timestamp).isoformat()

    def _compute_decision_metrics(self) -> Dict[str, Any]:
        """Compute request-level metrics from decision records."""
        decision_distribution = {"BLOCK": 0, "SANITIZE": 0, "ALLOW": 0}
        risk_distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for record in self.decisions:
            decision = record.get("decision", "ALLOW")
            if decision in decision_distribution:
                decision_distribution[decision] += 1

            risk_level = record.get("risk_level", "LOW")
            if risk_level not in risk_distribution:
                risk_distribution[risk_level] = 0
            risk_distribution[risk_level] += 1

        total_requests = len(self.trace_ids_seen)

        return {
            "total_requests": total_requests,
            "blocked_requests": decision_distribution["BLOCK"],
            "sanitized_requests": decision_distribution["SANITIZE"],
            "allowed_requests": decision_distribution["ALLOW"],
            "high_risk_requests": risk_distribution.get("HIGH", 0),
            "medium_risk_requests": risk_distribution.get("MEDIUM", 0),
            "low_risk_requests": risk_distribution.get("LOW", 0),
            "decision_distribution": decision_distribution,
            "risk_distribution": risk_distribution,
        }

    async def log_event(self, event_type: str, trace_id: str, user_id: str, details: Dict[str, Any]):
        """Log an event with trace tracking"""
        
        async with self._lock:
            event = {
                "trace_id": trace_id,
                "timestamp": datetime.now(),
                "user_id": user_id,
                "event_type": event_type,
                "details": details
            }
            
            self.events.append(event)
    
    async def log_decision(self, trace_id: str, user_id: str, mode: str, risk_score: int, risk_level: str, decision: str, reason: str):
        """Log a decision with full details"""
        
        async with self._lock:
            decision_record = {
                "trace_id": trace_id,
                "timestamp": datetime.now(),
                "user_id": user_id,
                "mode": mode,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "decision": decision,
                "reason": reason
            }

            self.decisions.append(decision_record)
            self.trace_ids_seen.add(trace_id)
    
    async def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        
        async with self._lock:
            # Get most recent events
            recent_events = list(self.events)[-limit:]
            
            # Convert to dict format
            return [
                {
                    "trace_id": event["trace_id"],
                    "timestamp": self._serialize_timestamp(event["timestamp"]),
                    "user_id": event["user_id"],
                    "event_type": event["event_type"],
                    "details": event["details"]
                }
                for event in recent_events
            ]
    
    async def get_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent decisions"""
        
        async with self._lock:
            # Get most recent decisions
            recent_decisions = list(self.decisions)[-limit:]

            return [
                {
                    **decision,
                    "timestamp": self._serialize_timestamp(decision.get("timestamp"))
                }
                for decision in recent_decisions
            ]
    
    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        
        async with self._lock:
            # Return most recent events
            recent_events = list(self.events)[-limit:]
            
            # Convert datetime objects to strings for JSON serialization
            for event in recent_events:
                event["timestamp"] = self._serialize_timestamp(event.get("timestamp"))
            
            return recent_events
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        
        async with self._lock:
            uptime = datetime.now() - self.start_time
            metrics = self._compute_decision_metrics()
            
            # Calculate rates
            total_requests = metrics["total_requests"]
            uptime_hours = uptime.total_seconds() / 3600
            requests_per_hour = total_requests / uptime_hours if uptime_hours > 0 else 0
            
            # Calculate percentages
            blocked_rate = (metrics["blocked_requests"] / total_requests * 100) if total_requests > 0 else 0
            sanitized_rate = (metrics["sanitized_requests"] / total_requests * 100) if total_requests > 0 else 0
            allowed_rate = (metrics["allowed_requests"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **metrics,
                "uptime_seconds": uptime.total_seconds(),
                "uptime_formatted": str(uptime).split(".")[0],  # Remove microseconds
                "requests_per_hour": round(requests_per_hour, 2),
                "blocked_rate_percent": round(blocked_rate, 2),
                "sanitized_rate_percent": round(sanitized_rate, 2),
                "allowed_rate_percent": round(allowed_rate, 2),
                "high_risk_rate_percent": round(
                    (metrics["high_risk_requests"] / total_requests * 100) if total_requests > 0 else 0, 2
                ),
                "medium_risk_rate_percent": round(
                    (metrics["medium_risk_requests"] / total_requests * 100) if total_requests > 0 else 0, 2
                ),
                "low_risk_rate_percent": round(
                    (metrics["low_risk_requests"] / total_requests * 100) if total_requests > 0 else 0, 2
                ),
            }

    async def get_admin_metrics(self) -> Dict[str, Any]:
        """Aggregate KPI metrics for admin dashboards and reporting."""
        base_metrics = await self.get_metrics()
        total_requests = base_metrics["total_requests"]
        total_decisions = len(self.decisions)

        attack_success_rate = round(
            (base_metrics["allowed_requests"] / total_requests * 100) if total_requests > 0 else 0,
            2,
        )
        false_positive_proxy_rate = round(
            (base_metrics["blocked_requests"] / total_requests * 100) if total_requests > 0 else 0,
            2,
        )

        return {
            "traffic": {
                "total_chat_traces": total_requests,
                "total_decision_records": total_decisions,
                "requests_per_hour": base_metrics["requests_per_hour"],
            },
            "decisions": {
                "distribution": base_metrics["decision_distribution"],
                "blocked_rate_percent": base_metrics["blocked_rate_percent"],
                "sanitized_rate_percent": base_metrics["sanitized_rate_percent"],
                "allowed_rate_percent": base_metrics["allowed_rate_percent"],
            },
            "risk": {
                "distribution": base_metrics["risk_distribution"],
                "high_risk_rate_percent": base_metrics["high_risk_rate_percent"],
                "medium_risk_rate_percent": base_metrics["medium_risk_rate_percent"],
                "low_risk_rate_percent": base_metrics["low_risk_rate_percent"],
            },
            "kpis": {
                "attack_success_rate_percent": attack_success_rate,
                "false_positive_proxy_percent": false_positive_proxy_rate,
                "throughput_rps_placeholder": None,
                "latency_p50_ms_placeholder": None,
                "latency_p95_ms_placeholder": None,
            },
            "generated_at": datetime.now().isoformat(),
        }
    
    async def get_user_activity(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get activity summary for a specific user"""
        
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            user_events = [
                event for event in self.events
                if event.get("user_id") == user_id and 
                   self._parse_timestamp(event.get("timestamp")) > cutoff_time
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
                    [self._serialize_timestamp(e.get("timestamp")) for e in user_events],
                    default=None
                )
            }
    
    async def get_risk_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get risk level trends over time"""
        
        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_events = [
                event for event in self.events
                if self._parse_timestamp(event.get("timestamp")) > cutoff_time and
                   event.get("event_type") == "chat_request"
            ]
            
            # Group by hour
            hourly_data = {}
            for event in recent_events:
                hour_key = self._parse_timestamp(event.get("timestamp")).strftime("%Y-%m-%d %H:00")
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
                 if self._parse_timestamp(event.get("timestamp")) > cutoff_time],
                maxlen=1000
            )
            
            cleared_count = initial_count - len(self.events)
            return cleared_count


# Global shared instance
shared_metrics_logger = MetricsLogger()
