"""
Configuration Management Module
Handles environment variables and application settings for the Reddit Startup Idea Scraper.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """
    Manages application configuration through environment variables.
    Loads settings from .env file and provides type-safe access to configuration values.
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration by loading environment variables.

        Args:
            env_file: Path to .env file. If None, looks for .env in project root.
        """
        if env_file is None:
            # Look for .env file in the current directory or parent directory
            possible_paths = [
                Path(".env"),
                Path(__file__).parent / ".env",
                Path(__file__).parent.parent / ".env",
            ]
            for path in possible_paths:
                if path.exists():
                    env_file = path
                    break

        if env_file is None or not Path(env_file).exists():
            env_file = Path(".env")  # Default fallback

        self.env_file = Path(env_file)
        self._load_env()

    def _load_env(self) -> None:
        """Load environment variables from .env file if it exists."""
        if self.env_file.exists():
            load_dotenv(self.env_file, override=True)
        else:
            print(f"Warning: .env file not found at {self.env_file}")
            print("This version uses web scraping, so Reddit API credentials are not required.")

    # Reddit Web Scraping Configuration (No credentials needed for web scraping)
    @property
    def reddit_client_id(self) -> str:
        """Reddit API client ID (not required for web scraping)."""
        return os.getenv("REDDIT_CLIENT_ID", "") or ""

    @property
    def reddit_client_secret(self) -> str:
        """Reddit API client secret (not required for web scraping)."""
        return os.getenv("REDDIT_CLIENT_SECRET", "") or ""

    @property
    def reddit_user_agent(self) -> str:
        """User agent for HTTP requests."""
        return os.getenv(
            "REDDIT_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    @property
    def reddit_credentials_set(self) -> bool:
        """
        Check if Reddit credentials are configured.
        Note: Web scraping version does not require API credentials.
        This always returns True since we use web scraping.
        """
        return True  # Web scraping doesn't need API credentials

    # Gemini API Configuration (Still required for AI analysis)
    @property
    def gemini_api_key(self) -> str:
        """Google Gemini API key."""
        return os.getenv("GEMINI_API_KEY", "") or ""

    @property
    def gemini_credentials_set(self) -> bool:
        """Check if Gemini API key is properly configured."""
        api_key = self.gemini_api_key
        return bool(api_key and api_key != "")

    # Target Subreddits
    @property
    def target_subreddits(self) -> List[str]:
        """
        List of subreddits to scrape.

        Returns:
            List of subreddit names (without r/ prefix).
        """
        subreddits = os.getenv("TARGET_SUBREDDITS", "Entrepreneur,SaaS,SideProject")
        if not subreddits:
            return ["Entrepreneur", "SaaS", "SideProject"]
        result = []
        for s in subreddits.split(","):
            stripped = s.strip()
            if stripped:
                result.append(stripped)
        return result

    # Scraping Configuration
    @property
    def post_limit(self) -> int:
        """Number of posts to fetch per subreddit."""
        try:
            value = os.getenv("POST_LIMIT", "25")
            if value is None:
                return 25
            return int(value)
        except (ValueError, TypeError):
            return 25

    @property
    def min_comments(self) -> int:
        """Minimum number of comments required for a post to be analyzed."""
        try:
            value = os.getenv("MIN_COMMENTS", "3")
            if value is None:
                return 3
            return int(value)
        except (ValueError, TypeError):
            return 3

    # Problem Detection Configuration
    @property
    def use_problem_filter(self) -> bool:
        """
        Whether to use problem phrase pre-filtering before AI analysis.
        This reduces API calls by filtering out non-problem posts early.
        """
        value = os.getenv("USE_PROBLEM_FILTER", "true")
        return value.lower() in ("true", "1", "yes")

    @property
    def min_problem_score(self) -> float:
        """
        Minimum problem indicator score for a post to be analyzed.
        Range: 0.0 to 1.0
        """
        try:
            value = os.getenv("MIN_PROBLEM_SCORE", "0.3")
            return float(value)
        except (ValueError, TypeError):
            return 0.3

    @property
    def use_keyword_categorizer(self) -> bool:
        """
        Whether to use keyword-based categorization as fallback.
        Useful when Gemini API is unavailable or for quick analysis.
        """
        value = os.getenv("USE_KEYWORD_CATEGORIZER", "true")
        return value.lower() in ("true", "1", "yes")

    @property
    def ai_fallback_enabled(self) -> bool:
        """
        Whether to fall back to keyword analysis if AI fails.
        When True, uses keyword-based analysis instead of failing.
        """
        value = os.getenv("AI_FALLBACK_ENABLED", "true")
        return value.lower() in ("true", "1", "yes")

    # Rate Limit Configuration
    @property
    def request_delay(self) -> float:
        """Delay between API requests in seconds."""
        try:
            value = os.getenv("REQUEST_DELAY", "2.0")
            return float(value)
        except (ValueError, TypeError):
            return 2.0

    @property
    def max_retries(self) -> int:
        """Maximum retry attempts on rate limit errors."""
        try:
            value = os.getenv("MAX_RETRIES", "5")
            return int(value)
        except (ValueError, TypeError):
            return 5

    # AI Provider Configuration
    @property
    def groq_api_key(self) -> str:
        """Groq API key for free cloud inference."""
        return os.getenv("GROQ_API_KEY", "") or ""

    @property
    def use_ollama(self) -> bool:
        """Whether to use Ollama for local AI inference."""
        value = os.getenv("USE_OLLAMA", "false")
        return value.lower() in ("true", "1", "yes")

    @property
    def ollama_model(self) -> str:
        """Ollama model to use for local inference."""
        return os.getenv("OLLAMA_MODEL", "") or ""

    # Output Configuration
    @property
    def output_format(self) -> str:
        """Output format: markdown, csv, json, or all."""
        value = os.getenv("OUTPUT_FORMAT", "all")
        if value is None:
            return "all"
        return str(value).lower()

    @property
    def output_directory(self) -> Path:
        """Directory for output files."""
        return Path(__file__).parent.parent / "outputs"

    @property
    def export_directory(self) -> Path:
        """Directory for exported CSV/JSON files."""
        return Path(__file__).parent.parent / "exports"

    @property
    def print_summary(self) -> bool:
        """Whether to print summary report to console."""
        value = os.getenv("PRINT_SUMMARY", "true")
        return value.lower() in ("true", "1", "yes")

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate that all required configuration is present.

        Returns:
            Tuple of (is_valid, list_of_missing_configurations).
        """
        missing = []

        # Web scraping version doesn't require Reddit API credentials
        # Only check Gemini API key if AI fallback is disabled
        if not self.ai_fallback_enabled:
            if not self.gemini_credentials_set:
                missing.append("GEMINI_API_KEY")

        return len(missing) == 0, missing

    def __repr__(self) -> str:
        """String representation of configuration (without sensitive values)."""
        return (
            f"Config(subreddits={self.target_subreddits}, "
            f"post_limit={self.post_limit}, "
            f"min_comments={self.min_comments}, "
            f"output_format={self.output_format}, "
            f"use_problem_filter={self.use_problem_filter}, "
            f"use_keyword_categorizer={self.use_keyword_categorizer}, "
            f"mode=web_scraping)"
        )
