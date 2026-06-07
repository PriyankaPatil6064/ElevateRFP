# app/api/router.py
from fastapi import APIRouter
from app.api.v1 import auth, knowledge_base
from app.api.v1.agents import router as agents_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(knowledge_base.router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(agents_router)