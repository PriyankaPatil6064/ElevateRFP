# app/models/rfp.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class RFPStatus(enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    MATCHED = "matched"
    PROPOSAL_GENERATED = "proposal_generated"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class RFPType(enum.Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    SERVICES = "services"
    CONSULTING = "consulting"
    MIXED = "mixed"

class RFP(Base):
    __tablename__ = "rfps"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # File information
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    
    # Processing status
    status = Column(Enum(RFPStatus), default=RFPStatus.UPLOADED)
    rfp_type = Column(Enum(RFPType))
    
    # Extracted content
    raw_text = Column(Text)
    processed_text = Column(Text)
    
    # Metadata
    client_name = Column(String(200))
    submission_deadline = Column(DateTime(timezone=True))
    project_budget = Column(Float)
    project_duration_months = Column(Integer)
    
    # Processing results
    extraction_results = Column(JSON)  # Structured requirements
    matching_results = Column(JSON)    # Matched products/services
    compliance_results = Column(JSON)  # Compliance analysis
    risk_assessment = Column(JSON)     # Risk analysis
    
    # Scores
    complexity_score = Column(Float)
    win_probability = Column(Float)
    confidence_score = Column(Float)
    
    # Relationships
    created_by = Column(Integer, ForeignKey("users.id"))
    created_by_user = relationship("User", back_populates="rfps")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    requirements = relationship("Requirement", back_populates="rfp", cascade="all, delete-orphan")
    proposals = relationship("Proposal", back_populates="rfp")
    workflow_actions = relationship("WorkflowAction", back_populates="rfp")
    
    def __repr__(self):
        return f"<RFP(title='{self.title}', status='{self.status.value}')>"

class Requirement(Base):
    __tablename__ = "requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=False)
    
    # Requirement details
    category = Column(String(100))  # technical, functional, compliance, etc.
    subcategory = Column(String(100))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Classification
    is_mandatory = Column(Boolean, default=False)
    priority = Column(String(20))  # high, medium, low
    
    # Extracted metadata
    extracted_entities = Column(JSON)  # Named entities, dates, numbers
    confidence_score = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rfp = relationship("RFP", back_populates="requirements")
    
    def __repr__(self):
        return f"<Requirement(title='{self.title}', mandatory={self.is_mandatory})>"