from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from app.modules.knowledge_base.services.knowledge_service import KnowledgeBaseService
from app.modules.knowledge_base.retrieval.semantic_retriever import SemanticRetriever
import json

# Lightweight replacement for crewai_tools.BaseTool
class BaseTool(BaseModel, ABC):
    """Base class for custom tools"""
    name: str
    description: str
    
    @abstractmethod
    def _run(self, *args, **kwargs) -> str:
        """Execute the tool logic"""
        pass
    
    class Config:
        arbitrary_types_allowed = True

class KnowledgeSearchInput(BaseModel):
    """Input schema for knowledge search tool"""
    query: str = Field(..., description="Search query for knowledge retrieval")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters for search")
    top_k: int = Field(5, description="Number of results to retrieve")

class KnowledgeSearchTool(BaseTool):
    """Tool for semantic knowledge search"""
    name: str = "knowledge_search"
    description: str = "Search the enterprise knowledge base using semantic similarity"
    args_schema: type[BaseModel] = KnowledgeSearchInput
    
    def __init__(self):
        super().__init__()
        self.knowledge_service = KnowledgeBaseService()
        self.semantic_retriever = SemanticRetriever()
    
    def _run(self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 5) -> str:
        """Execute knowledge search"""
        try:
            # Use asyncio to run async method
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(
                self.semantic_retriever.search(
                    query=query,
                    filters=filters,
                    top_k=top_k,
                    include_explanation=True
                )
            )
            
            # Format results for agent consumption
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "metadata": result.get("metadata", {}),
                    "explanation": result.get("explanation", "")
                })
            
            return json.dumps(formatted_results, indent=2)
            
        except Exception as e:
            return f"Error searching knowledge base: {str(e)}"

class ProductMatchingInput(BaseModel):
    """Input schema for product matching tool"""
    requirements: str = Field(..., description="Requirements to match against products")
    capacity_kg: Optional[int] = Field(None, description="Required capacity in kg")
    max_floors: Optional[int] = Field(None, description="Maximum floors")
    speed_ms: Optional[float] = Field(None, description="Required speed in m/s")

class ProductMatchingTool(BaseTool):
    """Tool for product matching based on requirements"""
    name: str = "product_matching"
    description: str = "Match requirements against available elevator products"
    args_schema: type[BaseModel] = ProductMatchingInput
    
    def __init__(self):
        super().__init__()
        self.knowledge_service = KnowledgeBaseService()
    
    def _run(self, requirements: str, capacity_kg: Optional[int] = None, 
             max_floors: Optional[int] = None, speed_ms: Optional[float] = None) -> str:
        """Execute product matching"""
        try:
            # Build search query
            query_parts = [requirements]
            if capacity_kg:
                query_parts.append(f"capacity {capacity_kg}kg")
            if max_floors:
                query_parts.append(f"{max_floors} floors")
            if speed_ms:
                query_parts.append(f"speed {speed_ms}m/s")
            
            search_query = " ".join(query_parts)
            
            # Search for matching products
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(
                self.knowledge_service.search_documents(
                    query=search_query,
                    filters={"document_type": "product_catalog"},
                    top_k=10
                )
            )
            
            # Filter and rank products
            matched_products = []
            for result in results:
                product_data = result.get("metadata", {})
                match_score = result.get("similarity_score", 0.0)
                
                # Apply capacity filter
                if capacity_kg and product_data.get("capacity_kg", 0) < capacity_kg:
                    match_score *= 0.5
                
                # Apply floors filter
                if max_floors and product_data.get("max_floors", 0) < max_floors:
                    match_score *= 0.5
                
                # Apply speed filter
                if speed_ms and product_data.get("speed_ms", 0) < speed_ms:
                    match_score *= 0.5
                
                matched_products.append({
                    "product_id": product_data.get("product_id", ""),
                    "model": product_data.get("model", ""),
                    "capacity_kg": product_data.get("capacity_kg", 0),
                    "max_floors": product_data.get("max_floors", 0),
                    "speed_ms": product_data.get("speed_ms", 0),
                    "base_price": product_data.get("base_price", 0),
                    "match_score": match_score,
                    "content": result.get("content", "")
                })
            
            # Sort by match score
            matched_products.sort(key=lambda x: x["match_score"], reverse=True)
            
            return json.dumps(matched_products[:5], indent=2)
            
        except Exception as e:
            return f"Error matching products: {str(e)}"

class ComplianceCheckInput(BaseModel):
    """Input schema for compliance checking tool"""
    requirements: str = Field(..., description="Requirements to check for compliance")
    compliance_types: List[str] = Field(["GDPR", "ISO27001", "SOC2"], description="Compliance standards to check")

class ComplianceCheckTool(BaseTool):
    """Tool for compliance validation"""
    name: str = "compliance_check"
    description: str = "Check requirements against compliance standards"
    args_schema: type[BaseModel] = ComplianceCheckInput
    
    def __init__(self):
        super().__init__()
        self.knowledge_service = KnowledgeBaseService()
    
    def _run(self, requirements: str, compliance_types: List[str] = None) -> str:
        """Execute compliance check"""
        try:
            if not compliance_types:
                compliance_types = ["GDPR", "ISO27001", "SOC2"]
            
            compliance_results = {}
            
            for compliance_type in compliance_types:
                # Search for compliance-related documents
                search_query = f"{requirements} {compliance_type} compliance"
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = loop.run_until_complete(
                    self.knowledge_service.search_documents(
                        query=search_query,
                        filters={"document_type": "compliance", "compliance_standard": compliance_type},
                        top_k=5
                    )
                )
                
                # Analyze compliance
                compliance_score = 0.0
                compliance_gaps = []
                compliance_evidence = []
                
                for result in results:
                    score = result.get("similarity_score", 0.0)
                    compliance_score = max(compliance_score, score)
                    
                    if score > 0.7:
                        compliance_evidence.append({
                            "content": result.get("content", ""),
                            "source": result.get("source", ""),
                            "score": score
                        })
                    elif score < 0.3:
                        compliance_gaps.append({
                            "requirement": result.get("content", ""),
                            "gap_reason": "Low similarity to compliance standards"
                        })
                
                compliance_results[compliance_type] = {
                    "compliance_score": compliance_score,
                    "status": "compliant" if compliance_score > 0.7 else "non_compliant" if compliance_score < 0.3 else "partial",
                    "evidence": compliance_evidence,
                    "gaps": compliance_gaps
                }
            
            return json.dumps(compliance_results, indent=2)
            
        except Exception as e:
            return f"Error checking compliance: {str(e)}"

class HistoricalDataInput(BaseModel):
    """Input schema for historical data retrieval"""
    query: str = Field(..., description="Query for historical data")
    data_type: str = Field("proposals", description="Type of historical data (proposals, pricing, projects)")

class HistoricalDataTool(BaseTool):
    """Tool for retrieving historical data"""
    name: str = "historical_data"
    description: str = "Retrieve historical proposals, pricing, and project data"
    args_schema: type[BaseModel] = HistoricalDataInput
    
    def __init__(self):
        super().__init__()
        self.knowledge_service = KnowledgeBaseService()
    
    def _run(self, query: str, data_type: str = "proposals") -> str:
        """Execute historical data retrieval"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(
                self.knowledge_service.search_documents(
                    query=query,
                    filters={"document_type": data_type},
                    top_k=10
                )
            )
            
            historical_data = []
            for result in results:
                historical_data.append({
                    "content": result.get("content", ""),
                    "source": result.get("source", ""),
                    "metadata": result.get("metadata", {}),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "timestamp": result.get("metadata", {}).get("created_at", "")
                })
            
            return json.dumps(historical_data, indent=2)
            
        except Exception as e:
            return f"Error retrieving historical data: {str(e)}"