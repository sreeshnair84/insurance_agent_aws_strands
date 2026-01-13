"""
Database models for message tracking, decisions, and agent audit.
"""
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class SenderType(str, enum.Enum):
    """Type of message sender."""
    USER = "USER"
    AGENT = "AGENT"
    APPROVER = "APPROVER"


class DecisionType(str, enum.Enum):
    """Type of decision made on a claim."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"


class Message(Base):
    """
    Tracks all communication between user, agent, and approver.
    Provides audit trail of claim conversations.
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True, index=True)
    sender_type = Column(Enum(SenderType), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for AGENT
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # For A2UI components and other metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    # claim = relationship("Claim", back_populates="messages")
    # sender = relationship("User", foreign_keys=[sender_id])


class Decision(Base):
    """
    Audit trail of all approval/rejection decisions.
    Enables replay and compliance tracking.
    """
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    decision = Column(Enum(DecisionType), nullable=False)
    reason = Column(Text, nullable=True)  # Approver's justification
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    # claim = relationship("Claim", back_populates="decisions")
    # decider = relationship("User")


class AgentAudit(Base):
    """
    Logs all LLM interactions for debugging and compliance.
    Stores prompts, responses, and model information.
    """
    __tablename__ = "agent_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    prompt = Column(Text, nullable=False)  # Input to LLM
    response = Column(Text, nullable=False)  # LLM output
    model = Column(String, nullable=False)  # Model identifier
    agent_metadata = Column(JSON, nullable=True)  # Additional context (tools used, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    # claim = relationship("Claim", back_populates="audit_logs")
