"""Test OpenAI integration for llm_advisory module"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from llm_advisory.llm_advisor import LLMAdvisor, LLMAdvisorUpdateStateData, LLMMessage
# Import with handling for missing configuration
try:
    from llm_advisory.services.openai_service import OpenAIService
    OPENAI_SERVICE_AVAILABLE = True
except ValueError as e:
    if "OPENAI_API_TOKEN not configured" in str(e):
        OPENAI_SERVICE_AVAILABLE = False
        OpenAIService = None
    else:
        raise
except Exception:
    OPENAI_SERVICE_AVAILABLE = False
    OpenAIService = None


class TestOpenAIIntegration(unittest.TestCase):
    """Test OpenAI service integration"""
    
    def test_openai_service_initialization(self):
        """Test OpenAIService initialization"""
        # Test with mock environment variables
        with patch.dict(os.environ, {
            'OPENAI_BASE_URL': 'https://api.openai.com/v1',
            'OPENAI_API_TOKEN': 'test_token'
        }):
            service = OpenAIService()
            self.assertEqual(service.base_url, 'https://api.openai.com/v1')
            self.assertEqual(service.api_token, 'test_token')
    
    def test_openai_service_missing_token(self):
        """Test OpenAIService with missing API token"""
        with patch.dict(os.environ, {
            'OPENAI_BASE_URL': 'https://api.openai.com/v1',
            'OPENAI_API_TOKEN': 'your_openai_api_token_here'
        }):
            with self.assertRaises(ValueError):
                OpenAIService()
    
    @patch('llm_advisory.services.openai_service.OpenAI')
    def test_chat_completion_mock(self, mock_openai):
        """Test chat completion with mocked OpenAI client"""
        # Mock the response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Create service with test config
        with patch.dict(os.environ, {
            'OPENAI_BASE_URL': 'https://api.openai.com/v1',
            'OPENAI_API_TOKEN': 'test_token'
        }):
            service = OpenAIService()
            service.client = mock_client
            
            # Test chat completion
            messages = [{"role": "user", "content": "Hello"}]
            response = service.create_chat_completion(messages)
            
            self.assertEqual(response["content"], "Test response")
            self.assertEqual(response["role"], "assistant")
            mock_client.chat.completions.create.assert_called_once()
    
    @patch('llm_advisory.llm_advisor.openai_service')
    def test_llm_advisor_openai_integration(self, mock_openai_service):
        """Test LLMAdvisor integration with OpenAI service"""
        # Mock the OpenAI service
        mock_response = {"content": "AI generated response"}
        mock_openai_service.generate_advisor_response.return_value = "AI generated response"
        mock_openai_service.test_connection.return_value = True
        
        # Create advisor instance
        advisor = LLMAdvisor()
        advisor.advisor_instructions = "You are a trading advisor."
        advisor.advisor_prompt = "Analyze this data"
        advisor.advisor_messages_input.advisor_data = "Test data"
        
        # Test state update
        state = LLMAdvisorUpdateStateData(
            messages=[LLMMessage(role="user", content="Test message")],
            data=[],
            metadata={}
        )
        
        result = advisor._update_state(state)
        
        # Verify the response contains AI content
        self.assertEqual(len(result.messages), 2)
        self.assertIn("AI generated response", result.messages[1].content)
        
    def test_openai_fallback_behavior(self):
        """Test fallback behavior when OpenAI is not available"""
        # Create advisor instance
        advisor = LLMAdvisor()
        advisor.advisor_instructions = "You are a trading advisor."
        advisor.advisor_prompt = "Analyze this data"
        advisor.advisor_messages_input.advisor_data = "Test data"
        
        # Mock OpenAI not being available
        with patch('llm_advisory.llm_advisor.OPENAI_AVAILABLE', False):
            state = LLMAdvisorUpdateStateData(
                messages=[LLMMessage(role="user", content="Test message")],
                data=[],
                metadata={}
            )
            
            result = advisor._update_state(state)
            
            # Should use fallback response
            self.assertIn("OpenAI service not configured", result.messages[1].content)


class TestOpenAIConfiguration(unittest.TestCase):
    """Test OpenAI configuration and environment setup"""
    
    def test_env_file_configuration(self):
        """Test that .env file contains required OpenAI configuration"""
        env_path = os.path.join(os.path.dirname(__file__), '../../../.env')
        
        self.assertTrue(os.path.exists(env_path), ".env file should exist")
        
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        # Check for required configuration
        self.assertIn("OPENAI_BASE_URL", env_content)
        self.assertIn("OPENAI_API_TOKEN", env_content)
        self.assertNotIn("your_openai_api_token_here", env_content, 
                        "Please replace placeholder with actual API token")


if __name__ == '__main__':
    unittest.main()