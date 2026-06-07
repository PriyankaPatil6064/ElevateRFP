# app/models/proposal.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class ProposalStatus(enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"

class ProposalQuality(enum.Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"

class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=False)
    
    # Proposal content
    title = Column(String(200), nullable=False)
    executive_summary = Column(Text)
    technical_approach = Column(Text)
    pricing_details = Column(JSON)
    timeline = Column(JSON)
    
    # Generated content
    full_content = Column(Text)  # Complete proposal text
    document_path = Column(String(500))  # Path to generated document
    
    # Quality metrics
    status = Column(Enum(ProposalStatus), default=ProposalStatus.DRAFT)
    quality_score = Column(Float)
    quality_classification = Column(Enum(ProposalQuality))
    
    # AI-generated insights
    win_probability = Column(Float)
    risk_factors = Column(JSON)
    recommendations = Column(JSON)
    
    # Compliance
    compliance_score = Column(Float)
    compliance_gaps = Column(JSON)
    
    # Relationships
    rfp = relationship("RFP", back_populates="proposals")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_by_user = relationship("User", back_populates="proposals")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True))
    
    # Relationships
    matched_products = relationship("ProposalProduct", back_populates="proposal")
    
    def __repr__(self):
        return f"<Proposal(title='{self.title}', status='{self.status.value}')>"

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Product information
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    subcategory = Column(String(100))
    
    # Technical specifications
    specifications = Column(JSON)
    features = Column(JSON)
    capabilities = Column(JSON)
    
    # Pricing
    base_price = Column(Float)
    pricing_model = Column(String(50))  # fixed, per_user, per_month, etc.
    
    # Compliance & Certifications
    certifications = Column(JSON)
    compliance_standards = Column(JSON)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    version = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    proposal_matches = relationship("ProposalProduct", back_populates="product")
    
    def __repr__(self):
        return f"<Product(name='{self.name}', category='{self.category}')>"

class ProposalProduct(Base):
    """Association table for proposal-product matching"""
    __tablename__ = "proposal_products"
    
    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Matching details
    match_score = Column(Float)
    match_reasoning = Column(Text)
    is_primary_match = Column(Boolean, default=False)
    
    # Customization
    customizations = Column(JSON)
    pricing_adjustments = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    proposal = relationship("Proposal", back_populates="matched_products")
    product = relationship("Product", back_populates="proposal_matches")
    
    def __repr__(self):
        return f"<ProposalProduct(proposal_id={self.proposal_id}, product_id={self.product_id}, score={self.match_score})>"