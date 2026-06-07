# app/core/embeddings.py
from typing import List, Dict, Optional, Union, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModel
import hashlib
import pickle
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio
import structlog
from app.config import settings

logger = structlog.get_logger()

class BaseEmbeddingModel:
    """Abstract base class for embedding models"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.dimension = None
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        raise NotImplementedError
    
    def encode_single(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """Sentence Transformers embedding model"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        super().__init__(model_name)
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info("SentenceTransformer model loaded", 
                   model=model_name, 
                   dimension=self.dimension)
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to embeddings"""
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error("Embedding encoding failed", error=str(e))
            raise

class HuggingFaceEmbedding(BaseEmbeddingModel):
    """HuggingFace transformer embedding model"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        super().__init__(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Get dimension from model config
        self.dimension = self.model.config.hidden_size
        logger.info("HuggingFace model loaded", 
                   model=model_name, 
                   dimension=self.dimension,
                   device=str(self.device))
    
    def encode(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        """Encode texts using HuggingFace model"""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize
            inputs = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)
            
            # Get embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use mean pooling
                batch_embeddings = self._mean_pooling(outputs, inputs['attention_mask'])
                embeddings.append(batch_embeddings.cpu().numpy())
        
        return np.vstack(embeddings).astype(np.float32)
    
    def _mean_pooling(self, model_output, attention_mask):
        """Apply mean pooling to get sentence embeddings"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

class EmbeddingCache:
    """Persistent cache for embeddings"""
    
    def __init__(self, cache_dir: str = "./embedding_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.memory_cache = {}
        self.max_memory_size = settings.EMBEDDING_CACHE_SIZE
    
    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate cache key for text and model"""
        content = f"{model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Get embedding from cache"""
        cache_key = self._get_cache_key(text, model_name)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Check disk cache
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    embedding = pickle.load(f)
                
                # Add to memory cache if space available
                if len(self.memory_cache) < self.max_memory_size:
                    self.memory_cache[cache_key] = embedding
                
                return embedding
            except Exception as e:
                logger.warning("Failed to load cached embedding", error=str(e))
        
        return None
    
    def set(self, text: str, model_name: str, embedding: np.ndarray):
        """Store embedding in cache"""
        cache_key = self._get_cache_key(text, model_name)
        
        # Store in memory cache
        if len(self.memory_cache) < self.max_memory_size:
            self.memory_cache[cache_key] = embedding
        
        # Store in disk cache
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.warning("Failed to cache embedding", error=str(e))
    
    def clear_memory_cache(self):
        """Clear memory cache"""
        self.memory_cache.clear()

class EmbeddingPipeline:
    """Enterprise embedding pipeline with caching and batch processing"""
    
    def __init__(self, model_name: str = None, use_cache: bool = True):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.use_cache = use_cache
        self.cache = EmbeddingCache() if use_cache else None
        
        # Initialize embedding model
        if "sentence-transformers" in self.model_name or self.model_name in ["all-MiniLM-L6-v2", "all-mpnet-base-v2"]:
            self.model = SentenceTransformerEmbedding(self.model_name)
        else:
            self.model = HuggingFaceEmbedding(self.model_name)
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        logger.info("Embedding pipeline initialized", 
                   model=self.model_name, 
                   dimension=self.model.dimension,
                   cache_enabled=use_cache)
    
    async def encode_texts(self, texts: List[str], batch_size: int = None) -> np.ndarray:
        """Encode multiple texts with caching"""
        if not texts:
            return np.array([])
        
        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        
        # Check cache for existing embeddings
        cached_embeddings = {}
        uncached_texts = []
        uncached_indices = []
        
        if self.use_cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text, self.model_name)
                if cached is not None:
                    cached_embeddings[i] = cached
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        # Encode uncached texts
        new_embeddings = []
        if uncached_texts:
            logger.info("Encoding texts", 
                       total=len(texts), 
                       cached=len(cached_embeddings), 
                       to_encode=len(uncached_texts))
            
            # Run encoding in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            new_embeddings = await loop.run_in_executor(
                self.executor,
                self.model.encode,
                uncached_texts,
                batch_size
            )
            
            # Cache new embeddings
            if self.use_cache:
                for text, embedding in zip(uncached_texts, new_embeddings):
                    self.cache.set(text, self.model_name, embedding)
        
        # Combine cached and new embeddings
        all_embeddings = np.zeros((len(texts), self.model.dimension), dtype=np.float32)
        
        # Add cached embeddings
        for i, embedding in cached_embeddings.items():
            all_embeddings[i] = embedding
        
        # Add new embeddings
        for i, embedding in zip(uncached_indices, new_embeddings):
            all_embeddings[i] = embedding
        
        return all_embeddings
    
    async def encode_single(self, text: str) -> np.ndarray:
        """Encode single text"""
        embeddings = await self.encode_texts([text])
        return embeddings[0]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.dimension
    
    async def encode_query(self, query: str, query_type: str = "search") -> np.ndarray:
        """Encode query with optional query-specific processing"""
        # Add query type prefix for better retrieval
        if query_type == "search":
            processed_query = f"search: {query}"
        elif query_type == "similarity":
            processed_query = f"similarity: {query}"
        else:
            processed_query = query
        
        return await self.encode_single(processed_query)
    
    def compute_similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and documents"""
        # Normalize embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        
        # Compute cosine similarity
        similarities = np.dot(doc_norms, query_norm)
        return similarities
    
    async def find_similar_texts(self, 
                                query: str, 
                                candidate_texts: List[str], 
                                top_k: int = 5) -> List[Tuple[str, float]]:
        """Find most similar texts to query"""
        if not candidate_texts:
            return []
        
        # Encode query and candidates
        query_embedding = await self.encode_single(query)
        candidate_embeddings = await self.encode_texts(candidate_texts)
        
        # Compute similarities
        similarities = self.compute_similarity(query_embedding, candidate_embeddings)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((candidate_texts[idx], float(similarities[idx])))
        
        return results
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

# Global embedding pipeline instance
embedding_pipeline = EmbeddingPipeline()