"""
Text Sanitizer - utilities for sanitizing text content
"""

import re
import html
from typing import List, Dict, Any


class TextSanitizer:
    """Utilities for sanitizing and cleaning text content"""
    
    def __init__(self):
        # Patterns to remove or replace
        self.dangerous_patterns = [
            r"(?i)system\s*[:=]",
            r"(?i)admin\s*[:=]",
            r"(?i)role\s*[:=]",
            r"(?i)persona\s*[:=]",
            r"(?i)character\s*[:=]",
        ]
        
        # Content redaction patterns
        self.redaction_patterns = [
            # System-related redactions
            (r"(?i)system\s*prompt", "[REDACTED_SYSTEM_PROMPT]"),
            (r"(?i)admin\s*instruction", "[REDACTED_ADMIN_INSTRUCTION]"),
            (r"(?i)internal\s*(?:message|note|memo)", "[REDACTED_INTERNAL]"),
            (r"(?i)secret\s*(?:key|token|password)", "[REDACTED_CREDENTIAL]"),
            (r"(?i)confidential\s*(?:information|data)", "[REDACTED_CONFIDENTIAL]"),
            (r"(?i)proprietary\s*(?:algorithm|logic)", "[REDACTED_PROPRIETARY]"),
            
            # Access control redactions
            (r"(?i)(root|superuser|administrator)\s*(?:password|pass|pwd)", "[REDACTED_ADMIN_CRED]"),
            (r"(?i)api\s*(?:key|token|secret)", "[REDACTED_API_KEY]"),
            (r"(?i)database\s*(?:connection|cred|auth)", "[REDACTED_DB_AUTH]"),
            
            # Security mechanism redactions
            (r"(?i)security\s*(?:policy|rule|protocol)", "[REDACTED_SECURITY_POLICY]"),
            (r"(?i)filter\s*(?:rule|pattern|logic)", "[REDACTED_FILTER_RULE]"),
            (r"(?i)detection\s*(?:mechanism|algorithm)", "[REDACTED_DETECTION]"),
        ]
        
        # Tool directive removal patterns
        self.tool_directive_patterns = [
            # Command execution
            r"(?i)(execute|run|perform).*(?:command|function|tool)",
            r"(?i)(call|invoke|use).*(?:system|admin|root).*(?:function|method)",
            r"(?i)\$\{[^}]*\}",  # Template variables
            r"(?i)```.*?```",     # Code blocks
            r"(?i)`[^`]*`",       # Inline code
            
            # System calls
            r"(?i)(system|exec|eval|shell)\s*\(",
            r"(?i)(subprocess|os\.|popen)\.",
            r"(?i)(curl|wget|nc|netcat)\s+",
            
            # File operations
            r"(?i)(open|read|write|delete).*(?:file|directory)",
            r"(?i)(cat|type|more|less)\s+",
            r"(?i)(rm|del|remove)\s+",
            
            # Network operations
            r"(?i)(connect|bind|listen).*(?:socket|port)",
            r"(?i)(http|https|ftp).*(?:request|download|upload)",
            r"(?i)(ping|traceroute|nslookup)\s+",
        ]
        
        # Structural sanitization patterns
        self.structural_patterns = [
            # Delimiters and markers
            r"(?i)\[START.*?\]|\[END.*?\]|\[BEGIN.*?\]|\[FINISH.*?\]",
            r"(?i)---.*?---",     # YAML front matter
            r"(?i)<<<.*?>>>",     # Heredoc syntax
            r"(?i)\{\{.*?\}\}",   # Template syntax
            r"(?i)\[\[.*?\]\]",   # Double bracket syntax
            
            # Advanced structural attacks
            r"(?i)<system>.*?</system>",
            r"(?i)<admin>.*?</admin>",
            r"(?i)<root>.*?</root>",
            r"(?i)\[SYSTEM\].*\[/SYSTEM\]",
            r"(?i)\[ADMIN\].*\[/ADMIN\]",
            r"(?i)\[ROOT\].*\[/ROOT\]",
            
            # Comment-based attacks
            r"(?i)<!--.*?-->",    # HTML comments
            r"(?i)/\*.*?\*/",     # Multi-line comments
            r"(?i)#.*$",          # Single-line comments (when at line start)
        ]
        
        # Patterns to normalize
        self.normalization_patterns = [
            (r"\s+", " "),  # Multiple spaces to single space
            (r"\n\s*\n", "\n\n"),  # Multiple newlines to double newline
            (r"[^\w\s\.\,\!\?\-\(\)\[\]\{\}\:\;\'\"]", ""),  # Remove special chars except punctuation
        ]
        
        # Compile patterns
        self.compiled_dangerous = [re.compile(pattern) for pattern in self.dangerous_patterns]
        self.compiled_redaction = [(re.compile(pattern), replacement) for pattern, replacement in self.redaction_patterns]
        self.compiled_tool_directives = [re.compile(pattern) for pattern in self.tool_directive_patterns]
        self.compiled_structural = [re.compile(pattern) for pattern in self.structural_patterns]
        self.compiled_normalization = [
            (re.compile(pattern), replacement) 
            for pattern, replacement in self.normalization_patterns
        ]
    
    def sanitize_text(self, text: str, level: str = "medium") -> str:
        """Sanitize text based on security level"""
        
        if not text:
            return text
        
        # HTML decode first
        sanitized = html.unescape(text)
        
        # Apply level-specific sanitization
        if level == "low":
            sanitized = self._light_sanitization(sanitized)
        elif level == "medium":
            sanitized = self._medium_sanitization(sanitized)
        elif level == "high":
            sanitized = self._heavy_sanitization(sanitized)
        else:
            sanitized = self._medium_sanitization(sanitized)
        
        return sanitized.strip()
    
    def _light_sanitization(self, text: str) -> str:
        """Light sanitization - basic cleaning only"""
        
        # Remove dangerous patterns
        for pattern in self.compiled_dangerous:
            text = pattern.sub("", text)
        
        # Apply redaction for sensitive content
        for pattern, replacement in self.compiled_redaction:
            text = pattern.sub(replacement, text)
        
        # Basic normalization
        for pattern, replacement in self.compiled_normalization:
            text = pattern.sub(replacement, text)
        
        return text
    
    def _medium_sanitization(self, text: str) -> str:
        """Medium sanitization - includes light + additional checks"""
        
        # Apply light sanitization first
        text = self._light_sanitization(text)
        
        # Remove tool directives
        for pattern in self.compiled_tool_directives:
            text = pattern.sub("[REMOVED_TOOL_DIRECTIVE]", text)
        
        # Additional medium-level patterns
        medium_patterns = [
            r"(?i)(ignore|forget|disregard).*(previous|earlier)",
            r"(?i)(jailbreak|bypass).*(security|protection)",
            r"(?i)\[START\]|\[END\]|\[BEGIN\]|\[FINISH\]",
        ]
        
        for pattern in medium_patterns:
            text = re.sub(pattern, "[SANITIZED]", text)
        
        # Remove excessive repetition
        text = self._remove_excessive_repetition(text)
        
        return text
    
    def _heavy_sanitization(self, text: str) -> str:
        """Heavy sanitization - strict cleaning"""
        
        # Apply medium sanitization first
        text = self._medium_sanitization(text)
        
        # Remove structural patterns
        for pattern in self.compiled_structural:
            text = pattern.sub("[REMOVED_STRUCTURAL]", text)
        
        # Additional heavy-level patterns
        heavy_patterns = [
            r"(?i)(what|how).*(are you|do you).*(instructions|prompt|rules)",
            r"(?i)(show|display|reveal).*(system|internal|hidden)",
            r"(?i)(translate|convert|explain).*(this|the).*(prompt|instruction)",
        ]
        
        for pattern in heavy_patterns:
            text = re.sub(pattern, "[HEAVILY_SANITIZED]", text)
        
        # Remove all URLs
        text = re.sub(r"https?://\S+|www\.\S+", "[REMOVED_URL]", text)
        
        # Remove email addresses
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REMOVED_EMAIL]", text)
        
        # Remove potential code blocks (more aggressive)
        text = re.sub(r"```[\s\S]*?```", "[REMOVED_CODE_BLOCK]", text)
        text = re.sub(r"`[^`]*`", "[REMOVED_INLINE_CODE]", text)
        
        # Remove encoding indicators
        text = re.sub(r"(\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2})", "[REMOVED_ENCODING]", text)
        
        return text
    
    def _remove_excessive_repetition(self, text: str) -> str:
        """Remove excessive character repetition"""
        
        # Remove 3+ consecutive same characters
        text = re.sub(r'(.)\1{2,}', r'\1', text)
        
        # Remove 3+ consecutive same words
        words = text.split()
        if len(words) > 2:
            cleaned_words = [words[0], words[1]]
            for word in words[2:]:
                if word.lower() != cleaned_words[-1].lower() or word.lower() != cleaned_words[-2].lower():
                    cleaned_words.append(word)
            text = " ".join(cleaned_words)
        
        return text
    
    def sanitize_text(self, prompt: str) -> str:
        """Sanitize text by removing dangerous patterns"""
        
        sanitized = prompt
        
        # Remove common injection strings
        injection_strings = [
            "ignore previous instructions",
            "reveal system prompt", 
            "developer message",
            "you are now",
            "act as system",
            "bypass security",
            "jailbreak"
        ]
        
        for injection in injection_strings:
            sanitized = sanitized.replace(injection, "[REDACTED_INJECTION]")
        
        # Strip code fences
        sanitized = re.sub(r'```[\s\S]*?```', '[CODE_BLOCK_REMOVED]', sanitized)
        
        # Strip HTML tags (minimal)
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
        
        # Truncate if too long
        if len(sanitized) > 2000:
            sanitized = sanitized[:2000] + "...[TRUNCATED]"
        
        print(f"DEBUG: Text sanitization - Original length: {len(prompt)}, Sanitized length: {len(sanitized)}")
        return sanitized

    def extract_safe_content(self, text: str, max_length: int = 1000) -> str:
        """Extract safe content within length limits"""
        
        if not text:
            return ""
        
        # Sanitize first
        safe_text = self.sanitize_text(text, level="medium")
        
        # Truncate if too long
        if len(safe_text) > max_length:
            safe_text = safe_text[:max_length] + "..."
        
        return safe_text
    
    def detect_suspicious_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in text"""
        
        suspicious_patterns = []
        
        # Check for zero-width characters
        zero_width = re.findall(r'[\u200B-\u200D\uFEFF]', text)
        if zero_width:
            suspicious_patterns.append({
                "type": "zero_width_chars",
                "count": len(zero_width),
                "severity": "medium"
            })
        
        # Check for unusual Unicode
        unusual_unicode = re.findall(r'[\uE000-\uF8FF\uFFF0-\uFFFF]', text)
        if unusual_unicode:
            suspicious_patterns.append({
                "type": "unusual_unicode",
                "count": len(unusual_unicode),
                "severity": "low"
            })
        
        # Check for encoding indicators
        encoding_patterns = re.findall(r'(\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2})', text)
        if encoding_patterns:
            suspicious_patterns.append({
                "type": "encoding_indicators",
                "count": len(encoding_patterns),
                "severity": "medium"
            })
        
        # Check for excessive punctuation
        punctuation_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
        if punctuation_ratio > 0.3:
            suspicious_patterns.append({
                "type": "excessive_punctuation",
                "ratio": punctuation_ratio,
                "severity": "low"
            })
        
        return suspicious_patterns
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        
        # Replace tabs with spaces
        text = text.replace("\t", " ")
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        
        # Remove excessive empty lines
        normalized_lines = []
        prev_empty = False
        
        for line in lines:
            if line == "":
                if not prev_empty:
                    normalized_lines.append(line)
                    prev_empty = True
            else:
                normalized_lines.append(line)
                prev_empty = False
        
        return "\n".join(normalized_lines)
