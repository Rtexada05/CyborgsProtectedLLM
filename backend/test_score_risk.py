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
    """Test the score_risk method with safe prompt"""
    
    policy_engine = PolicyEngine()
    
    # Test safe prompt signals
    safe_signals = {
        "prompt_injection_suspected": False,
        "rag_injection_suspected": False,
        "tool_abuse_suspected": False,
        "encoding_obfuscation": False,
        "suspicious_keywords": [],
        "pattern_hits": []
    }
    
    # Test in Strong mode
    score, level = await policy_engine.score_risk(safe_signals, "Strong")
    print(f"Safe prompt in Strong mode: Score={score}, Level={level}")
    
    # Test decision
    decision, reason = await policy_engine.decide_action(level, "Strong")
    print(f"Decision: {decision}, Reason: {reason}")
    
    # Test sanitization
    needs_sanitize = await policy_engine.needs_sanitization(safe_signals, level, "Strong")
    print(f"Needs sanitization: {needs_sanitize}")
    
    print("\n" + "="*50 + "\n")
    
    # Test injection signals
    injection_signals = {
        "prompt_injection_suspected": True,
        "rag_injection_suspected": False,
        "tool_abuse_suspected": False,
        "encoding_obfuscation": False,
        "suspicious_keywords": ["ignore", "instructions"],
        "pattern_hits": ["injection_pattern_1"]
    }
    
    # Test in Strong mode
    score, level = await policy_engine.score_risk(injection_signals, "Strong")
    print(f"Injection prompt in Strong mode: Score={score}, Level={level}")
    
    # Test decision
    decision, reason = await policy_engine.decide_action(level, "Strong")
    print(f"Decision: {decision}, Reason: {reason}")
    
    # Test sanitization
    needs_sanitize = await policy_engine.needs_sanitization(injection_signals, level, "Strong")
    print(f"Needs sanitization: {needs_sanitize}")

if __name__ == "__main__":
    asyncio.run(test_score_risk())
