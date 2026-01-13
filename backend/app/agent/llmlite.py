from typing import List, Dict, Any, Optional, Callable
import litellm
from app.core.config import settings
import json
import inspect

# Configure LiteLLM
if settings.GEMINI_API_KEY:
    litellm.api_key = settings.GEMINI_API_KEY

class Tool:
    """Base class for Agent tools."""
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func
    
    def to_openai_tool(self):
        """Converts to OpenAI/LiteLLM function schema."""
        sig = inspect.signature(self.func)
        params = {
            "type": "object",
            "properties": {},
            "required": []
        }
        for name, param in sig.parameters.items():
            if name == 'self': continue
            # Simplified schema generation
            params["properties"][name] = {"type": "string", "description": f"Parameter {name}"}
            params["required"].append(name)
            
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params
            }
        }

class LLMliteClient:
    """
    Wrapper for LiteLLM to simulate Strands Agent Framework.
    """
    def __init__(self, model_name: str = "gemini/gemini-2.5-flash-lite-preview-02-05"):
        # LiteLLM needs 'gemini/' prefix sometimes, or just standard model name
        self.model_name = model_name
    
    async def generate_response(self, 
                                prompt: str, 
                                tools: List[Tool] = [], 
                                history: List[Dict] = []) -> Dict[str, Any]:
        """
        Generates a response using LiteLLM.
        """
        messages = [{"role": "user", "content": prompt}]
        # TODO: integrate history
        
        # Convert tools to LiteLLM format (OpenAI compatible)
        lite_tools = [t.to_openai_tool() for t in tools] if tools else None
        
        try:
            response = await litellm.acompletion(
                model=self.model_name,
                messages=messages,
                tools=lite_tools,
                api_key=settings.GEMINI_API_KEY
            )
            
            content = response.choices[0].message.content
            tool_calls = response.choices[0].message.tool_calls
            
            return {
                "content": content,
                "tool_calls": tool_calls
            }
        except Exception as e:
            print(f"LiteLLM Error: {e}")
            return {"error": str(e)}
