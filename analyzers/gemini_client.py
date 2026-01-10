"""
Gemini AI Analysis Module
Handles all interactions with the Google Gemini API for post analysis.
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


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
    startup_type: str  # Micro-SaaS, Service, Product, etc.
    estimated_complexity: str  # Low, Medium, High
    potential_market_size: str  # Small, Medium, Large
    confidence_score: float  # 0.0 to 1.0

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
    """

    def __init__(self, config=None):
        """
        Initialize the Gemini client with API key from config.

        Args:
            config: Configuration object. If None, imports from config module.
        """
        if config is None:
            from config import Config
            config = Config()

        self._config = config

        if not config.gemini_credentials_set:
            raise ValueError(
                "Gemini API key not configured. "
                "Please set GEMINI_API_KEY in .env file."
            )

        genai.configure(api_key=config.gemini_api_key)

        # Use Gemini 1.5 Flash for speed and cost efficiency
        self.model = genai.GenerativeModel("gemini-1.5-flash")

        # Generation configuration for consistent output
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 1024,
            "response_mime_type": "application/json",
        }

        # System prompt for analyzing startup pain points
        self.system_prompt = """You are an expert startup consultant and business analyst. Your task is to analyze Reddit posts where people discuss problems, frustrations, or needs.

For each post, provide a structured analysis in JSON format with the following fields:

1. **core_problem_summary**: A clear, concise 1-2 sentence summary of the core pain point or problem being discussed.

2. **target_audience**: Identify the specific group of people who experience this problem. Be as specific as possible (e.g., "freelance graphic designers working with remote clients" instead of just "freelancers").

3. **startup_idea**: Propose a specific Micro-SaaS or service-based business idea that could solve this problem. Be concrete and actionable.

4. **startup_type**: Classify the idea as "Micro-SaaS", "Service", "Physical Product", "Marketplace", or "Content/SaaS Hybrid".

5. **estimated_complexity**: Rate the implementation complexity as "Low", "Medium", or "High" based on technical requirements, market complexity, and resource needs.

6. **potential_market_size**: Estimate the market size as "Small", "Medium", or "Large" based on how common the problem appears to be.

7. **confidence_score**: A float between 0.0 and 1.0 indicating your confidence in this analysis based on the clarity and specificity of the original post.

Always respond with valid JSON only. Do not include any markdown formatting or additional text outside the JSON object."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def analyze_post(self, title: str, body: str, subreddit: str, post_url: str) -> Optional[PostAnalysis]:
        """
        Analyze a single Reddit post using Gemini AI.

        Args:
            title: The title of the Reddit post.
            body: The body/content of the Reddit post.
            subreddit: The subreddit where the post was made.
            post_url: The URL of the Reddit post.

        Returns:
            PostAnalysis object with AI-generated insights, or None if analysis fails.
        """
        # Combine title and body for analysis
        content = f"Title: {title}\n\nContent: {body}"

        try:
            # Start chat session with system prompt
            chat_session = self.model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": [self.system_prompt],
                    }
                ]
            )

            # Send the post content for analysis
            response = chat_session.send_message(
                content,
                generation_config=self.generation_config,
            )

            # Get the response text safely
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'parts') and response.parts:
                response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            else:
                response_text = str(response)

            # Parse the JSON response
            analysis_data = self._parse_response(response_text)

            if analysis_data is None:
                logger.warning(f"Failed to parse Gemini response for post: {title[:50]}...")
                return None

            # Create PostAnalysis object
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
                model_used="gemini-1.5-flash",
                analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

            logger.info(f"Successfully analyzed post: {title[:50]}...")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing post with Gemini: {e}")
            raise

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the Gemini response into a dictionary.

        Args:
            response_text: Raw text response from Gemini.

        Returns:
            Dictionary with analysis results, or None if parsing fails.
        """
        try:
            # Try to parse directly as JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            try:
                # Remove markdown code block formatting
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
                logger.debug(f"Response text: {response_text[:200]}...")
                return None

    def analyze_posts_batch(
        self,
        posts: list,
        progress_callback=None
    ) -> List[PostAnalysis]:
        """
        Analyze multiple posts with optional progress tracking.

        Args:
            posts: List of RedditPost objects to analyze.
            progress_callback: Optional callback function(i, total) for progress updates.

        Returns:
            List of PostAnalysis objects.
        """
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

            # Add a small delay to avoid rate limits
            if i < total - 1:
                time.sleep(1.5)

        return analyses

    def test_connection(self) -> bool:
        """
        Test the Gemini API connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            response = self.model.generate_content(
                "Test connection. Respond with 'OK' if you can read this.",
                generation_config={"max_output_tokens": 10},
            )
            # Get response text safely
            response_text = ""
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'parts') and response.parts:
                response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            else:
                response_text = str(response)

            return "OK" in response_text.upper() or len(response_text) > 0
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
