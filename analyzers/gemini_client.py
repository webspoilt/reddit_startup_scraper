"""
Gemini AI Analysis Module
Handles all interactions with the Google Gemini API for post analysis.
Supports both the new google.genai package and the stable google-generativeai package.
Includes robust rate limit handling with exponential backoff.
"""

import json
import logging
import time
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Rate limit configuration for Gemini Free Tier
RATE_LIMIT_CONFIG = {
    "initial_delay": 2.0,        # Initial delay in seconds after rate limit
    "max_delay": 60.0,           # Maximum delay between retries
    "max_retries": 5,            # Maximum number of retries for rate limit
    "backoff_multiplier": 2.0,   # Exponential backoff multiplier
    "jitter": True,              # Add random jitter to prevent thundering herd
    "request_delay": 2.0,        # Delay between successful requests (seconds)
}


@dataclass
class PostAnalysis:
    """
    Data class representing the AI analysis of a Reddit post.
    """
    original_title: str
    original_body: str
    subreddit: str
    post_url: str

    # Analysis results
    core_problem_summary: str
    target_audience: str
    startup_idea: str
    startup_type: str
    estimated_complexity: str
    potential_market_size: str
    confidence_score: float

    # Metadata
    model_used: str
    analysis_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easier processing."""
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
        }

    def to_markdown(self) -> str:
        """Generate a Markdown representation of the analysis."""
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

---
"""


class GeminiClient:
    """
    Client for analyzing Reddit posts using Google Gemini AI.
    Supports both the new google.genai and stable google-generativeai packages.
    Includes robust rate limit handling with exponential backoff.
    """

    # Model names ordered by preference (most recent/stable first)
    # Using the newer gemini-2.0 models and falling back to 1.5 series
    AVAILABLE_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ]

    def __init__(self, config=None, rate_limit_config: Dict[str, float] = None):
        """
        Initialize the Gemini client with API key from config.

        Args:
            config: Configuration object. If None, imports from config module.
            rate_limit_config: Optional custom rate limit configuration.
                               Defaults to RATE_LIMIT_CONFIG if not provided.
        """
        if config is None:
            from config import Config
            config = Config()

        self._config = config
        self.model = None
        self._using_new_api = False
        self._genai = None
        self._client = None

        # Use provided config or defaults
        self._rate_limit_config = RATE_LIMIT_CONFIG.copy()
        if rate_limit_config:
            self._rate_limit_config.update(rate_limit_config)

        if not config.gemini_credentials_set:
            raise ValueError(
                "Gemini API key not configured. "
                "Please set GEMINI_API_KEY in .env file."
            )

        logger.info(f"Initializing Gemini client with API key: {config.gemini_api_key[:10]}...")

        # Try the stable google-generativeai package first (more reliable)
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.gemini_api_key)
            self._using_new_api = False
            self._genai = genai
            logger.info("Using google-generativeai package (stable)")
        except ImportError:
            # Try the newer google.genai package
            try:
                from google import genai
                self._using_new_api = True
                self._client = genai.Client(api_key=config.gemini_api_key)
                logger.info("Using google.genai package (newer)")
            except ImportError:
                logger.warning("No Gemini API package found. Gemini features will be disabled.")
                self._genai = None
                self._client = None


        if self._genai or self._client:
            # Try to find a working model with better error handling
            self.model = self._find_working_model()
            if self.model is None:
                logger.warning("No available Gemini model found.")
        else:
            self.model = None

        # System prompt for analyzing startup pain points
        self.system_prompt = """You are an expert startup consultant and business analyst. Your task is to analyze Reddit posts where people discuss problems, frustrations, or needs.

For each post, provide a structured analysis in JSON format with the following fields:

1. **core_problem_summary**: A clear, concise 1-2 sentence summary of the core pain point or problem being discussed.

2. **target_audience**: Identify the specific group of people who experience this problem. Be as specific as possible.

3. **startup_idea**: Propose a specific Micro-SaaS or service-based business idea that could solve this problem.

4. **startup_type**: Classify the idea as "Micro-SaaS", "Service", "Physical Product", "Marketplace", or "Content/SaaS Hybrid".

5. **estimated_complexity**: Rate as "Low", "Medium", or "High".

6. **potential_market_size**: Estimate as "Small", "Medium", or "Large".

7. **confidence_score**: A float between 0.0 and 1.0.

Always respond with valid JSON only. Do not include markdown formatting or additional text."""

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error."""
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Check for common rate limit indicators
        rate_limit_indicators = [
            "429",           # HTTP 429 Too Many Requests
            "rate limit",    # Rate limit in error message
            "too many",      # "Too many requests"
            "resource has",  # "resource has been exhausted"
            "quota",         # Quota exceeded
            "rate exceeded", # Rate exceeded
        ]

        return any(indicator in error_str for indicator in rate_limit_indicators)

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Current retry attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        config = self._rate_limit_config

        # Exponential backoff: initial_delay * (multiplier ^ attempt)
        delay = config["initial_delay"] * (config["backoff_multiplier"] ** attempt)

        # Cap at max delay
        delay = min(delay, config["max_delay"])

        # Add jitter if enabled (prevents thundering herd)
        if config["jitter"]:
            jitter_range = delay * 0.1  # 10% jitter
            delay = delay + random.uniform(-jitter_range, jitter_range)

        # Ensure delay is positive
        delay = max(0.1, delay)

        return delay

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if we should retry based on error type and attempt count."""
        if attempt >= self._rate_limit_config["max_retries"]:
            return False

        if self._is_rate_limit_error(error):
            return True

        return False

    def _find_working_model(self) -> Optional[str]:
        """Find the first available working model with proper error handling."""
        for model_name in self.AVAILABLE_MODELS:
            try:
                logger.debug(f"Testing model: {model_name}")

                if self._using_new_api:
                    # Test the model with the new API
                    response = self._client.models.generate_content(
                        model=model_name,
                        contents="Hi",
                    )
                else:
                    # Test with stable API
                    model = self._genai.GenerativeModel(model_name)
                    response = model.generate_content("Hi")

                # Verify we got a valid response
                response_text = ""
                if hasattr(response, 'text'):
                    response_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))

                if response_text and len(response_text.strip()) > 0:
                    logger.info(f"✓ Found working model: {model_name}")
                    return model_name
                else:
                    logger.debug(f"Model {model_name} returned empty response")

            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__

                # Log the actual error for debugging
                logger.debug(f"Model {model_name} error [{error_type}]: {e}")

                # Check for specific error types
                if "400" in error_str or "bad request" in error_str or "invalid" in error_str:
                    logger.warning(f"API key may be invalid for model {model_name}")
                elif "429" in error_str or "rate limit" in error_str:
                    logger.warning(f"Rate limited. Waiting before trying next model...")
                    time.sleep(2)
                elif "404" in error_str or "not found" in error_str:
                    logger.debug(f"Model {model_name} not available")
                elif "api key" in error_str:
                    logger.error("API key is invalid or missing required permissions")
                    # Continue to try other models
                else:
                    # Log unknown errors but continue trying
                    logger.debug(f"Unknown error with {model_name}: {error_type}")

                continue

        return None

    def _analyze_with_retry(self, title: str, body: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a post with automatic retry on rate limit errors.

        Uses exponential backoff to handle rate limits gracefully.
        """
        content = f"Title: {title}\n\nContent: {body}"

        attempt = 0
        last_error = None

        while attempt <= self._rate_limit_config["max_retries"]:
            try:
                if self._using_new_api:
                    # Use new API
                    response = self._client.models.generate_content(
                        model=self.model,
                        contents=f"{self.system_prompt}\n\n{content}",
                    )

                    # Get response text
                    response_text = ""
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
                else:
                    # Use stable API
                    model = self._genai.GenerativeModel(self.model)
                    response = model.generate_content(
                        contents=f"{self.system_prompt}\n\n{content}",
                        generation_config={
                            "temperature": 0.7,
                            "response_mime_type": "application/json",
                        }
                    )

                    response_text = ""
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'parts') and response.parts:
                        response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))

                return self._parse_response(response_text)

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if self._is_rate_limit_error(e):
                    if attempt < self._rate_limit_config["max_retries"]:
                        delay = self._calculate_backoff_delay(attempt)
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{self._rate_limit_config['max_retries']}). "
                            f"Waiting {delay:.1f}s before retry..."
                        )
                        time.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        logger.error(
                            f"Rate limit exceeded after {self._rate_limit_config['max_retries']} retries. "
                            f"Please wait a few minutes and try again."
                        )
                        return None
                else:
                    # Non-rate-limit error, log and return None
                    logger.error(f"API error: {e}")
                    return None

        # If we exhausted retries
        if last_error:
            logger.error(f"Failed after {self._rate_limit_config['max_retries']} retries: {last_error}")

        return None

    def _analyze_with_new_api(self, title: str, body: str) -> Optional[Dict[str, Any]]:
        """Analyze using the new google.genai API."""
        content = f"Title: {title}\n\nContent: {body}"

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=f"{self.system_prompt}\n\n{content}",
            )

            # Get response text
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))

            return self._parse_response(response_text)

        except Exception as e:
            logger.error(f"Error with new API: {e}")
            return None

    def _analyze_with_old_api(self, title: str, body: str) -> Optional[Dict[str, Any]]:
        """Analyze using the stable google-generativeai API."""
        content = f"Title: {title}\n\nContent: {body}"

        try:
            model = self._genai.GenerativeModel(self.model)
            response = model.generate_content(
                contents=f"{self.system_prompt}\n\n{content}",
                generation_config={
                    "temperature": 0.7,
                    "response_mime_type": "application/json",
                }
            )

            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'parts') and response.parts:
                response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))

            return self._parse_response(response_text)

        except Exception as e:
            logger.error(f"Error with old API: {e}")
            return None

    def analyze_post(self, title: str, body: str, subreddit: str, post_url: str) -> Optional[PostAnalysis]:
        """
        Analyze a single Reddit post using Gemini AI.
        Includes automatic retry on rate limit errors.
        """
        try:
            # Use retry-enabled analysis method
            analysis_data = self._analyze_with_retry(title, body)

            if analysis_data is None:
                logger.warning(f"Failed to analyze post (rate limited or error): {title[:50]}...")
                return None

            analysis = PostAnalysis(
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
                model_used=self.model,
                analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

            logger.info(f"Successfully analyzed post: {title[:50]}...")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing post with Gemini: {e}")
            return None

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the Gemini response into a dictionary."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            try:
                cleaned = response_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                return json.loads(cleaned.strip())
            except json.JSONDecodeError:
                logger.error(f"Failed to parse response as JSON")
                return None

    def analyze_posts_batch(self, posts: list, progress_callback=None) -> List[PostAnalysis]:
        """
        Analyze multiple posts with rate limit handling.

        Includes delays between requests and automatic retry on rate limits.
        """
        analyses: List[PostAnalysis] = []
        total = len(posts)

        for i, post in enumerate(posts):
            if progress_callback:
                progress_callback(i + 1, total)

            # Add delay between requests (helps prevent rate limiting)
            if i > 0:
                delay = self._rate_limit_config["request_delay"]
                # Add slight random variation to prevent synchronized requests
                delay += random.uniform(-0.5, 0.5)
                delay = max(0.5, delay)  # Ensure minimum delay
                logger.debug(f"Waiting {delay:.1f}s before next request...")
                time.sleep(delay)

            analysis = self.analyze_post(
                title=post.title,
                body=post.body,
                subreddit=post.subreddit,
                post_url=post.url,
            )

            if analysis:
                analyses.append(analysis)
            else:
                # Log which post failed
                logger.warning(f"Skipping post {i+1}/{total} due to analysis failure: {post.title[:50]}...")

        return analyses

    def test_connection(self) -> bool:
        """Test the Gemini API connection."""
        try:
            if self.model is None:
                return False

            if self._using_new_api:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents="Test. Respond with 'OK'.",
                )
                response_text = ""
                if hasattr(response, 'text'):
                    response_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        response_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
            else:
                model = self._genai.GenerativeModel(self.model)
                response = model.generate_content("Test. Respond with 'OK'.")
                response_text = ""
                if hasattr(response, 'text'):
                    response_text = response.text
                elif hasattr(response, 'parts') and response.parts:
                    response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))

            return "OK" in response_text.upper() or len(response_text) > 0
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
