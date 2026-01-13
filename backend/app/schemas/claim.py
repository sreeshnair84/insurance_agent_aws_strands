from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.claim import ClaimType, ClaimStatus

class ClaimBase(BaseModel):
    policy_number: str
    claim_type: ClaimType
    claim_amount: float
    description: Optional[str] = None
    incident_date: Optional[datetime] = None

class ClaimCreate(ClaimBase):
    pass

class ClaimResponse(ClaimBase):
    id: int
    status: ClaimStatus
    fraud_risk_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class ClaimUpdate(BaseModel):
    description: Optional[str] = None
