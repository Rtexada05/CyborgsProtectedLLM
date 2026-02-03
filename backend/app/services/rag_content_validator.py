"""
RAG Content Validator - validates retrieved RAG content
"""

from typing import List, Dict, Any, Optional
import re

from ..models.schemas import SecuritySignal


class RAGContentValidator:
    """Validates retrieved RAG content for safety and appropriateness"""
    
    def __init__(self):
        # Malicious content patterns in RAG content
        self.malicious_patterns = [
            r"(?i)(password|secret|token|key).*(=|:|is)",
            r"(?i)(sql|injection|drop|delete).*(table|database)",
            r"(?i)(exec|eval|system).*(command|shell)",
            r"(?i)(admin|root).*(access|privilege)",
            r"(?i)(bypass|override).*(security|auth)",
        ]
        
        # Inappropriate content patterns
        self.inappropriate_patterns = [
            r"(?i)(hate|violence|illegal|criminal)",
            r"(?i)(discrimination|harassment|abuse)",
        ]
        
        # Personal information patterns
        self.pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        ]
        
        self.compiled_malicious = [re.compile(pattern) for pattern in self.malicious_patterns]
        self.compiled_inappropriate = [re.compile(pattern) for pattern in self.inappropriate_patterns]
        self.compiled_pii = [re.compile(pattern) for pattern in self.pii_patterns]
    
    async def validate_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate retrieved RAG context"""
        
        if not context_data or "contexts" not in context_data:
            return {
                "is_valid": False,
                "reason": "No context data provided",
                "risk_level": "HIGH"
            }
        
        contexts = context_data.get("contexts", [])
        validation_results = []
        overall_risk_score = 0.0
        
        for ctx in contexts:
            content = ctx.get("content", "")
            result = await self._validate_single_context(content)
            validation_results.append(result)
            overall_risk_score += result["risk_score"]
        
        # Calculate average risk score
        if contexts:
            overall_risk_score /= len(contexts)
        
        # Make overall decision
        is_valid = overall_risk_score < 0.7
        risk_level = self._determine_risk_level(overall_risk_score)
        
        # Check for any high-risk individual contexts
        for result in validation_results:
            if result["risk_level"] == "HIGH":
                is_valid = False
                risk_level = "HIGH"
                break
        
        return {
            "is_valid": is_valid,
            "risk_level": risk_level,
            "overall_risk_score": overall_risk_score,
            "validation_results": validation_results,
            "reason": self._generate_validation_reason(is_valid, risk_level, validation_results)
        }
    
    async def _validate_single_context(self, content: str) -> Dict[str, Any]:
        """Validate a single context content"""
        
        risk_score = 0.0
        issues = []
        
        # Check for malicious patterns
        for i, pattern in enumerate(self.compiled_malicious):
            matches = pattern.findall(content)
            if matches:
                risk_score += 0.4
                issues.append({
                    "type": "malicious_content",
                    "pattern": self.malicious_patterns[i],
                    "matches": matches[:2]
                })
        
        # Check for inappropriate content
        for i, pattern in enumerate(self.compiled_inappropriate):
            matches = pattern.findall(content)
            if matches:
                risk_score += 0.3
                issues.append({
                    "type": "inappropriate_content",
                    "pattern": self.inappropriate_patterns[i],
                    "matches": matches[:2]
                })
        
        # Check for PII
        for i, pattern in enumerate(self.compiled_pii):
            matches = pattern.findall(content)
            if matches:
                risk_score += 0.5
                issues.append({
                    "type": "pii_detected",
                    "pattern": self.pii_patterns[i],
                    "matches": matches[:2]  # Limit for privacy
                })
        
        # Check for suspicious formatting
        if self._has_suspicious_formatting(content):
            risk_score += 0.2
            issues.append({
                "type": "suspicious_formatting",
                "description": "Unusual formatting detected"
            })
        
        # Check for extremely long content (potential injection)
        if len(content) > 5000:
            risk_score += 0.1
            issues.append({
                "type": "excessive_length",
                "length": len(content)
            })
        
        # Cap risk score
        risk_score = min(risk_score, 1.0)
        
        return {
            "is_valid": risk_score < 0.7,
            "risk_score": risk_score,
            "risk_level": self._determine_risk_level(risk_score),
            "issues": issues
        }
    
    def _has_suspicious_formatting(self, content: str) -> bool:
        """Check for suspicious formatting in content"""
        
        # Check for excessive special characters
        special_char_ratio = sum(1 for c in content if not c.isalnum() and not c.isspace()) / len(content)
        if special_char_ratio > 0.3:
            return True
        
        # Check for repeated patterns
        if re.search(r'(.)\1{10,}', content):
            return True
        
        # Check for unusual encoding indicators
        if re.search(r'\\[uU][0-9a-fA-F]{4}', content):
            return True
        
        return False
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 0.7:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_validation_reason(
        self,
        is_valid: bool,
        risk_level: str,
        validation_results: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable validation reason"""
        
        if not is_valid:
            if risk_level == "HIGH":
                return "Context blocked: High-risk content detected (malicious patterns or PII)"
            else:
                return "Context blocked: Medium-risk content detected"
        else:
            if risk_level == "MEDIUM":
                return "Context approved with caution: Some minor issues detected"
            else:
                return "Context approved: No significant issues detected"
