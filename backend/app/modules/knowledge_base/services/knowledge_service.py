# app/modules/knowledge_base/services/knowledge_service.py
from typing import List, Dict, Any, Optional, Union
import asyncio
from datetime import datetime
import structlog
from dataclasses import dataclass, asdict

from app.core.vector_store import enhanced_vector_store, SearchQuery, SearchResult
from app.core.embeddings import embedding_pipeline
from app.modules.document_processing.chunker import adaptive_chunker
from app.modules.knowledge_base.types import DocumentType, KnowledgeDocument
from app.modules.knowledge_base.ingestion.document_ingester import DocumentIngester
from app.modules.knowledge_base.retrieval.semantic_retriever import SemanticRetriever
from app.modules.knowledge_base.services.cache_service import CacheService
from app.config import settings

logger = structlog.get_logger()

@dataclass
class SearchRequest:
    """Search request structure"""
    query: str
    document_types: List[DocumentType] = None
    filters: Dict[str, Any] = None
    top_k: int = 10
    search_strategy: str = "hybrid"  # vector, bm25, hybrid
    include_metadata: bool = True
    min_score: float = 0.0
    rerank: bool = True

@dataclass
class RetrievalResult:
    """Enhanced retrieval result with explainability"""
    document_id: str
    title: str
    content: str
    score: float
    document_type: DocumentType
    source: str
    metadata: Dict[str, Any]
    matched_snippets: List[str]
    explanation: str
    confidence: float

class KnowledgeBaseService:
    """Enterprise Knowledge Base Service"""
    
    def __init__(self):
        self.vector_store = enhanced_vector_store
        self.embedding_pipeline = embedding_pipeline
        self.document_ingester = DocumentIngester()
        self.semantic_retriever = SemanticRetriever()
        self.hybrid_retriever = None   # hybrid_retriever.py not yet implemented
        self.product_matcher = None    # product_matcher.py not yet implemented
        self.cache_service = CacheService()
        
        # Statistics
        self.stats = {
            "documents_indexed": 0,
            "searches_performed": 0,
            "cache_hits": 0,
            "avg_search_latency": 0.0
        }
        
        logger.info("Knowledge Base Service initialized")
    
    async def ingest_document(self, 
                            document: KnowledgeDocument,
                            file_path: Optional[str] = None) -> Dict[str, Any]:
        """Ingest a single document into the knowledge base"""
        try:
            start_time = datetime.now()
            
            logger.info("Starting document ingestion", 
                       document_id=document.id,
                       document_type=document.document_type.value)
            
            # Process document content if file path provided
            if file_path:
                processed_content = await self.document_ingester.process_file(
                    file_path, document.document_type
                )
                document.content = processed_content.get("text", document.content)
                document.metadata.update(processed_content.get("metadata", {}))
            
            # Chunk the document
            chunks = adaptive_chunker.chunk_document(
                document.content, 
                {
                    **document.metadata,
                    "document_id": document.id,
                    "document_type": document.document_type.value,
                    "source": document.source,
                    "title": document.title,
                    "importance_score": document.importance_score
                }
            )
            
            # Prepare documents for vector store
            vector_documents = []
            for i, chunk in enumerate(chunks):
                chunk_doc = {
                    "id": f"{document.id}_chunk_{i}",
                    "content": chunk.page_content,
                    "metadata": {
                        **chunk.metadata,
                        "parent_document_id": document.id,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                }
                vector_documents.append(chunk_doc)
            
            # Generate embeddings and add to vector store
            await self.vector_store.add_documents(vector_documents)
            
            # Update statistics
            self.stats["documents_indexed"] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "document_id": document.id,
                "status": "success",
                "chunks_created": len(chunks),
                "processing_time_seconds": processing_time,
                "metadata": document.metadata
            }
            
            logger.info("Document ingestion completed", 
                       document_id=document.id,
                       chunks=len(chunks),
                       processing_time=processing_time)
            
            return result
            
        except Exception as e:
            logger.error("Document ingestion failed", 
                        document_id=document.id,
                        error=str(e))
            raise
    
    async def ingest_batch(self, 
                          documents: List[KnowledgeDocument],
                          batch_size: int = 10) -> Dict[str, Any]:
        """Ingest multiple documents in batches"""
        try:
            start_time = datetime.now()
            
            logger.info("Starting batch ingestion", 
                       total_documents=len(documents),
                       batch_size=batch_size)
            
            results = []
            failed_documents = []
            
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Process batch concurrently
                batch_tasks = [
                    self.ingest_document(doc) for doc in batch
                ]
                
                batch_results = await asyncio.gather(
                    *batch_tasks, 
                    return_exceptions=True
                )
                
                # Collect results
                for doc, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        failed_documents.append({
                            "document_id": doc.id,
                            "error": str(result)
                        })
                    else:
                        results.append(result)
                
                logger.info("Batch processed", 
                           batch_number=i // batch_size + 1,
                           successful=len([r for r in batch_results if not isinstance(r, Exception)]),
                           failed=len([r for r in batch_results if isinstance(r, Exception)]))
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            summary = {
                "total_documents": len(documents),
                "successful": len(results),
                "failed": len(failed_documents),
                "processing_time_seconds": processing_time,
                "results": results,
                "failed_documents": failed_documents
            }
            
            logger.info("Batch ingestion completed", 
                       total=len(documents),
                       successful=len(results),
                       failed=len(failed_documents))
            
            return summary
            
        except Exception as e:
            logger.error("Batch ingestion failed", error=str(e))
            raise
    
    async def search(self, request: SearchRequest) -> List[RetrievalResult]:
        """Perform semantic search in the knowledge base"""
        try:
            start_time = datetime.now()
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_results = await self.cache_service.get(cache_key)
            
            if cached_results:
                self.stats["cache_hits"] += 1
                logger.info("Cache hit for search query", query=request.query[:50])
                return cached_results
            
            logger.info("Performing knowledge base search", 
                       query=request.query[:100],
                       strategy=request.search_strategy,
                       top_k=request.top_k)
            
            # Prepare search query
            search_query = SearchQuery(
                query=request.query,
                filters=self._build_filters(request),
                top_k=request.top_k * 2,  # Get more for reranking
                score_threshold=request.min_score,
                search_type=request.search_strategy,
                rerank=request.rerank
            )
            
            # Perform search based on strategy
            if request.search_strategy == "hybrid" and self.hybrid_retriever:
                raw_results = await self.hybrid_retriever.search(search_query)
            else:
                raw_results = await self.semantic_retriever.search(search_query)
            
            # Convert to retrieval results with explainability
            results = await self._enhance_results(raw_results, request.query)
            
            # Limit to requested number
            results = results[:request.top_k]
            
            # Cache results
            await self.cache_service.set(cache_key, results, ttl=3600)  # 1 hour
            
            # Update statistics
            self.stats["searches_performed"] += 1
            search_time = (datetime.now() - start_time).total_seconds()
            self.stats["avg_search_latency"] = (
                (self.stats["avg_search_latency"] * (self.stats["searches_performed"] - 1) + search_time) 
                / self.stats["searches_performed"]
            )
            
            logger.info("Search completed", 
                       query=request.query[:50],
                       results_count=len(results),
                       search_time=search_time)
            
            return results
            
        except Exception as e:
            logger.error("Search failed", 
                        query=request.query[:50],
                        error=str(e))
            raise
    
    async def find_similar_documents(self, 
                                   document_id: str, 
                                   top_k: int = 5) -> List[RetrievalResult]:
        """Find documents similar to a given document"""
        try:
            # Get the document content
            # This would typically involve querying the vector store for the document
            # For now, we'll implement a placeholder
            
            logger.info("Finding similar documents", 
                       document_id=document_id,
                       top_k=top_k)
            
            # Implementation would go here
            # This is a placeholder for the actual implementation
            
            return []
            
        except Exception as e:
            logger.error("Similar document search failed", 
                        document_id=document_id,
                        error=str(e))
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[KnowledgeDocument]:
        """Retrieve a document by its ID"""
        try:
            # Implementation would query the vector store metadata
            # This is a placeholder
            return None
            
        except Exception as e:
            logger.error("Document retrieval failed", 
                        document_id=document_id,
                        error=str(e))
            raise
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base"""
        try:
            logger.info("Deleting document", document_id=document_id)
            
            # Find all chunks for this document
            chunk_ids = []  # Would be populated by querying metadata
            
            # Delete from vector store
            await self.vector_store.delete_documents(chunk_ids)
            
            # Clear related cache entries
            await self.cache_service.clear_pattern(f"*{document_id}*")
            
            logger.info("Document deleted", document_id=document_id)
            return True
            
        except Exception as e:
            logger.error("Document deletion failed", 
                        document_id=document_id,
                        error=str(e))
            return False
    
    def _build_filters(self, request: SearchRequest) -> Dict[str, Any]:
        """Build metadata filters from search request"""
        filters = request.filters or {}
        
        # Add document type filter
        if request.document_types:
            filters["document_type"] = [dt.value for dt in request.document_types]
        
        return filters
    
    def _generate_cache_key(self, request: SearchRequest) -> str:
        """Generate cache key for search request"""
        import hashlib
        
        key_data = {
            "query": request.query,
            "document_types": [dt.value for dt in (request.document_types or [])],
            "filters": request.filters,
            "top_k": request.top_k,
            "strategy": request.search_strategy,
            "min_score": request.min_score
        }
        
        key_string = str(sorted(key_data.items()))
        return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def _enhance_results(self, 
                             raw_results: List[SearchResult], 
                             query: str) -> List[RetrievalResult]:
        """Enhance search results with explainability"""
        enhanced_results = []
        
        for result in raw_results:
            # Extract matched snippets
            matched_snippets = self._extract_snippets(result.content, query)
            
            # Generate explanation
            explanation = self._generate_explanation(result, query)
            
            # Calculate confidence
            confidence = self._calculate_confidence(result)
            
            enhanced_result = RetrievalResult(
                document_id=result.document_id,
                title=result.metadata.get("title", "Untitled"),
                content=result.content,
                score=result.score,
                document_type=DocumentType(result.metadata.get("document_type", "unknown")),
                source=result.metadata.get("source", "unknown"),
                metadata=result.metadata,
                matched_snippets=matched_snippets,
                explanation=explanation,
                confidence=confidence
            )
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _extract_snippets(self, content: str, query: str, max_snippets: int = 3) -> List[str]:
        """Extract relevant snippets from content"""
        import re
        
        query_terms = query.lower().split()
        sentences = re.split(r'[.!?]+', content)
        
        scored_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            # Score sentence based on query term matches
            sentence_lower = sentence.lower()
            score = sum(1 for term in query_terms if term in sentence_lower)
            
            if score > 0:
                scored_sentences.append((sentence, score))
        
        # Sort by score and return top snippets
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sentence for sentence, _ in scored_sentences[:max_snippets]]
    
    def _generate_explanation(self, result: SearchResult, query: str) -> str:
        """Generate explanation for why this result was retrieved"""
        score = result.score
        doc_type = result.metadata.get("document_type", "document")
        
        if score > 0.8:
            return f"High semantic similarity ({score:.2f}) to query. This {doc_type} contains highly relevant content."
        elif score > 0.6:
            return f"Good semantic match ({score:.2f}) to query. This {doc_type} has relevant information."
        elif score > 0.4:
            return f"Moderate relevance ({score:.2f}) to query. This {doc_type} may contain useful context."
        else:
            return f"Lower relevance ({score:.2f}) but potentially useful {doc_type} for broader context."
    
    def _calculate_confidence(self, result: SearchResult) -> float:
        """Calculate confidence score for the result"""
        # Base confidence on similarity score and metadata quality
        base_confidence = result.score
        
        # Boost confidence for high-quality documents
        importance = result.metadata.get("importance_score", 1.0)
        confidence_boost = min(0.2, importance * 0.1)
        
        return min(1.0, base_confidence + confidence_boost)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        vector_stats = self.vector_store.get_stats()
        
        return {
            **self.stats,
            **vector_stats,
            "cache_stats": self.cache_service.get_stats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on knowledge base components"""
        try:
            # Test vector store
            vector_health = self.vector_store.get_stats()
            
            # Test embedding pipeline
            test_embedding = await self.embedding_pipeline.encode_single("test")
            embedding_health = len(test_embedding) > 0
            
            # Test cache
            cache_health = await self.cache_service.health_check()
            
            return {
                "status": "healthy",
                "components": {
                    "vector_store": "healthy" if vector_health["total_documents"] >= 0 else "unhealthy",
                    "embedding_pipeline": "healthy" if embedding_health else "unhealthy",
                    "cache_service": "healthy" if cache_health else "unhealthy"
                },
                "statistics": self.get_statistics()
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Global knowledge base service instance
knowledge_base_service = KnowledgeBaseService()