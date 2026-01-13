from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User, UserRole
from app.schemas.claim import ClaimCreate, ClaimResponse, ClaimUpdate, ClaimReviewRequest, ClaimRequestInfoRequest
from app.services.claim_service import ClaimService
from app.db.session import get_db

router = APIRouter()

@router.post("/", response_model=ClaimResponse)
async def create_claim(
    claim_in: ClaimCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ClaimService(db)
    return await service.create_claim(claim_in.dict(), current_user.id)

@router.get("/", response_model=List[ClaimResponse])
async def read_claims(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ClaimService(db)
    if current_user.role in [UserRole.ADMIN, UserRole.APPROVER]:
        return await service.get_all_claims()
    return await service.get_all_claims(user_id=current_user.id)

@router.get("/{claim_id}", response_model=ClaimResponse)
async def read_claim(
    claim_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ClaimService(db)
    claim = await service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Check permissions
    if current_user.role not in [UserRole.ADMIN, UserRole.APPROVER] and claim.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this claim")
        
    return claim

@router.put("/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    claim_id: int,
    claim_in: ClaimUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ClaimService(db)
    claim = await service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.created_by_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        return await service.update_claim(claim_id, claim_in.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{claim_id}/submit", response_model=ClaimResponse)
async def submit_claim(
    claim_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = ClaimService(db)
    # Check permissions if needed
    try:
        return await service.submit_claim(claim_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{claim_id}/approve", response_model=ClaimResponse)
async def approve_claim(
    claim_id: int,
    request: ClaimReviewRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if current_user.role not in [UserRole.APPROVER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = ClaimService(db)
    try:
        return await service.approve_claim(claim_id, current_user.id, request.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{claim_id}/reject", response_model=ClaimResponse)
async def reject_claim(
    claim_id: int,
    request: ClaimReviewRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if current_user.role not in [UserRole.APPROVER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = ClaimService(db)
    try:
        return await service.reject_claim(claim_id, current_user.id, request.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{claim_id}/request-info", response_model=ClaimResponse)
async def request_more_info(
    claim_id: int,
    request: ClaimRequestInfoRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Approver requests additional information from user."""
    if current_user.role not in [UserRole.APPROVER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    service = ClaimService(db)
    try:
        return await service.request_more_info(claim_id, current_user.id, request.requested_info)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{claim_id}/messages")
async def get_claim_messages(
    claim_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get all messages for a claim."""
    service = ClaimService(db)
    return await service.get_claim_messages(claim_id)

@router.get("/{claim_id}/decisions")
async def get_claim_decisions(
    claim_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get decision history for a claim."""
    service = ClaimService(db)
    return await service.get_claim_decisions(claim_id)

@router.get("/{claim_id}/audit")
async def get_claim_audit(
    claim_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get agent audit trail for a claim."""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    service = ClaimService(db)
    return await service.get_claim_audit(claim_id)
