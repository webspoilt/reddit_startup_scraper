"""
Reddit API Client Module
Handles all interactions with the Reddit API using PRAW.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import praw
from praw.models import Submission

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """
    Data class representing a processed Reddit post.
    """
    id: str
    title: str
    body: str
    subreddit: str
    url: str
    author: str
    score: int
    num_comments: int
    created_utc: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easier processing."""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "subreddit": self.subreddit,
            "url": self.url,
            "author": self.author,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_utc": self.created_utc,
        }


class RedditClient:
    """
    Client for interacting with the Reddit API.
    Handles authentication, rate limiting, and data fetching.
    """

    def __init__(self, config=None):
        """
        Initialize the Reddit client with credentials from config.

        Args:
            config: Configuration object. If None, imports from config module.
        """
        if config is None:
            from config import Config
            config = Config()

        self._config = config

        if not config.reddit_credentials_set:
            raise ValueError(
                "Reddit API credentials not configured. "
                "Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env file."
            )

        self._client = praw.Reddit(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent,
            check_for_updates=False,
        )

        # Track rate limit state
        self._rate_limit_remaining: Optional[float] = None
        self._rate_limit_reset_time: Optional[float] = None

    def _handle_rate_limit(self, exception: Exception) -> None:
        """
        Handle Reddit API rate limiting (HTTP 429).

        Args:
            exception: The exception raised by PRAW.
        """
        logger.warning(f"Rate limit encountered: {exception}")
        print("\nRate limit hit. Waiting 60 seconds before retry...")

        # Wait for 60 seconds (Reddit's typical rate limit reset time)
        time.sleep(60)

        logger.info("Resuming after rate limit wait.")

    def _create_reddit_post(self, submission: Submission, subreddit_name: str) -> RedditPost:
        """
        Create a RedditPost object from a PRAW submission.

        Args:
            submission: PRAW Submission object.
            subreddit_name: Name of the subreddit.

        Returns:
            RedditPost instance.
        """
        # Handle potentially missing fields
        if submission.author is not None:
            author_name = str(submission.author)
        else:
            author_name = "[deleted]"

        # Safely get post body
        body_text = ""
        if hasattr(submission, 'selftext'):
            body_text = submission.selftext
        elif hasattr(submission, 'url') and submission.url:
            body_text = str(submission.url)
        else:
            body_text = ""

        # Get permalink safely
        permalink = getattr(submission, 'permalink', '')
        if not permalink:
            permalink = f"/r/{subreddit_name}/comments/{submission.id}/"

        return RedditPost(
            id=str(submission.id),
            title=str(submission.title),
            body=str(body_text),
            subreddit=str(subreddit_name),
            url=f"https://reddit.com{permalink}",
            author=author_name,
            score=int(submission.score),
            num_comments=int(submission.num_comments),
            created_utc=float(submission.created_utc),
        )

    def fetch_posts(self, subreddit_name: str, limit: Optional[int] = None) -> List[RedditPost]:
        """
        Fetch latest posts from a specific subreddit.

        Args:
            subreddit_name: Name of the subreddit (without r/ prefix).
            limit: Maximum number of posts to fetch. Defaults to config setting.

        Returns:
            List of RedditPost objects.
        """
        if limit is None:
            limit = self._config.post_limit

        print(f"Fetching {limit} posts from r/{subreddit_name}...")

        posts: List[RedditPost] = []
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                subreddit = self._client.subreddit(subreddit_name)
                submissions = subreddit.new(limit=limit)

                for submission in submissions:
                    try:
                        post = self._create_reddit_post(submission, subreddit_name)
                        posts.append(post)
                    except Exception as e:
                        logger.warning(f"Error processing submission: {e}")
                        continue

                logger.info(f"Successfully fetched {len(posts)} posts from r/{subreddit_name}")
                return posts

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    self._handle_rate_limit(e)
                    retry_count += 1
                    continue
                else:
                    logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
                    raise

        logger.error(f"Failed to fetch posts from r/{subreddit_name} after {max_retries} retries")
        return posts

    def fetch_all_subreddits(self) -> Dict[str, List[RedditPost]]:
        """
        Fetch posts from all configured subreddits.

        Returns:
            Dictionary mapping subreddit names to lists of RedditPost objects.
        """
        results: Dict[str, List[RedditPost]] = {}

        for subreddit in self._config.target_subreddits:
            posts = self.fetch_posts(subreddit)
            results[subreddit] = posts

        return results

    def test_connection(self) -> bool:
        """
        Test the Reddit API connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            # Try to access a subreddit to test the connection
            subreddit = self._client.subreddit("test")
            # Access a property to trigger the API call
            _ = subreddit.display_name
            return True
        except Exception as e:
            logger.error(f"Reddit connection test failed: {e}")
            return False
