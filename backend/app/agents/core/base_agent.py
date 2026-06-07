from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from app.modules.knowledge_base.services.knowledge_service import KnowledgeBaseService
from app.modules.knowledge_base.retrieval.semantic_retriever import SemanticRetriever, RetrievalConfig

@dataclass
class ReasoningTrace:
    """Structured reasoning trace for explainable AI"""
    agent_name: str
    step: str
    reasoning: str
    evidence: List[Dict[str, Any]]
    confidence: float
    timestamp: datetime
    sources: List[str]

@dataclass
class AgentResult:
    """Standardized agent result with explainability"""
    agent_name: str
    result: Dict[str, Any]
    reasoning_traces: List[ReasoningTrace]
    confidence_score: float
    execution_time: float
    retrieved_context: List[Dict[str, Any]]
    citations: List[str]

class BaseElevateAgent(ABC):
    """Base class for all ElevateRFP agents with RAG integration"""
    
    def __init__(self, name: str, role: str, goal: str, backstory: str):
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.knowledge_service = KnowledgeBaseService()
        self.semantic_retriever = SemanticRetriever()
        self.reasoning_traces: List[ReasoningTrace] = []
        self.logger = logging.getLogger(f"agent.{name}")
    
    def add_reasoning_trace(self, step: str, reasoning: str, evidence: List[Dict], confidence: float, sources: List[str] = None):
        """Add reasoning trace for explainability"""
        trace = ReasoningTrace(
            agent_name=self.name,
            step=step,
            reasoning=reasoning,
            evidence=evidence or [],
            confidence=confidence,
            timestamp=datetime.now(),
            sources=sources or []
        )
        self.reasoning_traces.append(trace)
    
    async def retrieve_knowledge(self, query: str, filters: Dict = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge using RAG"""
        try:
            results = await self.semantic_retriever.search(
                query=query,
                filters=filters,
                config=RetrievalConfig(top_k=top_k)
            )
            # Normalise SemanticSearchResult objects to plain dicts
            results_as_dicts = [
                {
                    "content": r.content,
                    "source": r.source_attribution.get("source", "unknown"),
                    "similarity_score": r.semantic_similarity,
                    "metadata": r.metadata,
                    "explanation": r.query_match_explanation,
                }
                for r in results
            ]
            
            self.add_reasoning_trace(
                step="knowledge_retrieval",
                reasoning=f"Retrieved {len(results_as_dicts)} relevant documents for query: {query}",
                evidence=results_as_dicts,
                confidence=0.9,
                sources=[r.get('source', 'unknown') for r in results_as_dicts]
            )
            return results_as_dicts
        except Exception as e:
            self.logger.error(f"Knowledge retrieval failed: {e}")
            return []
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute agent logic with context"""
        pass
    
    @abstractmethod
    def get_tools(self) -> List:
        """Get agent-specific tools"""
        pass