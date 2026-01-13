from typing import List, Dict, Any, Tuple
import json
import re
from strands import Agent
from strands.models.litellm import LiteLLMModel
from app.core.config import settings

class A2UIConverter:
    """
    Service responsible for extracting and converting A2UI definitions 
    from raw text (usually from an agent response) into structured components.
    """
    
    def __init__(self):
        # Configure the parsing model once
        self.parser_model = LiteLLMModel(
            client_args={"api_key": settings.GEMINI_API_KEY},
            model_id="gemini/gemini-2.5-flash-lite",
            params={"max_tokens": 1000, "temperature": 0.0} 
        )

    async def extract_and_convert(self, text: str, data_context: Any = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extracts embedded JSON A2UI definitions from text or context.
        Returns cleaned text and a list of A2UI components.
        """
        components = []
        clean_text = text
        
        # 1. Quick pass: code blocks in text (Legacy support)
        code_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_blocks:
            for block in code_blocks:
                try:
                    data = json.loads(block)
                    if isinstance(data, dict) and "a2ui_intent" in data:
                        clean_text = clean_text.replace(f"```json{block}```", "").strip()
                        comp = self._process_data(data)
                        if comp: components.append(comp)
                except:
                    pass
            
            if components:
                return clean_text, components

        # 2. Smart Conversion: Parser Agent uses Text + Data Context
        try:
            p_agent = Agent(
                model=self.parser_model,
                system_prompt=(
                    "You are an A2UI Bridge Agent. Your goal is to convert Tool Data into structured A2UI components "
                    "and deduplicate the message if it repeats the tool data in a verbose way.\n\n"
                    "MAPPING RULES:\n"
                    "1. If Tool Data has type='claims_list': Generate a `table_card` with columns ['ID', 'Policy', 'Type', 'Status', 'Amount'].\n"
                    "2. If Tool Data has type='form_schema' and purpose='create_claim': Generate a `form_card` with the provided fields.\n"
                    "3. If Tool Data has type='form_schema' and purpose='update_claim': Generate a `form_card` with the provided fields and defaultValue values.\n"
                    "4. If Tool Data has type='claim_detail': Generate an `info_card` or `status_card` with claim details.\n"
                    "5. If Tool Data has type='claim_updated' or 'claim_submitted': Generate a `status_card` showing the result.\n"
                    "\n"
                    "DEDUPLICATION RULES:\n"
                    "- If the 'Agent Message' contains a redundant textual representation of the Tool Data (like a list of claims already in the table), you MUST suggest a concise 'replacementText' (e.g., 'Here are your claims:').\n"
                    "- Do NOT skip 'replacementText' if the original message is verbose.\n"
                    "\n"
                    "OUTPUT FORMAT:\n"
                    "Output ONLY a valid JSON object with the following schema:\n"
                    "{\n"
                    "  \"components\": [ ... ],  // List of A2UI components\n"
                    "  \"replacementText\": \"...\" // Concise replacement for the original agent message\n"
                    "}\n"
                    "No markdown, no explanation."
                )
            )
            
            prompt = f"Agent Message: {text}\n\nTool Data: {json.dumps(data_context) if data_context else 'None'}"
            result = p_agent(f"Convert to A2UI JSON components:\n\n{prompt}")
            
            extraction_response = result.lastMessage if hasattr(result, 'lastMessage') else str(result)
            extraction_response = extraction_response.replace("```json", "").replace("```", "").strip()
            
            extracted_data = json.loads(extraction_response)
            
            # Handle list of components (backward compatibility/legacy)
            if isinstance(extracted_data, list):
                for item in extracted_data:
                    if "type" in item:
                        components.append(item)
                    elif "a2ui_intent" in item:
                        comp = self._process_data(item)
                        if comp: components.append(comp)
            
            # Handle new JSON object format
            elif isinstance(extracted_data, dict):
                # Check for replacementText
                if "replacementText" in extracted_data and extracted_data["replacementText"]:
                    clean_text = extracted_data["replacementText"]
                
                # Check for components list or single component
                if "components" in extracted_data and isinstance(extracted_data["components"], list):
                    for item in extracted_data["components"]:
                        if "type" in item:
                            components.append(item)
                        elif "a2ui_intent" in item:
                            comp = self._process_data(item)
                            if comp: components.append(comp)
                elif "type" in extracted_data:
                    components.append(extracted_data)
                elif "a2ui_intent" in extracted_data:
                    comp = self._process_data(extracted_data)
                    if comp: components.append(comp)

        except Exception as e:
            print(f"A2UI Conversion Error: {e}")
            
        return clean_text, components

    def _process_data(self, data: Dict) -> Dict[str, Any] | None:
        """Converts raw data dict to specific component types."""
        intent = data.get("a2ui_intent")
        
        if intent == "list_claims_table":
            return {
                "type": "table_card",
                "title": data.get("summary", "Claims List"),
                "columns": ["ID", "Policy", "Type", "Status", "Amount"],
                "rows": data.get("data", [])
            }
            
        elif intent == "list_claims_cards":
            claims = data.get("data", [])
            cards = []
            for c in claims:
                status = c.get("Status", "DRAFT")
                cards.append({
                    "type": "status_card",
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
            
        elif intent == "create_claim_form":
            return {
                "type": "form_card",
                "title": "Create New Claim",
                "submitLabel": "Submit",
                "fullWidth": True,
                "fields": data.get("fields", [])
            }
            
        elif intent == "update_claim_form":
            return {
                "type": "form_card",
                "title": f"Update Claim #{data.get('claim_id')}",
                "submitLabel": "Submit",
                "fullWidth": True,
                "fields": data.get("fields", [])
            }
            
        return None

    def _get_status_color(self, status: str) -> str:
        colors = {
            "DRAFT": "gray", "UNDER_AGENT_REVIEW": "blue", "PENDING_APPROVAL": "yellow",
            "NEEDS_MORE_INFO": "orange", "APPROVED": "green", "REJECTED": "red"
        }
        return colors.get(status, "gray")

    def _get_status_icon(self, status: str) -> str:
        icons = {
            "DRAFT": "📝", "UNDER_AGENT_REVIEW": "🤖", "PENDING_APPROVAL": "⏳",
            "NEEDS_MORE_INFO": "❓", "APPROVED": "✅", "REJECTED": "❌"
        }
        return icons.get(status, "📋")
