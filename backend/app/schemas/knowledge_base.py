# app/schemas/knowledge_base.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

from app.modules.knowledge_base.types import DocumentType

class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"

class SearchStrategy(str, Enum):
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"

# Request Schemas
class DocumentCreateRequest(BaseModel):
    """Request schema for creating a document"""
    title: str = Field(..., min_length=1, max_length=200, description="Document title")
    content: str = Field(..., min_length=10, description="Document content")
    document_type: DocumentType = Field(..., description="Type of document")
    source: Optional[str] = Field("manual", max_length=100, description="Document source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="Document tags")
    importance_score: Optional[float] = Field(1.0, ge=0.0, le=10.0, description="Importance score (0-10)")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return v
    
    @validator('content')
    def validate_content_length(cls, v):
        if len(v) > 100000:  # 100KB limit
            raise ValueError('Content too long (max 100KB)')
        return v

class BatchIngestRequest(BaseModel):
    """Request schema for batch document ingestion"""
    documents: List[DocumentCreateRequest] = Field(..., min_items=1, max_items=100)
    batch_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('documents')
    def validate_batch_size(cls, v):
        if len(v) > 100:
            raise ValueError('Maximum 100 documents per batch')
        return v

class SearchRequestSchema(BaseModel):
    """Request schema for knowledge base search"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    document_types: Optional[List[DocumentType]] = Field(None, description="Filter by document types")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return")
    search_strategy: SearchStrategy = Field(SearchStrategy.HYBRID, description="Search strategy")
    include_metadata: bool = Field(True, description="Include document metadata in results")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    rerank: bool = Field(True, description="Enable result reranking")
    
    @validator('query')
    def validate_query(cls, v):
        # Remove excessive whitespace
        cleaned = ' '.join(v.split())
        if len(cleaned) < 1:
            raise ValueError('Query cannot be empty')
        return cleaned

class SimilarDocumentsRequest(BaseModel):
    """Request schema for finding similar documents"""
    document_id: str = Field(..., description="Reference document ID")
    top_k: int = Field(5, ge=1, le=20, description="Number of similar documents to return")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")

# Response Schemas
class DocumentResponse(BaseModel):
    """Response schema for document information"""
    id: str
    title: str
    content: Optional[str] = None
    document_type: DocumentType
    source: str
    status: DocumentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    importance_score: float = 1.0
    validation_score: Optional[float] = None
    
    class Config:
        from_attributes = True

class SearchResultSchema(BaseModel):
    """Schema for individual search result"""
    document_id: str
    title: str
    content: str
    score: float = Field(..., ge=0.0, le=1.0)
    document_type: DocumentType
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    matched_snippets: List[str] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    @validator('matched_snippets')
    def limit_snippets(cls, v):
        return v[:5]  # Limit to 5 snippets

class SearchResponseSchema(BaseModel):
    """Response schema for search results"""
    query: str
    results: List[SearchResultSchema]
    total_results: int = Field(..., ge=0)
    search_time: float = Field(..., ge=0.0)
    search_strategy: SearchStrategy
    filters_applied: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = Field(default_factory=list)
    
    @validator('results')
    def sort_by_score(cls, v):
        return sorted(v, key=lambda x: x.score, reverse=True)

class BatchIngestResponse(BaseModel):
    """Response schema for batch ingestion"""
    batch_id: str
    document_count: int = Field(..., ge=0)
    status: DocumentStatus
    estimated_completion_time: Optional[int] = None  # seconds
    created_at: datetime = Field(default_factory=datetime.now)

class BatchIngestStatusResponse(BaseModel):
    """Response schema for batch ingestion status"""
    batch_id: str
    status: DocumentStatus
    total_documents: int
    processed_documents: int
    successful_documents: int
    failed_documents: int
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    estimated_remaining_time: Optional[int] = None  # seconds
    errors: List[str] = Field(default_factory=list)

class KnowledgeStatsResponse(BaseModel):
    """Response schema for knowledge base statistics"""
    total_documents: int = Field(..., ge=0)
    total_searches: int = Field(..., ge=0)
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0)
    avg_search_latency: float = Field(..., ge=0.0)
    vector_store_size: int = Field(..., ge=0)
    index_health: str
    document_types_distribution: Dict[str, int] = Field(default_factory=dict)
    recent_activity: Dict[str, Any] = Field(default_factory=dict)

class SimilarDocumentResponse(BaseModel):
    """Response schema for similar document"""
    document_id: str
    title: str
    score: float = Field(..., ge=0.0, le=1.0)
    document_type: DocumentType
    explanation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SimilarDocumentsResponse(BaseModel):
    """Response schema for similar documents search"""
    document_id: str
    similar_documents: List[SimilarDocumentResponse]
    total_found: int = Field(..., ge=0)

class SearchExplanationResponse(BaseModel):
    """Response schema for search result explanation"""
    query: str
    result_id: str
    explanation: str
    factors: Dict[str, Any]
    similarity_breakdown: Dict[str, float] = Field(default_factory=dict)
    matched_terms: List[str] = Field(default_factory=list)
    ranking_factors: Dict[str, float] = Field(default_factory=dict)

class HealthCheckResponse(BaseModel):
    """Response schema for health check"""
    status: str  # healthy, degraded, unhealthy
    components: Dict[str, str] = Field(default_factory=dict)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"

class ReindexResponse(BaseModel):
    """Response schema for reindexing operation"""
    message: str
    status: str
    estimated_time: str
    reindex_id: str
    started_at: datetime = Field(default_factory=datetime.now)

# Utility Schemas
class FilterSchema(BaseModel):
    """Schema for search filters"""
    document_type: Optional[List[DocumentType]] = None
    source: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date_range: Optional[Dict[str, datetime]] = None
    importance_range: Optional[Dict[str, float]] = None
    validation_score_range: Optional[Dict[str, float]] = None
    
    @validator('date_range')
    def validate_date_range(cls, v):
        if v and 'start' in v and 'end' in v:
            if v['start'] > v['end']:
                raise ValueError('Start date must be before end date')
        return v
    
    @validator('importance_range')
    def validate_importance_range(cls, v):
        if v:
            if 'min' in v and v['min'] < 0:
                raise ValueError('Minimum importance must be >= 0')
            if 'max' in v and v['max'] > 10:
                raise ValueError('Maximum importance must be <= 10')
            if 'min' in v and 'max' in v and v['min'] > v['max']:
                raise ValueError('Minimum importance must be <= maximum')
        return v

class QueryExpansionResponse(BaseModel):
    """Response schema for query expansion"""
    original_query: str
    expanded_queries: List[str]
    extracted_entities: Dict[str, List[str]] = Field(default_factory=dict)
    query_intent: str
    query_type: str
    suggested_filters: Dict[str, Any] = Field(default_factory=dict)

class DocumentValidationResponse(BaseModel):
    """Response schema for document validation"""
    document_id: str
    validation_score: float = Field(..., ge=0.0, le=1.0)
    is_valid: bool
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    quality_metrics: Dict[str, float] = Field(default_factory=dict)

# Error Schemas
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    """Validation error response schema"""
    error: str = "Validation Error"
    detail: str
    validation_errors: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.now)

# Configuration Schemas
class KnowledgeBaseConfig(BaseModel):
    """Configuration schema for knowledge base"""
    max_document_size: int = Field(50 * 1024 * 1024)  # 50MB
    max_batch_size: int = 100
    default_search_strategy: SearchStrategy = SearchStrategy.HYBRID
    cache_ttl: int = 3600  # 1 hour
    enable_query_expansion: bool = True
    enable_reranking: bool = True
    similarity_threshold: float = Field(0.5, ge=0.0, le=1.0)
    max_search_results: int = 50
    
    class Config:
        validate_assignment = True

# Export all schemas
__all__ = [
    # Request schemas
    "DocumentCreateRequest",
    "BatchIngestRequest", 
    "SearchRequestSchema",
    "SimilarDocumentsRequest",
    
    # Response schemas
    "DocumentResponse",
    "SearchResultSchema",
    "SearchResponseSchema",
    "BatchIngestResponse",
    "BatchIngestStatusResponse",
    "KnowledgeStatsResponse",
    "SimilarDocumentResponse",
    "SimilarDocumentsResponse",
    "SearchExplanationResponse",
    "HealthCheckResponse",
    "ReindexResponse",
    
    # Utility schemas
    "FilterSchema",
    "QueryExpansionResponse",
    "DocumentValidationResponse",
    
    # Error schemas
    "ErrorResponse",
    "ValidationErrorResponse",
    
    # Configuration schemas
    "KnowledgeBaseConfig",
    
    # Enums
    "DocumentStatus",
    "SearchStrategy"
]