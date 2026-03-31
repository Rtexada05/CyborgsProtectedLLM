"""In-process traffic guard for chat rate limiting and overload protection."""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple

from ..core.config import settings


RATE_WINDOW_SECONDS = 60
DAY_WINDOW_SECONDS = 24 * 60 * 60
RECENT_ALERT_LIMIT = 20


@dataclass
class AdmissionResult:
    """Outcome from a traffic-guard admission decision."""

    admitted: bool
    reason_code: Optional[str] = None
    message: Optional[str] = None
    retry_after_seconds: Optional[int] = None
    active_in_flight: int = 0
    alert_events: List[Dict[str, Any]] = field(default_factory=list)


class TrafficGuard:
    """Single-instance in-memory rate limiter and concurrency guard."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._ip_windows: Dict[str, Deque[float]] = {}
        self._api_key_windows: Dict[str, Deque[float]] = {}
        self._user_minute_windows: Dict[Tuple[str, str], Deque[float]] = {}
        self._user_day_windows: Dict[Tuple[str, str], Deque[float]] = {}
        self._accepted_recent: Deque[float] = deque()
        self._rejected_recent: Deque[float] = deque()
        self._attempt_recent: Deque[float] = deque()
        self._active_in_flight = 0
        self._rejection_counts = {
            "ip_rate_limit": 0,
            "api_key_rate_limit": 0,
            "user_minute_quota": 0,
            "user_daily_quota": 0,
            "concurrency": 0,
            "timeout": 0,
        }
        self._active_alert: Optional[Dict[str, Any]] = None
        self._recent_alerts: Deque[Dict[str, Any]] = deque(maxlen=RECENT_ALERT_LIMIT)
        self._last_alert_monotonic: Optional[float] = None
        self._time = time.monotonic
        self._utcnow = datetime.now

    def reset(self) -> None:
        """Reset all in-memory state for tests."""

        self._ip_windows.clear()
        self._api_key_windows.clear()
        self._user_minute_windows.clear()
        self._user_day_windows.clear()
        self._accepted_recent.clear()
        self._rejected_recent.clear()
        self._attempt_recent.clear()
        self._active_in_flight = 0
        for key in self._rejection_counts:
            self._rejection_counts[key] = 0
        self._active_alert = None
        self._recent_alerts.clear()
        self._last_alert_monotonic = None
        self._time = time.monotonic
        self._utcnow = datetime.now

    async def admit(self, api_key: str, client_ip: str, user_id: str) -> AdmissionResult:
        """Admit or reject a chat request before it reaches the controller."""

        async with self._lock:
            if not settings.ENABLE_TRAFFIC_GUARD:
                return AdmissionResult(admitted=True, active_in_flight=self._active_in_flight)

            now = self._time()
            self._prune_locked(now)

            self._attempt_recent.append(now)

            ip_window = self._window_for(self._ip_windows, client_ip)
            api_window = self._window_for(self._api_key_windows, api_key)
            ip_window.append(now)
            api_window.append(now)

            user_minute_window: Optional[Deque[float]] = None
            user_day_window: Optional[Deque[float]] = None
            if settings.ENABLE_USER_QUOTAS and user_id:
                user_key = (api_key, user_id)
                user_minute_window = self._window_for(self._user_minute_windows, user_key)
                user_day_window = self._window_for(self._user_day_windows, user_key)
                user_minute_window.append(now)
                user_day_window.append(now)

            if len(ip_window) > settings.RATE_LIMIT_IP_PER_MINUTE:
                return self._reject_locked(
                    now=now,
                    count_key="ip_rate_limit",
                    reason_code="ip_rate_limit_exceeded",
                    message="IP rate limit exceeded",
                    retry_after_seconds=self._retry_after_seconds(ip_window, RATE_WINDOW_SECONDS, now),
                )

            if len(api_window) > settings.RATE_LIMIT_API_KEY_PER_MINUTE:
                return self._reject_locked(
                    now=now,
                    count_key="api_key_rate_limit",
                    reason_code="api_key_rate_limit_exceeded",
                    message="API key rate limit exceeded",
                    retry_after_seconds=self._retry_after_seconds(api_window, RATE_WINDOW_SECONDS, now),
                )

            if user_minute_window is not None and len(user_minute_window) > settings.USER_QUOTA_PER_MINUTE:
                return self._reject_locked(
                    now=now,
                    count_key="user_minute_quota",
                    reason_code="user_minute_quota_exceeded",
                    message="User minute quota exceeded",
                    retry_after_seconds=self._retry_after_seconds(user_minute_window, RATE_WINDOW_SECONDS, now),
                )

            if user_day_window is not None and len(user_day_window) > settings.USER_QUOTA_PER_DAY:
                return self._reject_locked(
                    now=now,
                    count_key="user_daily_quota",
                    reason_code="user_daily_quota_exceeded",
                    message="User daily quota exceeded",
                    retry_after_seconds=self._retry_after_seconds(user_day_window, DAY_WINDOW_SECONDS, now),
                )

            if self._active_in_flight >= settings.CHAT_MAX_IN_FLIGHT:
                return self._reject_locked(
                    now=now,
                    count_key="concurrency",
                    reason_code="chat_capacity_exceeded",
                    message="Chat capacity exceeded",
                    retry_after_seconds=1,
                )

            self._active_in_flight += 1
            self._accepted_recent.append(now)
            alert_events = self._update_spike_alert_locked(now)
            return AdmissionResult(
                admitted=True,
                active_in_flight=self._active_in_flight,
                alert_events=alert_events,
            )

    async def release(self, timed_out: bool = False) -> int:
        """Release an in-flight request slot and optionally count a timeout."""

        async with self._lock:
            if self._active_in_flight > 0:
                self._active_in_flight -= 1

            if timed_out and settings.ENABLE_TRAFFIC_GUARD:
                now = self._time()
                self._prune_locked(now)
                self._rejected_recent.append(now)
                self._rejection_counts["timeout"] += 1

            return self._active_in_flight

    async def snapshot(self) -> Dict[str, Any]:
        """Return live abuse-protection metrics and alert state."""

        async with self._lock:
            if not settings.ENABLE_TRAFFIC_GUARD:
                return {
                    "abuse_protection": {
                        "enabled": False,
                        "topology": "single_instance",
                        "limits": self._limits_snapshot(),
                        "live": {
                            "active_in_flight": 0,
                            "requests_last_60s": 0,
                            "rejections_last_60s": 0,
                        },
                        "rejections": dict(self._rejection_counts),
                    },
                    "alerts": {"active": [], "recent": []},
                }

            now = self._time()
            self._prune_locked(now)
            self._refresh_active_alert_locked()

            active_alerts = []
            if self._active_alert is not None:
                active_alert = dict(self._active_alert)
                active_alert["current_value"] = len(self._attempt_recent)
                active_alerts.append(active_alert)

            return {
                "abuse_protection": {
                    "enabled": True,
                    "topology": "single_instance",
                    "limits": self._limits_snapshot(),
                    "live": {
                        "active_in_flight": self._active_in_flight,
                        "requests_last_60s": len(self._accepted_recent),
                        "rejections_last_60s": len(self._rejected_recent),
                    },
                    "rejections": dict(self._rejection_counts),
                },
                "alerts": {
                    "active": active_alerts,
                    "recent": list(self._recent_alerts),
                },
            }

    def fingerprint_api_key(self, api_key: str) -> str:
        """Return a stable redacted fingerprint for an API key."""

        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]

    def _limits_snapshot(self) -> Dict[str, Any]:
        return {
            "ip_per_minute": settings.RATE_LIMIT_IP_PER_MINUTE,
            "api_key_per_minute": settings.RATE_LIMIT_API_KEY_PER_MINUTE,
            "user_per_minute": settings.USER_QUOTA_PER_MINUTE,
            "user_per_day": settings.USER_QUOTA_PER_DAY,
            "user_quotas_enabled": settings.ENABLE_USER_QUOTAS,
            "max_in_flight": settings.CHAT_MAX_IN_FLIGHT,
            "timeout_seconds": settings.CHAT_REQUEST_TIMEOUT_SECONDS,
        }

    def _window_for(self, store: Dict[Any, Deque[float]], key: Any) -> Deque[float]:
        bucket = store.get(key)
        if bucket is None:
            bucket = deque()
            store[key] = bucket
        return bucket

    def _prune_locked(self, now: float) -> None:
        self._prune_mapping(self._ip_windows, RATE_WINDOW_SECONDS, now)
        self._prune_mapping(self._api_key_windows, RATE_WINDOW_SECONDS, now)
        self._prune_mapping(self._user_minute_windows, RATE_WINDOW_SECONDS, now)
        self._prune_mapping(self._user_day_windows, DAY_WINDOW_SECONDS, now)
        self._prune_deque(self._accepted_recent, RATE_WINDOW_SECONDS, now)
        self._prune_deque(self._rejected_recent, RATE_WINDOW_SECONDS, now)
        self._prune_deque(self._attempt_recent, settings.SPIKE_ALERT_WINDOW_SECONDS, now)
        if self._active_alert is not None and len(self._attempt_recent) < settings.SPIKE_ALERT_THRESHOLD_REQUESTS:
            self._active_alert = None

    def _prune_mapping(self, store: Dict[Any, Deque[float]], window_seconds: int, now: float) -> None:
        empty_keys = []
        for key, timestamps in store.items():
            self._prune_deque(timestamps, window_seconds, now)
            if not timestamps:
                empty_keys.append(key)
        for key in empty_keys:
            del store[key]

    def _prune_deque(self, timestamps: Deque[float], window_seconds: int, now: float) -> None:
        cutoff = now - window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

    def _retry_after_seconds(self, timestamps: Deque[float], window_seconds: int, now: float) -> int:
        if not timestamps:
            return 1
        remaining = window_seconds - (now - timestamps[0])
        return max(1, int(math.ceil(remaining)))

    def _reject_locked(
        self,
        now: float,
        count_key: str,
        reason_code: str,
        message: str,
        retry_after_seconds: int,
    ) -> AdmissionResult:
        self._rejected_recent.append(now)
        self._rejection_counts[count_key] += 1
        alert_events = self._update_spike_alert_locked(now)
        return AdmissionResult(
            admitted=False,
            reason_code=reason_code,
            message=message,
            retry_after_seconds=retry_after_seconds,
            active_in_flight=self._active_in_flight,
            alert_events=alert_events,
        )

    def _update_spike_alert_locked(self, now: float) -> List[Dict[str, Any]]:
        current_value = len(self._attempt_recent)
        threshold = settings.SPIKE_ALERT_THRESHOLD_REQUESTS
        if current_value < threshold:
            self._active_alert = None
            return []

        if self._active_alert is None:
            self._active_alert = {
                "code": "chat_request_spike",
                "started_at": self._utcnow().isoformat(),
                "threshold": threshold,
                "window_seconds": settings.SPIKE_ALERT_WINDOW_SECONDS,
                "current_value": current_value,
            }
        else:
            self._active_alert["current_value"] = current_value

        cooldown = settings.SPIKE_ALERT_COOLDOWN_SECONDS
        if self._last_alert_monotonic is not None and now - self._last_alert_monotonic < cooldown:
            return []

        self._last_alert_monotonic = now
        alert = {
            "code": "chat_request_spike",
            "level": "warning",
            "triggered_at": self._utcnow().isoformat(),
            "threshold": threshold,
            "window_seconds": settings.SPIKE_ALERT_WINDOW_SECONDS,
            "current_value": current_value,
        }
        self._recent_alerts.append(alert)
        return [alert]

    def _refresh_active_alert_locked(self) -> None:
        if self._active_alert is None:
            return
        if len(self._attempt_recent) < settings.SPIKE_ALERT_THRESHOLD_REQUESTS:
            self._active_alert = None
            return
        self._active_alert["current_value"] = len(self._attempt_recent)


shared_traffic_guard = TrafficGuard()
