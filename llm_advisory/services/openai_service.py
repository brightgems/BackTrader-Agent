"""OpenAI integration service for LLM advisory system"""

import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class OpenAIService:
    """Service for integrating with OpenAI API"""
    
    def __init__(self):
        """Initialize OpenAI client with configuration from environment"""
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.api_token = os.getenv('OPENAI_API_KEY')
        
        if not self.api_token or self.api_token == 'your_OPENAI_API_KEY_here':
            raise ValueError(
                "OPENAI_API_KEY not configured. "
                "Please set OPENAI_API_KEY in your .env file"
            )
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_token
        )
    
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a chat completion using OpenAI API
        
        Args:
            messages: List of message dictionaries with role and content
            model: The model to use for completion
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters for the API call
            
        Returns:
            Dictionary containing the completion response
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return {
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role,
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None
            }
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")
    
    def generate_advisor_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gpt-3.5-turbo",
        **kwargs
    ) -> str:
        """Generate a response for an advisor using OpenAI
        
        Args:
            system_prompt: The system instructions for the advisor
            user_prompt: The user prompt with data and context
            model: The model to use
            **kwargs: Additional parameters
            
        Returns:
            The generated response content
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.create_chat_completion(messages, model=model, **kwargs)
        return response["content"]
    
    def test_connection(self) -> bool:
        """Test the connection to OpenAI API
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Simple test with a small completion
            response = self.create_chat_completion(
                messages=[{"role": "user", "content": "Say 'hello'"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False


# Singleton instance for easier access (will be created on first use)
openai_service = None

def get_openai_service():
    """Get or create the OpenAI service instance"""
    global openai_service
    if openai_service is None:
        openai_service = OpenAIService()
    return openai_service