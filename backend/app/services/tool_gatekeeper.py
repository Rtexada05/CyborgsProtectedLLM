"""Tool Gatekeeper - controls access to system tools and functions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import re


class ToolGatekeeper:
    """Controls access to system tools and prevents tool abuse."""

    def __init__(self):
        self.high_risk_prompt_patterns = [
            re.compile(r"(?i)(reveal|dump|exfiltrate|steal|leak|credentials|secret|token|password)"),
            re.compile(r"(?i)(internal|private|confidential|payroll|system prompt|hidden rules)"),
            re.compile(r"(?i)(ignore|bypass|override).*(security|safeguard|filter)"),
        ]

    async def detect_requested_tools(self, prompt: str, requested_tools: Optional[List[str]]) -> List[str]:
        """Detect requested tools from prompt or explicit list."""

        if requested_tools:
            return list(dict.fromkeys(requested_tools))

        prompt_lower = prompt.lower()
        detected_tools = []

        if re.search(r"(?i)(calculate|compute|solve|math).*(\d+|formula|equation)", prompt) or re.search(r"(?i)\d+\s*[\+\-\*\/]\s*\d+", prompt):
            detected_tools.append("calculator")

        if re.search(r"(?i)(read|open|load|access).*(file|document|data)", prompt) or re.search(r"(?i)\.(txt|csv|json|xml|log|pdf)", prompt):
            detected_tools.append("file_reader")

        if re.search(r"(?i)(write|save|create|append|modify|update).*(file|document|data)", prompt):
            detected_tools.append("write_file")

        if re.search(r"(?i)(browse|search|surf).*(web|internet)", prompt) or re.search(r"(?i)(look up|find).*(online|website)", prompt):
            detected_tools.append("web")

        if re.search(r"(?i)(database|sql|query|table|records|rows|popularity)", prompt):
            detected_tools.append("database")

        if re.search(r"(?i)(execute|run|launch|invoke).*(command|shell|terminal|powershell|cmd|script)", prompt):
            detected_tools.append("execute_command")

        return list(dict.fromkeys(detected_tools))

    def _is_adversarial_prompt(self, prompt: str, signals: Optional[Dict[str, Any]]) -> bool:
        prompt_lower = prompt.lower()
        if any(pattern.search(prompt_lower) for pattern in self.high_risk_prompt_patterns):
            return True

        signals = signals or {}
        return any(
            signals.get(key, False)
            for key in (
                "prompt_injection_suspected",
                "rag_injection_suspected",
                "encoding_obfuscation",
                "attachment_risk_suspected",
            )
        )

    async def authorize_tools(
        self,
        tools: List[str],
        mode: str,
        risk_level: str,
        prompt: str = "",
        signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Authorize tools using tool-specific policy and adversarial overrides."""

        tool_decisions: Dict[str, str] = {}
        allowed_tools: List[str] = []
        adversarial = self._is_adversarial_prompt(prompt, signals)

        for tool in tools:
            allowed = False

            if mode == "Off":
                allowed = True
            elif tool == "calculator":
                allowed = risk_level == "LOW" or (mode == "Normal" and risk_level == "MEDIUM" and not adversarial)
            elif tool == "database":
                allowed = mode in {"Normal", "Weak"} and risk_level == "LOW" and not adversarial
            elif tool in {"file_reader", "web"}:
                allowed = mode == "Normal" and risk_level == "LOW" and not adversarial
            elif tool in {"write_file", "execute_command"}:
                allowed = False

            if mode == "Strong" and tool != "calculator":
                allowed = False

            if tool == "calculator" and mode == "Strong":
                allowed = risk_level == "LOW" and not adversarial

            tool_decisions[tool] = "allowed" if allowed else "denied"
            if allowed:
                allowed_tools.append(tool)

        tools_allowed = len(allowed_tools) == len(tools)
        reason = "Tools allowed" if tools_allowed else "One or more requested tools were denied by security policy"
        if adversarial and tools:
            reason = "Tool access denied due to adversarial prompt indicators"

        return {
            "tools_allowed": tools_allowed,
            "allowed_tools": allowed_tools,
            "tool_decisions": tool_decisions,
            "tool_reason": reason,
        }
