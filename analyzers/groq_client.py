"""
Groq AI Analyzer
Uses Groq's free API for fast AI inference.
Groq offers extremely fast inference with generous free tier limits.

Get API key: https://console.groq.com/
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PostAnalysis:
    """Data class representing AI analysis of a Reddit post."""
    original_title: str
    original_body: str
    subreddit: str
    post_url: str
    core_problem_summary: str
    target_audience: str
    startup_idea: str
    startup_type: str
    estimated_complexity: str
    potential_market_size: str
    confidence_score: float
    model_used: str
    analysis_timestamp: str
    tags: list = None  # Tags like ["frustration", "india", "b2b"]
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_title": self.original_title,
            "original_body": self.original_body,
            "subreddit": self.subreddit,
            "post_url": self.post_url,
            "core_problem_summary": self.core_problem_summary,
            "target_audience": self.target_audience,
            "startup_idea": self.startup_idea,
            "startup_type": self.startup_type,
            "estimated_complexity": self.estimated_complexity,
            "potential_market_size": self.potential_market_size,
            "confidence_score": self.confidence_score,
            "model_used": self.model_used,
            "analysis_timestamp": self.analysis_timestamp,
            "tags": self.tags,
        }

    def to_markdown(self) -> str:
        return f"""
### Original Post
**Title:** {self.original_title}

**Source:** [Reddit Link]({self.post_url})

**Subreddit:** r/{self.subreddit}

---

### Problem Analysis
**Core Problem:** {self.core_problem_summary}

**Target Audience:** {self.target_audience}

---

### Startup Idea
**Suggested Solution:** {self.startup_idea}

**Type:** {self.startup_type}

**Complexity:** {self.estimated_complexity}

**Market Size:** {self.potential_market_size}

**Confidence Score:** {self.confidence_score:.2f}
"""


class GroqAnalyzer:
    """
    AI Analyzer using Groq's free API.
    
    Groq offers:
    - Free tier with generous rate limits
    - Extremely fast inference (100+ tokens/second)
    - Models: Llama 3.1, Mixtral, Gemma
    
    Get API key: https://console.groq.com/
    """

    # Available models on Groq (ordered by preference)
    AVAILABLE_MODELS = [
        "llama-3.3-70b-versatile",     # Latest Llama, best quality
        "llama-3.1-8b-instant",        # Fast, efficient model
        "mixtral-8x7b-32768",          # Mixtral MoE
        "gemma-7b-it",                 # Google's model
    ]

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the Groq analyzer.
        
        Args:
            api_key: Groq API key (optional, reads from GROQ_API_KEY env var)
            model: Model to use (auto-selects best available if None)
        """
        self._api_key = api_key
        self._model = model
        self._client = None
        self._selected_model = None

        # Try to import groq
        try:
            from groq import Groq as GroqClient
            self._GroqClient = GroqClient
        except ImportError:
            raise ImportError(
                "Groq package not installed. Install with: pip install groq"
            )

        # Load API key from environment if not provided
        if not self._api_key:
            import os
            self._api_key = os.getenv("GROQ_API_KEY", "")

        if not self._api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY in .env or pass it to constructor."
            )

        # Initialize client
        self._client = self._GroqClient(api_key=self._api_key)

        # Select model
        self._selected_model = self._select_model()

        logger.info(f"Groq analyzer initialized with model: {self._selected_model}")

    def _select_model(self) -> str:
        """Select the best available model."""
        if self._model and self._model in self.AVAILABLE_MODELS:
            return self._model

        # Try models in order until one works
        for model_name in self.AVAILABLE_MODELS:
            try:
                response = self._client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10,
                )
                if response:
                    logger.info(f"Selected model: {model_name}")
                    return model_name
            except Exception as e:
                logger.debug(f"Model {model_name} not available: {e}")
                continue

        raise ValueError("No available Groq models found")

    def _create_prompt(self, title: str, body: str) -> List[Dict[str, str]]:
        """Create the chat messages for analysis."""
        system_prompt = """You are an expert startup consultant and business analyst. 
Your task is to analyze Reddit posts where people discuss problems, frustrations, or needs.

For each post, provide a structured JSON response with these fields:
1. core_problem_summary: Clear 1-2 sentence summary of the pain point
2. target_audience: Specific group experiencing this problem
3. startup_idea: Specific Micro-SaaS or business idea to solve it
4. startup_type: "Micro-SaaS", "Service", "Physical Product", "Marketplace", or "Content/SaaS Hybrid"
5. estimated_complexity: "Low", "Medium", or "High"
6. potential_market_size: "Small", "Medium", or "Large"
7. confidence_score: Float between 0.0 and 1.0
8. tags: Array of relevant tags from these categories:
   - Sentiment: "frustration", "complaint", "rant", "question", "seeking_advice", "idea_validation"
   - Region (if mentioned): "india", "us", "uk", "europe", "asia", "global"
   - Problem type: "b2b", "b2c", "technical", "financial", "productivity", "automation", "communication"
   - Industry: "saas", "ecommerce", "freelance", "agency", "fintech", "edtech", "healthcare"
   Pick 3-5 most relevant tags.

Respond with valid JSON only, no markdown formatting."""

        user_content = f"Title: {title}\n\nContent: {body}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the AI response into a dictionary."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            try:
                # Try to extract JSON from markdown code blocks
                cleaned = response_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                return json.loads(cleaned.strip())
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Groq response as JSON")
                return None

    def analyze_post(self, title: str, body: str, subreddit: str, post_url: str) -> Optional[PostAnalysis]:
        """Analyze a single post."""
        try:
            messages = self._create_prompt(title, body)

            response = self._client.chat.completions.create(
                model=self._selected_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )

            response_text = response.choices[0].message.content

            analysis_data = self._parse_response(response_text)

            if analysis_data is None:
                logger.warning(f"Failed to parse response for: {title[:50]}...")
                return None

            return PostAnalysis(
                original_title=title,
                original_body=body,
                subreddit=subreddit,
                post_url=post_url,
                core_problem_summary=analysis_data.get("core_problem_summary", "Unable to identify problem"),
                target_audience=analysis_data.get("target_audience", "Unknown audience"),
                startup_idea=analysis_data.get("startup_idea", "No idea generated"),
                startup_type=analysis_data.get("startup_type", "Unknown"),
                estimated_complexity=analysis_data.get("estimated_complexity", "Unknown"),
                potential_market_size=analysis_data.get("potential_market_size", "Unknown"),
                confidence_score=analysis_data.get("confidence_score", 0.5),
                model_used=f"groq/{self._selected_model}",
                analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                tags=analysis_data.get("tags", []),
            )

        except Exception as e:
            logger.error(f"Error analyzing post with Groq: {e}")
            return None

    def analyze_posts_batch(self, posts: list, progress_callback=None) -> List[PostAnalysis]:
        """Analyze multiple posts."""
        analyses: List[PostAnalysis] = []
        total = len(posts)

        for i, post in enumerate(posts):
            if progress_callback:
                progress_callback(i + 1, total)

            analysis = self.analyze_post(
                title=post.title,
                body=post.body,
                subreddit=post.subreddit,
                post_url=post.url,
            )

            if analysis:
                analyses.append(analysis)

            # Rate limiting (Groq is fast but be respectful)
            if i < total - 1:
                time.sleep(0.5)

        return analyses

    def test_connection(self) -> bool:
        """Test the Groq API connection."""
        try:
            response = self._client.chat.completions.create(
                model=self._selected_model,
                messages=[{"role": "user", "content": "Respond with 'OK'."}],
                max_tokens=10,
            )
            return "OK" in response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq connection test failed: {e}")
            return False

    @property
    def model_name(self) -> str:
        """Return the selected model name."""
        return self._selected_model


def create_groq_analyzer(config=None) -> Optional[GroqAnalyzer]:
    """Factory function to create Groq analyzer from config."""
    try:
        import os
        api_key = os.getenv("GROQ_API_KEY", "")
        
        if not api_key:
            logger.debug("GROQ_API_KEY not found in environment")
            return None
        
        model = getattr(config, 'groq_model', None) if config else None
        
        return GroqAnalyzer(api_key=api_key, model=model)
    except Exception as e:
        logger.warning(f"Failed to create Groq analyzer: {e}")
        return None
