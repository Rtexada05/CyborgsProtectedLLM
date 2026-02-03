"""
Steganography Detector - detects potential hidden content
"""

from typing import List, Dict, Any
import re

from ..models.schemas import SecuritySignal


class SteganographyDetector:
    """Detects potential steganographic content in user input"""
    
    def __init__(self):
        # Steganography indicators
        self.stego_indicators = [
            r"(?i)(stego|steganography)",
            r"(?i)(hidden|secret|covert).*(message|text|data)",
            r"(?i)(embed|hide|conceal).*(information|data)",
            r"(?i)(invisible|zero-width|whitespace).*(text|character)",
            r"(?i)(lsb|least significant bit)",
            r"(?i)(watermark|fingerprint)",
        ]
        
        # Zero-width character patterns
        self.zero_width_patterns = [
            r'[\u200B-\u200D\uFEFF]',  # Zero-width space, non-joiner, joiner, BOM
            r'[\u2060\u180E\u061C]',    # More invisible characters
        ]
        
        # Unusual Unicode patterns
        self.unusual_unicode = [
            r'[\uE000-\uF8FF]',  # Private Use Area
            r'[\uFFF0-\uFFFF]',  # Specials
        ]
        
        # Compile patterns
        self.compiled_indicators = [re.compile(pattern) for pattern in self.stego_indicators]
        self.compiled_zero_width = [re.compile(pattern) for pattern in self.zero_width_patterns]
        self.compiled_unicode = [re.compile(pattern) for pattern in self.unusual_unicode]
    
    async def detect_steganography(self, content: str) -> List[SecuritySignal]:
        """Detect potential steganographic content"""
        
        signals = []
        
        # Check for explicit steganography mentions
        for i, pattern in enumerate(self.compiled_indicators):
            matches = pattern.findall(content)
            if matches:
                signals.append(SecuritySignal(
                    signal_type="stego_keyword",
                    confidence=0.9,
                    details={
                        "pattern": self.stego_indicators[i],
                        "matches": matches
                    }
                ))
        
        # Check for zero-width characters
        zero_width_count = 0
        for pattern in self.compiled_zero_width:
            matches = pattern.findall(content)
            zero_width_count += len(matches)
        
        if zero_width_count > 0:
            confidence = min(0.3 + (zero_width_count * 0.1), 0.8)
            signals.append(SecuritySignal(
                signal_type="zero_width_chars",
                confidence=confidence,
                details={
                    "count": zero_width_count,
                    "suspicious": zero_width_count > 5
                }
            ))
        
        # Check for unusual Unicode characters
        unusual_unicode_count = 0
        for pattern in self.compiled_unicode:
            matches = pattern.findall(content)
            unusual_unicode_count += len(matches)
        
        if unusual_unicode_count > 0:
            signals.append(SecuritySignal(
                signal_type="unusual_unicode",
                confidence=0.4,
                details={
                    "count": unusual_unicode_count,
                    "characters": list(set(matches))[:5]  # Unique chars, max 5
                }
            ))
        
        # Check for suspicious spacing patterns
        if self._has_suspicious_spacing(content):
            signals.append(SecuritySignal(
                signal_type="suspicious_spacing",
                confidence=0.3,
                details={"irregular_spacing": True}
            ))
        
        # Check for character frequency anomalies
        if self._has_frequency_anomaly(content):
            signals.append(SecuritySignal(
                signal_type="frequency_anomaly",
                confidence=0.2,
                details={"unusual_distribution": True}
            ))
        
        return signals
    
    def _has_suspicious_spacing(self, content: str) -> bool:
        """Check for suspicious spacing patterns"""
        # Multiple consecutive spaces
        if re.search(r' {3,}', content):
            return True
        
        # Irregular tab/space mixing
        if '\t' in content and '  ' in content:
            return True
        
        # Unusual line break patterns
        lines = content.split('\n')
        if len(lines) > 10:  # Many short lines
            avg_length = sum(len(line.strip()) for line in lines) / len(lines)
            if avg_length < 10:  # Very short average line length
                return True
        
        return False
    
    def _has_frequency_anomaly(self, content: str) -> bool:
        """Check for character frequency anomalies"""
        if len(content) < 50:
            return False
        
        # Count character frequencies
        char_counts = {}
        for char in content:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Check for unusual repetition
        total_chars = len(content)
        for char, count in char_counts.items():
            frequency = count / total_chars
            # If any character appears more than 30% of the time
            if frequency > 0.3 and char not in ' \t\n\r':
                return True
        
        return False
