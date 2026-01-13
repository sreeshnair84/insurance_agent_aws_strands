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
from sqlalchemy.future import select
from sqlalchemy import text, delete, update
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
        val = claim_data.get(field)
        # Check for None or empty string. 0.0 is allowed as a value (though unlikely for amount).
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing


@tool
async def assess_risk(claim_data: dict) -> str:
    """
    Calculates risk level (LOW | MEDIUM | HIGH) based on heuristics.
    
    Risk factors:
    - Amount > $250,000 or fraud score > 0.7 → HIGH
    - Amount > $10,000 or fraud score > 0.4 → MEDIUM
    - Otherwise → LOW
    """
    amount = float(claim_data.get("claim_amount", 0))
    fraud_score = float(claim_data.get("fraud_risk_score", 0))
    if amount > 250000:
        return "HIGH"
    if amount > 100000 or fraud_score > 0.7:
        return "HIGH"
    if amount > 10000 or fraud_score > 0.4:
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

# Approval hook removed in favor of explicit request_approval tool calls.


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
        Processes an insurance claim using the Strands agent.
        
        Args:
            claim: The claim object to process
            db: Async database session
            user_input: Optional user response for continuing interrupted sessions
            
        Returns:
            AgentResult with stop_reason, interrupts, and final message
        """
        # Create session manager for this claim
        # Each claim gets its own session for conversation history
        session_manager = FileSessionManager(
            session_id=f"claim-{claim.id}",
            storage_dir="./agent_sessions"
        )
        
        # Get DB tools
        db_tools = self.create_db_tools(db, claim.created_by_id)

        # Create agent with tools and session management
        agent = Agent(
            model=self.model,
            session_manager=session_manager,
            hooks=[],  # Explicitly empty hooks
            tools=[
                validate_claim,
                assess_risk,
                request_approval,
                request_more_info
            ] + db_tools,
            system_prompt=(
                "You are an expert Insurance Claims Audit AI. Your MANDATORY task is to strictly follow the claim validation protocol. "
                "You are NOT allowed to bypass tools or hallucinate results. "
                "\n\n"
                "STRICT SEQUENCE OF OPERATIONS (DO NOT SKIP ANY STEP):\n"
                "1. **VALIDATE**: Call `validate_claim` with the provided claim dictionary. If it returns ANY missing fields, you MUST call `request_more_info` and STOP.\n"
                "2. **ASSESS RISK**: If all fields are present, you MUST call the `assess_risk` tool. You are FORBIDDEN from guessing the risk level based on the prompt alone.\n"
                "3. **HANDLE RISK**:\n"
                "   - If `assess_risk` returns 'HIGH' or 'MEDIUM': You MUST call the `request_approval` tool with a detailed summary. This is MANDATORY for all non-low risk claims.\n"
                "   - If `assess_risk` returns 'LOW': You may proceed to suggest approval in your final response text.\n"
                "\n"
                "CORE RESTRICTIONS:\n"
                "- NEVER approve or reject a claim yourself. Only use tools to signal status changes.\n"
                "- NEVER hallucinate that data is missing if you haven't called `validate_claim`.\n"
                "- ALWAYS think step-by-step before calling a tool (Chain of Thought), but DO NOT share this thinking with the final user. Keep it in your internal tool call planning.\n"
                "- Your final response must be concise and based SOLELY on the outputs of the tools you called."
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
        
        # Get DB tools
        db_tools = self.create_db_tools(db, claim.created_by_id)

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
            ] + db_tools,
            system_prompt=(
                "You are an enterprise insurance validation AI assistant. "
                "Continue processing the claim based on the approver's decision. "
                "You also have access to general tools like `list_user_claims_tool` if needed.\n"
                "- **CRITICAL**: When a tool returns a JSON object containing 'a2ui_intent', you MUST include that EXACT JSON in your final response, wrapped in a markdown code block (```json ... ```)."
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


    def create_db_tools(self, db: AsyncSession, user_id: int):
        """
        Creates tools that require DB access and User context.
        """
        
        @tool
        async def list_user_claims_tool(view_type: str = "table") -> str:
            """
            Lists recent claims for the current user.
            """
            try:
                result = await db.execute(
                    select(Claim).where(Claim.created_by_id == user_id).order_by(Claim.created_at.desc()).limit(10)
                )
                claims = result.scalars().all()
                
                if not claims:
                    return "No claims found."

                # Return raw data structure
                return json.dumps({
                    "type": "claims_list",
                    "view_preference": view_type,
                    "claims": [
                        {
                            "id": c.id,
                            "policy": c.policy_number,
                            "claim_type": c.claim_type,
                            "status": c.status,
                            "amount": c.claim_amount,
                            "description": c.description
                        } for c in claims
                    ]
                })
            except Exception as e:
                return f"Error listing claims: {str(e)}"

        @tool
        async def create_claim_draft_tool(
            policy_number: str,
            claim_type: str,
            description: str,
            incident_date: str = None
        ) -> str:
            """Creates a new insurance claim draft."""
            # Normalize enum value to uppercase
            norm_type = claim_type.upper() if claim_type else "HEALTH"
            
            new_claim = Claim(
                policy_number=policy_number,
                claim_type=norm_type,
                description=description,
                status=ClaimStatus.DRAFT,
                created_by_id=user_id,
                claim_amount=0.0,
                incident_date=datetime.datetime.now()
            )
            db.add(new_claim)
            await db.commit()
            await db.refresh(new_claim)
            return json.dumps({
                "type": "claim_created",
                "claim_id": new_claim.id,
                "status": "DRAFT"
            })

        @tool
        async def get_claim_details_tool(claim_id: int = None, policy_number: str = None) -> str:
            """Gets details of a specific claim by ID or Policy Number."""
            if claim_id:
                query = select(Claim).where(Claim.id == claim_id)
            elif policy_number:
                query = select(Claim).where(Claim.policy_number == policy_number, Claim.created_by_id == user_id).order_by(Claim.created_at.desc())
            else:
                return "Please provide a claim ID or Policy Number."

            result = await db.execute(query)
            claim = result.scalars().first()
            if not claim:
                return "Claim not found."
            if claim.created_by_id != user_id:
                return "Unauthorized access."
            
            return json.dumps({
                "type": "claim_detail",
                "id": claim.id,
                "policy": claim.policy_number,
                "claim_type": claim.claim_type,
                "status": claim.status,
                "amount": claim.claim_amount,
                "description": claim.description
            })
        
        @tool
        async def get_claim_form_schema_tool() -> str:
            """
            Returns the schema for the claim creation form.
            """
            return json.dumps({
                "type": "form_schema",
                "purpose": "create_claim",
                "fields": [
                    {"name": "policy_number", "label": "Policy Number", "required": True},
                    {"name": "claim_type", "options": ["HEALTH", "AUTO", "PROPERTY"], "required": True},
                    {"name": "description", "required": True},
                    {"name": "incident_date", "type": "date"}
                ]
            })

        @tool
        async def get_update_form_schema_tool(claim_id: int) -> str:
            """Returns schema for updating an existing claim."""
            claim = await db.get(Claim, claim_id)
            if not claim or claim.created_by_id != user_id:
                return "Claim not found or unauthorized."
            
            return json.dumps({
                "type": "form_schema",
                "purpose": "update_claim",
                "claim_id": claim.id,
                "current_values": {
                    "claim_amount": claim.claim_amount,
                    "description": claim.description
                }
            })
            
        @tool
        async def update_claim_tool(claim_id: int, claim_amount: float = None, description: str = None) -> str:
            """Update an existing claim's details directly."""
            from app.services.claim_service import ClaimService
            service = ClaimService(db)
            update_data = {}
            if claim_amount is not None:
                update_data["claim_amount"] = claim_amount
            if description:
                update_data["description"] = description
            
            try:
                claim = await db.get(Claim, claim_id)
                if not claim or claim.created_by_id != user_id:
                     return "Claim not found or unauthorized."

                updated = await service.update_claim(claim_id, update_data)
                return json.dumps({
                    "type": "claim_updated",
                    "id": updated.id,
                    "new_amount": updated.claim_amount,
                    "status": updated.status
                })
            except ValueError as e:
                return f"Error updating claim: {str(e)}"

        @tool
        async def submit_claim_tool(claim_id: int) -> str:
            """
            Submits a claim for final review and processing.
            Moves claim from DRAFT to UNDER_AGENT_REVIEW and triggers risk assessment.
            """
            from app.services.claim_service import ClaimService
            service = ClaimService(db)
            try:
                updated = await service.submit_claim(claim_id)
                return json.dumps({
                    "type": "claim_submitted",
                    "id": updated.id,
                    "status": updated.status,
                    "summary": f"Claim #{updated.id} has been submitted for review."
                })
            except Exception as e:
                return f"Error submitting claim: {str(e)}"
                
        return [
            list_user_claims_tool,
            create_claim_draft_tool,
            get_claim_details_tool,
            get_claim_form_schema_tool,
            get_update_form_schema_tool,
            update_claim_tool,
            submit_claim_tool
        ]

    async def process_general_chat(
        self,
        user_id: int,
        user_input: str,
        db: AsyncSession
    ) -> AgentResult:
        """
        Process general user chat.
        """
        # Get DB tools
        db_tools = self.create_db_tools(db, user_id)
        
        session_manager = FileSessionManager(
            session_id=f"user-chat-{user_id}",
            storage_dir="./agent_sessions/general"
        )
        
        agent = Agent(
            model=self.model,
            session_manager=session_manager,
            tools=db_tools,
            system_prompt=(
                "You are a professional insurance assistant. "
                "You can help users list claims, create new claims, or update existing ones.\n\n"
                "TOOLS:\n"
                "- **Listing Claims**: `list_user_claims_tool`.\n"
                "- **Creating Claims**: `get_claim_form_schema_tool`.\n"
                "- **Updating Claims**: `update_claim_tool` (direct) or `get_update_form_schema_tool` (form).\n"
                "- **Submitting Claims**: `submit_claim_tool` (moves from DRAFT to REVIEW).\n"
                "- **Claim Details**: Call `get_claim_details_tool`. You MUST use this tool if a user provides a Claim ID OR a Policy Number.\n"
                "\n"
                "CRITICAL: If a user asks to CHANGE, UPDATE, or SUBMIT a claim, use the respective tool immediately."
            )
        )
        
        return agent(user_input)

