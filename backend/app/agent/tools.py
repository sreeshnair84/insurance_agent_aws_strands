from typing import List, Dict, Any
from app.models.claim import Claim

async def validate_claim(claim_data: Dict[str, Any]) -> List[str]:
    """
    Validates claim for completeness.
    Returns a list of missing fields.
    """
    missing = []
    required_fields = ["policy_number", "claim_type", "claim_amount", "incident_date", "description"]
    for field in required_fields:
        if not claim_data.get(field):
            missing.append(field)
    return missing

async def assess_risk(claim_data: Dict[str, Any]) -> str:
    """
    Calculates risk level (LOW | MEDIUM | HIGH) based on heuristics.
    """
    amount = float(claim_data.get("claim_amount", 0))
    fraud_score = float(claim_data.get("fraud_risk_score", 0))
    
    if amount > 500000 or fraud_score > 0.7:
        return "HIGH"
    if amount > 50000 or fraud_score > 0.4:
        return "MEDIUM"
    return "LOW"

async def summarize_for_approver(claim_data: Dict[str, Any]) -> str:
    """
    Produces 1-paragraph executive summary using logic (or LLM via tool in future).
    For now, a template based summary.
    """
    return (f"Claim for {claim_data.get('claim_type')} policy {claim_data.get('policy_number')} "
            f"amounting to ${claim_data.get('claim_amount')}. "
            f"Incident reported on {claim_data.get('incident_date')}. "
            f"Risk Level: {await assess_risk(claim_data)}.")

async def request_more_info(missing_fields: List[str]) -> str:
    """
    Generates user-facing clarification question.
    """
    return f"Please provide the following missing details to proceed: {', '.join(missing_fields)}."

async def create_claim_draft(policy_number: str, claim_type: str, description: str, incident_date: str = None) -> Dict[str, Any]:
    """
    Creates a new insurance claim draft.
    Returns the created claim ID and status.
    """
    # Note: In a real app this would call a service to write to DB
    # We will hook this up in strands_service.py where we have DB access
    return {
        "action": "create_claim",
        "policy_number": policy_number,
        "claim_type": claim_type,
        "description": description,
        "incident_date": incident_date
    }

async def list_user_claims(user_id: int) -> List[Dict[str, Any]]:
    """
    Lists recent claims for the current user.
    """
    # Note: Hooked up in service
    return {"action": "list_claims", "user_id": user_id}

async def get_claim_details(claim_id: int) -> Dict[str, Any]:
    """
    Gets details of a specific claim.
    """
    return {"action": "get_claim", "claim_id": claim_id}
