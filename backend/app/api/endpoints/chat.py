from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api import deps
from app.models.user import User, UserRole
from app.services.chat_service import ChatService
from app.db.session import get_db

router = APIRouter()


class SendMessageRequest(BaseModel):
    claim_id: Optional[int] = None
    content: str


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Send a message to the agent and get response.
    If claim_id is provided, it's a claim-specific chat.
    If claim_id is None, it's a general user-agent chat.
    """
    service = ChatService(db)
    try:
        return await service.send_message(
            claim_id=request.claim_id,
            user_id=current_user.id,
            content=request.content
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/messages")
@router.get("/messages/{claim_id}")
async def get_messages(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
    claim_id: Optional[int] = None,
) -> Any:
    """
    Get all messages.
    If claim_id is:
    - provided: returns messages for that claim
    - None: returns general messages (where claim_id is None)
    """
    service = ChatService(db)
    try:
        if current_user.role in [UserRole.ADMIN, UserRole.APPROVER] and claim_id:
             # Approvers can see any claim's messages
            return await service.get_messages(claim_id)
        
        # Regular users (or general chat) must own the resource
        return await service.get_messages(claim_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/messages")
async def clear_messages(
    claim_id: Optional[int] = None,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Clear chat history.
    - If claim_id is None: Clears general chat history.
    - If claim_id is provided: Clears specific claim chat history.
    """
    service = ChatService(db)
    try:
        await service.clear_messages(user_id=current_user.id, claim_id=claim_id)
        return {"status": "success", "message": "Chat history cleared"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
