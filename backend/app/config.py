# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ElevateRFP Enterprise Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600
    
    # Vector Database
    VECTOR_DB_TYPE: str = "faiss"  # faiss or chromadb
    VECTOR_DB_PATH: str = "./vector_store"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic, or local
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4-turbo-preview"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4000
    
    # Embeddings
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_CACHE_SIZE: int = 10000
    
    # Document Processing
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".txt"]
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "eng"
    
    # Celery Task Queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # ML Models
    ML_MODEL_PATH: str = "./ml_models"
    RETRAIN_THRESHOLD: int = 100  # Retrain after N new proposals
    
    # Compliance
    COMPLIANCE_RULES_PATH: str = "./compliance_rules"
    
    # Monitoring
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "elevate-rfp"
    LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    LLM_RATE_LIMIT_PER_MINUTE: int = 20
    
    # File Storage
    UPLOAD_PATH: str = "./uploads"
    PROPOSAL_OUTPUT_PATH: str = "./proposals"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Enterprise Knowledge Base Configuration
KNOWLEDGE_BASE_CONFIG = {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "similarity_threshold": 0.7,
    "max_retrieval_results": 10,
    "rerank_top_k": 5
}

# Agent Configuration
AGENT_CONFIG = {
    "max_iterations": 5,
    "timeout_seconds": 300,
    "retry_attempts": 3,
    "parallel_execution": True
}

# ML Model Configuration
ML_CONFIG = {
    "win_probability": {
        "model_type": "xgboost",
        "features": ["compliance_score", "requirement_coverage", "pricing_score", "timeline_feasibility"],
        "target": "win_probability"
    },
    "quality_classifier": {
        "model_type": "random_forest",
        "classes": ["strong", "medium", "weak"],
        "features": ["content_quality", "structure_score", "completeness"]
    },
    "risk_predictor": {
        "model_type": "logistic_regression",
        "classes": ["low", "medium", "high"],
        "features": ["complexity_score", "timeline_risk", "compliance_gaps"]
    }
}