import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ai_write_x.utils import log
from src.ai_write_x.core.llm_client import LLMClient
from src.ai_write_x.core.direct_llm import OpenAIDirectLLM

class TestAILoggingAndFiltering(unittest.TestCase):
    @patch('src.ai_write_x.core.llm_client.OpenAI')
    @patch('src.ai_write_x.core.llm_client.LLMClient._get_client')
    @patch('src.ai_write_x.core.llm_client.LLMClient._get_current_client')
    def test_llm_client_logging(self, mock_get_current, mock_get, mock_openai):
        # Mocking for LLMClient.chat
        mock_client = MagicMock()
        mock_get_current.return_value = mock_client
        mock_get.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response", tool_calls=None))]
        mock_client.chat.completions.create.return_value = mock_response
        
        client = LLMClient()
        print("\n--- Simulate LLMClient.chat call (with details log) ---")
        result = client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o",
            req_id="test-llm-client"
        )
        print("\n--- Simulate call end ---")
        self.assertEqual(result, "Test response")

    @patch('src.ai_write_x.core.direct_llm.OpenAI')
    def test_direct_llm_parameter_filtering(self, mock_openai):
        # Prepare Mock
        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Filtered response", tool_calls=None))]
        )
        
        llm = OpenAIDirectLLM(
            model="gpt-4o",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            stream=False
        )
        
        # Simulate CrewAI passing extra invalid kwargs
        messages = [{"role": "user", "content": "Hello"}]
        print("\n--- Simulate OpenAIDirectLLM call (with parameter filtering) ---")
        llm.call(messages, from_task="some-task-object", extra_metadata="ignore-me")
        
        # Verify from_task is not in call kwargs
        args, kwargs = mock_instance.chat.completions.create.call_args
        self.assertNotIn('from_task', kwargs)
        self.assertNotIn('extra_metadata', kwargs)
        self.assertEqual(kwargs['model'], "gpt-4o")
        print("\n[OK] Parameter filtering logic verified successfully.")

if __name__ == '__main__':
    unittest.main()
