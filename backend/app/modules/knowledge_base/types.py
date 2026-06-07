# app/modules/knowledge_base/types.py
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

class DocumentType(Enum):
    PRODUCT_CATALOG = "product_catalog"
    PROPOSAL = "proposal"
    CASE_STUDY = "case_study"
    COMPLIANCE_DOC = "compliance_document"
    CERTIFICATION = "certification"
    PRICING_SHEET = "pricing_sheet"
    TECHNICAL_SPEC = "technical_specification"
    CONTRACT_TEMPLATE = "contract_template"

@dataclass
class KnowledgeDocument:
    """Knowledge base document structure"""
    id: str
    title: str
    content: str
    document_type: DocumentType
    source: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    version: str = "1.0"
    tags: List[str] = None
    importance_score: float = 1.0
