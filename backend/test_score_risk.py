#!/usr/bin/env python3
"""
Test script to debug score_risk method
"""

import asyncio
import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.policy_engine import PolicyEngine

async def test_score_risk():
    """Test the score_risk method across representative mode boundaries."""
    
    policy_engine = PolicyEngine()
    
    safe_signals = {
        "prompt_injection_suspected": False,
        "rag_injection_suspected": False,
        "rag_poisoning_suspected": False,
        "rag_cross_user_access_blocked": False,
        "rag_source_quarantined": False,
        "tool_abuse_suspected": False,
        "destructive_tool_requested": False,
        "command_execution_requested": False,
        "encoding_obfuscation": False,
        "steganography_suspected": False,
        "attachment_risk_suspected": False,
        "suspicious_keywords": [],
        "pattern_hits": [],
        "attachment_pattern_hits": [],
        "rag_chunks_dropped": 0,
        "rag_chunk_sanitized_count": 0,
    }

    cases = [
        (
            "safe prompt",
            safe_signals,
            {
                "Weak": ("LOW", "ALLOW"),
                "Normal": ("LOW", "ALLOW"),
                "Strong": ("LOW", "ALLOW"),
            },
        ),
        (
            "single prompt injection",
            {
                **safe_signals,
                "prompt_injection_suspected": True,
                "suspicious_keywords": ["ignore", "system"],
                "pattern_hits": ["injection_pattern_1"],
            },
            {
                "Weak": ("MEDIUM", "SANITIZE"),
                "Normal": ("MEDIUM", "SANITIZE"),
                "Strong": ("MEDIUM", "SANITIZE"),
            },
        ),
        (
            "bare command execution",
            {
                **safe_signals,
                "tool_abuse_suspected": True,
                "command_execution_requested": True,
                "pattern_hits": ["tool_trigger_detected", "command_tool_detected"],
                "suspicious_keywords": ["system"],
            },
            {
                "Weak": ("HIGH", "SANITIZE"),
                "Normal": ("HIGH", "BLOCK"),
                "Strong": ("CRITICAL", "BLOCK"),
            },
        ),
        (
            "destructive write",
            {
                **safe_signals,
                "tool_abuse_suspected": True,
                "destructive_tool_requested": True,
                "pattern_hits": ["tool_trigger_detected", "write_tool_detected"],
                "suspicious_keywords": ["secret"],
            },
            {
                "Weak": ("HIGH", "SANITIZE"),
                "Normal": ("HIGH", "BLOCK"),
                "Strong": ("CRITICAL", "BLOCK"),
            },
        ),
        (
            "stacked hostile attack",
            {
                **safe_signals,
                "prompt_injection_suspected": True,
                "tool_abuse_suspected": True,
                "command_execution_requested": True,
                "encoding_obfuscation": True,
                "pattern_hits": [
                    "injection_pattern_1",
                    "tool_trigger_detected",
                    "command_tool_detected",
                    "encoding_detected",
                ],
                "suspicious_keywords": ["ignore", "override", "system", "secret", "key"],
            },
            {
                "Weak": ("CRITICAL", "BLOCK"),
                "Normal": ("CRITICAL", "BLOCK"),
                "Strong": ("CRITICAL", "BLOCK"),
            },
        ),
    ]

    for case_name, case_signals, expectations in cases:
        print(f"\n{case_name}")
        for mode in ("Weak", "Normal", "Strong"):
            score, level = await policy_engine.score_risk(case_signals, mode)
            decision, reason = await policy_engine.decide_action(level, mode)
            needs_sanitize = await policy_engine.needs_sanitization(case_signals, level, mode)
            expected_level, expected_decision = expectations[mode]
            print(
                f"  {mode}: Score={score}, Level={level}, Decision={decision}, "
                f"Sanitize={needs_sanitize}, Reason={reason}"
            )
            assert level == expected_level
            assert decision == expected_decision

if __name__ == "__main__":
    asyncio.run(test_score_risk())
