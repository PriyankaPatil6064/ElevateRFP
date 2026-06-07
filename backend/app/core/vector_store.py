# app/core/vector_store.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import chromadb
import pickle
import os
import json
from datetime import datetime
import structlog
from dataclasses import dataclass, asdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3

from app.config import settings
from app.core.embeddings import embedding_pipeline

logger = structlog.get_logger()

@dataclass
class SearchResult:
    """Search result with metadata"""
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None
    source: str = "vector"  # vector, bm25, hybrid

@dataclass
class SearchQuery:
    """Search query with filters and parameters"""
    query: str
    filters: Dict[str, Any] = None
    top_k: int = 10
    score_threshold: float = 0.0
    search_type: str = "hybrid"  # vector, bm25, hybrid
    rerank: bool = True
    include_metadata: List[str] = None

class EnhancedVectorStore(ABC):
    """Enhanced vector store with metadata filtering and hybrid search"""
    
    @abstractmethod
    async def add_documents(self, documents: List[Dict], embeddings: np.ndarray = None):
        pass
    
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]):
        pass
    
    @abstractmethod
    async def update_document(self, document_id: str, document: Dict, embedding: np.ndarray = None):
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass

class FAISSEnhancedStore(EnhancedVectorStore):
    """Enhanced FAISS store with metadata filtering and BM25 hybrid search"""
    
    def __init__(self, index_path: str = None):
        self.index_path = index_path or settings.VECTOR_DB_PATH
        self.dimension = embedding_pipeline.get_dimension()
        
        # FAISS index with IVF for large-scale search
        self.index = None
        self.metadata_db_path = os.path.join(self.index_path, "metadata.db")
        
        # BM25 for keyword search
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = None
        self.documents = []
        
        # Initialize
        self._initialize_index()
        self._initialize_metadata_db()
    
    def _initialize_index(self):
        """Initialize FAISS index"""
        # Use IVF index for better performance with large datasets
        nlist = 100  # Number of clusters
        quantizer = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        
        # Set search parameters
        self.index.nprobe = 10  # Number of clusters to search
        
        logger.info("FAISS enhanced index initialized", 
                   dimension=self.dimension, 
                   index_type="IVFFlat")
    
    def _initialize_metadata_db(self):
        """Initialize SQLite database for metadata"""
        os.makedirs(os.path.dirname(self.metadata_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                embedding_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for common metadata fields
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(json_extract(metadata, "$.document_type"))')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_section ON documents(json_extract(metadata, "$.source_section"))')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON documents(json_extract(metadata, "$.importance_score"))')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_has_requirements ON documents(json_extract(metadata, "$.has_requirements"))')
        
        conn.commit()
        conn.close()
        
        logger.info("Metadata database initialized", path=self.metadata_db_path)
    
    async def add_documents(self, documents: List[Dict], embeddings: np.ndarray = None):
        """Add documents to the vector store"""
        if not documents:
            return
        
        try:
            # Generate embeddings if not provided
            if embeddings is None:
                texts = [doc["content"] for doc in documents]
                embeddings = await embedding_pipeline.encode_texts(texts)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Train index if not trained and we have enough data
            if not self.index.is_trained and len(documents) >= 100:
                logger.info("Training FAISS index", documents_count=len(documents))
                self.index.train(embeddings.astype('float32'))
            
            # Add to FAISS index
            start_index = self.index.ntotal
            self.index.add(embeddings.astype('float32'))
            
            # Add to metadata database
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.cursor()
            
            for i, doc in enumerate(documents):
                cursor.execute('''
                    INSERT OR REPLACE INTO documents 
                    (id, content, metadata, embedding_index, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    doc["id"],
                    doc["content"],
                    json.dumps(doc.get("metadata", {})),
                    start_index + i,
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            # Update BM25 index
            self._update_bm25_index()
            
            logger.info("Documents added to enhanced vector store", 
                       count=len(documents),
                       total_documents=self.index.ntotal)
            
        except Exception as e:
            logger.error("Failed to add documents", error=str(e))
            raise
    
    def _update_bm25_index(self):
        """Update BM25 index with all documents"""
        try:
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT content FROM documents ORDER BY embedding_index")
            documents = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            if documents:
                self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
                self.documents = documents
                
                logger.info("BM25 index updated", documents_count=len(documents))
        
        except Exception as e:
            logger.warning("Failed to update BM25 index", error=str(e))
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Enhanced search with multiple strategies"""
        try:
            if query.search_type == "vector":
                return await self._vector_search(query)
            elif query.search_type == "bm25":
                return await self._bm25_search(query)
            elif query.search_type == "hybrid":
                return await self._hybrid_search(query)
            else:
                raise ValueError(f"Unknown search type: {query.search_type}")
        
        except Exception as e:
            logger.error("Search failed", error=str(e))
            raise
    
    async def _vector_search(self, query: SearchQuery) -> List[SearchResult]:
        """Pure vector similarity search"""
        if self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = await embedding_pipeline.encode_single(query.query)
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Search FAISS index
        scores, indices = self.index.search(
            query_embedding.reshape(1, -1).astype('float32'), 
            min(query.top_k * 2, self.index.ntotal)  # Get more results for filtering
        )
        
        # Get documents with metadata filtering
        results = []
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < query.score_threshold:
                continue
            
            # Get document by embedding index
            cursor.execute(
                "SELECT id, content, metadata FROM documents WHERE embedding_index = ?",
                (int(idx),)
            )
            row = cursor.fetchone()
            
            if row:
                doc_id, content, metadata_json = row
                metadata = json.loads(metadata_json)
                
                # Apply metadata filters
                if self._matches_filters(metadata, query.filters):
                    results.append(SearchResult(
                        document_id=doc_id,
                        content=content,
                        score=float(score),
                        metadata=metadata,
                        source="vector"
                    ))
        
        conn.close()
        
        # Sort by score and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:query.top_k]
    
    async def _bm25_search(self, query: SearchQuery) -> List[SearchResult]:
        """BM25 keyword search"""
        if self.tfidf_matrix is None or len(self.documents) == 0:
            return []
        
        # Transform query
        query_vector = self.tfidf_vectorizer.transform([query.query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top results
        top_indices = np.argsort(similarities)[::-1][:query.top_k * 2]
        
        results = []
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        for idx in top_indices:
            score = similarities[idx]
            if score < query.score_threshold:
                continue
            
            cursor.execute(
                "SELECT id, content, metadata FROM documents WHERE embedding_index = ?",
                (int(idx),)
            )
            row = cursor.fetchone()
            
            if row:
                doc_id, content, metadata_json = row
                metadata = json.loads(metadata_json)
                
                if self._matches_filters(metadata, query.filters):
                    results.append(SearchResult(
                        document_id=doc_id,
                        content=content,
                        score=float(score),
                        metadata=metadata,
                        source="bm25"
                    ))
        
        conn.close()
        return results[:query.top_k]
    
    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Hybrid search combining vector and BM25"""
        # Get results from both methods
        vector_query = SearchQuery(
            query=query.query,
            filters=query.filters,
            top_k=query.top_k,
            score_threshold=query.score_threshold * 0.5,  # Lower threshold for individual methods
            search_type="vector"
        )
        
        bm25_query = SearchQuery(
            query=query.query,
            filters=query.filters,
            top_k=query.top_k,
            score_threshold=query.score_threshold * 0.5,
            search_type="bm25"
        )
        
        vector_results = await self._vector_search(vector_query)
        bm25_results = await self._bm25_search(bm25_query)
        
        # Combine and rerank results
        combined_results = self._combine_search_results(vector_results, bm25_results)
        
        # Apply reranking if requested
        if query.rerank and len(combined_results) > 1:
            combined_results = await self._rerank_results(query.query, combined_results)
        
        return combined_results[:query.top_k]
    
    def _combine_search_results(self, 
                               vector_results: List[SearchResult], 
                               bm25_results: List[SearchResult]) -> List[SearchResult]:
        """Combine and score results from different search methods"""
        # Create a map of document_id to results
        result_map = {}
        
        # Add vector results with weight
        for result in vector_results:
            result_map[result.document_id] = SearchResult(
                document_id=result.document_id,
                content=result.content,
                score=result.score * 0.7,  # Weight vector search
                metadata=result.metadata,
                source="hybrid"
            )
        
        # Add or combine BM25 results
        for result in bm25_results:
            if result.document_id in result_map:
                # Combine scores
                existing = result_map[result.document_id]
                existing.score += result.score * 0.3  # Weight BM25 search
            else:
                result_map[result.document_id] = SearchResult(
                    document_id=result.document_id,
                    content=result.content,
                    score=result.score * 0.3,
                    metadata=result.metadata,
                    source="hybrid"
                )
        
        # Sort by combined score
        combined_results = list(result_map.values())
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        return combined_results
    
    async def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank results using cross-encoder or advanced scoring"""
        # For now, implement a simple reranking based on query term overlap
        query_terms = set(query.lower().split())
        
        for result in results:
            content_terms = set(result.content.lower().split())
            overlap = len(query_terms.intersection(content_terms))
            
            # Boost score based on term overlap
            boost = overlap / max(len(query_terms), 1) * 0.1
            result.score += boost
        
        # Re-sort by updated scores
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _matches_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if document metadata matches filters"""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif isinstance(value, dict):
                # Range filter
                if "min" in value and metadata[key] < value["min"]:
                    return False
                if "max" in value and metadata[key] > value["max"]:
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True
    
    async def delete_documents(self, document_ids: List[str]):
        """Delete documents from the store"""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        # Get embedding indices to remove
        placeholders = ','.join(['?' for _ in document_ids])
        cursor.execute(
            f"SELECT embedding_index FROM documents WHERE id IN ({placeholders})",
            document_ids
        )
        indices_to_remove = [row[0] for row in cursor.fetchall()]
        
        # Delete from metadata database
        cursor.execute(
            f"DELETE FROM documents WHERE id IN ({placeholders})",
            document_ids
        )
        
        conn.commit()
        conn.close()
        
        # Note: FAISS doesn't support deletion, so we'd need to rebuild the index
        # For now, we'll mark them as deleted in metadata
        logger.info("Documents deleted from metadata", 
                   document_ids=document_ids,
                   note="FAISS index rebuild required for complete removal")
    
    async def update_document(self, document_id: str, document: Dict, embedding: np.ndarray = None):
        """Update a document in the store"""
        # For simplicity, we'll delete and re-add
        await self.delete_documents([document_id])
        await self.add_documents([{**document, "id": document_id}], 
                                embedding.reshape(1, -1) if embedding is not None else None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        conn = sqlite3.connect(self.metadata_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT json_extract(metadata, '$.document_type')) FROM documents")
        unique_types = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_documents": total_docs,
            "faiss_index_size": self.index.ntotal if self.index else 0,
            "unique_document_types": unique_types,
            "index_dimension": self.dimension,
            "index_trained": self.index.is_trained if self.index else False
        }
    
    def save_index(self, path: str = None):
        """Save the vector store to disk"""
        save_path = path or self.index_path
        os.makedirs(save_path, exist_ok=True)
        
        # Save FAISS index
        if self.index and self.index.ntotal > 0:
            faiss.write_index(self.index, os.path.join(save_path, "faiss.index"))
        
        # Save BM25 components
        if self.tfidf_vectorizer and self.tfidf_matrix is not None:
            with open(os.path.join(save_path, "tfidf_vectorizer.pkl"), "wb") as f:
                pickle.dump(self.tfidf_vectorizer, f)
            
            with open(os.path.join(save_path, "tfidf_matrix.pkl"), "wb") as f:
                pickle.dump(self.tfidf_matrix, f)
        
        logger.info("Vector store saved", path=save_path)
    
    def load_index(self, path: str = None):
        """Load the vector store from disk"""
        load_path = path or self.index_path
        
        # Load FAISS index
        faiss_path = os.path.join(load_path, "faiss.index")
        if os.path.exists(faiss_path):
            self.index = faiss.read_index(faiss_path)
            logger.info("FAISS index loaded", documents=self.index.ntotal)
        
        # Load BM25 components
        tfidf_vectorizer_path = os.path.join(load_path, "tfidf_vectorizer.pkl")
        tfidf_matrix_path = os.path.join(load_path, "tfidf_matrix.pkl")
        
        if os.path.exists(tfidf_vectorizer_path) and os.path.exists(tfidf_matrix_path):
            with open(tfidf_vectorizer_path, "rb") as f:
                self.tfidf_vectorizer = pickle.load(f)
            
            with open(tfidf_matrix_path, "rb") as f:
                self.tfidf_matrix = pickle.load(f)
            
            logger.info("BM25 index loaded")

# Global enhanced vector store
enhanced_vector_store = FAISSEnhancedStore()