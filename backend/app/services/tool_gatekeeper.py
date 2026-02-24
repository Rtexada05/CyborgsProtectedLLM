"""
Tool Gatekeeper - controls access to system tools and functions
"""

from typing import List, Dict, Any, Optional
import re

from ..models.schemas import SecuritySignal
from ..core.security_modes import SecurityMode


class ToolGatekeeper:
    """Controls access to system tools and prevents tool abuse"""
    
    def __init__(self):
        # Tool request patterns
        self.tool_patterns = {
            "calculate": [
                r"(?i)(calculate|compute|solve|math).*(\d+|formula|equation)",
                r"(?i)\d+\s*[\+\-\*\/]\s*\d+",
                r"(?i)(sqrt|power|log|sin|cos|tan)",
            ],
            "read_file": [
                r"(?i)(read|open|load|access).*(file|document|data)",
                r"(?i)(cat|type|view).*(file|content)",
                r"(?i)\.(txt|csv|json|xml|log).*(file|content)",
            ],
            "write_file": [
                r"(?i)(write|create|save|store).*(file|document)",
                r"(?i)(echo|print|output).*(to|into).*(file)",
                r"(?i)>>|>.*file",
            ],
            "execute_command": [
                r"(?i)(run|execute|exec|system).*(command|program|script)",
                r"(?i)(bash|cmd|powershell|shell)",
                r"(?i)\$(\w+|\{[^}]+\})",
            ],
            "network_request": [
                r"(?i)(fetch|download|request|curl|wget)",
                r"(?i)(http|https|ftp|api).*(request|call)",
                r"(?i)(connect|ping|nslookup)",
            ],
            "database_query": [
                r"(?i)(select|insert|update|delete).*(from|into)",
                r"(?i)(sql|query|database).*(execute|run)",
                r"(?i)(create|drop|alter).*(table|database)",
            ]
        }
        
        # Compile patterns
        self.compiled_patterns = {}
        for tool, patterns in self.tool_patterns.items():
            self.compiled_patterns[tool] = [re.compile(pattern) for pattern in patterns]
        
        # Dangerous tool combinations
        self.dangerous_combinations = [
            ["execute_command", "write_file"],
            ["network_request", "execute_command"],
            ["database_query", "write_file"],
        ]
    
    async def detect_tool_requests(self, prompt: str) -> List[Dict[str, Any]]:
        """Detect tool requests in the prompt"""
        
        detected_tools = []
        
        for tool_name, patterns in self.compiled_patterns.items():
            matches = []
            for pattern in patterns:
                pattern_matches = pattern.findall(prompt)
                if pattern_matches:
                    matches.extend(pattern_matches)
            
            if matches:
                detected_tools.append({
                    "tool_name": tool_name,
                    "matches": matches[:3],  # Limit to first 3 matches
                    "confidence": min(0.5 + (len(matches) * 0.1), 0.9),
                    "risk_level": self._get_tool_risk_level(tool_name)
                })
        
        return detected_tools
    
    async def evaluate_tools(
        self,
        tool_requests: List[Dict[str, Any]],
        mode: SecurityMode
    ) -> Dict[str, Any]:
        """Evaluate and decide which tools to allow"""
        
        allowed_tools = []
        blocked_tools = []
        
        for tool_request in tool_requests:
            tool_name = tool_request["tool_name"]
            risk_level = tool_request["risk_level"]
            
            # Check if tool is allowed based on mode and risk
            if await self._is_tool_allowed(tool_name, risk_level, mode):
                allowed_tools.append(tool_request)
            else:
                blocked_tools.append(tool_request)
        
        # Check for dangerous combinations
        allowed_tool_names = [t["tool_name"] for t in allowed_tools]
        for combination in self.dangerous_combinations:
            if all(tool in allowed_tool_names for tool in combination):
                # Block the entire combination
                for tool_name in combination:
                    for tool_request in allowed_tools:
                        if tool_request["tool_name"] == tool_name:
                            allowed_tools.remove(tool_request)
                            blocked_tools.append({
                                **tool_request,
                                "block_reason": "dangerous_combination"
                            })
        
        return {
            "allowed_tools": allowed_tools,
            "blocked_tools": blocked_tools,
            "total_requests": len(tool_requests),
            "decision_summary": f"Allowed {len(allowed_tools)}, blocked {len(blocked_tools)} tools"
        }
    
    async def _is_tool_allowed(
        self,
        tool_name: str,
        risk_level: str,
        mode: SecurityMode
    ) -> bool:
        """Check if a specific tool is allowed"""
        
        # Off mode allows everything
        if mode == SecurityMode.OFF:
            return True
        
        # Weak mode allows low-risk tools only
        if mode == SecurityMode.WEAK:
            return risk_level == "LOW"
        
        # Normal mode allows low and medium risk tools
        if mode == SecurityMode.NORMAL:
            return risk_level in ["LOW", "MEDIUM"]
        
        # Strong mode only allows very low-risk tools
        if mode == SecurityMode.STRONG:
            return tool_name == "calculate" and risk_level == "LOW"
        
        return False
    
    def _get_tool_risk_level(self, tool_name: str) -> str:
        """Get the risk level for a tool"""
        
        risk_mapping = {
            "calculate": "LOW",
            "read_file": "MEDIUM",
            "write_file": "HIGH",
            "execute_command": "HIGH",
            "network_request": "MEDIUM",
            "database_query": "HIGH"
        }
        
        return risk_mapping.get(tool_name, "MEDIUM")
    
    async def get_tool_safety_info(self, tool_name: str) -> Dict[str, Any]:
        """Get safety information for a tool"""
        
        safety_info = {
            "calculate": {
                "description": "Mathematical calculations",
                "risks": ["Resource exhaustion with complex calculations"],
                "mitigations": ["Limit calculation complexity", "Set timeouts"]
            },
            "read_file": {
                "description": "Read file contents",
                "risks": ["Accessing sensitive files", "Path traversal"],
                "mitigations": ["Restrict file paths", "Validate permissions"]
            },
            "write_file": {
                "description": "Write to files",
                "risks": ["Overwriting system files", "Data corruption"],
                "mitigations": ["Restrict write locations", "Validate content"]
            },
            "execute_command": {
                "description": "Execute system commands",
                "risks": ["Code injection", "System compromise"],
                "mitigations": ["Sandbox execution", "Command whitelist"]
            },
            "network_request": {
                "description": "Make network requests",
                "risks": ["Data exfiltration", "SSRF attacks"],
                "mitigations": ["Allowlist domains", "Monitor traffic"]
            },
            "database_query": {
                "description": "Execute database queries",
                "risks": ["SQL injection", "Data leakage"],
                "mitigations": ["Parameterized queries", "Access controls"]
            }
        }
        
        return safety_info.get(tool_name, {
            "description": "Unknown tool",
            "risks": ["Unknown risks"],
            "mitigations": ["Manual review required"]
        })

    async def detect_requested_tools(self, prompt: str, requested_tools: Optional[List[str]]) -> List[str]:
        """Detect requested tools from prompt or explicit list"""
        
        if requested_tools:
            return requested_tools
        
        # Detect from prompt
        prompt_lower = prompt.lower()
        detected_tools = []
        
        # Calculator patterns
        calculator_patterns = [
            r"(?i)(calculate|compute|solve|math).*(\d+|formula|equation)",
            r"(?i)\d+\s*[\+\-\*\/]\s*\d+",
            r"(?i)(sqrt|power|log|sin|cos|tan)"
        ]
        
        for pattern in calculator_patterns:
            if re.search(pattern, prompt):
                detected_tools.append("calculator")
                break
        
        # File reader patterns
        file_patterns = [
            r"(?i)(read|open|load|access).*(file|document|data)",
            r"(?i)(cat|type|view).*(file|content)",
            r"(?i)\.(txt|csv|json|xml|log).*(file|content)"
        ]
        
        for pattern in file_patterns:
            if re.search(pattern, prompt):
                detected_tools.append("file_reader")
                break
        
        # Web patterns
        web_patterns = [
            r"(?i)(browse|search|surf).*(web|internet)",
            r"(?i)(look up|find).*(online|website)"
        ]
        
        for pattern in web_patterns:
            if re.search(pattern, prompt):
                detected_tools.append("web")
                break
        
        return list(set(detected_tools))  # Remove duplicates
    
    async def authorize_tools(self, tools: List[str], mode: str, risk_level: str) -> Dict[str, Any]:
        """Authorize tools based on mode and risk level"""
        
        result = {
            "tools_allowed": True,
            "allowed_tools": tools.copy(),
            "tool_reason": "Tools allowed"
        }
        
        # Mode-specific rules
        if mode == "Off":
            # Allow all tools
            return result
        
        elif mode == "Weak":
            # Allow calculator, deny web/file_reader unless LOW
            if risk_level != "LOW":
                restricted_tools = ["web", "file_reader"]
                result["allowed_tools"] = [t for t in tools if t not in restricted_tools]
                if len(result["allowed_tools"]) < len(tools):
                    result["tools_allowed"] = False
                    result["tool_reason"] = "Web/file access not allowed in Weak mode for Medium/High risk"
        
        elif mode == "Normal":
            # Allow calculator if <=MEDIUM, deny web/file_reader unless LOW and no injection
            if risk_level not in ["LOW", "MEDIUM"]:
                restricted_tools = ["web", "file_reader"]
                result["allowed_tools"] = [t for t in tools if t not in restricted_tools]
                if len(result["allowed_tools"]) < len(tools):
                    result["tools_allowed"] = False
                    result["tool_reason"] = "Web/file access not allowed in Normal mode for High risk"
            elif risk_level == "HIGH":
                restricted_tools = ["web", "file_reader"]
                result["allowed_tools"] = [t for t in tools if t not in restricted_tools]
                if len(result["allowed_tools"]) < len(tools):
                    result["tools_allowed"] = False
                    result["tool_reason"] = "Web/file access not allowed in Normal mode for High risk"
        
        elif mode == "Strong":
            # Default deny all tools unless LOW and explicit allow list includes calculator only
            if risk_level != "LOW":
                result["tools_allowed"] = False
                result["allowed_tools"] = []
                result["tool_reason"] = "All tools blocked in Strong mode for Medium/High risk"
            else:
                # Only allow calculator in Strong mode even for LOW risk
                result["allowed_tools"] = [t for t in tools if t == "calculator"]
                if len(result["allowed_tools"]) < len(tools):
                    result["tools_allowed"] = False
                    result["tool_reason"] = "Only calculator allowed in Strong mode"
        
        print(f"DEBUG: Tool authorization - Mode: {mode}, Risk: {risk_level}, Tools: {tools}, Allowed: {result['allowed_tools']}")
        return result
