"""Policy Engine - evaluates security policies and makes decisions."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PolicyEngine:
    """Evaluates security policies and makes allow/sanitize/block decisions."""

    _MAJOR_SIGNAL_KEYS = (
        "prompt_injection_suspected",
        "rag_injection_suspected",
        "tool_abuse_suspected",
        "destructive_tool_requested",
        "command_execution_requested",
        "encoding_obfuscation",
        "steganography_suspected",
        "attachment_risk_suspected",
    )

    async def score_risk(self, signals: Dict[str, Any], mode: str) -> Tuple[int, str]:
        """Score risk on a 0-100 scale with category floors by mode."""

        score = 0
        if signals.get("prompt_injection_suspected"):
            score += 45
        if signals.get("rag_injection_suspected"):
            score += 35
        if signals.get("tool_abuse_suspected"):
            score += 40
        if signals.get("destructive_tool_requested"):
            score += 30
        if signals.get("command_execution_requested"):
            score += 35
        if signals.get("encoding_obfuscation"):
            score += 40
        if signals.get("steganography_suspected"):
            score += 35
        if signals.get("attachment_risk_suspected"):
            score += 30

        score += min(len(signals.get("pattern_hits", [])) * 6, 30)
        score += min(len(signals.get("suspicious_keywords", [])) * 4, 16)
        score += min(len(signals.get("attachment_pattern_hits", [])) * 5, 20)

        if signals.get("prompt_injection_suspected") and signals.get("tool_abuse_suspected"):
            score += 20
        if signals.get("destructive_tool_requested") and signals.get("command_execution_requested"):
            score += 15
        if signals.get("prompt_injection_suspected") and signals.get("command_execution_requested"):
            score += 20
        if signals.get("prompt_injection_suspected") and signals.get("rag_injection_suspected"):
            score += 15
        if signals.get("encoding_obfuscation") and signals.get("prompt_injection_suspected"):
            score += 15
        if signals.get("attachment_risk_suspected") and (
            signals.get("prompt_injection_suspected") or signals.get("tool_abuse_suspected")
        ):
            score += 15

        mode_bias = {
            "Off": -25,
            "Weak": 0,
            "Normal": 10,
            "Strong": 25,
        }
        score = max(0, min(100, score + mode_bias.get(mode, 0)))

        score = self._apply_mode_floor(score, signals, mode)
        risk_level = self._score_to_level(score)
        return score, risk_level

    def _apply_mode_floor(self, score: int, signals: Dict[str, Any], mode: str) -> int:
        has_major_signal = any(signals.get(key, False) for key in self._MAJOR_SIGNAL_KEYS)
        if not has_major_signal:
            return score

        floors = {
            "Off": 0,
            "Weak": 35,
            "Normal": 40,
            "Strong": 65,
        }
        score = max(score, floors.get(mode, 40))

        if signals.get("prompt_injection_suspected") and signals.get("tool_abuse_suspected"):
            score = max(score, 75 if mode == "Strong" else 50)
        if signals.get("command_execution_requested"):
            if mode == "Strong":
                score = max(score, 85)
            elif mode == "Normal":
                score = max(score, 75)
            else:
                score = max(score, 70)
        if signals.get("destructive_tool_requested"):
            if mode == "Strong":
                score = max(score, 70)
            elif mode == "Normal":
                score = max(score, 65)
            else:
                score = max(score, 65)
        if signals.get("attachment_risk_suspected") and mode == "Strong":
            score = max(score, 65)
        return min(score, 100)

    def _score_to_level(self, score: int) -> str:
        if score >= 90:
            return "CRITICAL"
        if score >= 65:
            return "HIGH"
        if score >= 35:
            return "MEDIUM"
        return "LOW"

    async def decide_action(self, risk_level: str, mode: str) -> Tuple[str, str]:
        """Decide action based on risk level and mode."""

        if mode == "Off":
            return "ALLOW", "Protection disabled in Off mode"

        if mode == "Strong":
            if risk_level in {"HIGH", "CRITICAL"}:
                return "BLOCK", "High-confidence threat blocked in Strong mode"
            return "SANITIZE", "Lower-risk content sanitized in Strong mode"

        if mode == "Normal":
            if risk_level in {"HIGH", "CRITICAL"}:
                return "BLOCK", "High-confidence threat blocked in Normal mode"
            if risk_level == "MEDIUM":
                return "SANITIZE", "Medium-risk content sanitized in Normal mode"
            return "ALLOW", "Low-risk content allowed in Normal mode"

        if mode == "Weak":
            if risk_level == "CRITICAL":
                return "BLOCK", "Critical threat blocked in Weak mode"
            if risk_level in {"MEDIUM", "HIGH"}:
                return "SANITIZE", "Risky content sanitized in Weak mode"
            return "ALLOW", "Low-risk content allowed in Weak mode"

        return "ALLOW", "Request allowed"

    async def needs_sanitization(self, signals: Dict[str, Any], risk_level: str, mode: str) -> bool:
        """Determine if content needs sanitization."""

        if mode == "Off":
            return False

        if mode == "Strong":
            return risk_level in {"LOW", "MEDIUM"}
        if mode in {"Weak", "Normal"}:
            return risk_level in {"MEDIUM", "HIGH"}
        return False
