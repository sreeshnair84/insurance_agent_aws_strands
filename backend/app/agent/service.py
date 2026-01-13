from app.agent.llmlite import LLMliteClient, Tool
from app.agent import tools as agent_tools
from app.models.claim import Claim, ClaimStatus
from sqlalchemy.ext.asyncio import AsyncSession
import json

class InsuranceAgent:
    def __init__(self):
        self.llm = LLMliteClient(model_name="gemini/gemini-2.5-flash-lite-preview-02-05")
    
    async def process_claim(self, claim: Claim, db: AsyncSession):
        """
        Main agent loop to process a claim state.
        """
        claim_data = {
            "policy_number": claim.policy_number,
            "claim_type": claim.claim_type,
            "claim_amount": claim.claim_amount,
            "incident_date": str(claim.incident_date) if claim.incident_date else None,
            "description": claim.description,
            "fraud_risk_score": claim.fraud_risk_score
        }

        # 1. Validate
        missing = await agent_tools.validate_claim(claim_data)
        if missing:
            # Action: Transition to NEEDS_MORE_INFO or ask user
            # In our FSM, we might stay in DRAFT or go to NEEDS_MORE_INFO
            return {
                "action": "REQUEST_INFO",
                "message": await agent_tools.request_more_info(missing),
                "missing_fields": missing
            }

        # 2. Risk Assessment
        risk = await agent_tools.assess_risk(claim_data)
        
        # 3. Summary (Using LLM)
        summary_prompt = (
            f"Generate a professional, 1-paragraph executive summary for an insurance claim approver. "
            f"Details: {json.dumps(claim_data)}. Risk Assessment: {risk}. "
            f"Highlight key risk factors."
        )
        try:
            llm_response = await self.llm.generate_response(summary_prompt)
            summary = llm_response.get("content", "Summary generation failed.")
        except Exception:
            summary = await agent_tools.summarize_for_approver(claim_data) # Fallback
        
        # 4. Construct Agent thought/response
        # For simplicity, we return the analysis. In a real LLM loop, we'd feed this to the LLM.
        
        return {
            "action": "READY_FOR_APPROVAL",
            "risk_level": risk,
            "summary": summary,
            "message": f"Claim validated. Risk Level: {risk}. Sent to approver."
        }
