"""LLM Service Adapter for unified LLM provider integration"""

import os
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMService(ABC):
    """Abstract base class for LLM services"""
    
    @abstractmethod
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a chat completion"""
        pass
    
    @abstractmethod
    def generate_advisor_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        **kwargs
    ) -> str:
        """Generate a response for an advisor"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the service"""
        pass


class LLMServiceAdapter:
    """Adapter for switching between different LLM providers"""
    
    def __init__(self, provider: str = None):
        """Initialize with a specific provider or auto-detect"""
        self.provider = provider or self._auto_detect_provider()
        self.service = self._create_service(self.provider)
    
    def _auto_detect_provider(self) -> str:
        """Auto-detect the best available provider"""
        # Check environment variables for configuration
        if os.getenv('OPENAI_API_TOKEN'):
            return 'openai'
        elif self._test_ollama_connection():
            return 'ollama'
        else:
            # Default to ollama for development
            return 'ollama'
    
    def _test_ollama_connection(self) -> bool:
        """Test if Ollama is available"""
        try:
            import requests
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _create_service(self, provider: str):
        """Create the appropriate service instance"""
        if provider == 'openai':
            from .openai_service import get_openai_service
            return get_openai_service()
        elif provider == 'ollama':
            from .ollama_service import get_ollama_service
            return get_ollama_service()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create chat completion using the configured provider"""
        if model is None:
            model = self._get_default_model()
        
        return self.service.create_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def generate_advisor_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        **kwargs
    ) -> str:
        """Generate advisor response using the configured provider"""
        if model is None:
            model = self._get_default_model()
        
        return self.service.generate_advisor_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            **kwargs
        )
    
    def _get_default_model(self) -> str:
        """Get default model based on provider"""
        if self.provider == 'openai':
            return os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        elif self.provider == 'ollama':
            return os.getenv('OLLAMA_MODEL', 'qwen3-vl')
        else:
            return 'default'
    
    def test_connection(self) -> bool:
        """Test connection to the configured service"""
        return self.service.test_connection()
    
    def switch_provider(self, provider: str):
        """Switch to a different provider"""
        self.provider = provider
        self.service = self._create_service(provider)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = []
        
        # Check OpenAI availability
        if os.getenv('OPENAI_API_TOKEN'):
            providers.append('openai')
        
        # Check Ollama availability
        if self._test_ollama_connection():
            providers.append('ollama')
        
        return providers


# Global adapter instance for easy access
llm_adapter = None

def get_llm_adapter(provider: str = None):
    """Get or create the global LLM adapter"""
    global llm_adapter
    if llm_adapter is None:
        llm_adapter = LLMServiceAdapter(provider)
    elif provider is not None and provider != llm_adapter.provider:
        llm_adapter.switch_provider(provider)
    
    return llm_adapter
