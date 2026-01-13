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
                     # In real app, check detailed permissions
                     # Allowing limited access for now or verifying strict ownership
                    if claim.created_by_id != user_id: # Re-check strictly for now
                         raise ValueError("Not authorized to access this claim")

                result = await self.agent.process_claim(claim, self.db, content)
                
                # Simple result text extraction
                agent_response_text = getattr(result, 'lastMessage', str(result))
                
                # Generate A2UI for this specific claim context
                a2ui_components = self._create_a2ui_components(claim, content)

            else:
                # --- General / Multi-Claim Chat ---
                result = await self.agent.process_general_chat(user_id, content, self.db)
                raw_response_text = getattr(result, 'lastMessage', str(result))
                
                # Extract A2UI JSON if present in the text (passed through from tools)
                agent_response_text, extracted_components = self._extract_a2ui_from_text(raw_response_text)
                a2ui_components = extracted_components
                
                # If no components extracted but we have text, we keep the text.
                # If empty text (just a JSON blob that we stripped), we might want to add a default message.
                if not agent_response_text.strip() and a2ui_components:
                    agent_response_text = "Here is the information you requested:"
                    
        except Exception as e:
            # Handle Rate Limit and other Agent errors gracefully
            import traceback
            error_str = str(e)
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
        # For general chat (claim_id is None), we use sender_id to link the message to the user context
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

    def _extract_a2ui_from_text(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        """
        Extracts embedded JSON A2UI definitions from agent text.
        Returns (clean_text, list_of_components).
        """
        import json
        import re
        
        components = []
        clean_text = text
        
        # Regex to find JSON blocks containing "a2ui_intent"
        # Matches { ... "a2ui_intent": ... } potentially across lines
        # Non-greedy match for the content inside braces
        pattern = r'({[^{]*"a2ui_intent"[^}]*})' 
        # Note: Simple regex might fail on nested JSON. 
        # Attempting a more robust extraction if possible, or assuming flat JSON from our tools.
        # Our tools return flat keys mostly, but data is a list.
        # Let's try to find potential JSON start/ends.
        
        try:
            # Iteratively find JSON candidates
            potential_jsons = []
            
            # Simple heuristic: look for lines starting with { or embedded `{`
            # Since our tool output is `json.dumps`, it's likely a valid JSON string.
            # The agent might wrap it in markdown block ```json ... ```
            
            # 1. Try extracting markdown code blocks first
            code_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            for block in code_blocks:
                potential_jsons.append(block)
                clean_text = clean_text.replace(f"```json{block}```", "") # Remove from text
                
            # 2. If no code blocks, look for raw JSON-like strings
            # Look for start of our specific JSON signature
            start_marker = '"a2ui_intent":'
            
            if start_marker in text and not code_blocks:
                # Naive extraction: Find the enclosing braces. 
                # Since we control the tool output, we know it starts with `{` and contains `a2ui_intent`.
                # We can try to parse the entire text if it's Just JSON?
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and "a2ui_intent" in data:
                        extract = data
                        clean_text = "" # Text was entirely JSON
                        potential_jsons.append(json.dumps(extract)) # Re-queue for processing
                except json.JSONDecodeError:
                    # It's mixed with text.
                    # Fallback: Assume the JSON is a distinct block?
                    # Let's just Regex for the known structure from OUR tools.
                    # list_user_claims_tool returns {"a2ui_intent": "list_claims_table", ...}
                    pass

            # Process candidates
            for json_str in potential_jsons:
                try:
                    data = json.loads(json_str) 
                except:
                     data = json_str if isinstance(json_str, dict) else None # Handle if we appended dict above
                
                if data and isinstance(data, dict):
                    intent = data.get("a2ui_intent")
                    if intent == "list_claims_table":
                        components.append(self._create_table_card(data))
                    elif intent == "list_claims_cards":
                        components.append(self._create_card_list(data))
                    elif intent == "create_claim_form":
                        components.append(self._create_form_card(data, "Create New Claim"))
                    elif intent == "update_claim_form":
                        components.append(self._create_form_card(data, f"Update Claim #{data.get('claim_id')}"))
                        
            # If regex didn't work (likely), let's try a scan for the specfic intents manually
            # if we didn't find anything yet.
            if not components:
                 # Scan for table intent
                 if "list_claims_table" in text:
                     # Attempt to locate the brace before it
                     # This is tricky without a parser.
                     # Let's rely on the System Prompt to output CLEAN valid JSON or Code Block.
                     pass

        except Exception as e:
            print(f"Error extracting A2UI: {e}")
            
        return clean_text, components

    def _create_table_card(self, data: Dict) -> Dict[str, Any]:
        """Creates a table card from data."""
        return {
            "type": "table_card",
            "title": data.get("summary", "Claims List"),
            "columns": ["ID", "Policy", "Type", "Status", "Amount"],
            "rows": data.get("data", [])
        }

    def _create_card_list(self, data: Dict) -> Dict[str, Any]:
        """Creates a list of cards for claims."""
        claims = data.get("data", [])
        cards = []
        for c in claims:
            # Determine card type/color based on status
            status = c.get("Status", "DRAFT")
            cards.append({
                "type": "status_card", # Or info_card
                "status": status,
                "title": f"Claim #{c.get('ID')} - {c.get('Type')}",
                "description": c.get("Description") or f"Amount: {c.get('Amount')}",
                "color": self._get_status_color(status),
                "icon": self._get_status_icon(status)
            })
            
        return {
            "type": "card_list",
            "title": data.get("summary", "Claims View"),
            "cards": cards
        }

    def _create_form_card(self, data: Dict, title: str) -> Dict[str, Any]:
        """Creates a form card from data."""
        return {
            "type": "form_card",
            "title": title,
            "submitLabel": "Submit",
            "fullWidth": True, # A2UI hint
            "fields": data.get("fields", [])
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
                    # If claim doesn't exist, return 404 or empty? API expects 403 for unauthorized.
                    raise ValueError("Claim not found")
                if claim.created_by_id != user_id:
                     # Allow if user is approver? 
                     # For now, simplistic check matching send_message strictness.
                     # In real app, check if user is the assigned approver.
                     if claim.assigned_approver_id != user_id:
                        raise ValueError("Not authorized to access this claim")

            # Query messages for this claim
            # Agent messages in claim chat have sender_id=None usually, grouped by claim_id
            query = select(Message).where(Message.claim_id == claim_id).order_by(Message.created_at)
            
        else:
            # --- General / Multi-Claim Chat ---
            # Must have user_id to identify whose general chat it is
            if not user_id:
                raise ValueError("User ID required for general chat")
            
            # Query messages where claim_id is NULL AND sender_id is user_id
            # Note: User messages have sender_id=user_id.
            # Agent messages in general chat MUST also have sender_id=user_id (as a 'reply-to' marker) 
            # to distinguish between users.
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
        If claim_id is None, clears general chat for the user.
        If claim_id is provided, clears (or could clear) messages for that claim if authorized.
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
             # General chat: Delete where claim_id is None and sender_id is user_id (or agent's "reply to" sender_id)
             # Wait, agent messages in general chat also have sender_id = user_id.
             # So we just delete where claim_id is NULL and sender_id == user_id.
             query = delete(Message).where(
                 Message.claim_id.is_(None),
                 Message.sender_id == user_id
             )
             
        await self.db.execute(query)
        await self.db.commit()

    async def _get_claim(self, claim_id: int) -> Claim:
        """Get claim by ID."""
        result = await self.db.execute(select(Claim).where(Claim.id == claim_id))
        return result.scalars().first()

    async def _get_agent_response(self, claim: Claim, user_message: str) -> Dict[str, Any]:
        """
        Get agent response with A2UI components using Strands agent.
        Returns structured response with text and A2UI components.
        """
        # Build context for agent with chat-specific system prompt
        from strands import Agent
        from strands.models.litellm import LiteLLMModel
        from strands.session import FileSessionManager
        from app.core.config import settings
        
        # Create LiteLLM model
        model = LiteLLMModel(
            client_args={"api_key": settings.GEMINI_API_KEY},
            model_id="gemini/gemini-2.5-flash-lite",
            params={"max_tokens": 1000, "temperature": 0.7}
        )
        
        # Create session manager for conversation continuity
        session_manager = FileSessionManager(
            session_id=f"chat-claim-{claim.id}",
            storage_dir="./agent_sessions/chat"
        )
        
        # Create agent for chat
        agent = Agent(
            model=model,
            session_manager=session_manager,
            system_prompt=(
                "You are a helpful insurance claim assistant chatbot. "
                "You help users understand their claims, answer questions, and provide status updates. "
                "\n\n"
                "GUIDELINES:\n"
                "- Be friendly, concise, and helpful\n"
                "- Provide accurate information about the claim\n"
                "- Explain status changes and next steps clearly\n"
                "- If you don't know something, say so honestly\n"
                "- Keep responses brief but informative\n"
                "\n"
                f"CURRENT CLAIM CONTEXT:\n"
                f"- Policy Number: {claim.policy_number}\n"
                f"- Type: {claim.claim_type}\n"
                f"- Amount: ${claim.claim_amount:,.2f}\n"
                f"- Status: {claim.status}\n"
                f"- Description: {claim.description}\n"
                f"- Fraud Risk Score: {claim.fraud_risk_score}\n"
                f"- Submitted: {claim.created_at.strftime('%B %d, %Y')}\n"
            )
        )
        
        # Get agent response
        try:
            result = agent(user_message)
            response_text = result.lastMessage if hasattr(result, 'lastMessage') else str(result)
        except Exception as e:
            print(f"Error getting agent response: {e}")
            # Fallback to simple response
            response_text = self._generate_simple_response(claim, user_message)
        
        # Create A2UI components based on message content
        a2ui_components = self._create_a2ui_components(claim, user_message)
        
        return {
            "text": response_text,
            "a2ui": a2ui_components
        }

    def _generate_simple_response(self, claim: Claim, user_message: str) -> str:
        """Generate a simple text response based on common questions."""
        msg_lower = user_message.lower()
        
        if "status" in msg_lower:
            status_explanations = {
                "DRAFT": "Your claim is in draft status and hasn't been submitted yet.",
                "UNDER_AGENT_REVIEW": "Your claim is currently being analyzed by our AI agent.",
                "PENDING_APPROVAL": "Your claim requires human review and is waiting for an approver to make a decision.",
                "NEEDS_MORE_INFO": "We need additional information from you to process this claim.",
                "APPROVED": "Great news! Your claim has been approved.",
                "REJECTED": "Unfortunately, your claim has been rejected."
            }
            return status_explanations.get(
                claim.status,
                f"Your claim is currently in {claim.status} status."
            )
        
        elif "amount" in msg_lower or "how much" in msg_lower:
            return f"Your claim is for ${claim.claim_amount:,.2f}. The claim status is {claim.status}."
        
        elif "when" in msg_lower or "time" in msg_lower:
            return f"Your claim was submitted on {claim.created_at.strftime('%B %d, %Y at %I:%M %p')}. Current status: {claim.status}."
        
        elif "help" in msg_lower or "what can" in msg_lower:
            return "I can help you with:\n• Check your claim status\n• Explain claim details\n• Answer questions about the approval process\n• Provide updates on your claim\n\nWhat would you like to know?"
        
        else:
            return f"I'm here to help with your claim (Policy: {claim.policy_number}). Your claim status is {claim.status}. What specific information would you like to know?"

    def _create_a2ui_components(self, claim: Claim, user_message: str) -> List[Dict[str, Any]]:
        """Create A2UI components for rich UI rendering."""
        components = []
        
        msg_lower = user_message.lower()
        
        # Status card for status queries
        if "status" in msg_lower:
            components.append({
                "type": "status_card",
                "status": claim.status,
                "title": f"Claim Status: {claim.status.replace('_', ' ').title()}",
                "description": self._get_status_description(claim.status),
                "color": self._get_status_color(claim.status),
                "icon": self._get_status_icon(claim.status)
            })
        
        # Claim details card
        components.append({
            "type": "info_card",
            "title": "Claim Details",
            "fields": [
                {"label": "Policy Number", "value": claim.policy_number},
                {"label": "Type", "value": claim.claim_type},
                {"label": "Amount", "value": f"${claim.claim_amount:,.2f}"},
                {"label": "Status", "value": claim.status.replace('_', ' ').title()},
                {"label": "Submitted", "value": claim.created_at.strftime('%B %d, %Y')}
            ]
        })
        
        # Action buttons based on status
        if claim.status == "NEEDS_MORE_INFO":
            components.append({
                "type": "action_buttons",
                "buttons": [
                    {"label": "Upload Documents", "action": "upload_docs", "style": "primary"},
                    {"label": "Contact Support", "action": "contact_support", "style": "secondary"}
                ]
            })
        
        return components

    def _get_status_description(self, status: str) -> str:
        """Get human-readable status description."""
        descriptions = {
            "DRAFT": "Not yet submitted",
            "UNDER_AGENT_REVIEW": "Being analyzed by AI",
            "PENDING_APPROVAL": "Awaiting human review",
            "NEEDS_MORE_INFO": "Additional information required",
            "APPROVED": "Claim approved",
            "REJECTED": "Claim denied"
        }
        return descriptions.get(status, status)

    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        colors = {
            "DRAFT": "gray",
            "UNDER_AGENT_REVIEW": "blue",
            "PENDING_APPROVAL": "yellow",
            "NEEDS_MORE_INFO": "orange",
            "APPROVED": "green",
            "REJECTED": "red"
        }
        return colors.get(status, "gray")

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status."""
        icons = {
            "DRAFT": "📝",
            "UNDER_AGENT_REVIEW": "🤖",
            "PENDING_APPROVAL": "⏳",
            "NEEDS_MORE_INFO": "❓",
            "APPROVED": "✅",
            "REJECTED": "❌"
        }
        return icons.get(status, "📋")

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
