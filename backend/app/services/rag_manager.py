"""
RAG Manager - handles retrieval-augmented generation context
"""

from typing import List, Dict, Any, Optional
import re

from ..models.schemas import SecuritySignal


class RAGManager:
    """Manages RAG context retrieval and processing"""
    
    def __init__(self):
        # Stub context database (in production, this would connect to vector DB)
        self.stub_contexts = {
            "python": "Python is a high-level programming language...",
            "security": "Security best practices include input validation...",
            "ai": "Artificial Intelligence systems require careful oversight...",
            "database": "Database security involves proper access controls...",
        }
        
        # Context extraction patterns
        self.context_patterns = [
            r"(?i)use context[:\s]+(.+)",
            r"(?i)based on[:\s]+(.+)",
            r"(?i)refer to[:\s]+(.+)",
            r"(?i)context[:\s]+(.+)",
        ]
        
        self.compiled_patterns = [re.compile(pattern) for pattern in self.context_patterns]
    
    async def retrieve_context(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Retrieve context based on prompt content"""
        
        # Check if prompt contains context requests
        context_keywords = self._extract_context_keywords(prompt)
        
        if not context_keywords:
            return None
        
        # Stub context retrieval (in production, this would query vector DB)
        retrieved_contexts = []
        for keyword in context_keywords:
            if keyword.lower() in self.stub_contexts:
                retrieved_contexts.append({
                    "keyword": keyword,
                    "content": self.stub_contexts[keyword.lower()],
                    "source": f"stub_db_{keyword}",
                    "relevance_score": 0.8
                })
        
        if not retrieved_contexts:
            # Return generic context if no specific matches
            return {
                "contexts": [{
                    "keyword": "general",
                    "content": "General information about the topic requested.",
                    "source": "stub_db_general",
                    "relevance_score": 0.5
                }],
                "total_contexts": 1,
                "retrieval_method": "keyword_match"
            }
        
        return {
            "contexts": retrieved_contexts,
            "total_contexts": len(retrieved_contexts),
            "retrieval_method": "keyword_match",
            "keywords_used": context_keywords
        }
    
    def _extract_context_keywords(self, prompt: str) -> List[str]:
        """Extract context keywords from prompt"""
        
        keywords = []
        
        # Try to extract using patterns
        for pattern in self.compiled_patterns:
            matches = pattern.findall(prompt)
            for match in matches:
                # Clean and split the match
                cleaned = re.sub(r'[^\w\s]', ' ', match).strip()
                words = [word.strip() for word in cleaned.split() if word.strip()]
                keywords.extend(words[:3])  # Limit to first 3 words
        
        # If no pattern matches, look for "use context:" specifically
        if "use context:" in prompt.lower():
            context_part = prompt.lower().split("use context:")[-1].strip()
            words = [word.strip() for word in re.sub(r'[^\w\s]', ' ', context_part).split() if word.strip()]
            keywords.extend(words[:2])
        
        # Remove duplicates and return
        return list(set(keywords))[:5]  # Limit to 5 keywords
    
    async def search_contexts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for contexts based on query (stub implementation)"""
        
        # Simple keyword matching for stub implementation
        results = []
        query_lower = query.lower()
        
        for keyword, content in self.stub_contexts.items():
            if keyword in query_lower or any(word in query_lower for word in keyword.split()):
                results.append({
                    "keyword": keyword,
                    "content": content,
                    "source": f"stub_db_{keyword}",
                    "relevance_score": 0.7
                })
        
        return results[:limit]
    
    async def validate_context_request(self, prompt: str) -> Dict[str, Any]:
        """Validate if context request is legitimate"""
        
        # Check for suspicious context requests
        suspicious_patterns = [
            r"(?i)(all|every).*(context|data|information)",
            r"(?i)(admin|system|internal).*(context|data)",
            r"(?i)(bypass|override).*(context|security)",
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, prompt):
                return {
                    "is_valid": False,
                    "reason": "Suspicious context request pattern detected",
                    "risk_level": "HIGH"
                }
        
        # Check for reasonable request length
        if len(prompt) > 2000:
            return {
                "is_valid": False,
                "reason": "Context request too long",
                "risk_level": "MEDIUM"
            }
        
        return {
            "is_valid": True,
            "reason": "Context request appears legitimate",
            "risk_level": "LOW"
        }
