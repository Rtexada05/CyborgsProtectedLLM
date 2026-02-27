"""
Defense Controller - orchestrates the protection pipeline
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models.schemas import ChatResponse
from ..core.security_modes import SecurityMode, SecurityConfig
from ..services.policy_engine import PolicyEngine
from ..services.input_content_checker import InputContentChecker
from ..services.steganography_detector import SteganographyDetector
from ..services.rag_manager import RAGManager
from ..services.rag_content_validator import RAGContentValidator
from ..services.tool_gatekeeper import ToolGatekeeper
from ..services.llm_service import LLMService
from ..services.metrics_logger import shared_metrics_logger
from ..services.mode_manager import shared_mode_manager
from ..utils.text_sanitizer import TextSanitizer


class DefenseController:
    """Orchestrates the defense pipeline for chat requests"""
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.input_checker = InputContentChecker()
        self.stego_detector = SteganographyDetector()
        self.rag_manager = RAGManager()
        self.rag_validator = RAGContentValidator()
        self.tool_gatekeeper = ToolGatekeeper()
        self.llm_service = LLMService()
        self.text_sanitizer = TextSanitizer()
        self.metrics_logger = shared_metrics_logger
    
    async def handle_request(
        self,
        user_id: str,
        prompt: str,
        mode: Optional[str] = None,
        attachments: List[str] = [],
        requested_tools: Optional[List[str]] = None
    ) -> ChatResponse:
        """Handle chat request with complete security pipeline"""
        
        trace_id = str(uuid.uuid4())
        
        try:
            # Step 1: Determine effective mode
            mode_input = shared_mode_manager.get_mode().value if mode is None else mode
            effective_mode_enum = self._resolve_mode(mode_input)
            effective_mode = effective_mode_enum.value
            mode_config = SecurityConfig.get_config(effective_mode_enum)
            print(f"DEBUG: Effective mode: {effective_mode}")
            print(f"DEBUG: Mode config: {mode_config}")

            # Default signal object (used when checks are disabled)
            signals = {
                "prompt_injection_suspected": False,
                "rag_injection_suspected": False,
                "tool_abuse_suspected": False,
                "encoding_obfuscation": False,
                "steganography_suspected": False,
                "suspicious_keywords": [],
                "pattern_hits": []
            }
            
            # Step 2: Analyze prompt
            if mode_config.get("enable_input_validation", False):
                signals = await self.input_checker.analyze(prompt)
            else:
                print("DEBUG: Input validation skipped for current mode")
            print(f"DEBUG: Analyzed signals: {signals}")

            # Step 3: Steganography detection (mode-dependent)
            if mode_config.get("enable_steganography_detection", False):
                stego_results = await self.stego_detector.detect_steganography(prompt)
                if stego_results:
                    signals["steganography_suspected"] = True
                    signals["pattern_hits"].append("steganography_detected")
                    signals["steganography_signal_count"] = len(stego_results)
                    signals["steganography_max_confidence"] = max(
                        (result.confidence for result in stego_results),
                        default=0.0
                    )

                    for result in stego_results:
                        signal_hit = f"stego_{result.signal_type}"
                        if signal_hit not in signals["pattern_hits"]:
                            signals["pattern_hits"].append(signal_hit)

                        if result.signal_type in {"zero_width_chars", "unusual_unicode", "frequency_anomaly"}:
                            signals["encoding_obfuscation"] = True

                    await self.metrics_logger.log_event(
                        event_type="steganography_checked",
                        trace_id=trace_id,
                        user_id=user_id,
                        details={
                            "steganography_detected": True,
                            "signals": [result.signal_type for result in stego_results],
                            "max_confidence": signals.get("steganography_max_confidence", 0.0)
                        }
                    )
            else:
                print("DEBUG: Steganography detection skipped for current mode")
            
            # Step 4: Check RAG if needed (mode-dependent)
            context_result = None
            clean_context = None
            if mode_config.get("enable_rag_validation", False) and await self.rag_manager.should_retrieve(prompt):
                raw_context = await self.rag_manager.retrieve_context(prompt)
                context_result = await self.rag_validator.validate_context(raw_context)
                clean_context = self._build_clean_context(context_result)
                
                # Log RAG check
                await self.metrics_logger.log_event(
                    event_type="rag_checked",
                    trace_id=trace_id,
                    user_id=user_id,
                    details={
                        "context_safe": context_result.get("context_safe", True),
                        "context_flags": context_result.get("context_flags", []),
                        "clean_context_provided": bool(clean_context)
                    }
                )
                
                # Update signals if context unsafe
                if not context_result.get("context_safe", True):
                    signals["rag_injection_suspected"] = True
                    signals["pattern_hits"].append("rag_poisoning_detected")
            elif not mode_config.get("enable_rag_validation", False):
                print("DEBUG: RAG validation skipped for current mode")
            
            # Step 5: Score risk
            risk_score, risk_level = await self.policy_engine.score_risk(signals, effective_mode)
            print(f"DEBUG: Risk scored - Score: {risk_score}, Level: {risk_level}")
            
            # Step 6: Check tool requests (mode-dependent)
            detected_tools = []
            tool_result = {
                "tools_allowed": True,
                "allowed_tools": [],
                "tool_reason": "Tool gatekeeping disabled"
            }

            if mode_config.get("enable_tool_gatekeeping", False):
                detected_tools = await self.tool_gatekeeper.detect_requested_tools(prompt, requested_tools)
                tool_result = await self.tool_gatekeeper.authorize_tools(detected_tools, effective_mode, risk_level)

                # Log tool check
                await self.metrics_logger.log_event(
                    event_type="tool_checked",
                    trace_id=trace_id,
                    user_id=user_id,
                    details={
                        "requested_tools": detected_tools,
                        "tools_allowed": tool_result.get("tools_allowed", []),
                        "tool_reason": tool_result.get("tool_reason", "")
                    }
                )
            else:
                print("DEBUG: Tool gatekeeping skipped for current mode")
            
            # Update decision if tools not allowed
            decision = None
            reason = None
            if not tool_result.get("tools_allowed", True):
                if effective_mode == "Strong":
                    risk_level = "HIGH"
                    decision = "BLOCK"
                    reason = "Tool request not allowed in Strong mode"
                elif effective_mode in ["Normal", "Weak"]:
                    if decision != "BLOCK":  # Only escalate if not already blocked
                        decision = "SANITIZE"
                        reason = "Tool request not allowed"
            
            # Step 7: Make final decision if not already set by tool restrictions
            if decision not in ["BLOCK", "SANITIZE"]:
                decision, reason = await self.policy_engine.decide_action(risk_level, effective_mode)
            
            # Step 8: Check if sanitization needed
            needs_sanitization = await self.policy_engine.needs_sanitization(signals, risk_level, effective_mode)
            
            # Step 9: Generate response
            if decision == "BLOCK":
                response_text = "Your request was blocked due to security policy."
                # Do NOT call LLM service
            else:
                # Sanitize if needed
                final_prompt = self.text_sanitizer.sanitize_text(prompt) if needs_sanitization else prompt
                
                # Include clean context if available
                if clean_context:
                    final_prompt = f"Context: {clean_context}\n\nUser: {final_prompt}"
                else:
                    final_prompt = final_prompt
                
                response_text = await self.llm_service.generate_response(final_prompt, clean_context)
            
            # Step 10: Log events
            await self.metrics_logger.log_event(
                event_type="risk_scored",
                trace_id=trace_id,
                user_id=user_id,
                details={
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "signals_summary": signals
                }
            )
            
            await self.metrics_logger.log_decision(
                trace_id=trace_id,
                user_id=user_id,
                mode=effective_mode,
                risk_score=risk_score,
                risk_level=risk_level,
                decision=decision,
                reason=reason
            )
            
            # Step 11: Return response
            return ChatResponse(
                decision=decision,
                risk_level=risk_level,
                response=response_text,
                reason=reason,
                trace_id=trace_id,
                signals={
                    "prompt_injection_suspected": signals.get("prompt_injection_suspected", False),
                    "rag_injection_suspected": signals.get("rag_injection_suspected", False),
                    "tool_abuse_suspected": signals.get("tool_abuse_suspected", False),
                    "encoding_obfuscation": signals.get("encoding_obfuscation", False),
                    "steganography_suspected": signals.get("steganography_suspected", False),
                    "suspicious_keywords": signals.get("suspicious_keywords", []),
                    "pattern_hits": signals.get("pattern_hits", [])
                },
                user_id=user_id,
                security_mode=effective_mode_enum,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            # Log error and return safe response
            await self.metrics_logger.log_event(
                event_type="error",
                trace_id=trace_id,
                user_id=user_id,
                details={"error": str(e)}
            )
            
            return ChatResponse(
                decision="BLOCK",
                risk_level="HIGH",
                response="System error occurred. Request blocked for safety.",
                reason=f"Processing error: {str(e)}",
                trace_id=trace_id,
                signals=None,
                user_id=user_id,
                security_mode=shared_mode_manager.get_mode(),
                timestamp=datetime.now()
            )

    def _resolve_mode(self, mode: Any) -> SecurityMode:
        """Normalize string/enum inputs into SecurityMode."""
        if isinstance(mode, SecurityMode):
            return mode

        if isinstance(mode, str):
            normalized = mode.strip().lower()
            mode_map = {
                "off": SecurityMode.OFF,
                "weak": SecurityMode.WEAK,
                "normal": SecurityMode.NORMAL,
                "strong": SecurityMode.STRONG,
            }
            if normalized in mode_map:
                return mode_map[normalized]

        return SecurityMode.NORMAL
    
    def _build_clean_context(self, context_result: Dict[str, Any]) -> str:
        """Build context text deterministically from validated canonical context."""
        if not context_result:
            return ""

        if not context_result.get("context_safe", True):
            return context_result.get("clean_context", "")

        normalized_context = context_result.get("normalized_context", {})
        context_entries = normalized_context.get("contexts", []) if isinstance(normalized_context, dict) else []

        clean_chunks = []
        for entry in context_entries:
            if not isinstance(entry, dict):
                continue

            keyword = entry.get("keyword", "")
            content = entry.get("content", "")
            source = entry.get("source", "")
            if not content:
                continue

            clean_chunks.append(f"[{keyword}|{source}] {content}" if keyword or source else content)

        return "\n".join(clean_chunks)

    async def _sanitize_prompt(self, prompt: str) -> str:
        """Basic prompt sanitization"""
        # Remove potentially dangerous patterns
        sanitized = prompt.replace("system:", "").replace("admin:", "")
        # TODO: Implement more sophisticated sanitization
        return sanitized
