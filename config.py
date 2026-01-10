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
            print("Please copy .env.example to .env and fill in your API credentials.")

    # Reddit API Configuration
    @property
    def reddit_client_id(self) -> str:
        """Reddit API client ID."""
        return os.getenv("REDDIT_CLIENT_ID", "") or ""

    @property
    def reddit_client_secret(self) -> str:
        """Reddit API client secret."""
        return os.getenv("REDDIT_CLIENT_SECRET", "") or ""

    @property
    def reddit_user_agent(self) -> str:
        """Reddit API user agent string."""
        return os.getenv(
            "REDDIT_USER_AGENT",
            "script:startup-idea-scraper:v1.0 (by /u/anonymous)"
        )

    @property
    def reddit_credentials_set(self) -> bool:
        """Check if Reddit API credentials are properly configured."""
        client_id = self.reddit_client_id
        client_secret = self.reddit_client_secret
        return bool(client_id and client_secret and client_id != "" and client_secret != "")

    # Gemini API Configuration
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
            value = os.getenv("POST_LIMIT", "50")
            if value is None:
                return 50
            return int(value)
        except (ValueError, TypeError):
            return 50

    @property
    def min_comments(self) -> int:
        """Minimum number of comments required for a post to be analyzed."""
        try:
            value = os.getenv("MIN_COMMENTS", "5")
            if value is None:
                return 5
            return int(value)
        except (ValueError, TypeError):
            return 5

    # Output Configuration
    @property
    def output_format(self) -> str:
        """Output format: markdown, csv, or both."""
        value = os.getenv("OUTPUT_FORMAT", "markdown")
        if value is None:
            return "markdown"
        return str(value).lower()

    @property
    def output_directory(self) -> Path:
        """Directory for output files."""
        return Path(__file__).parent.parent / "outputs"

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate that all required configuration is present.

        Returns:
            Tuple of (is_valid, list_of_missing_configurations).
        """
        missing = []

        if not self.reddit_credentials_set:
            missing.append("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")

        if not self.gemini_credentials_set:
            missing.append("GEMINI_API_KEY")

        return len(missing) == 0, missing

    def __repr__(self) -> str:
        """String representation of configuration (without sensitive values)."""
        return (
            f"Config(subreddits={self.target_subreddits}, "
            f"post_limit={self.post_limit}, "
            f"min_comments={self.min_comments}, "
            f"output_format={self.output_format})"
        )
