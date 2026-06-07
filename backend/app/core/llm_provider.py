# app/core/llm_provider.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_community.llms.ollama import Ollama
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import structlog
from app.config import settings

logger = structlog.get_logger()

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def chat(self, messages: List[BaseMessage], **kwargs) -> str:
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        pass

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.client = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = await self.client.agenerate([[HumanMessage(content=prompt)]])
            return response.generations[0][0].text
        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e))
            raise
    
    async def chat(self, messages: List[BaseMessage], **kwargs) -> str:
        try:
            response = await self.client.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error("OpenAI chat failed", error=str(e))
            raise
    
    def get_token_count(self, text: str) -> int:
        # Approximate token count (1 token ≈ 4 characters)
        return len(text) // 4

class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        # Implementation for Claude API
        pass
    
    async def generate(self, prompt: str, **kwargs) -> str:
        # Implement Anthropic API calls
        pass
    
    async def chat(self, messages: List[BaseMessage], **kwargs) -> str:
        # Implement Anthropic chat
        pass
    
    def get_token_count(self, text: str) -> int:
        return len(text) // 4

class LocalLLMProvider(BaseLLMProvider):
    def __init__(self):
        self.client = Ollama(model="llama3")
    
    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = await self.client.agenerate([prompt])
            return response.generations[0][0].text
        except Exception as e:
            logger.error("Local LLM generation failed", error=str(e))
            raise
    
    async def chat(self, messages: List[BaseMessage], **kwargs) -> str:
        # Convert messages to single prompt for local models
        prompt = "\n".join([msg.content for msg in messages])
        return await self.generate(prompt)
    
    def get_token_count(self, text: str) -> int:
        return len(text) // 4

class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(provider_type: str = None) -> BaseLLMProvider:
        provider_type = provider_type or settings.LLM_PROVIDER
        
        if provider_type == "openai":
            return OpenAIProvider()
        elif provider_type == "anthropic":
            return AnthropicProvider()
        elif provider_type == "local":
            return LocalLLMProvider()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

class LLMManager:
    """Manages LLM interactions with rate limiting and caching"""
    
    def __init__(self):
        self.provider = LLMProviderFactory.create_provider()
        self.request_count = 0
        self.cache = {}
    
    async def generate_with_cache(self, prompt: str, cache_key: str = None, **kwargs) -> str:
        """Generate with optional caching"""
        if cache_key and cache_key in self.cache:
            logger.info("Cache hit for LLM request", cache_key=cache_key)
            return self.cache[cache_key]
        
        response = await self.provider.generate(prompt, **kwargs)
        
        if cache_key:
            self.cache[cache_key] = response
        
        self.request_count += 1
        logger.info("LLM request completed", request_count=self.request_count)
        
        return response
    
    async def chat_with_context(self, messages: List[BaseMessage], **kwargs) -> str:
        """Chat with conversation context"""
        return await self.provider.chat(messages, **kwargs)

# Global LLM manager instance
llm_manager = LLMManager()