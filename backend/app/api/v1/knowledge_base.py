# app/api/v1/knowledge_base.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import structlog
from datetime import datetime

from app.core.database import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.modules.knowledge_base.types import DocumentType, KnowledgeDocument
from app.modules.knowledge_base.services.knowledge_service import (
    knowledge_base_service, 
    SearchRequest,
    RetrievalResult
)
from app.schemas.knowledge_base import (
    DocumentCreateRequest,
    DocumentResponse,
    SearchRequestSchema,
    SearchResponseSchema,
    BatchIngestRequest,
    BatchIngestResponse,
    KnowledgeStatsResponse
)

logger = structlog.get_logger()
router = APIRouter()

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    source: str = Form("upload"),
    tags: Optional[str] = Form(None),
    importance_score: float = Form(1.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and ingest a document into the knowledge base"""
    try:
        logger.info("Document upload started", 
                   filename=file.filename,
                   document_type=document_type.value,
                   user_id=current_user.id)
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size
        if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create knowledge document
        document = KnowledgeDocument(
            id=f"doc_{datetime.now().timestamp()}_{current_user.id}",
            title=title,
            content="",  # Will be populated during processing
            document_type=document_type,
            source=source,
            metadata={
                "uploaded_by": current_user.id,
                "uploaded_by_name": current_user.full_name,
                "original_filename": file.filename,
                "file_size": file.size
            },
            created_at=datetime.now(),
            tags=tag_list,
            importance_score=importance_score
        )
        
        # Process document ingestion in background
        background_tasks.add_task(
            _process_document_upload,
            document,
            file,
            current_user.id
        )
        
        return DocumentResponse(
            id=document.id,
            title=document.title,
            document_type=document.document_type,
            source=document.source,
            status="processing",
            created_at=document.created_at,
            metadata=document.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed", 
                    filename=file.filename,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Document upload failed")

@router.post("/documents/batch", response_model=BatchIngestResponse)
async def batch_ingest_documents(
    request: BatchIngestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Batch ingest multiple documents"""
    try:
        logger.info("Batch ingest started", 
                   document_count=len(request.documents),
                   user_id=current_user.id)
        
        # Convert request documents to KnowledgeDocument objects
        documents = []
        for doc_req in request.documents:
            document = KnowledgeDocument(
                id=f"batch_{datetime.now().timestamp()}_{len(documents)}",
                title=doc_req.title,
                content=doc_req.content,
                document_type=doc_req.document_type,
                source=doc_req.source or "batch_import",
                metadata={
                    **doc_req.metadata,
                    "batch_imported_by": current_user.id,
                    "batch_imported_by_name": current_user.full_name
                },
                created_at=datetime.now(),
                tags=doc_req.tags or [],
                importance_score=doc_req.importance_score or 1.0
            )
            documents.append(document)
        
        # Process batch ingestion in background
        background_tasks.add_task(
            _process_batch_ingestion,
            documents,
            current_user.id
        )
        
        return BatchIngestResponse(
            batch_id=f"batch_{datetime.now().timestamp()}",
            document_count=len(documents),
            status="processing",
            estimated_completion_time=len(documents) * 2  # Rough estimate in seconds
        )
        
    except Exception as e:
        logger.error("Batch ingest failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch ingestion failed")

@router.post("/search", response_model=SearchResponseSchema)
async def search_knowledge_base(
    request: SearchRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search the knowledge base"""
    try:
        logger.info("Knowledge base search", 
                   query=request.query[:100],
                   user_id=current_user.id)
        
        # Convert schema to service request
        search_request = SearchRequest(
            query=request.query,
            document_types=request.document_types,
            filters=request.filters,
            top_k=request.top_k,
            search_strategy=request.search_strategy,
            include_metadata=request.include_metadata,
            min_score=request.min_score,
            rerank=request.rerank
        )
        
        # Perform search
        results = await knowledge_base_service.search(search_request)
        
        # Convert results to response schema
        search_results = []
        for result in results:
            search_results.append({
                "document_id": result.document_id,
                "title": result.title,
                "content": result.content[:500] if len(result.content) > 500 else result.content,
                "score": result.score,
                "document_type": result.document_type,
                "source": result.source,
                "metadata": result.metadata if request.include_metadata else {},
                "matched_snippets": result.matched_snippets,
                "explanation": result.explanation,
                "confidence": result.confidence
            })
        
        return SearchResponseSchema(
            query=request.query,
            results=search_results,
            total_results=len(results),
            search_time=0.0,  # Would be calculated in practice
            search_strategy=request.search_strategy
        )
        
    except Exception as e:
        logger.error("Knowledge base search failed", 
                    query=request.query[:50],
                    error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/search/similar/{document_id}")
async def find_similar_documents(
    document_id: str,
    top_k: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user)
):
    """Find documents similar to a given document"""
    try:
        logger.info("Finding similar documents", 
                   document_id=document_id,
                   top_k=top_k)
        
        results = await knowledge_base_service.find_similar_documents(
            document_id, 
            top_k
        )
        
        return {
            "document_id": document_id,
            "similar_documents": [
                {
                    "document_id": result.document_id,
                    "title": result.title,
                    "score": result.score,
                    "document_type": result.document_type.value,
                    "explanation": result.explanation
                }
                for result in results
            ]
        }
        
    except Exception as e:
        logger.error("Similar document search failed", 
                    document_id=document_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Similar document search failed")

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific document by ID"""
    try:
        document = await knowledge_base_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(
            id=document.id,
            title=document.title,
            content=document.content,
            document_type=document.document_type,
            source=document.source,
            status="completed",
            created_at=document.created_at,
            updated_at=document.updated_at,
            metadata=document.metadata,
            tags=document.tags,
            importance_score=document.importance_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document retrieval failed", 
                    document_id=document_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Document retrieval failed")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(require_role(UserRole.MANAGER))
):
    """Delete a document from the knowledge base"""
    try:
        logger.info("Deleting document", 
                   document_id=document_id,
                   user_id=current_user.id)
        
        success = await knowledge_base_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document deletion failed", 
                    document_id=document_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Document deletion failed")

@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_base_stats(
    current_user: User = Depends(get_current_user)
):
    """Get knowledge base statistics"""
    try:
        stats = knowledge_base_service.get_statistics()
        
        return KnowledgeStatsResponse(
            total_documents=stats.get("documents_indexed", 0),
            total_searches=stats.get("searches_performed", 0),
            cache_hit_rate=stats.get("cache_hits", 0) / max(stats.get("searches_performed", 1), 1),
            avg_search_latency=stats.get("avg_search_latency", 0.0),
            vector_store_size=stats.get("total_documents", 0),
            index_health="healthy" if stats.get("total_documents", 0) > 0 else "empty"
        )
        
    except Exception as e:
        logger.error("Stats retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Statistics retrieval failed")

@router.get("/health")
async def health_check():
    """Health check for knowledge base service"""
    try:
        health_status = await knowledge_base_service.health_check()
        
        if health_status["status"] == "healthy":
            return health_status
        else:
            return JSONResponse(
                status_code=503,
                content=health_status
            )
            
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@router.post("/reindex")
async def reindex_knowledge_base(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Trigger knowledge base reindexing"""
    try:
        logger.info("Knowledge base reindexing triggered", user_id=current_user.id)
        
        # Add reindexing task to background
        background_tasks.add_task(_reindex_knowledge_base, current_user.id)
        
        return {
            "message": "Reindexing started",
            "status": "processing",
            "estimated_time": "10-30 minutes depending on data size"
        }
        
    except Exception as e:
        logger.error("Reindexing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Reindexing failed")

@router.get("/search/explain/{result_id}")
async def explain_search_result(
    result_id: str,
    query: str = Query(..., description="Original search query"),
    current_user: User = Depends(get_current_user)
):
    """Get detailed explanation for a search result"""
    try:
        explanation = await knowledge_base_service.semantic_retriever.explain_search(
            query, 
            result_id
        )
        
        return explanation
        
    except Exception as e:
        logger.error("Search explanation failed", 
                    result_id=result_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Search explanation failed")

# Background task functions
async def _process_document_upload(
    document: KnowledgeDocument,
    file: UploadFile,
    user_id: int
):
    """Background task to process document upload"""
    try:
        logger.info("Processing document upload", 
                   document_id=document.id,
                   user_id=user_id)
        
        # Process the uploaded file
        result = await knowledge_base_service.document_ingester.process_upload(
            file.file,
            file.filename,
            document.document_type,
            document.metadata
        )
        
        if result.success:
            # Update document with processed content
            document.content = result.text
            document.metadata.update(result.metadata)
            
            # Ingest into knowledge base
            await knowledge_base_service.ingest_document(document)
            
            logger.info("Document upload processing completed", 
                       document_id=document.id,
                       validation_score=result.validation_score)
        else:
            logger.error("Document upload processing failed", 
                        document_id=document.id,
                        error=result.error)
            
    except Exception as e:
        logger.error("Document upload background processing failed", 
                    document_id=document.id,
                    error=str(e))

async def _process_batch_ingestion(
    documents: List[KnowledgeDocument],
    user_id: int
):
    """Background task to process batch ingestion"""
    try:
        logger.info("Processing batch ingestion", 
                   document_count=len(documents),
                   user_id=user_id)
        
        result = await knowledge_base_service.ingest_batch(documents)
        
        logger.info("Batch ingestion completed", 
                   total=result["total_documents"],
                   successful=result["successful"],
                   failed=result["failed"])
        
    except Exception as e:
        logger.error("Batch ingestion background processing failed", 
                    error=str(e))

async def _reindex_knowledge_base(user_id: int):
    """Background task to reindex knowledge base"""
    try:
        logger.info("Starting knowledge base reindexing", user_id=user_id)
        
        # This would implement the actual reindexing logic
        # For now, it's a placeholder
        
        logger.info("Knowledge base reindexing completed", user_id=user_id)
        
    except Exception as e:
        logger.error("Knowledge base reindexing failed", error=str(e))