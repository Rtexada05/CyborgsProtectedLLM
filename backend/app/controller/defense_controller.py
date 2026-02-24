"""
Defense Controller - orchestrates the protection pipeline
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models.schemas import ChatResponse
from ..core.security_modes import SecurityMode
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
            effective_mode = shared_mode_manager.get_mode().value if mode is None else mode
            print(f"DEBUG: Effective mode: {effective_mode}")
            
            # Step 2: Analyze prompt
            signals = await self.input_checker.analyze(prompt)
            print(f"DEBUG: Analyzed signals: {signals}")
            
            # Step 3: Check RAG if needed
            context_result = None
            clean_context = None
            if await self.rag_manager.should_retrieve(prompt):
                raw_context = await self.rag_manager.retrieve_context(prompt)
                context_result = await self.rag_content_validator.validate_context(raw_context)
                clean_context = context_result.get("clean_context", "")
                
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
            
            # Step 4: Score risk
            risk_score, risk_level = await self.policy_engine.score_risk(signals, effective_mode)
            print(f"DEBUG: Risk scored - Score: {risk_score}, Level: {risk_level}")
            
            # Step 5: Check tool requests
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
            
            # Step 6: Make final decision if not already set by tool restrictions
            if decision not in ["BLOCK", "SANITIZE"]:
                decision, reason = await self.policy_engine.decide_action(risk_level, effective_mode)
            
            # Step 7: Check if sanitization needed
            needs_sanitization = await self.policy_engine.needs_sanitization(signals, risk_level, effective_mode)
            
            # Step 8: Generate response
            if decision == "BLOCK":
                response_text = "Your request was blocked due to security policy."
                # Do NOT call LLM service
            else:
                # Sanitize if needed
                final_prompt = await self.text_sanitizer.sanitize_text(prompt) if needs_sanitization else prompt
                
                # Include clean context if available
                if clean_context:
                    final_prompt = f"Context: {clean_context}\n\nUser: {final_prompt}"
                else:
                    final_prompt = final_prompt
                
                response_text = await self.llm_service.generate_response(final_prompt, clean_context)
            
            # Step 9: Log events
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
            
            # Step 10: Return response
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
                    "suspicious_keywords": signals.get("suspicious_keywords", []),
                    "pattern_hits": signals.get("pattern_hits", [])
                },
                user_id=user_id,
                security_mode=shared_mode_manager.get_mode(),
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
    
    async def _sanitize_prompt(self, prompt: str) -> str:
        """Basic prompt sanitization"""
        # Remove potentially dangerous patterns
        sanitized = prompt.replace("system:", "").replace("admin:", "")
        # TODO: Implement more sophisticated sanitization
        return sanitized
