
import unittest
import json
import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

from app.core.a2ui_converter import A2UIConverter

class TestA2UIExtraction(unittest.TestCase):
    def test_extract_table_from_markdown(self):
        asyncio.run(self._test_async_extraction())

    async def _test_async_extraction(self):
        converter = A2UIConverter()
        
        tool_data = {
            "type": "claims_list",
            "claims": [
                {"id": 1, "policy": "P-123", "claim_type": "AUTO", "status": "DRAFT", "amount": 100.0}
            ]
        }
        
        # Verbose message that should be deduplicated
        agent_text = "I found one claim for you: ID: 1, Policy: P-123, Type: AUTO, Status: DRAFT, Amount: 100. Here are the details in a table."

        print("Testing data-driven conversion + deduplication...")
        clean_text, components = await converter.extract_and_convert(agent_text, data_context=[tool_data])
        
        print(f"Clean text: {clean_text}")
        print(f"Components: {components}")
        
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0]['type'], 'table_card')
        
        # Check if the clean_text is different and more concise than agent_text
        self.assertNotEqual(clean_text, agent_text)
        print(f"Deduplication SUCCESS: Original length {len(agent_text)}, New length {len(clean_text)}")
        
        # Tiny sleep to allow background aiohttp/SSL cleanup to finish
        await asyncio.sleep(0.5)

if __name__ == '__main__':
    unittest.main()
