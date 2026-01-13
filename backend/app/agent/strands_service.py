"""
AWS Strands-based Insurance Agent Service
Implements human-in-the-loop claim validation using Strands interrupts.
"""
from typing import Any, Dict, List, Optional
from strands import Agent, tool
from strands.models.litellm import LiteLLMModel
from strands.session import FileSessionManager
from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry
from strands.types.tools import ToolContext
from strands.agent import AgentResult
from app.core.config import settings
from app.models.claim import Claim, ClaimStatus, ClaimType
from sqlalchemy.ext.asyncio import AsyncSession
import json
import datetime



# ============================================================================
# AGENT TOOLS
# ============================================================================

@tool
async def validate_claim(claim_data: dict) -> List[str]:
    """
    Validates claim for completeness.
    Returns a list of missing required fields.
    """
    missing = []
    required_fields = [
        "policy_number",
        "claim_type",
        "claim_amount",
        "incident_date",
        "description"
    ]
    for field in required_fields:
        if not claim_data.get(field):
            missing.append(field)
    return missing


@tool
async def assess_risk(claim_data: dict) -> str:
    """
    Calculates risk level (LOW | MEDIUM | HIGH) based on heuristics.
    
    Risk factors:
    - Amount > $500,000 or fraud score > 0.7 → HIGH
    - Amount > $50,000 or fraud score > 0.4 → MEDIUM
    - Otherwise → LOW
    """
    amount = float(claim_data.get("claim_amount", 0))
    fraud_score = float(claim_data.get("fraud_risk_score", 0))
    
    if amount > 500000 or fraud_score > 0.7:
        return "HIGH"
    if amount > 50000 or fraud_score > 0.4:
        return "MEDIUM"
    return "LOW"


@tool(context=True)
async def request_approval(
    tool_context: ToolContext,
    claim_id: int,
    risk_level: str,
    summary: str,
    claim_amount: float
) -> str:
    """
    Requests human approval for insurance claim.
    Raises an interrupt to pause agent execution until approver responds.
    
    This tool should be called for HIGH or MEDIUM risk claims.
    """
    approval = tool_context.interrupt(
        "claim-approval",
        reason={
            "claim_id": claim_id,
            "risk_level": risk_level,
            "summary": summary,
            "claim_amount": claim_amount
        }
    )
    return approval


@tool
async def request_more_info(missing_fields: List[str]) -> str:
    """
    Generates user-facing clarification question for missing claim information.
    """
    return f"Please provide the following missing details to proceed: {', '.join(missing_fields)}."


@tool(context=True)
async def create_claim_draft(
    tool_context: ToolContext,
    policy_number: str,
    claim_type: str,
    description: str,
    incident_date: str = None
) -> str:
    """
    Creates a new insurance claim draft.
    Returns the created claim ID.
    """
    # Requires DB access via context or dependency injection
    # For now, we'll signal the backend to create it via a special return or side-effect
    # In Strands, tools are best kept pure or using external services.
    # We will use a unique return structure that the service layer interprets to do the DB write
    # OR we can inject the DB session into the tool context if we extended it.
    
    # Simpler approach: Return a structured action that the caller (ChatService) executes
    # BUT tools need to return strings/results to the agent.
    # So we will do the "Action Pattern":
    return json.dumps({
        "action": "create_claim",
        "data": {
            "policy_number": policy_number,
            "claim_type": claim_type,
            "description": description,
            "incident_date": incident_date
        }
    })

@tool(context=True)
async def list_user_claims(tool_context: ToolContext) -> str:
    """
    Lists recent claims for the current user.
    """
    # The actual retrieval will happen in the service layer based on this signal
    return json.dumps({"action": "list_claims"})

@tool(context=True)
async def get_claim_details(tool_context: ToolContext, claim_id: int) -> str:
    """
    Gets details of a specific claim.
    """
    return json.dumps({"action": "get_claim", "claim_id": claim_id})


# ============================================================================
# APPROVAL HOOK
# ============================================================================

class ClaimApprovalHook(HookProvider):
    """
    Hook to intercept high-risk claim approvals and request human intervention.
    Implements human-in-the-loop pattern using Strands interrupts.
    """
    
    def __init__(self, app_name: str = "insurance-agent"):
        self.app_name = app_name
    
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register the approval hook for BeforeToolCallEvent."""
        registry.add_callback(BeforeToolCallEvent, self.intercept_approval)
    
    def intercept_approval(self, event: BeforeToolCallEvent) -> None:
        """
        Intercept tool calls that require approval.
        Only intercepts 'request_approval' tool calls.
        """
        # Only intercept approval requests
        if event.tool_use["name"] != "request_approval":
            return
        
        # Check if approver has "trust" status in agent state
        # This allows approvers to skip future interrupts if they choose
        if event.agent.state.get(f"{self.app_name}-trust") == "trusted":
            return  # Skip interrupt for trusted approvers
        
        # Extract claim data from tool input
        tool_input = event.tool_use["input"]
        
        # Raise interrupt for human decision
        approval = event.interrupt(
            f"{self.app_name}-approval",
            reason={
                "claim_id": tool_input.get("claim_id"),
                "risk_level": tool_input.get("risk_level"),
                "summary": tool_input.get("summary"),
                "claim_amount": tool_input.get("claim_amount")
            }
        )
        
        # Handle approval response
        if approval.lower() not in ["approved", "approve", "yes", "y"]:
            # Cancel tool execution if not approved
            event.cancel_tool = f"Claim approval denied: {approval}"
        
        # If approver chose "trust", remember for future interactions
        if approval.lower() == "trust":
            event.agent.state.set(f"{self.app_name}-trust", "trusted")


# ============================================================================
# INSURANCE AGENT SERVICE
# ============================================================================

class StrandsInsuranceAgent:
    """
    AWS Strands-based Insurance Agent Service.
    
    Handles claim validation, risk assessment, and human-in-the-loop approvals
    using the official AWS Strands SDK with interrupts and session management.
    """
    
    def __init__(self):
        """Initialize the Strands LiteLLM model."""
        self.model = LiteLLMModel(
            client_args={
                "api_key": settings.GEMINI_API_KEY,
            },
            model_id="gemini/gemini-2.5-flash-lite",
            params={
                "max_tokens": 2000,
                "temperature": 0.3,
            }
        )
    
    async def process_claim(
        self,
        claim: Claim,
        db: AsyncSession,
        user_input: str = None
    ) -> AgentResult:
        """
        Process insurance claim with Strands agent.
        
        Args:
            claim: The claim to process
            db: Database session
            user_input: Optional user input for resuming interrupted sessions
        
        Returns:
            AgentResult with stop_reason, interrupts, and final message
        """
        # Create session manager for this claim
        # Each claim gets its own session for conversation history
        session_manager = FileSessionManager(
            session_id=f"claim-{claim.id}",
            storage_dir="./agent_sessions"
        )
        
        # Create agent with tools, hooks, and session management
        agent = Agent(
            model=self.model,
            session_manager=session_manager,
            hooks=[ClaimApprovalHook()],
            tools=[
                validate_claim,
                assess_risk,
                request_approval,
                request_more_info
            ],
            system_prompt=(
                "You are an enterprise insurance validation AI assistant. "
                "Your role is to analyze insurance claims and assist with processing, "
                "but you NEVER approve or reject claims yourself. "
                "\n\n"
                "WORKFLOW:\n"
                "1. First, validate the claim using validate_claim tool\n"
                "2. If missing information, use request_more_info tool\n"
                "3. Assess risk using assess_risk tool\n"
                "4. For HIGH or MEDIUM risk claims, use request_approval tool\n"
                "5. For LOW risk claims, provide a summary and recommendation\n"
                "\n"
                "RULES:\n"
                "- Be neutral, explainable, and audit-friendly\n"
                "- Always explain your risk assessment reasoning\n"
                "- Highlight key risk factors clearly\n"
                "- Never make final approval/rejection decisions\n"
                "- Output clear, professional summaries for human approvers"
            )
        )
        
        # Prepare claim data
        claim_data = {
            "claim_id": claim.id,
            "policy_number": claim.policy_number,
            "claim_type": claim.claim_type,
            "claim_amount": claim.claim_amount,
            "incident_date": str(claim.incident_date) if claim.incident_date else None,
            "description": claim.description,
            "fraud_risk_score": claim.fraud_risk_score
        }
        
        # Invoke agent
        if user_input:
            # Resume with user input (for continuing interrupted sessions)
            result = agent(user_input)
        else:
            # Initial invocation
            prompt = (
                f"Analyze and validate this insurance claim:\n\n"
                f"Claim ID: {claim_data['claim_id']}\n"
                f"Policy: {claim_data['policy_number']}\n"
                f"Type: {claim_data['claim_type']}\n"
                f"Amount: ${claim_data['claim_amount']}\n"
                f"Incident Date: {claim_data['incident_date']}\n"
                f"Description: {claim_data['description']}\n"
                f"Fraud Risk Score: {claim_data['fraud_risk_score']}\n\n"
                f"Please validate completeness, assess risk, and determine next steps."
            )
            result = agent(prompt)
        
        return result
    
    async def resume_with_response(
        self,
        claim: Claim,
        interrupt_id: str,
        response: str,
        db: AsyncSession
    ) -> AgentResult:
        """
        Resume agent execution with approver response to interrupt.
        
        Args:
            claim: The claim being processed
            interrupt_id: ID of the interrupt to respond to
            response: Approver's response (e.g., "approved", "rejected")
            db: Database session
        
        Returns:
            AgentResult after resuming with response
        """
        # Create session manager (same session as original)
        session_manager = FileSessionManager(
            session_id=f"claim-{claim.id}",
            storage_dir="./agent_sessions"
        )
        
        # Create agent (will restore session state)
        agent = Agent(
            model=self.model,
            session_manager=session_manager,
            hooks=[ClaimApprovalHook()],
            tools=[
                validate_claim,
                assess_risk,
                request_approval,
                request_more_info
            ],
            system_prompt=(
                "You are an enterprise insurance validation AI assistant. "
                "Continue processing the claim based on the approver's decision."
            )
        )
        
        # Resume with interrupt response
        result = agent([{
            "interruptResponse": {
                "interruptId": interrupt_id,
                "response": response
            }
        }])
        
        return result

    async def process_general_chat(
        self,
        user_id: int,
        user_input: str,
        db: AsyncSession
    ) -> AgentResult:
        """
        Process general user chat for listing/creating claims.
        """
        # --- Dynamic Tools with DB Access ---
        
        # --- Dynamic Tools with DB Access ---
        
        @tool
        async def list_user_claims_tool(view_type: str = "table") -> str:
            """
            Lists recent claims for the current user.
            Args:
                view_type: "table" (default) or "cards". Use "cards" if user asks for "cards" or "visual" view.
            """
            try:
                # Debug logging
                with open("tool_debug.log", "a") as f:
                    f.write(f"Executing list_user_claims_tool for user_id={user_id}\n")

                result = await db.execute(
                    select(Claim).where(Claim.created_by_id == user_id).order_by(Claim.created_at.desc()).limit(10)
                )
                claims = result.scalars().all()
                
                with open("tool_debug.log", "a") as f:
                    f.write(f"Found {len(claims)} claims\n")
                
                if not claims:
                    return "No claims found."

                intent = "list_claims_table"
                if view_type == "cards":
                    intent = "list_claims_cards"
                
                # Return JSON structure with intent
                data = [
                    {
                        "ID": c.id,
                        "Policy": c.policy_number,
                        "Type": c.claim_type,
                        "Status": c.status,
                        "Amount": f"${c.claim_amount:,.2f}",
                        "Description": c.description # Needed for cards
                    } for c in claims
                ]
                
                return json.dumps({
                    "a2ui_intent": intent,
                    "data": data,
                    "summary": f"Found {len(claims)} recent claims."
                })
            except Exception as e:
                import traceback
                error_msg = f"Error in list_user_claims_tool: {str(e)}\n{traceback.format_exc()}"
                with open("tool_error.log", "a") as f:
                    f.write(error_msg + "\n")
                return f"Error listing claims: {str(e)}"

        @tool
        async def create_claim_draft_tool(
            policy_number: str,
            claim_type: str,
            description: str,
            incident_date: str = None
        ) -> str:
            """Creates a new insurance claim draft."""
            new_claim = Claim(
                policy_number=policy_number,
                claim_type=claim_type, # Expects Enum string
                description=description,
                status=ClaimStatus.DRAFT,
                created_by_id=user_id,
                claim_amount=0.0, # Default
                incident_date=datetime.datetime.now() # Default to now if not provided or parse str
            )
            db.add(new_claim)
            await db.commit()
            await db.refresh(new_claim)
            return f"Claim created successfully. Claim ID: {new_claim.id}. You can now view it."

        @tool
        async def get_claim_details_tool(claim_id: int) -> str:
            """Gets details of a specific claim."""
            result = await db.execute(select(Claim).where(Claim.id == claim_id))
            claim = result.scalars().first()
            if not claim:
                return "Claim not found."
            if claim.created_by_id != user_id:
                return "Unauthorized access to this claim."
            return (f"Claim ID: {claim.id}\nPolicy: {claim.policy_number}\nType: {claim.claim_type}\n"
                    f"Status: {claim.status}\nDescription: {claim.description}\nAmount: ${claim.claim_amount}")
        
        @tool
        async def present_claim_form_tool() -> str:
            """
            Present a form to create a new claim.
            """
            return json.dumps({
                "a2ui_intent": "create_claim_form",
                "fields": [
                    {"name": "policy_number", "label": "Policy Number", "type": "text", "required": True},
                    {"name": "claim_type", "label": "Claim Type", "type": "select", "options": ["HEALTH", "AUTO", "PROPERTY"], "required": True},
                    {"name": "description", "label": "Description", "type": "textarea", "required": True},
                    {"name": "incident_date", "label": "Incident Date", "type": "date", "required": False}
                ]
            })

        @tool
        async def present_update_claim_form_tool(claim_id: int) -> str:
            """
            Present a form to update an existing claim.
            Use this when user wants to update a claim but hasn't provided all details.
            """
            claim = await db.get(Claim, claim_id)
            if not claim or claim.created_by_id != user_id:
                return "Claim not found or unauthorized."
                
            if claim.status not in [ClaimStatus.DRAFT, ClaimStatus.NEEDS_MORE_INFO]:
                 return f"Cannot update claim in {claim.status} status."

            return json.dumps({
                "a2ui_intent": "update_claim_form",
                "claim_id": claim.id,
                "fields": [
                    {"name": "claim_amount", "label": "Claim Amount ($)", "type": "number", "required": False, "defaultValue": claim.claim_amount},
                    {"name": "description", "label": "Description", "type": "textarea", "required": False, "defaultValue": claim.description},
                    # Add more fields as needed
                ]
            })

        @tool
        async def update_claim_tool(claim_id: int, claim_amount: float = None, description: str = None) -> str:
            """
            Update an existing claim's details directly. 
            Use this when user provides value directly (e.g. "Update amount to 500").
            """
            from app.services.claim_service import ClaimService
            service = ClaimService(db)
            update_data = {}
            if claim_amount is not None:
                update_data["claim_amount"] = claim_amount
            if description:
                update_data["description"] = description
                
            if not update_data:
                return "No updates provided."

            try:
                # We need to verify ownership roughly here or let Service handle it. 
                # Service treats all updates as valid if ID matches, so effectively we should check ownership 
                # but for now we trust the ID passed. In real app, Service methods should take user_id.
                # Actually ClaimService doesn't take user_id for update_claim, which is a gap.
                # We'll do a quick check here.
                claim = await db.get(Claim, claim_id)
                if not claim or claim.created_by_id != user_id:
                     return "Claim not found or unauthorized."

                updated = await service.update_claim(claim_id, update_data)
                return f"Claim {claim_id} updated successfully. New Amount: ${updated.claim_amount}. Status: {updated.status}."
            except ValueError as e:
                return f"Error updating claim: {str(e)}"

        # --- execution ---
        
        session_manager = FileSessionManager(
            session_id=f"user-chat-{user_id}",
            storage_dir="./agent_sessions/general"
        )
        
        agent = Agent(
            model=self.model,
            session_manager=session_manager,
            tools=[
                list_user_claims_tool, 
                create_claim_draft_tool, 
                get_claim_details_tool, 
                present_claim_form_tool,
                present_update_claim_form_tool,
                update_claim_tool
            ],
            system_prompt=(
                "You are a helpful insurance assistant. "
                "You can help users list claims, create new claims, or update existing ones. "
                "\n\nUI GUIDELINES:\n"
                "- **Listing Claims**: Call `list_user_claims_tool`. If user asks for 'cards' or 'grid' view, pass `view_type='cards'`, otherwise default to 'table'.\n"
                "- **Creating Claims**: If user asks to create a claim, call `present_claim_form_tool` to show the form.\n"
                "  - EXCEPTION: If they provide ALL details (Policy, Type, Desc) in one go, call `create_claim_draft_tool`.\n"
                "- **Updating Claims**: \n"
                "  - If user says 'Update claim 123' without details, call `present_update_claim_form_tool(123)`.\n"
                "  - If user says 'Update claim 123 amount to 500', call `update_claim_tool(123, claim_amount=500)`.\n"
                "  - Verify claim ID exists before updating.\n"
                "- Always provide a brief text summary along with any UI component."
            )
        )
        
        result = agent(user_input)
        return result
