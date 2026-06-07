# app/models/workflow.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class WorkflowStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class ActionType(enum.Enum):
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    COMMENT = "comment"
    ASSIGN = "assign"

class WorkflowAction(Base):
    __tablename__ = "workflow_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Action details
    action_type = Column(Enum(ActionType), nullable=False)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING)
    
    # Content
    title = Column(String(200))
    description = Column(Text)
    comments = Column(Text)
    
    # Metadata
    metadata = Column(JSON)  # Additional action-specific data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    
    # Relationships
    rfp = relationship("RFP", back_populates="workflow_actions")
    user = relationship("User", back_populates="workflow_actions")
    
    def __repr__(self):
        return f"<WorkflowAction(type='{self.action_type.value}', status='{self.status.value}')>"

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Rule identification
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)  # e.g., GDPR-001
    category = Column(String(100))  # GDPR, ISO27001, SOC2, etc.
    
    # Rule definition
    description = Column(Text, nullable=False)
    requirements = Column(JSON)  # Structured requirements
    validation_criteria = Column(JSON)  # How to validate compliance
    
    # Metadata
    is_mandatory = Column(Boolean, default=True)
    severity = Column(String(20))  # critical, high, medium, low
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    compliance_checks = relationship("ComplianceCheck", back_populates="rule")
    
    def __repr__(self):
        return f"<ComplianceRule(code='{self.code}', category='{self.category}')>"

class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("compliance_rules.id"), nullable=False)
    
    # Check results
    is_compliant = Column(Boolean)
    confidence_score = Column(Float)
    
    # Evidence and reasoning
    evidence = Column(JSON)  # Supporting evidence found
    reasoning = Column(Text)  # AI explanation
    gaps = Column(JSON)  # What's missing for compliance
    
    # Recommendations
    recommendations = Column(JSON)
    
    # Timestamps
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rule = relationship("ComplianceRule", back_populates="compliance_checks")
    
    def __repr__(self):
        return f"<ComplianceCheck(rfp_id={self.rfp_id}, compliant={self.is_compliant})>"

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # rfp_uploaded, proposal_generated, etc.
    event_category = Column(String(50))  # user_action, system_event, etc.
    
    # Context
    user_id = Column(Integer, ForeignKey("users.id"))
    rfp_id = Column(Integer, ForeignKey("rfps.id"))
    
    # Event data
    properties = Column(JSON)  # Event-specific properties
    metrics = Column(JSON)     # Numerical metrics
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AnalyticsEvent(type='{self.event_type}', timestamp='{self.timestamp}')>"