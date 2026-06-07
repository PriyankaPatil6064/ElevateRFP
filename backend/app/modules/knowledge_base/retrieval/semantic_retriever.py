# app/modules/knowledge_base/retrieval/semantic_retriever.py
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import structlog
import numpy as np
from dataclasses import dataclass

from app.core.vector_store import enhanced_vector_store, SearchQuery, SearchResult
from app.core.embeddings import embedding_pipeline
from app.modules.knowledge_base.retrieval.query_processor import QueryProcessor

logger = structlog.get_logger()

@dataclass
class RetrievalConfig:
    """Configuration for semantic retrieval"""
    top_k: int = 10
    similarity_threshold: float = 0.5
    max_context_length: int = 4000
    enable_query_expansion: bool = True
    enable_reranking: bool = True
    enable_diversity: bool = True
    diversity_threshold: float = 0.8

@dataclass
class SemanticSearchResult:
    """Enhanced search result with semantic information"""
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    semantic_similarity: float
    query_match_explanation: str
    matched_concepts: List[str]
    context_relevance: float
    source_attribution: Dict[str, Any]

class SemanticRetriever:
    """Advanced semantic retrieval engine"""
    
    def __init__(self, config: RetrievalConfig = None):
        self.config = config or RetrievalConfig()
        self.vector_store = enhanced_vector_store
        self.embedding_pipeline = embedding_pipeline
        self.query_processor = QueryProcessor()
        self.result_ranker = None   # result_ranker.py not yet implemented
        self.context_builder = None  # context_builder.py not yet implemented
        
        # Performance tracking
        self.stats = {
            "total_searches": 0,
            "avg_search_time": 0.0,
            "cache_hits": 0,
            "query_expansions": 0
        }
        
        logger.info("Semantic Retriever initialized", config=self.config)
    
    async def search(self, 
                    query: str,
                    filters: Dict[str, Any] = None,
                    config: RetrievalConfig = None) -> List[SemanticSearchResult]:
        """Perform semantic search with advanced features"""
        start_time = datetime.now()
        search_config = config or self.config
        
        try:
            logger.info("Starting semantic search", 
                       query=query[:100],
                       filters=filters,
                       top_k=search_config.top_k)
            
            # Step 1: Process and expand query
            processed_query = await self.query_processor.process_query(
                query, 
                expand=search_config.enable_query_expansion
            )
            
            if processed_query.expanded_queries:
                self.stats["query_expansions"] += 1
            
            # Step 2: Perform vector search
            search_results = await self._vector_search(
                processed_query, 
                filters, 
                search_config
            )
            
            # Step 3: Rerank results if enabled
            if search_config.enable_reranking and len(search_results) > 1 and self.result_ranker:
                search_results = await self.result_ranker.rerank_results(
                    query,
                    search_results
                )
            
            # Step 4: Apply diversity filtering if enabled
            if search_config.enable_diversity:
                search_results = await self._apply_diversity_filtering(
                    search_results, 
                    search_config.diversity_threshold
                )
            
            # Step 5: Enhance results with semantic information
            enhanced_results = await self._enhance_results(
                query, 
                search_results, 
                processed_query
            )
            
            # Step 6: Limit to requested number
            final_results = enhanced_results[:search_config.top_k]
            
            # Update statistics
            search_time = (datetime.now() - start_time).total_seconds()
            self.stats["total_searches"] += 1
            self.stats["avg_search_time"] = (
                (self.stats["avg_search_time"] * (self.stats["total_searches"] - 1) + search_time) 
                / self.stats["total_searches"]
            )
            
            logger.info("Semantic search completed", 
                       query=query[:50],
                       results_count=len(final_results),
                       search_time=search_time)
            
            return final_results
            
        except Exception as e:
            logger.error("Semantic search failed", 
                        query=query[:50],
                        error=str(e))
            raise
    
    async def find_similar_content(self, 
                                  content: str,
                                  filters: Dict[str, Any] = None,
                                  top_k: int = 5) -> List[SemanticSearchResult]:
        """Find content similar to provided text"""
        try:
            logger.info("Finding similar content", 
                       content_length=len(content),
                       top_k=top_k)
            
            # Use content as query
            return await self.search(
                content[:500],  # Limit content length for query
                filters=filters,
                config=RetrievalConfig(
                    top_k=top_k,
                    enable_query_expansion=False,  # Don't expand for similarity search
                    enable_reranking=True
                )
            )
            
        except Exception as e:
            logger.error("Similar content search failed", error=str(e))
            raise
    
    async def search_by_concepts(self, 
                               concepts: List[str],
                               filters: Dict[str, Any] = None,
                               top_k: int = 10) -> List[SemanticSearchResult]:
        """Search by semantic concepts"""
        try:
            logger.info("Searching by concepts", 
                       concepts=concepts,
                       top_k=top_k)
            
            # Combine concepts into a query
            query = " ".join(concepts)
            
            return await self.search(
                query,
                filters=filters,
                config=RetrievalConfig(
                    top_k=top_k,
                    enable_query_expansion=True,
                    enable_diversity=True
                )
            )
            
        except Exception as e:
            logger.error("Concept search failed", error=str(e))
            raise
    
    async def _vector_search(self, 
                           processed_query,
                           filters: Dict[str, Any],
                           config: RetrievalConfig) -> List[SearchResult]:
        """Perform vector similarity search"""
        try:
            # Create search query for vector store
            search_query = SearchQuery(
                query=processed_query.original_query,
                filters=filters,
                top_k=config.top_k * 2,  # Get more results for reranking
                score_threshold=config.similarity_threshold,
                search_type="vector",
                rerank=False  # We'll handle reranking separately
            )
            
            # Perform primary search
            primary_results = await self.vector_store.search(search_query)
            
            # If query expansion is enabled, search with expanded queries
            if processed_query.expanded_queries:
                expanded_results = []
                
                for expanded_query in processed_query.expanded_queries[:3]:  # Limit expansions
                    expanded_search_query = SearchQuery(
                        query=expanded_query,
                        filters=filters,
                        top_k=config.top_k,
                        score_threshold=config.similarity_threshold * 0.8,  # Lower threshold for expansions
                        search_type="vector",
                        rerank=False
                    )
                    
                    exp_results = await self.vector_store.search(expanded_search_query)
                    expanded_results.extend(exp_results)
                
                # Combine and deduplicate results
                all_results = primary_results + expanded_results
                seen_ids = set()
                unique_results = []
                
                for result in all_results:
                    if result.document_id not in seen_ids:
                        seen_ids.add(result.document_id)
                        unique_results.append(result)
                
                # Sort by score
                unique_results.sort(key=lambda x: x.score, reverse=True)
                return unique_results[:config.top_k * 2]
            
            return primary_results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            raise
    
    async def _apply_diversity_filtering(self, 
                                       results: List[SearchResult],
                                       diversity_threshold: float) -> List[SearchResult]:
        """Apply diversity filtering to avoid similar results"""
        if len(results) <= 1:
            return results
        
        try:
            # Extract embeddings for all results
            contents = [result.content for result in results]
            embeddings = await self.embedding_pipeline.encode_texts(contents)
            
            # Apply diversity filtering
            diverse_results = []
            diverse_embeddings = []
            
            for i, result in enumerate(results):
                current_embedding = embeddings[i]
                
                # Check similarity with already selected results
                is_diverse = True
                
                for diverse_embedding in diverse_embeddings:
                    similarity = np.dot(current_embedding, diverse_embedding) / (
                        np.linalg.norm(current_embedding) * np.linalg.norm(diverse_embedding)
                    )
                    
                    if similarity > diversity_threshold:
                        is_diverse = False
                        break
                
                if is_diverse:
                    diverse_results.append(result)
                    diverse_embeddings.append(current_embedding)
            
            logger.info("Diversity filtering applied", 
                       original_count=len(results),
                       diverse_count=len(diverse_results))
            
            return diverse_results
            
        except Exception as e:
            logger.warning("Diversity filtering failed", error=str(e))
            return results  # Return original results if filtering fails
    
    async def _enhance_results(self, 
                             query: str,
                             results: List[SearchResult],
                             processed_query) -> List[SemanticSearchResult]:
        """Enhance search results with semantic information"""
        enhanced_results = []
        
        try:
            # Generate query embedding for similarity calculations
            query_embedding = await self.embedding_pipeline.encode_single(query)
            
            for result in results:
                # Calculate semantic similarity
                content_embedding = await self.embedding_pipeline.encode_single(result.content)
                semantic_similarity = float(np.dot(query_embedding, content_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(content_embedding)
                ))
                
                # Extract matched concepts
                matched_concepts = await self._extract_matched_concepts(
                    query, 
                    result.content, 
                    processed_query
                )
                
                # Generate query match explanation
                explanation = await self._generate_match_explanation(
                    query, 
                    result, 
                    semantic_similarity,
                    matched_concepts
                )
                
                # Calculate context relevance
                context_relevance = await self._calculate_context_relevance(
                    result, 
                    processed_query
                )
                
                # Create source attribution
                source_attribution = self._create_source_attribution(result)
                
                enhanced_result = SemanticSearchResult(
                    document_id=result.document_id,
                    content=result.content,
                    score=result.score,
                    metadata=result.metadata,
                    semantic_similarity=semantic_similarity,
                    query_match_explanation=explanation,
                    matched_concepts=matched_concepts,
                    context_relevance=context_relevance,
                    source_attribution=source_attribution
                )
                
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            logger.error("Result enhancement failed", error=str(e))
            # Return basic results if enhancement fails
            return [
                SemanticSearchResult(
                    document_id=r.document_id,
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                    semantic_similarity=r.score,
                    query_match_explanation="Basic similarity match",
                    matched_concepts=[],
                    context_relevance=r.score,
                    source_attribution={"source": r.metadata.get("source", "unknown")}
                )
                for r in results
            ]
    
    async def _extract_matched_concepts(self, 
                                      query: str,
                                      content: str,
                                      processed_query) -> List[str]:
        """Extract concepts that match between query and content"""
        try:
            # Simple keyword-based concept extraction
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            
            # Find common words (basic concept matching)
            common_words = query_words.intersection(content_words)
            
            # Filter out common stop words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
            }
            
            concepts = [word for word in common_words if word not in stop_words and len(word) > 2]
            
            # Add expanded query terms if they appear in content
            if hasattr(processed_query, 'expanded_terms'):
                for term in processed_query.expanded_terms:
                    if term.lower() in content.lower():
                        concepts.append(term)
            
            return list(set(concepts))[:10]  # Limit to top 10 concepts
            
        except Exception as e:
            logger.warning("Concept extraction failed", error=str(e))
            return []
    
    async def _generate_match_explanation(self, 
                                        query: str,
                                        result: SearchResult,
                                        semantic_similarity: float,
                                        matched_concepts: List[str]) -> str:
        """Generate explanation for why this result matches the query"""
        try:
            explanation_parts = []
            
            # Similarity-based explanation
            if semantic_similarity > 0.8:
                explanation_parts.append("High semantic similarity to query")
            elif semantic_similarity > 0.6:
                explanation_parts.append("Good semantic match with query")
            elif semantic_similarity > 0.4:
                explanation_parts.append("Moderate semantic relevance")
            else:
                explanation_parts.append("Lower semantic similarity but potentially relevant")
            
            # Concept-based explanation
            if matched_concepts:
                if len(matched_concepts) > 3:
                    explanation_parts.append(f"Contains multiple matching concepts: {', '.join(matched_concepts[:3])} and {len(matched_concepts) - 3} more")
                else:
                    explanation_parts.append(f"Contains matching concepts: {', '.join(matched_concepts)}")
            
            # Document type relevance
            doc_type = result.metadata.get("document_type", "")
            if doc_type:
                explanation_parts.append(f"Relevant {doc_type.replace('_', ' ')} document")
            
            # Source credibility
            source = result.metadata.get("source", "")
            if source:
                explanation_parts.append(f"From {source}")
            
            return ". ".join(explanation_parts) + "."
            
        except Exception as e:
            logger.warning("Match explanation generation failed", error=str(e))
            return f"Semantic similarity score: {semantic_similarity:.2f}"
    
    async def _calculate_context_relevance(self, 
                                         result: SearchResult,
                                         processed_query) -> float:
        """Calculate how relevant the result is in the current context"""
        try:
            relevance_score = result.score  # Base on similarity score
            
            # Boost for document importance
            importance = result.metadata.get("importance_score", 1.0)
            relevance_score *= importance
            
            # Boost for recent documents
            created_at = result.metadata.get("created_at")
            if created_at:
                # Simple recency boost (this would be more sophisticated in practice)
                relevance_score *= 1.1
            
            # Boost for high-quality documents
            validation_score = result.metadata.get("validation_score", 1.0)
            relevance_score *= validation_score
            
            return min(1.0, relevance_score)
            
        except Exception as e:
            logger.warning("Context relevance calculation failed", error=str(e))
            return result.score
    
    def _create_source_attribution(self, result: SearchResult) -> Dict[str, Any]:
        """Create source attribution information"""
        return {
            "source": result.metadata.get("source", "unknown"),
            "document_type": result.metadata.get("document_type", "unknown"),
            "title": result.metadata.get("title", "Untitled"),
            "section": result.metadata.get("source_section"),
            "page": result.metadata.get("page_number"),
            "chunk_id": result.metadata.get("chunk_id"),
            "confidence": result.metadata.get("validation_score", 1.0)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        return {
            **self.stats,
            "config": {
                "top_k": self.config.top_k,
                "similarity_threshold": self.config.similarity_threshold,
                "query_expansion_enabled": self.config.enable_query_expansion,
                "reranking_enabled": self.config.enable_reranking,
                "diversity_enabled": self.config.enable_diversity
            }
        }
    
    async def explain_search(self, 
                           query: str,
                           result_id: str) -> Dict[str, Any]:
        """Provide detailed explanation for a specific search result"""
        try:
            # This would provide detailed explanation for why a specific result
            # was returned for a query, including similarity scores, matched terms,
            # and ranking factors
            
            return {
                "query": query,
                "result_id": result_id,
                "explanation": "Detailed explanation would be generated here",
                "factors": {
                    "semantic_similarity": 0.85,
                    "keyword_matches": ["example", "terms"],
                    "document_quality": 0.9,
                    "recency_boost": 1.1,
                    "source_credibility": 0.95
                }
            }
            
        except Exception as e:
            logger.error("Search explanation failed", error=str(e))
            raise