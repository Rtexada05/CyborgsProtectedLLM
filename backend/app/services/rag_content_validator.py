"""RAG content validation and sanitization primitives."""

from __future__ import annotations

import re
from typing import Any, Dict, List


class RAGContentValidator:
    """Validate retrieved RAG chunks before they are passed to the model."""

    def __init__(self) -> None:
        self.malicious_patterns = [
            r"(?i)(password|secret|token|key).*(=|:|is)",
            r"(?i)(sql|injection|drop|delete).*(table|database)",
            r"(?i)(exec|eval|system).*(command|shell)",
            r"(?i)(admin|root).*(access|privilege)",
            r"(?i)(bypass|override).*(security|auth)",
        ]
        self.inappropriate_patterns = [
            r"(?i)(hate|violence|illegal|criminal)",
            r"(?i)(discrimination|harassment|abuse)",
        ]
        self.pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ]
        self.injection_markers = [
            "ignore previous instructions",
            "system prompt",
            "developer message",
            "you are chatgpt",
            "bypass security",
            "admin access",
            "jailbreak",
            "override all safeguards",
            "reveal hidden instructions",
        ]
        self.compiled_malicious = [re.compile(pattern) for pattern in self.malicious_patterns]
        self.compiled_inappropriate = [re.compile(pattern) for pattern in self.inappropriate_patterns]
        self.compiled_pii = [re.compile(pattern) for pattern in self.pii_patterns]

    async def validate_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single retrieved chunk."""

        payload = dict(chunk or {})
        content = str(payload.get("content", ""))
        provenance_ok = bool(payload.get("document_id") and (payload.get("source") or payload.get("source_path")))
        security_label = payload.get("security_label", "user_supplied")
        issues: List[str] = []
        warnings: List[str] = []
        disposition = "allow"
        quarantine_source = False
        sanitized_content = content
        risk_score = 0.0

        if not provenance_ok:
            disposition = "drop"
            issues.append("missing_provenance")
            risk_score += 0.7

        if security_label == "quarantined":
            disposition = "drop"
            issues.append("quarantined_source")
            quarantine_source = True
            risk_score += 0.9

        content_lower = content.lower()
        matched_markers = [marker for marker in self.injection_markers if marker in content_lower]
        if matched_markers:
            issues.extend(f"injection_marker:{marker}" for marker in matched_markers)
            risk_score += 0.7
            if disposition != "drop":
                disposition = "sanitize"
                sanitized_content = self._sanitize_injection_markers(content)
            if len(matched_markers) >= 2:
                quarantine_source = True
                warnings.append("multiple_injection_markers_detected")

        single_validation = await self._validate_single_context(content)
        risk_score += single_validation["risk_score"]
        for issue in single_validation["issues"]:
            issue_type = issue.get("type", "unknown")
            if issue_type not in issues:
                issues.append(issue_type)

        if single_validation["risk_level"] == "HIGH":
            disposition = "drop"
        elif single_validation["risk_level"] == "MEDIUM" and disposition == "allow":
            disposition = "sanitize"

        if self._looks_obfuscated(content):
            issues.append("encoding_obfuscation")
            warnings.append("obfuscated_content_detected")
            risk_score += 0.4
            if disposition == "allow":
                disposition = "sanitize"
                sanitized_content = self._sanitize_injection_markers(sanitized_content)

        if disposition == "sanitize" and not sanitized_content.strip():
            disposition = "drop"
            issues.append("sanitized_to_empty")

        return {
            "is_valid": disposition != "drop",
            "disposition": disposition,
            "content": sanitized_content if disposition == "sanitize" else content,
            "issues": issues,
            "warnings": warnings,
            "risk_score": min(risk_score, 1.0),
            "risk_level": self._determine_risk_level(min(risk_score, 1.0)),
            "quarantine_source": quarantine_source,
            "source_security_label": security_label,
        }

    async def validate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a multi-chunk retrieval result."""

        normalized_context = context if isinstance(context, dict) else {"contexts": [{"content": str(context)}], "metadata": {}}
        original_entries = normalized_context.get("contexts", [])
        validated_entries = []
        flags: List[str] = []
        warnings: List[str] = []
        dropped_count = 0
        sanitized_count = 0
        quarantine_sources: List[str] = []

        for entry in original_entries:
            result = await self.validate_chunk(entry if isinstance(entry, dict) else {"content": str(entry)})
            entry_payload = dict(entry if isinstance(entry, dict) else {"content": str(entry)})
            entry_payload["validation"] = {
                "disposition": result["disposition"],
                "issues": result["issues"],
                "warnings": result["warnings"],
                "risk_level": result["risk_level"],
            }

            if result["disposition"] == "drop":
                dropped_count += 1
                flags.extend(result["issues"])
                if result["quarantine_source"] and entry_payload.get("document_id"):
                    quarantine_sources.append(entry_payload["document_id"])
                continue

            if result["disposition"] == "sanitize":
                sanitized_count += 1
                entry_payload["content"] = result["content"]
                flags.extend(result["issues"])

            warnings.extend(result["warnings"])
            validated_entries.append(entry_payload)

        raw_context_text = "\n".join(entry.get("content", "") for entry in validated_entries if isinstance(entry, dict))
        context_safe = dropped_count == 0 and sanitized_count == 0 and not flags

        metadata = dict(normalized_context.get("metadata", {}))
        metadata.update(
            {
                "validated_contexts": len(validated_entries),
                "dropped_contexts": dropped_count,
                "sanitized_contexts": sanitized_count,
                "warnings": list(dict.fromkeys(warnings)),
                "quarantine_sources": list(dict.fromkeys(quarantine_sources)),
            }
        )

        return {
            "context_safe": context_safe,
            "context_flags": list(dict.fromkeys(flags)),
            "clean_context": raw_context_text,
            "normalized_context": {
                "contexts": validated_entries,
                "metadata": metadata,
            },
        }

    async def _validate_single_context(self, content: str) -> Dict[str, Any]:
        """Validate a single context payload for harmful content classes."""

        risk_score = 0.0
        issues = []

        for i, pattern in enumerate(self.compiled_malicious):
            matches = pattern.findall(content)
            if matches:
                risk_score += 0.4
                issues.append({"type": "malicious_content", "pattern": self.malicious_patterns[i]})

        for i, pattern in enumerate(self.compiled_inappropriate):
            matches = pattern.findall(content)
            if matches:
                risk_score += 0.25
                issues.append({"type": "inappropriate_content", "pattern": self.inappropriate_patterns[i]})

        for i, pattern in enumerate(self.compiled_pii):
            matches = pattern.findall(content)
            if matches:
                risk_score += 0.5
                issues.append({"type": "pii_detected", "pattern": self.pii_patterns[i]})

        if self._has_suspicious_formatting(content):
            risk_score += 0.2
            issues.append({"type": "suspicious_formatting"})

        if len(content) > 5000:
            risk_score += 0.1
            issues.append({"type": "excessive_length"})

        risk_score = min(risk_score, 1.0)
        return {
            "is_valid": risk_score < 0.7,
            "risk_score": risk_score,
            "risk_level": self._determine_risk_level(risk_score),
            "issues": issues,
        }

    def _sanitize_injection_markers(self, content: str) -> str:
        lines = []
        for line in content.splitlines():
            lowered = line.lower()
            if any(marker in lowered for marker in self.injection_markers):
                lines.append("[REDACTED_RAG_INSTRUCTION]")
            else:
                lines.append(line)
        return "\n".join(lines)

    def _looks_obfuscated(self, content: str) -> bool:
        return bool(
            re.search(r'\\[uU][0-9a-fA-F]{4}', content)
            or re.search(r'(?i)base64', content)
            or re.search(r'(?i)encodedcommand', content)
        )

    def _has_suspicious_formatting(self, content: str) -> bool:
        if not content:
            return False
        special_char_ratio = sum(1 for c in content if not c.isalnum() and not c.isspace()) / len(content)
        if special_char_ratio > 0.3:
            return True
        if re.search(r'(.)\1{10,}', content):
            return True
        return False

    def _determine_risk_level(self, risk_score: float) -> str:
        if risk_score >= 0.7:
            return "HIGH"
        if risk_score >= 0.4:
            return "MEDIUM"
        return "LOW"
