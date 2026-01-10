"""
Reddit Startup Idea Scraper - Main Entry Point
Scrapes Reddit for pain points and uses AI to generate startup ideas.
"""

import sys
import logging
import argparse
from datetime import datetime
from typing import List

# Configure logging FIRST before any imports that use logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def print_banner() -> None:
    """Print the application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║     REDDIT STARTUP IDEA SCRAPER                                   ║
    ║                                                                   ║
    ║     Discover Micro-SaaS opportunities from Reddit pain points    ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_step(step_number: int, total_steps: int, message: str) -> None:
    """Print a formatted step indicator."""
    separator = "-" * 60
    print(f"\n{separator}")
    print(f"  Step {step_number}/{total_steps}: {message}")
    print(f"{separator}\n")


def validate_config(config_instance) -> bool:
    """
    Validate that all required configuration is present.

    Args:
        config_instance: Configuration object to validate.

    Returns:
        True if configuration is valid, False otherwise.
    """
    is_valid, missing = config_instance.validate()

    if not is_valid:
        print("\nConfiguration Error!")
        print("Missing required environment variables:")
        for item in missing:
            print(f"   - {item}")
        print("\nPlease copy .env.example to .env and fill in your API credentials.")
        return False

    print("Configuration validated successfully!")
    return True


def fetch_and_filter_posts(reddit_client, config_instance):
    """
    Fetch posts from Reddit and apply filtering.

    Args:
        reddit_client: Configured RedditClient instance.
        config_instance: Configuration object.

    Returns:
        List of filtered RedditPost objects.
    """
    print_step(1, 4, "Fetching Posts from Reddit")

    # Fetch posts from all configured subreddits
    all_posts = reddit_client.fetch_all_subreddits()

    # Flatten posts into a single list
    posts: List = []
    for subreddit_name, post_list in all_posts.items():
        posts.extend(post_list)

    print(f"\nTotal posts fetched: {len(posts)}")

    # Apply filters
    print_step(2, 4, "Filtering Posts")

    from utils.filters import PostFilter
    filter_obj = PostFilter(min_comments=config_instance.min_comments)
    filtered_posts, filter_results = filter_obj.filter_posts(posts)

    # Display filter statistics
    filter_obj.display_filter_stats(filter_results)

    print(f"\nPosts ready for analysis: {len(filtered_posts)}")

    return filtered_posts


def analyze_posts(posts: List, gemini_client) -> List:
    """
    Analyze filtered posts using Gemini AI.

    Args:
        posts: List of filtered RedditPost objects.
        gemini_client: Configured GeminiClient instance.

    Returns:
        List of PostAnalysis objects.
    """
    print_step(3, 4, "Analyzing Posts with AI")

    if not posts:
        print("\nNo posts to analyze after filtering.")
        return []

    print(f"Analyzing {len(posts)} posts with Gemini 1.5 Flash...")

    def progress_callback(current: int, total: int) -> None:
        """Progress callback for batch analysis."""
        percent = (current / total) * 100
        bar_length = 30
        filled = int(bar_length * current // total)
        bar_char = "#" * filled
        empty_char = "." * (bar_length - filled)
        print(f"\r   Analyzing: [{bar_char}{empty_char}] {current}/{total} ({percent:.0f}%)", end="", flush=True)

    analyses = gemini_client.analyze_posts_batch(posts, progress_callback)
    print()  # New line after progress bar

    print(f"\nSuccessfully analyzed {len(analyses)} posts!")

    return analyses


def save_results(analyses: List) -> None:
    """
    Save analysis results to output files.

    Args:
        analyses: List of PostAnalysis objects.
    """
    print_step(4, 4, "Saving Results")

    from utils.outputs import OutputManager, print_summary, save_quick_summary

    output_manager = OutputManager()
    output_paths = output_manager.save_all_formats(analyses)

    print("\nOutput files generated:")
    for format_name, filepath in output_paths.items():
        print(f"   - {format_name.upper()}: {filepath}")

    # Print summary to console
    print_summary(analyses)

    # Print quick summary of top ideas
    if analyses:
        print(save_quick_summary(analyses))


def run_scraper(args: argparse.Namespace) -> int:
    """
    Main execution function for the scraper.

    Args:
        args: Command line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        # Import here to avoid circular imports
        from config import Config
        from scrapers.reddit_client import RedditClient
        from analyzers.gemini_client import GeminiClient

        # Print banner
        print_banner()

        # Load configuration
        config_instance = Config()

        # Validate configuration
        if not validate_config(config_instance):
            return 1

        # Initialize clients
        print("\nInitializing clients...")
        reddit_client = RedditClient(config=config_instance)
        gemini_client = GeminiClient(config=config_instance)

        # Test connections
        print("   Testing Reddit connection...", end=" ", flush=True)
        if reddit_client.test_connection():
            print("OK")
        else:
            print("FAILED")
            return 1

        print("   Testing Gemini connection...", end=" ", flush=True)
        if gemini_client.test_connection():
            print("OK")
        else:
            print("FAILED")
            return 1

        # Fetch and filter posts
        filtered_posts = fetch_and_filter_posts(reddit_client, config_instance)

        if not filtered_posts:
            print("\nNo posts found matching criteria.")
            print("Try adjusting your filter settings or check the subreddits for active discussions.")
            return 0

        # Analyze posts
        analyses = analyze_posts(filtered_posts, gemini_client)

        if not analyses:
            print("\nFailed to generate any analyses.")
            return 1

        # Save results
        save_results(analyses)

        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\nError: {e}")
        return 1


def main() -> int:
    """
    Main entry point for the application.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Reddit Startup Idea Scraper - Discover Micro-SaaS opportunities from Reddit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run with default settings
  python main.py --verbose          # Enable verbose logging
  python main.py --min-comments 10  # Only analyze posts with 10+ comments

For configuration, copy .env.example to .env and fill in your API keys.
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    parser.add_argument(
        "--min-comments",
        type=int,
        default=None,
        help="Minimum comments required for analysis (overrides .env setting)",
    )

    parser.add_argument(
        "--subreddits",
        type=str,
        default=None,
        help="Comma-separated list of subreddits to scrape (overrides .env setting)",
    )

    parser.add_argument(
        "--post-limit",
        type=int,
        default=None,
        help="Number of posts to fetch per subreddit (overrides .env setting)",
    )

    args = parser.parse_args()

    # Apply command line overrides
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    return run_scraper(args)


if __name__ == "__main__":
    sys.exit(main())
