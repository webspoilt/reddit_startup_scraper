"""
AI Analyzers Package
Contains multiple AI backends for post analysis.

Available Analyzers:
- GeminiClient: Google's Gemini API (cloud, paid)
- GroqAnalyzer: Groq's free API (cloud, very fast, generous free tier)
- OllamaAnalyzer: Local models via Ollama (free, offline)
- HuggingFaceAnalyzer: Hugging Face Inference API (cloud, free tier)

Factory:
- get_analyzer(): Auto-selects best available backend
- AnalyzerFactory: Advanced provider selection and status checking
"""

import os
import logging
from typing import Optional, List
from enum import Enum

from .gemini_client import GeminiClient
from .groq_client import GroqAnalyzer, create_groq_analyzer
from .ollama_client import OllamaAnalyzer, create_ollama_analyzer
from .huggingface_client import HuggingFaceAnalyzer, create_huggingface_analyzer
from .ai_provider import AIProvider

logger = logging.getLogger(__name__)


class AnalyzerFactory:
    """
    Factory for creating AI analyzers with automatic provider selection.
    """

    @staticmethod
    def get_available_providers(config=None) -> List[AIProvider]:
        """
        Get list of available AI providers based on configuration and environment.
        
        Args:
            config: Optional configuration object
            
        Returns:
            List of available AIProvider enums, ordered by preference
        """
        available = []
        
        # Check Groq (fast, free tier)
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            available.append(AIProvider.GROQ)
        
        # Check Ollama (local, free)
        ollama_model = os.getenv("OLLAMA_MODEL", "")
        use_ollama = getattr(config, 'use_ollama', False) if config else False
        if ollama_model or use_ollama:
            available.append(AIProvider.OLLAMA)
        
        # Check HuggingFace (always available, may have rate limits)
        available.append(AIProvider.HUGGINGFACE)
        
        # Check Gemini (paid tier)
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key:
            available.append(AIProvider.GEMINI)
        
        # Keyword fallback is always available
        available.append(AIProvider.KEYWORD)
        
        return available

    @staticmethod
    def create_analyzer(provider: AIProvider, config=None):
        """
        Create an analyzer instance for the specified provider.
        
        Args:
            provider: The AI provider to use
            config: Optional configuration object
            
        Returns:
            Analyzer instance or None if creation fails
        """
        try:
            if provider == AIProvider.GROQ:
                return create_groq_analyzer(config)
            elif provider == AIProvider.OLLAMA:
                return create_ollama_analyzer(config)
            elif provider == AIProvider.HUGGINGFACE:
                return create_huggingface_analyzer(config)
            elif provider == AIProvider.GEMINI:
                return GeminiClient(config)
            elif provider == AIProvider.KEYWORD:
                return None  # Keyword-only mode, no AI analyzer
            else:
                logger.warning(f"Unknown provider: {provider}")
                return None
        except Exception as e:
            logger.warning(f"Failed to create {provider.value} analyzer: {e}")
            return None


def get_analyzer(config=None, provider=None):
    """
    Get the best available AI analyzer.
    
    Args:
        config: Configuration object
        provider: Optional specific provider to use (string or AIProvider enum)
        
    Returns:
        Analyzer instance or None if no analyzer available
    """
    # If specific provider requested
    if provider:
        if isinstance(provider, str):
            try:
                provider = AIProvider(provider.lower())
            except ValueError:
                logger.warning(f"Unknown provider: {provider}")
                provider = None
        
        if provider and provider != AIProvider.KEYWORD:
            analyzer = AnalyzerFactory.create_analyzer(provider, config)
            if analyzer:
                logger.info(f"Using requested provider: {provider.value}")
                return analyzer
            logger.warning(f"Requested provider {provider.value} not available, falling back")
    
    # Auto-select best available provider
    available = AnalyzerFactory.get_available_providers(config)
    
    for prov in available:
        if prov == AIProvider.KEYWORD:
            continue  # Skip keyword-only as last resort
        
        analyzer = AnalyzerFactory.create_analyzer(prov, config)
        if analyzer:
            logger.info(f"Auto-selected provider: {prov.value}")
            return analyzer
    
    logger.warning("No AI analyzer available, using keyword-only mode")
    return None


__all__ = [
    # Main client classes
    'GeminiClient',
    'GroqAnalyzer',
    'OllamaAnalyzer',
    'HuggingFaceAnalyzer',
    # Factory functions
    'create_groq_analyzer',
    'create_ollama_analyzer',
    'create_huggingface_analyzer',
    'get_analyzer',
    'AnalyzerFactory',
    'AIProvider',
]
