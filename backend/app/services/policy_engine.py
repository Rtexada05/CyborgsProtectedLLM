"""Policy Engine - evaluates security policies and makes decisions."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PolicyEngine:
    """Evaluates security policies and makes allow/sanitize/block decisions."""

    _MAJOR_SIGNAL_KEYS = (
        "prompt_injection_suspected",
        "rag_injection_suspected",
        "rag_poisoning_suspected",
        "rag_cross_user_access_blocked",
        "rag_source_quarantined",
        "tool_abuse_suspected",
        "destructive_tool_requested",
        "command_execution_requested",
        "encoding_obfuscation",
        "steganography_suspected",
        "attachment_risk_suspected",
    )

    async def score_risk(self, signals: Dict[str, Any], mode: str) -> Tuple[int, str]:
        """Score risk on a 0-100 scale with category floors by mode."""

        explicit_flag_prompt = self._has_pattern_prefix(signals, "flag_prompt_pattern_")
        jailbreak_prompt = self._has_jailbreak_prompt(signals)

        score = 0
        if signals.get("prompt_injection_suspected"):
            score += 30
        if signals.get("rag_injection_suspected"):
            score += 28
        if signals.get("rag_poisoning_suspected"):
            score += 35
        if signals.get("rag_cross_user_access_blocked"):
            score += 45
        if signals.get("rag_source_quarantined"):
            score += 20
        if signals.get("tool_abuse_suspected"):
            score += 28
        if signals.get("destructive_tool_requested"):
            score += 35
        if signals.get("command_execution_requested"):
            score += 35
        if signals.get("encoding_obfuscation"):
            score += 25
        if signals.get("steganography_suspected"):
            score += 30
        if signals.get("attachment_risk_suspected"):
            score += 25

        score += min(len(signals.get("pattern_hits", [])) * 4, 18)
        score += min(len(signals.get("suspicious_keywords", [])) * 3, 10)
        score += min(len(signals.get("attachment_pattern_hits", [])) * 4, 12)
        score += min(int(signals.get("rag_chunks_dropped", 0)) * 4, 16)
        score += min(int(signals.get("rag_chunk_sanitized_count", 0)) * 4, 16)
        if explicit_flag_prompt:
            score += 18
        if jailbreak_prompt:
            score += 12

        if signals.get("prompt_injection_suspected") and signals.get("tool_abuse_suspected"):
            score += 18
        if signals.get("destructive_tool_requested") and signals.get("command_execution_requested"):
            score += 20
        if signals.get("prompt_injection_suspected") and signals.get("command_execution_requested"):
            score += 20
        if signals.get("prompt_injection_suspected") and signals.get("rag_injection_suspected"):
            score += 15
        if signals.get("rag_poisoning_suspected") and signals.get("rag_cross_user_access_blocked"):
            score += 25
        if signals.get("encoding_obfuscation") and signals.get("prompt_injection_suspected"):
            score += 15
        if signals.get("attachment_risk_suspected") and (
            signals.get("prompt_injection_suspected") or signals.get("tool_abuse_suspected")
        ):
            score += 15
        if explicit_flag_prompt and jailbreak_prompt:
            score += 25

        mode_bias = {
            "Off": -30,
            "Weak": -5,
            "Normal": 0,
            "Strong": 15,
        }
        score = max(0, min(100, score + mode_bias.get(mode, 0)))

        score = self._apply_mode_floor(score, signals, mode)
        risk_level = self._score_to_level(score)
        return score, risk_level

    def _apply_mode_floor(self, score: int, signals: Dict[str, Any], mode: str) -> int:
        has_major_signal = any(signals.get(key, False) for key in self._MAJOR_SIGNAL_KEYS)
        if not has_major_signal:
            return score

        explicit_flag_prompt = self._has_pattern_prefix(signals, "flag_prompt_pattern_")
        jailbreak_prompt = self._has_jailbreak_prompt(signals)

        floors = {
            "Off": 0,
            "Weak": 25,
            "Normal": 30,
            "Strong": 40,
        }
        score = max(score, floors.get(mode, 40))

        if signals.get("prompt_injection_suspected") and signals.get("tool_abuse_suspected"):
            if mode == "Strong":
                score = max(score, 70)
            elif mode == "Normal":
                score = max(score, 55)
            else:
                score = max(score, 50)
        if signals.get("command_execution_requested"):
            if mode == "Strong":
                score = max(score, 75)
            elif mode == "Normal":
                score = max(score, 60)
            else:
                score = max(score, 55)
        if signals.get("destructive_tool_requested"):
            if mode == "Strong":
                score = max(score, 75)
            elif mode == "Normal":
                score = max(score, 60)
            else:
                score = max(score, 55)
        if signals.get("attachment_risk_suspected") and mode == "Strong":
            score = max(score, 45)
        if signals.get("rag_cross_user_access_blocked"):
            if mode == "Strong":
                score = max(score, 90)
            elif mode == "Normal":
                score = max(score, 80)
            else:
                score = max(score, 70)
        if signals.get("rag_poisoning_suspected"):
            if mode == "Strong":
                score = max(score, 75)
            elif mode == "Normal":
                score = max(score, 55)
            else:
                score = max(score, 50)
        if explicit_flag_prompt:
            if mode == "Strong":
                score = max(score, 60)
            elif mode == "Normal":
                score = max(score, 45)
            else:
                score = max(score, 40)
        if explicit_flag_prompt and jailbreak_prompt:
            if mode == "Strong":
                score = max(score, 80)
            elif mode == "Normal":
                score = max(score, 65)
            else:
                score = max(score, 55)
        return min(score, 100)

    def _has_pattern_prefix(self, signals: Dict[str, Any], prefix: str) -> bool:
        return any(str(hit).startswith(prefix) for hit in signals.get("pattern_hits", []))

    def _has_jailbreak_prompt(self, signals: Dict[str, Any]) -> bool:
        pattern_hits = {str(hit) for hit in signals.get("pattern_hits", [])}
        suspicious_keywords = {str(keyword) for keyword in signals.get("suspicious_keywords", [])}
        return "injection_pattern_9" in pattern_hits or bool(
            {"jailbreak", "override", "bypass"} & suspicious_keywords
        )

    def _score_to_level(self, score: int) -> str:
        if score >= 85:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 30:
            return "MEDIUM"
        return "LOW"

    async def decide_action(self, risk_level: str, mode: str) -> Tuple[str, str]:
        """Decide action based on risk level and mode."""

        if mode == "Off":
            return "ALLOW", "Protection disabled in Off mode"

        if mode == "Strong":
            if risk_level in {"HIGH", "CRITICAL"}:
                return "BLOCK", "High-confidence threat blocked in Strong mode"
            if risk_level == "MEDIUM":
                return "SANITIZE", "Moderately risky content sanitized in Strong mode"
            return "ALLOW", "Low-risk content allowed in Strong mode"

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
            return risk_level == "MEDIUM"
        if mode in {"Weak", "Normal"}:
            return risk_level in {"MEDIUM", "HIGH"}
        return False
