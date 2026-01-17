"""
AI Provider Enum
Defines available AI providers for the analyzer factory.
"""

from enum import Enum


class AIProvider(Enum):
    """Available AI providers."""
    GROQ = "groq"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    GEMINI = "gemini"
    KEYWORD = "keyword"  # Fallback to keyword-only analysis


__all__ = ['AIProvider']
