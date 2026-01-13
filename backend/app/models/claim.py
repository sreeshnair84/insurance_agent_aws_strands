import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class ClaimStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_AGENT_REVIEW = "UNDER_AGENT_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ClaimType(str, enum.Enum):
    HEALTH = "HEALTH"
    AUTO = "AUTO"
    PROPERTY = "PROPERTY"

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    policy_number = Column(String, index=True, nullable=False)
    claim_type = Column(Enum(ClaimType), nullable=False)
    claim_amount = Column(Float, nullable=False)
    incident_date = Column(DateTime(timezone=True), nullable=True) # Can be null in draft
    description = Column(String, nullable=True)
    documents_uploaded = Column(Boolean, default=False)
    fraud_risk_score = Column(Float, default=0.0)
    
    status = Column(Enum(ClaimStatus), default=ClaimStatus.DRAFT, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    version = Column(Integer, default=1)
    claim_metadata = Column(JSON, nullable=True)  # Store interrupt data and other metadata
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    # created_by = relationship("User", foreign_keys=[created_by_id])
    # assigned_approver = relationship("User", foreign_keys=[assigned_approver_id])
