import asyncio
import os
import sys
from dotenv import load_dotenv

# Load before any app imports
load_dotenv(".env")

# Move to backend/ to find sql_app.db relative paths
if os.path.exists("backend"):
    os.chdir("backend")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup path for app imports
sys.path.append(os.getcwd())

from app.services.chat_service import ChatService
from app.agent.strands_service import StrandsInsuranceAgent
from app.core.config import settings

async def test_list_claims():
    # Use real DB or at least the engine
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        chat_service = ChatService(db)
        
        user_id = 1
        print("Sending message: 'List all my claims' to general chat (Testing Deduplication)")
        
        # Format: send_message(claim_id, user_id, content)
        result_pkg = await chat_service.send_message(None, user_id, "List all my claims")
        
        agent_msg = result_pkg.get("agent_message", {})
        response_text = agent_msg.get("content", "")
        a2ui = agent_msg.get("a2ui", [])
        
        print(f"\nResponse Text: {response_text}")
        print(f"A2UI Components: {len(a2ui) if a2ui else 0}")
        if a2ui:
            for comp in a2ui:
                print(f"- Type: {comp.get('type')}")
        
        # Assertions for deduplication
        if len(a2ui) > 0:
            print(f"Deduplication Check: text length is {len(response_text)}")
            if len(response_text) > 200:
                print("WARNING: Response text seems too long, deduplication might have failed.")
            else:
                print("SUCCESS: Response text is concise (deduplicated).")
            # Safe access to comp
            comp = a2ui[0]
            if 'columns' in comp:
                print(f"  Columns: {comp['columns']}")
                print(f"  Rows count: {len(comp.get('rows', comp.get('data', [])))}")

    # Cleanup resources to avoid unclosed sessions/engine warnings
    await engine.dispose()
    # Tiny sleep to allow background aiohttp/SSL cleanup to finish before loop closes
    await asyncio.sleep(0.5)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_list_claims())
