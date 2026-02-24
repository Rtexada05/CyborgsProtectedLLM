"""
Input Content Checker - validates user input for injection attempts
"""

from typing import List, Dict, Any
import re

from ..models.schemas import SecuritySignal


class InputContentChecker:
    """Checks user input for potential injection attempts and malicious content"""
    
    def __init__(self):
        # Injection patterns to detect
        self.injection_patterns = [
            # Original patterns
            r"(?i)(ignore|forget|disregard).*(previous|earlier|above).*(instruction|prompt|rule)",
            r"(?i)(system|admin|root).*(access|privilege|mode)",
            r"(?i)(jailbreak|bypass|override).*(security|protection|filter)",
            r"(?i)(roleplay|pretend|act as).*(system|admin|ai)",
            r"(?i)(new|change|switch).*(character|persona|role)",
            r"(?i)(translate|convert|explain).*(this|the).*(prompt|instruction)",
            r"(?i)(what|how).*(are you|do you).*(instructions|prompt|rules)",
            r"(?i)(show|display|reveal).*(system|internal|hidden)",
            r"(?i)\[START\]|\[END\]|\[BEGIN\]|\[FINISH\]",
            r"(?i)(DAN|Do Anything Now)",
            
            # Advanced injection patterns
            # Role manipulation
            r"(?i)(you are now|from now on|starting now).*(system|admin|assistant|ai)",
            r"(?i)(let's pretend|imagine|假设).*(you are|we are).*(system|admin)",
            r"(?i)(in character|as a|playing the role of).*(system|admin|ai)",
            r"(?i)(act|behave|respond).*(as if|like).*(you are|we are).*(system|admin)",
            
            # Context switching
            r"(?i)(new conversation|fresh start|reset).*(context|memory|history)",
            r"(?i)(forget|erase|clear).*(everything|all|previous).*(instructions|rules)",
            r"(?i)(step|part|phase).*\d+.*of.*\d+",
            r"(?i)(first|next|then|after this).*(ignore|forget|skip)",
            
            # Direct prompt leaks
            r"(?i)(show me|tell me|reveal).*(your|the).*(prompt|instructions|system)",
            r"(?i)(what are|what's).*(your|the).*(initial|original|system).*(prompt|message)",
            r"(?i)(repeat|echo|copy).*(your|the).*(instructions|prompt|system)",
            r"(?i)(print|output|display).*(your|the).*(system|internal|hidden).*(message|text)",
            
            # Encoding attacks
            r"(?i)(base64|hex|rot13|caesar|atbash).*(decode|decrypt|translate)",
            r"(?i)\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}",
            r"(?i)(unicode|utf|ascii).*(encode|decode|convert)",
            r"(?i)(binary|decimal|octal).*(translate|convert|decode)",
            
            # Token manipulation
            r"(?i)(token|character|word).*(limit|count|boundary)",
            r"(?i)(bypass|avoid|evade).*(filter|restriction|limit)",
            r"(?i)(maximum|max|min).*(length|size|count).*(exceed|bypass)",
            
            # Semantic patterns
            r"(?i)(simulate|emulate|imitate).*(system|program|ai)",
            r"(?i)(hypothetically|theoretically|imagine).*(if you were|as a).*(system|admin)",
            r"(?i)(for testing|debug|demo).*(purposes|only).*(show|reveal|display)",
            
            # Multi-step and conditional attacks
            r"(?i)(if|when|once).*(you|the system).*(can|able to).*(ignore|skip|bypass)",
            r"(?i)(condition|requirement|prerequisite).*(for|to).*(access|unlock|reveal)",
            r"(?i)(after|when|once).*(reading|processing).*(this|the).*(message|prompt)",
            
            # Structural attacks
            r"(?i)```.*?system.*?```",
            r"(?i)\{\{.*?system.*?\}\}",
            r"(?i)\[SYSTEM\].*\[/SYSTEM\]",
            r"(?i)<system>.*?</system>",
            
            # Advanced role manipulation
            r"(?i)(developer mode|debug mode|admin mode|god mode)",
            r"(?i)(elevated|super|root).*(privileges|access|permissions)",
            r"(?i)(override|disable|deactivate).*(safety|security|protection)",
        ]
        
        # Suspicious patterns
        self.suspicious_patterns = [
            r"(?i)(base64|hex|encode|decode)",
            r"(?i)(exec|eval|system|shell)",
            r"(?i)(password|token|secret|key).*(=|:)",
            r"(?i)(drop|delete|remove).*(table|database|file)",
            # Additional suspicious patterns
            r"(?i)(obfuscate|hide|conceal|mask).*(content|text|message)",
            r"(?i)(injection|exploit|payload|malicious)",
            r"(?i)(backdoor|rootkit|trojan|virus)",
            r"(?i)(privilege|escalation|sudo|chmod)",
        ]
        
        # Pattern combinations that are more suspicious
        self.combination_patterns = [
            # Role + instruction override
            {"patterns": ["roleplay", "ignore"], "weight": 0.9, "description": "Role manipulation with instruction override"},
            {"patterns": ["system", "forget"], "weight": 0.8, "description": "System access with memory manipulation"},
            {"patterns": ["admin", "access"], "weight": 0.9, "description": "Admin access attempt"},
            {"patterns": ["jailbreak", "security"], "weight": 0.95, "description": "Direct jailbreak attempt"},
            
            # Encoding + suspicious content
            {"patterns": ["base64", "prompt"], "weight": 0.8, "description": "Encoded prompt attempt"},
            {"patterns": ["hex", "instruction"], "weight": 0.7, "description": "Hex encoded instruction"},
            {"patterns": ["unicode", "system"], "weight": 0.75, "description": "Unicode system manipulation"},
            
            # Multi-step attacks
            {"patterns": ["step", "ignore"], "weight": 0.8, "description": "Multi-step attack with instruction override"},
            {"patterns": ["phase", "bypass"], "weight": 0.85, "description": "Phased attack with bypass attempt"},
            
            # Context manipulation
            {"patterns": ["reset", "context"], "weight": 0.7, "description": "Context reset attempt"},
            {"patterns": ["clear", "memory"], "weight": 0.75, "description": "Memory manipulation"},
        ]
        
        # High-risk keyword combinations
        self.high_risk_combinations = [
            {"keywords": ["developer", "mode", "override"], "weight": 0.95},
            {"keywords": ["debug", "mode", "admin"], "weight": 0.9},
            {"keywords": ["god", "mode", "access"], "weight": 0.95},
            {"keywords": ["elevated", "privileges", "root"], "weight": 0.9},
        ]
        
        # Compile regex patterns
        self.compiled_injection = [re.compile(pattern) for pattern in self.injection_patterns]
        self.compiled_suspicious = [re.compile(pattern) for pattern in self.suspicious_patterns]
    
    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """Analyze prompt and return structured signals"""
        
        # Debug: Log the content being checked
        print(f"DEBUG: Analyzing content: '{prompt}'")
        
        signals = {
            "prompt_injection_suspected": False,
            "rag_injection_suspected": False,
            "tool_abuse_suspected": False,
            "encoding_obfuscation": False,
            "suspicious_keywords": [],
            "pattern_hits": []
        }
        
        content_lower = prompt.lower()
        
        # Check for injection patterns
        injection_matches = []
        for i, pattern in enumerate(self.compiled_injection):
            matches = pattern.findall(prompt)
            if matches:
                print(f"DEBUG: Injection pattern {i} matched: {matches}")
                injection_matches.extend(matches)
                signals["pattern_hits"].append(f"injection_pattern_{i}")
                signals["prompt_injection_suspected"] = True
        
        # Check for suspicious patterns
        suspicious_matches = []
        for i, pattern in enumerate(self.compiled_suspicious):
            matches = pattern.findall(prompt)
            if matches:
                print(f"DEBUG: Suspicious pattern {i} matched: {matches}")
                suspicious_matches.extend(matches)
                signals["pattern_hits"].append(f"suspicious_pattern_{i}")
        
        # Check for RAG injection triggers
        rag_triggers = ["use context:", "from documents:", "retrieve", "based on context", "refer to"]
        if any(trigger in content_lower for trigger in rag_triggers):
            signals["rag_injection_suspected"] = True
            signals["pattern_hits"].append("rag_trigger_detected")
        
        # Check for tool abuse triggers
        tool_triggers = ["calculate", "open file", "read file", "browse", "execute", "shell", "run command"]
        if any(trigger in content_lower for trigger in tool_triggers):
            signals["tool_abuse_suspected"] = True
            signals["pattern_hits"].append("tool_trigger_detected")
        
        # Check for encoding obfuscation
        encoding_triggers = ["base64", "hex", "decode", "rot13", "atbash", "caesar"]
        if any(trigger in content_lower for trigger in encoding_triggers):
            signals["encoding_obfuscation"] = True
            signals["pattern_hits"].append("encoding_detected")
        
        # Extract suspicious keywords
        suspicious_keywords = [
            "ignore", "forget", "disregard", "bypass", "override", "jailbreak",
            "system", "admin", "root", "password", "token", "secret", "key"
        ]
        for keyword in suspicious_keywords:
            if keyword in content_lower:
                signals["suspicious_keywords"].append(keyword)
        
        print(f"DEBUG: Analysis result: {signals}")
        return signals
    
    async def check_content(self, content: str) -> List[SecuritySignal]:
        """Check content for injection attempts and return signals"""
        
        signals = []
        content_lower = content.lower()
        
        # Debug: Log the content being checked
        print(f"DEBUG: Checking content: '{content}'")
        
        # Check for injection patterns
        injection_matches = []
        for i, pattern in enumerate(self.compiled_injection):
            matches = pattern.findall(content)
            if matches:
                print(f"DEBUG: Injection pattern {i} matched: {matches}")
                injection_matches.extend(matches)
                signals.append(SecuritySignal(
                    signal_type="prompt_injection",
                    confidence=0.8,
                    details={
                        "pattern": self.injection_patterns[i],
                        "matches": matches[:3]  # Limit to first 3 matches
                    }
                ))
        
        # Check for suspicious patterns
        suspicious_matches = []
        for i, pattern in enumerate(self.compiled_suspicious):
            matches = pattern.findall(content)
            if matches:
                print(f"DEBUG: Suspicious pattern {i} matched: {matches}")
                suspicious_matches.extend(matches)
                signals.append(SecuritySignal(
                    signal_type="suspicious_content",
                    confidence=0.6,
                    details={
                        "pattern": self.suspicious_patterns[i],
                        "matches": matches[:3]
                    }
                ))
        
        # Check for pattern combinations
        combination_signals = await self._check_pattern_combinations(content_lower)
        signals.extend(combination_signals)
        
        # Check for high-risk keyword combinations
        keyword_signals = await self._check_keyword_combinations(content_lower)
        signals.extend(keyword_signals)
        
        # Check for excessive length (potential DoS)
        if len(content) > 5000:
            signals.append(SecuritySignal(
                signal_type="excessive_length",
                confidence=0.4,
                details={"length": len(content)}
            ))
        
        # Check for repeated characters (potential obfuscation)
        if self._has_repeated_chars(content):
            signals.append(SecuritySignal(
                signal_type="repeated_chars",
                confidence=0.3,
                details={"suspicious_repetition": True}
            ))
        
        # Check for unusual encoding indicators
        if self._has_encoding_indicators(content):
            signals.append(SecuritySignal(
                signal_type="encoding_indicators",
                confidence=0.5,
                details={"potential_encoding": True}
            ))
        
        # Calculate overall risk score
        overall_risk = await self._calculate_overall_risk(content, signals)
        
        # Add overall risk signal if high
        if overall_risk > 0.7:
            signals.append(SecuritySignal(
                signal_type="high_risk_combination",
                confidence=overall_risk,
                details={
                    "overall_risk_score": overall_risk,
                    "total_signals": len(signals),
                    "risk_factors": [s.signal_type for s in signals]
                }
            ))
        
        return signals
    
    async def _check_pattern_combinations(self, content_lower: str) -> List[SecuritySignal]:
        """Check for suspicious pattern combinations"""
        
        signals = []
        
        for combo in self.combination_patterns:
            patterns = combo["patterns"]
            weight = combo["weight"]
            description = combo["description"]
            
            # Check if all patterns in the combination are present
            if all(pattern in content_lower for pattern in patterns):
                signals.append(SecuritySignal(
                    signal_type="pattern_combination",
                    confidence=weight,
                    details={
                        "combination": patterns,
                        "description": description,
                        "weight": weight
                    }
                ))
        
        return signals
    
    async def _check_keyword_combinations(self, content_lower: str) -> List[SecuritySignal]:
        """Check for high-risk keyword combinations"""
        
        signals = []
        
        for combo in self.high_risk_combinations:
            keywords = combo["keywords"]
            weight = combo["weight"]
            
            # Check if all keywords are present
            if all(keyword in content_lower for keyword in keywords):
                signals.append(SecuritySignal(
                    signal_type="keyword_combination",
                    confidence=weight,
                    details={
                        "keywords": keywords,
                        "weight": weight
                    }
                ))
        
        return signals
    
    async def _calculate_overall_risk(self, content: str, signals: List[SecuritySignal]) -> float:
        """Calculate overall risk score based on all signals"""
        
        if not signals:
            return 0.0
        
        # Base risk from individual signals
        total_confidence = sum(signal.confidence for signal in signals)
        avg_confidence = total_confidence / len(signals)
        
        # Bonus for multiple signals
        signal_count_bonus = min(len(signals) * 0.1, 0.3)
        
        # Content length risk
        length_risk = min(len(content) / 10000, 0.2)
        
        # Pattern diversity bonus
        signal_types = set(signal.signal_type for signal in signals)
        diversity_bonus = min(len(signal_types) * 0.05, 0.2)
        
        # Calculate final risk
        overall_risk = avg_confidence + signal_count_bonus + length_risk + diversity_bonus
        
        return min(overall_risk, 1.0)
    
    def _has_repeated_chars(self, content: str) -> bool:
        """Check for suspicious repeated character patterns"""
        # Look for 5+ consecutive same characters
        repeated_pattern = re.compile(r'(.)\1{4,}')
        return bool(repeated_pattern.search(content))
    
    def _has_encoding_indicators(self, content: str) -> bool:
        """Check for potential encoding/obfuscation indicators"""
        encoding_indicators = [
            "\\u", "\\x", "%", "&#", "base64:", "hex:",
            "rot13", "caesar", "atbash"
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in encoding_indicators)
