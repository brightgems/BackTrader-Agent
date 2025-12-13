"""Ollama integration service for LLM advisory system"""

import os
import requests
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class OllamaService:
    """Service for integrating with local Ollama API"""
    
    def __init__(self):
        """Initialize Ollama client with configuration from environment"""
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'qwen3-vl')
        
        # Test connection on initialization
        if not self.test_connection():
            print(f"警告: 无法连接到 Ollama 服务 ({self.base_url})")
            print("请确保 Ollama 已安装并运行，或者检查 OLLAMA_BASE_URL 配置")
    
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a chat completion using Ollama API
        
        Args:
            messages: List of message dictionaries with role and content
            model: The model to use for completion (defaults to configured model)
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters for the API call
            
        Returns:
            Dictionary containing the completion response
        """
        try:
            # Use configured model if not specified
            if model is None:
                model = self.model
                
            # Prepare messages for Ollama API format
            # Ollama uses a simpler format than OpenAI
            prompt = self._format_messages_for_ollama(messages)
            
            # Prepare request data
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or 500,  # Default to 500 tokens
                }
            }
            
            # Add any additional options
            if kwargs:
                data["options"].update(kwargs)
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=60  # 60 second timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            return {
                "content": result.get("response", ""),
                "role": "assistant",  # Ollama doesn't return role
                "finish_reason": "stop",  # Ollama doesn't provide finish reason
                "usage": {
                    "prompt_tokens": len(prompt.split()),  # Approximate
                    "completion_tokens": len(result.get("response", "").split()),  # Approximate
                    "total_tokens": len(prompt.split()) + len(result.get("response", "").split())
                }
            }
            
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接到 Ollama 服务: {self.base_url}")
        except Exception as e:
            raise Exception(f"Ollama API 调用失败: {str(e)}")
    
    def _format_messages_for_ollama(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to Ollama prompt format"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"系统指令: {content}")
            elif role == "user":
                prompt_parts.append(f"用户输入: {content}")
            elif role == "assistant":
                prompt_parts.append(f"助手回复: {content}")
            else:
                prompt_parts.append(content)
        
        return "\n\n".join(prompt_parts)
    
    def generate_advisor_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        **kwargs
    ) -> str:
        """Generate a response for an advisor using Ollama
        
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
        """Test the connection to Ollama API
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models
        
        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []


# Singleton instance for easier access
ollama_service = None

def get_ollama_service():
    """Get or create the Ollama service instance"""
    global ollama_service
    if ollama_service is None:
        ollama_service = OllamaService()
    return ollama_service


# Service registry for easy switching between providers
class LLMServiceRegistry:
    """Registry for managing different LLM service providers"""
    
    def __init__(self):
        self.services = {}
    
    def register_service(self, name: str, service_class, getter_function):
        """Register a new LLM service"""
        self.services[name] = {
            'class': service_class,
            'getter': getter_function
        }
    
    def get_service(self, name: str):
        """Get a service by name"""
        if name not in self.services:
            raise ValueError(f"Unknown service: {name}")
        return self.services[name]['getter']()
    
    def list_services(self):
        """List all registered services"""
        return list(self.services.keys())


# Global service registry
service_registry = LLMServiceRegistry()


def register_default_services():
    """Register the default LLM services"""
    try:
        from .openai_service import get_openai_service
        service_registry.register_service('openai', 'OpenAIService', get_openai_service)
    except ImportError:
        print("OpenAI service not available")
    
    service_registry.register_service('ollama', 'OllamaService', get_ollama_service)


# Register default services on module import
register_default_services()