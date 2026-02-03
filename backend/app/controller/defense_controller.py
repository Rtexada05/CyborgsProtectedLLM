"""
Defense Controller - orchestrates the protection pipeline
"""

from typing import List, Dict, Any
from datetime import datetime

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
        self.metrics_logger = shared_metrics_logger
    
    async def handle_request(
        self,
        user_id: str,
        prompt: str,
        mode: SecurityMode,
        attachments: List[str]
    ) -> ChatResponse:
        """Handle a chat request through the defense pipeline"""
        
        # Initialize signals collection
        signals = []
        risk_factors = []
        
        try:
            # Step 1: Input Content Checking
            if mode != SecurityMode.OFF:
                input_signals = await self.input_checker.check_content(prompt)
                signals.extend(input_signals)
                if input_signals:
                    risk_factors.append("input_validation_issues")
            
            # Step 2: Steganography Detection
            if mode in [SecurityMode.NORMAL, SecurityMode.STRONG]:
                stego_signals = await self.stego_detector.detect_steganography(prompt)
                signals.extend(stego_signals)
                if stego_signals:
                    risk_factors.append("steganography_detected")
            
            # Step 3: RAG Processing (if requested)
            rag_context = None
            if "use context:" in prompt.lower():
                if mode != SecurityMode.OFF:
                    rag_context = await self.rag_manager.retrieve_context(prompt)
                    if rag_context and mode != SecurityMode.WEAK:
                        rag_validation = await self.rag_validator.validate_context(rag_context)
                        if not rag_validation["is_valid"]:
                            risk_factors.append("rag_content_blocked")
                            rag_context = None
            
            # Step 4: Tool Gatekeeping
            tool_requests = await self.tool_gatekeeper.detect_tool_requests(prompt)
            allowed_tools = []
            if tool_requests and mode != SecurityMode.OFF:
                tool_decision = await self.tool_gatekeeper.evaluate_tools(tool_requests, mode)
                allowed_tools = tool_decision["allowed_tools"]
                if tool_decision["blocked_tools"]:
                    risk_factors.append("tool_abuse_blocked")
            
            # Step 5: Policy Engine Evaluation
            policy_result = await self.policy_engine.evaluate_prompt(
                prompt=prompt,
                signals=signals,
                mode=mode,
                risk_factors=risk_factors
            )
            
            # Step 6: Generate Response
            if policy_result["decision"] == "BLOCK":
                response_text = "Request blocked due to security policy violation."
                reason = policy_result["reason"]
            elif policy_result["decision"] == "SANITIZE":
                sanitized_prompt = await self._sanitize_prompt(prompt)
                response_text = await self.llm_service.generate_response(
                    sanitized_prompt, rag_context, allowed_tools
                )
                reason = "Prompt sanitized and processed"
            else:  # ALLOW
                response_text = await self.llm_service.generate_response(
                    prompt, rag_context, allowed_tools
                )
                reason = "Request processed normally"
            
            # Step 7: Log the event
            await self.metrics_logger.log_event({
                "event_type": "chat_request",
                "user_id": user_id,
                "decision": policy_result["decision"],
                "risk_level": policy_result["risk_level"],
                "reason": reason,
                "signals_count": len(signals),
                "risk_factors": risk_factors
            })
            
            return ChatResponse(
                decision=policy_result["decision"],
                risk_level=policy_result["risk_level"],
                response=response_text,
                reason=reason,
                user_id=user_id,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            # Log error and return safe response
            await self.metrics_logger.log_event({
                "event_type": "error",
                "user_id": user_id,
                "error": str(e)
            })
            
            return ChatResponse(
                decision="BLOCK",
                risk_level="HIGH",
                response="System error occurred. Request blocked for safety.",
                reason=f"Processing error: {str(e)}",
                user_id=user_id,
                timestamp=datetime.now()
            )
    
    async def _sanitize_prompt(self, prompt: str) -> str:
        """Basic prompt sanitization"""
        # Remove potentially dangerous patterns
        sanitized = prompt.replace("system:", "").replace("admin:", "")
        # TODO: Implement more sophisticated sanitization
        return sanitized
