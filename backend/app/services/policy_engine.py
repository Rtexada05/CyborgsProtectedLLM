"""
Policy Engine - evaluates security policies and makes decisions
"""

from typing import List, Dict, Any
from datetime import datetime
import re

from ..core.security_modes import SecurityMode, SecurityConfig
from ..models.schemas import SecuritySignal


class PolicyEngine:
    """Evaluates security policies and makes allow/sanitize/block decisions"""
    
    def __init__(self):
        self.injection_patterns = [
            "ignore previous instructions",
            "system prompt",
            "admin access",
            "bypass security",
            "jailbreak",
            "roleplay as"
        ]
        
        self.high_risk_keywords = [
            "password", "token", "api key", "secret",
            "delete", "drop", "exec", "eval"
        ]
        
        # Adaptive thresholds based on attack patterns
        self.adaptive_thresholds = {
            "low_risk": 0.3,
            "medium_risk": 0.6,
            "high_risk": 0.8,
            "critical_risk": 0.9
        }
        
        # Pattern risk weights
        self.pattern_weights = {
            "prompt_injection": 0.8,
            "suspicious_content": 0.6,
            "pattern_combination": 0.9,
            "keyword_combination": 0.95,
            "high_risk_combination": 1.0,
            "excessive_length": 0.4,
            "repeated_chars": 0.3,
            "encoding_indicators": 0.5,
            "steganography_detected": 0.7,
            "tool_abuse_blocked": 0.8,
            "rag_content_blocked": 0.6
        }
    
    async def evaluate_prompt(
        self,
        prompt: str,
        signals: List[SecuritySignal],
        mode: SecurityMode,
        risk_factors: List[str]
    ) -> Dict[str, Any]:
        """Evaluate a prompt and return security decision"""
        
        # Calculate risk score
        risk_score = await self._calculate_risk_score(prompt, signals, risk_factors)
        
        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)
        
        # Get mode configuration
        config = SecurityConfig.get_config(mode)
        
        # Make decision based on risk score and mode
        decision = await self._make_decision(risk_score, risk_level, mode, config)
        
        # Generate reason
        reason = await self._generate_reason(decision, risk_factors, signals)
        
        return {
            "decision": decision,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reason": reason,
            "signals_analyzed": len(signals)
        }
    
    async def _calculate_risk_score(
        self,
        prompt: str,
        signals: List[SecuritySignal],
        risk_factors: List[str]
    ) -> float:
        """Calculate overall risk score (0.0 to 1.0) with multi-factor assessment"""
        
        risk_score = 0.0
        
        # Base risk from signals (weighted)
        signal_risk = 0.0
        for signal in signals:
            weight = self.pattern_weights.get(signal.signal_type, 0.5)
            signal_risk += signal.confidence * weight
        
        # Normalize signal risk
        risk_score += min(signal_risk * 0.4, 0.4)  # Cap at 0.4
        
        # Risk from factors (weighted)
        factor_weights = {
            "input_validation_issues": 0.4,
            "steganography_detected": 0.5,
            "rag_content_blocked": 0.3,
            "tool_abuse_blocked": 0.4
        }
        
        for factor in risk_factors:
            weight = factor_weights.get(factor, 0.2)
            risk_score += weight
        
        # Pattern analysis bonus
        pattern_bonus = await self._analyze_pattern_complexity(prompt, signals)
        risk_score += pattern_bonus * 0.2
        
        # Contextual analysis
        context_risk = await self._analyze_context(prompt)
        risk_score += context_risk * 0.2
        
        # Structural analysis
        structural_risk = await self._analyze_structure(prompt)
        risk_score += structural_risk * 0.1
        
        # Length and complexity analysis
        complexity_risk = await self._analyze_complexity(prompt)
        risk_score += complexity_risk * 0.1
        
        # Cap at 1.0
        return min(risk_score, 1.0)
    
    async def _analyze_pattern_complexity(self, prompt: str, signals: List[SecuritySignal]) -> float:
        """Analyze the complexity and sophistication of attack patterns"""
        
        complexity_score = 0.0
        
        # Check for multi-signal attacks
        if len(signals) > 3:
            complexity_score += 0.3
        
        # Check for diverse signal types
        signal_types = set(signal.signal_type for signal in signals)
        if len(signal_types) > 2:
            complexity_score += 0.2
        
        # Check for encoding attempts
        encoding_signals = [s for s in signals if "encoding" in s.signal_type.lower()]
        if encoding_signals:
            complexity_score += 0.3
        
        # Check for combination attacks
        combination_signals = [s for s in signals if "combination" in s.signal_type.lower()]
        if combination_signals:
            complexity_score += 0.4
        
        # Check for structural attacks
        if any(keyword in prompt.lower() for keyword in ["```", "{{", "[SYSTEM]", "<system>"]):
            complexity_score += 0.2
        
        return min(complexity_score, 1.0)
    
    async def _analyze_context(self, prompt: str) -> float:
        """Analyze contextual risk factors"""
        
        context_risk = 0.0
        prompt_lower = prompt.lower()
        
        # Check for role manipulation attempts
        role_indicators = ["act as", "pretend to be", "you are now", "from now on"]
        if any(indicator in prompt_lower for indicator in role_indicators):
            context_risk += 0.3
        
        # Check for instruction override attempts
        override_indicators = ["ignore", "forget", "disregard", "skip", "bypass"]
        if any(indicator in prompt_lower for indicator in override_indicators):
            context_risk += 0.4
        
        # Check for system access attempts
        system_indicators = ["system prompt", "admin access", "root privileges", "developer mode"]
        if any(indicator in prompt_lower for indicator in system_indicators):
            context_risk += 0.5
        
        # Check for multi-step attacks
        step_indicators = ["step 1", "phase 1", "first", "then", "next"]
        if sum(indicator in prompt_lower for indicator in step_indicators) > 1:
            context_risk += 0.3
        
        return min(context_risk, 1.0)
    
    async def _analyze_structure(self, prompt: str) -> float:
        """Analyze structural risk factors"""
        
        structure_risk = 0.0
        
        # Check for unusual formatting
        if re.search(r'[{}[\]<>]', prompt):
            structure_risk += 0.2
        
        # Check for code blocks
        if re.search(r'```', prompt):
            structure_risk += 0.3
        
        # Check for template syntax
        if re.search(r'\{\{|\$\{', prompt):
            structure_risk += 0.3
        
        # Check for excessive punctuation
        punctuation_ratio = sum(1 for c in prompt if not c.isalnum() and not c.isspace()) / len(prompt)
        if punctuation_ratio > 0.2:
            structure_risk += 0.2
        
        # Check for unusual line breaks
        lines = prompt.split('\n')
        if len(lines) > 10:
            structure_risk += 0.1
        
        return min(structure_risk, 1.0)
    
    async def _analyze_complexity(self, prompt: str) -> float:
        """Analyze prompt complexity and potential for obfuscation"""
        
        complexity_risk = 0.0
        
        # Length-based risk
        if len(prompt) > 2000:
            complexity_risk += 0.2
        elif len(prompt) > 5000:
            complexity_risk += 0.4
        
        # Word diversity
        words = prompt.split()
        unique_words = set(word.lower() for word in words)
        if len(unique_words) / len(words) < 0.3:  # Low diversity
            complexity_risk += 0.2
        
        # Capitalization patterns
        upper_ratio = sum(1 for c in prompt if c.isupper()) / len(prompt)
        if upper_ratio > 0.3:
            complexity_risk += 0.1
        
        # Special character density
        special_ratio = sum(1 for c in prompt if not c.isalnum() and not c.isspace()) / len(prompt)
        if special_ratio > 0.15:
            complexity_risk += 0.2
        
        return min(complexity_risk, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 0.7:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _make_decision(
        self,
        risk_score: float,
        risk_level: str,
        mode: SecurityMode,
        config: Dict[str, Any]
    ) -> str:
        """Make final decision based on risk score and mode with adaptive thresholds"""
        
        # Get adaptive thresholds based on mode
        thresholds = self._get_adaptive_thresholds(mode)
        
        # Critical risk - always block
        if risk_score >= thresholds["critical_risk"]:
            return "BLOCK"
        
        # High risk - mode-dependent
        if risk_score >= thresholds["high_risk"]:
            if mode in [SecurityMode.OFF, SecurityMode.WEAK]:
                return "SANITIZE"
            else:
                return "BLOCK"
        
        # Medium risk - mode-dependent
        if risk_score >= thresholds["medium_risk"]:
            if mode == SecurityMode.OFF:
                return "ALLOW"
            elif mode == SecurityMode.WEAK:
                return "SANITIZE"
            else:
                return "SANITIZE"
        
        # Low risk - usually allow
        if risk_score >= thresholds["low_risk"]:
            return "ALLOW" if mode != SecurityMode.STRONG else "SANITIZE"
        
        # Very low risk - always allow
        return "ALLOW"
    
    async def score_risk(self, signals: Dict[str, Any], mode: str) -> tuple[int, str]:
        """Score risk on 0-100 scale with mode-dependent weights"""
        
        # Base score calculation
        base_score = 0
        
        # Prompt injection signals
        if signals.get("prompt_injection_suspected", False):
            base_score += 30
        
        # RAG injection signals
        if signals.get("rag_injection_suspected", False):
            base_score += 20
        
        # Tool abuse signals
        if signals.get("tool_abuse_suspected", False):
            base_score += 25
        
        # Encoding obfuscation
        if signals.get("encoding_obfuscation", False):
            base_score += 35
        
        # Pattern hits (each hit adds points)
        pattern_hits = len(signals.get("pattern_hits", []))
        base_score += min(pattern_hits * 5, 25)
        
        # Suspicious keywords (each keyword adds points)
        suspicious_keywords = len(signals.get("suspicious_keywords", []))
        base_score += min(suspicious_keywords * 3, 20)
        
        # Mode-dependent weight adjustment
        mode_weights = {
            "Off": 0.1,      # Very lenient
            "Weak": 0.4,     # More lenient  
            "Normal": 0.7,    # Standard
            "Strong": 1.2       # Strict (amplifies score)
        }
        
        weight = mode_weights.get(mode, 0.7)
        final_score = int(min(base_score * weight, 100))
        
        # Map to risk level
        if final_score >= 75:
            risk_level = "CRITICAL"
        elif final_score >= 50:
            risk_level = "HIGH"
        elif final_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        print(f"DEBUG: Risk scoring - Base: {base_score}, Weight: {weight}, Final: {final_score}, Level: {risk_level}")
        return final_score, risk_level
    
    async def decide_action(self, risk_level: str, mode: str) -> tuple[str, str]:
        """Decide action based on risk level and mode"""
        
        decision_rules = {
            "Off": {
                "LOW": ("ALLOW", "Request allowed in Off mode"),
                "MEDIUM": ("ALLOW", "Request allowed in Off mode"),
                "HIGH": ("SANITIZE", "High risk sanitized in Off mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked even in Off mode")
            },
            "Weak": {
                "LOW": ("ALLOW", "Low risk allowed in Weak mode"),
                "MEDIUM": ("SANITIZE", "Medium risk sanitized in Weak mode"),
                "HIGH": ("SANITIZE", "High risk sanitized in Weak mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked in Weak mode")
            },
            "Normal": {
                "LOW": ("ALLOW", "Low risk allowed in Normal mode"),
                "MEDIUM": ("SANITIZE", "Medium risk sanitized in Normal mode"),
                "HIGH": ("SANITIZE", "High risk sanitized in Normal mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked in Normal mode")
            },
            "Strong": {
                "LOW": ("SANITIZE", "Low risk sanitized in Strong mode"),
                "MEDIUM": ("SANITIZE", "Medium risk sanitized in Strong mode"),
                "HIGH": ("BLOCK", "High risk blocked in Strong mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked in Strong mode")
            }
        }
        
        decision, reason = decision_rules.get(mode, {}).get(risk_level, ("BLOCK", "Unknown mode/risk combination"))
        print(f"DEBUG: Decision - Mode: {mode}, Risk: {risk_level}, Action: {decision}")
        return decision, reason
    
    async def needs_sanitization(self, signals: Dict[str, Any], risk_level: str, mode: str) -> bool:
        """Determine if content needs sanitization"""
        
        # Direct sanitization rules
        if mode == "Strong":
            return risk_level in ["LOW", "MEDIUM"]
        elif mode == "Normal":
            return risk_level in ["MEDIUM", "HIGH"]
        elif mode == "Weak":
            return risk_level in ["MEDIUM", "HIGH"]
        else:  # Off mode
            return risk_level in ["HIGH", "CRITICAL"]
    
    def _get_adaptive_thresholds(self, mode: SecurityMode) -> Dict[str, float]:
        """Get adaptive thresholds based on security mode"""
        
        base_thresholds = self.adaptive_thresholds.copy()
        
        # Adjust thresholds based on mode
        if mode == SecurityMode.OFF:
            # Much more lenient
            return {
                "low_risk": 0.8,
                "medium_risk": 0.9,
                "high_risk": 0.95,
                "critical_risk": 1.0
            }
        elif mode == SecurityMode.WEAK:
            # More lenient
            return {
                "low_risk": 0.5,
                "medium_risk": 0.7,
                "high_risk": 0.85,
                "critical_risk": 0.95
            }
        elif mode == SecurityMode.NORMAL:
            # Standard thresholds
            return base_thresholds
        elif mode == SecurityMode.STRONG:
            # Much stricter
            return {
                "low_risk": 0.1,
                "medium_risk": 0.3,
                "high_risk": 0.5,
                "critical_risk": 0.7
            }
        
        return base_thresholds
    
    async def _generate_reason(
        self,
        decision: str,
        risk_factors: List[str],
        signals: List[SecuritySignal]
    ) -> str:
        """Generate human-readable reason for decision"""
        
        if decision == "BLOCK":
            if "steganography_detected" in risk_factors:
                return "Blocked: Potential steganographic content detected"
            elif "input_validation_issues" in risk_factors:
                return "Blocked: Input validation failed - potential injection attempt"
            elif "tool_abuse_blocked" in risk_factors:
                return "Blocked: Tool abuse attempt detected"
            elif "rag_content_blocked" in risk_factors:
                return "Blocked: RAG content validation failed"
            else:
                return "Blocked: High risk content detected"
        
        elif decision == "SANITIZE":
            return "Content sanitized due to moderate risk factors"
        
        else:  # ALLOW
            return "Request approved - no significant risks detected"
    
    async def score_risk(self, signals: Dict[str, Any], mode: str) -> tuple[int, str]:
        """Score risk on 0-100 scale with mode-dependent weights"""
        
        # Base score calculation
        base_score = 0
        
        # Prompt injection signals
        if signals.get("prompt_injection_suspected", False):
            base_score += 30
        
        # RAG injection signals
        if signals.get("rag_injection_suspected", False):
            base_score += 20
        
        # Tool abuse signals
        if signals.get("tool_abuse_suspected", False):
            base_score += 25
        
        # Encoding obfuscation
        if signals.get("encoding_obfuscation", False):
            base_score += 35
        
        # Pattern hits (each hit adds points)
        pattern_hits = len(signals.get("pattern_hits", []))
        base_score += min(pattern_hits * 5, 25)
        
        # Suspicious keywords (each keyword adds points)
        suspicious_keywords = len(signals.get("suspicious_keywords", []))
        base_score += min(suspicious_keywords * 3, 20)
        
        # Mode-dependent weight adjustment
        mode_weights = {
            "Off": 0.1,      # Very lenient
            "Weak": 0.4,     # More lenient  
            "Normal": 0.7,    # Standard
            "Strong": 1.2       # Strict (amplifies score)
        }
        
        weight = mode_weights.get(mode, 0.7)
        final_score = int(min(base_score * weight, 100))
        
        # Map to risk level
        if final_score >= 75:
            risk_level = "CRITICAL"
        elif final_score >= 50:
            risk_level = "HIGH"
        elif final_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        print(f"DEBUG: Risk scoring - Base: {base_score}, Weight: {weight}, Final: {final_score}, Level: {risk_level}")
        return final_score, risk_level
    
    async def decide_action(self, risk_level: str, mode: str) -> tuple[str, str]:
        """Decide action based on risk level and mode"""
        
        decision_rules = {
            "Off": {
                "LOW": ("ALLOW", "Request allowed in Off mode"),
                "MEDIUM": ("ALLOW", "Request allowed in Off mode"),
                "HIGH": ("SANITIZE", "High risk sanitized in Off mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked even in Off mode")
            },
            "Weak": {
                "LOW": ("ALLOW", "Low risk allowed in Weak mode"),
                "MEDIUM": ("SANITIZE", "Medium risk sanitized in Weak mode"),
                "HIGH": ("SANITIZE", "High risk sanitized in Weak mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked in Weak mode")
            },
            "Normal": {
                "LOW": ("ALLOW", "Low risk allowed in Normal mode"),
                "MEDIUM": ("SANITIZE", "Medium risk sanitized in Normal mode"),
                "HIGH": ("SANITIZE", "High risk sanitized in Normal mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked in Normal mode")
            },
            "Strong": {
                "LOW": ("SANITIZE", "Low risk sanitized in Strong mode"),
                "MEDIUM": ("SANITIZE", "Medium risk sanitized in Strong mode"),
                "HIGH": ("BLOCK", "High risk blocked in Strong mode"),
                "CRITICAL": ("BLOCK", "Critical risk blocked in Strong mode")
            }
        }
        
        decision, reason = decision_rules.get(mode, {}).get(risk_level, ("BLOCK", "Unknown mode/risk combination"))
        print(f"DEBUG: Decision - Mode: {mode}, Risk: {risk_level}, Action: {decision}")
        return decision, reason
    
    async def needs_sanitization(self, signals: Dict[str, Any], risk_level: str, mode: str) -> bool:
        """Determine if content needs sanitization"""
        
        # Direct sanitization rules
        if mode == "Strong":
            return risk_level in ["LOW", "MEDIUM"]
        elif mode == "Normal":
            return risk_level in ["MEDIUM", "HIGH"]
        elif mode == "Weak":
            return risk_level in ["MEDIUM", "HIGH"]
        else:  # Off mode
            return risk_level in ["HIGH", "CRITICAL"]
