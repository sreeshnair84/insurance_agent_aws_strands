"""
Chat service for user-agent interactions with A2UI support.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.claim import Claim
from app.models.audit import Message, SenderType
from app.agent.strands_service import StrandsInsuranceAgent
from typing import List, Dict, Any
import datetime


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent = StrandsInsuranceAgent()

    async def send_message(
        self, claim_id: int | None, user_id: int, content: str
    ) -> Dict[str, Any]:
        """
        Send a user message and get agent response with A2UI components.
        Supports both specific claim chat (claim_id provided) and general chat (claim_id=None).
        """
        from app.core.a2ui_converter import A2UIConverter
        
        user_message = Message(
            claim_id=claim_id,
            sender_type=SenderType.USER,
            sender_id=user_id,
            content=content
        )
        self.db.add(user_message)
        await self.db.commit()
        await self.db.refresh(user_message)
        
        agent_response_text = ""
        a2ui_components = []

        try:
            if claim_id:
                # --- Specific Claim Chat ---
                claim = await self._get_claim(claim_id)
                if not claim:
                    raise ValueError("Claim not found")
                if claim.created_by_id != user_id:
                    if claim.created_by_id != user_id: # Re-check strictly for now
                         raise ValueError("Not authorized to access this claim")

                result = await self.agent.process_claim(claim, self.db, content)
                raw_response_text = getattr(result, 'lastMessage', str(result))
                
                # Extract tool data for A2UI context
                tool_data = []
                if hasattr(result, 'history'):
                    with open("backend/debug_history.txt", "a", encoding="utf-8") as f:
                        f.write(f"\n--- Specific Chat History ---\n")
                        for event in result.history:
                            f.write(f"Type: {type(event)} | Attrs: {[a for a in dir(event) if not a.startswith('_')]}\n")
                            if hasattr(event, 'content'): f.write(f"Content: {event.content}\n")
                            if hasattr(event, 'tool_call_result'): f.write(f"Tool Result: {event.tool_call_result}\n")
                    
                    for event in result.history:
                        if hasattr(event, 'tool_call_result'):
                            try:
                                tool_data.append(json.loads(event.tool_call_result))
                            except:
                                tool_data.append(event.tool_call_result)

                # Convert A2UI using text + tool data context
                converter = A2UIConverter()
                agent_response_text, a2ui_components = await converter.extract_and_convert(raw_response_text, data_context=tool_data)

            else:
                # --- General / Multi-Claim Chat ---
                result = await self.agent.process_general_chat(user_id, content, self.db)
                raw_response_text = getattr(result, 'lastMessage', str(result))
                
                # Extract tool data for A2UI context
                tool_data = []
                if hasattr(result, 'history'):
                    with open("backend/debug_history.txt", "a", encoding="utf-8") as f:
                        f.write(f"\n--- General Chat History ---\n")
                        for event in result.history:
                            f.write(f"Type: {type(event)} | Attrs: {[a for a in dir(event) if not a.startswith('_')]}\n")
                            if hasattr(event, 'content'): f.write(f"Content: {event.content}\n")
                            if hasattr(event, 'tool_call_result'): f.write(f"Tool Result: {event.tool_call_result}\n")

                    for event in result.history:
                        if hasattr(event, 'tool_call_result'):
                            try:
                                tool_data.append(json.loads(event.tool_call_result))
                            except:
                                tool_data.append(event.tool_call_result)

                # Convert A2UI using text + tool data context
                converter = A2UIConverter()
                agent_response_text, a2ui_components = await converter.extract_and_convert(raw_response_text, data_context=tool_data)
                
                # If no components extracted but we have text, we keep the text.
                if not agent_response_text.strip() and a2ui_components:
                    agent_response_text = "Here is the information you requested:"
                    
        except Exception as e:
            # Handle Rate Limit and other Agent errors gracefully
            import traceback
            error_str = str(e)
            print(f"Agent Processing Error: {error_str}\n{traceback.format_exc()}")
            with open("debug_log.txt", "a") as f:
                f.write(f"Agent Processing Error: {error_str}\n{traceback.format_exc()}\n")
            
            if "All generated alerts" in error_str: # Strands specific
                 agent_response_text = "I encountered an internal processing error. Please try again."
            elif "429" in error_str or "RateLimitError" in type(e).__name__ or "Quota exceeded" in error_str:
                 agent_response_text = "⚠️ **Service Busy**: I am currently experiencing high traffic (Rate Limit Exceeded). Please wait a minute and try again."
                 a2ui_components = [{
                     "type": "status_card",
                     "status": "RATE_LIMIT",
                     "title": "Service Busy",
                     "description": "The AI model is currently rate limited.",
                     "color": "red",
                     "icon": "⏳"
                 }]
            else:
                 agent_response_text = "I encountered an error while processing your request. Please try again later."
                 a2ui_components = [{
                     "type": "info_card",
                     "title": "Error",
                     "fields": [{"label": "Details", "value": "Internal System Error"}]
                 }]

        # Save agent message
        agent_sender_id = None
        if claim_id is None:
             agent_sender_id = user_id
             
        agent_message = Message(
            claim_id=claim_id,
            sender_type=SenderType.AGENT,
            sender_id=agent_sender_id,
            content=agent_response_text,
            message_metadata={"a2ui": a2ui_components}
        )
        self.db.add(agent_message)
        await self.db.commit()
        await self.db.refresh(agent_message)

        return {
            "user_message": self._format_message(user_message),
            "agent_message": self._format_message(agent_message)
        }

    async def get_messages(self, claim_id: int | None, user_id: int = None) -> List[Dict[str, Any]]:
        """
        Get messages.
        If claim_id is provided, gets messages for that claim (verifying ownership).
        If claim_id is None, gets general chat messages for the user (using sender_id as grouping).
        """
        if claim_id:
            # --- Specific Claim Chat ---
            # Check ownership if user_id provided (regular user access)
            if user_id:
                claim = await self._get_claim(claim_id)
                if not claim:
                    raise ValueError("Claim not found")
                # Re-check strictly for now, duplicate logic is fine for safety
                if claim.created_by_id != user_id:
                     raise ValueError("Not authorized to access this claim")

            # Query messages for this claim
            query = select(Message).where(Message.claim_id == claim_id).order_by(Message.created_at)
            
        else:
            # --- General / Multi-Claim Chat ---
            if not user_id:
                raise ValueError("User ID required for general chat")
            
            # Query messages where claim_id is NULL AND sender_id is user_id
            query = select(Message).where(
                Message.claim_id.is_(None),
                Message.sender_id == user_id
            ).order_by(Message.created_at)

        result = await self.db.execute(query)
        messages = result.scalars().all()
        return [self._format_message(msg) for msg in messages]

    async def clear_messages(self, user_id: int, claim_id: int | None = None) -> None:
        """
        Clear messages for a chat session.
        """
        from sqlalchemy import delete
        
        if claim_id:
             # Check auth first
             claim = await self._get_claim(claim_id)
             if not claim or claim.created_by_id != user_id:
                  raise ValueError("Unauthorized to clear this chat")
             
             # Delete all messages for this claim
             query = delete(Message).where(Message.claim_id == claim_id)
        else:
             # General chat
             query = delete(Message).where(
                 Message.claim_id.is_(None),
                 Message.sender_id == user_id
             )
             
        await self.db.execute(query)
        await self.db.commit()

    async def _get_claim(self, claim_id: int) -> Claim:
        """Get claim by ID."""
        result = await self.db.execute(select(Claim).where(Claim.id == claim_id))
        result = result.scalars().first()
        return result

    def _format_message(self, message: Message) -> Dict[str, Any]:
        """Format message for API response."""
        return {
            "id": message.id,
            "claim_id": message.claim_id,
            "sender_type": message.sender_type.value,
            "sender_id": message.sender_id,
            "content": message.content,
            "a2ui": message.message_metadata.get("a2ui") if message.message_metadata else None,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }
