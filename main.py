"""
Reddit Startup Idea Scraper - 2026 Edition
Uses Reddit's free JSON endpoints with enhanced problem detection and analysis.

FREE AI OPTIONS (No API limits!):
1. Ollama (LOCAL) - Runs on your machine, totally free
2. Groq (CLOUD) - Extremely fast, generous free tier
3. HuggingFace (CLOUD) - Free serverless inference
4. Keyword Only - Rule-based, no AI needed

Setup guides:
- Ollama: https://ollama.com/ (install, run 'ollama serve', pull 'ollama pull llama3.2')
- Groq: https://console.groq.com/ (free API key)
- HuggingFace: https://huggingface.co/ (optional token for higher limits)
"""

import sys
import logging
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any

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
    +---------------------------------------------------------------------+
    |                                                                     |
    |     REDDIT STARTUP IDEA SCRAPER - 2026 EDITION                      |
    |                                                                     |
    |     FREE AI OPTIONS (No API Limits!):                               |
    |                                                                     |
    |     1. OLLAMA (Local)    - Runs on your machine, totally free       |
    |     2. GROQ (Cloud)      - Extremely fast, generous free tier        |
    |     3. HUGGINGFACE (API) - Free serverless inference                |
    |     4. KEYWORD ONLY     - Rule-based, no AI needed                  |
    |                                                                     |
    |     Features:                                                        |
    |     - Problem phrase detection for smart filtering                  |
    |     - Multiple AI backends (free + local)                           |
    |     - Confidence scoring for quality assessment                     |
    |     - Multiple export formats (CSV, JSON, Markdown)                 |
    |                                                                     |
    +---------------------------------------------------------------------+
    """
    print(banner)


def print_step(step_number: int, total_steps: int, message: str) -> None:
    """Print a formatted step indicator."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  STEP {step_number}/{total_steps}: {message}")
    print(f"{separator}\n")


def print_ai_provider_status(config_instance) -> None:
    """Print status of available AI providers."""
    from analyzers import AnalyzerFactory

    print("\n" + "=" * 70)
    print("  AI PROVIDER STATUS")
    print("=" * 70)

    providers_info = [
        ("Ollama (Local)", "✓ Available" if config_instance.use_ollama else "✗ Disabled",
         "Install Ollama, run 'ollama serve', pull 'ollama pull llama3.2'"),
        ("Groq (Cloud)", "✓ Available" if config_instance.groq_api_key else "✗ No API key",
         "Get free key: https://console.groq.com/"),
        ("HuggingFace", "✓ Available",
         "Free serverless inference: https://huggingface.co/inference"),
        ("Gemini", "✓ Available" if config_instance.gemini_credentials_set else "✗ No API key",
         "Get key: https://aistudio.google.com/ (paid tier)"),
        ("Keyword Only", "✓ Always Available",
         "Rule-based analysis, no AI needed"),
    ]

    for provider, status, setup in providers_info:
        print(f"\n  {provider}")
        print(f"    Status: {status}")
        print(f"    Setup: {setup}")

    # Check which is currently selected
    available = AnalyzerFactory.get_available_providers(config_instance)
    print(f"\n  Currently Selected: {available[0].value.upper() if available else 'None'}")

    print("\n" + "=" * 70)


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
        print("\n" + "!" * 70)
        print("  CONFIGURATION ERROR")
        print("!" * 70)
        print("\nMissing required configuration:")
        for item in missing:
            print(f"   - {item}")
        print("\nTo fix, set one of these in your .env file:")
        print("   - GROQ_API_KEY (recommended - free & fast)")
        print("   - OLLAMA_MODEL (for local AI)")
        print("   - Or set AI_FALLBACK_ENABLED=true for keyword-only mode")
        return False

    print("✓ Configuration validated successfully!")
    print("  - Reddit API: NOT REQUIRED (free JSON endpoints)")
    print_ai_provider_status(config_instance)
    return True


def detect_problems_and_categorize(posts: List, config_instance) -> List[Dict[str, Any]]:
    """
    Apply problem detection and categorization to posts.

    Args:
        posts: List of RedditPost objects.
        config_instance: Configuration object.

    Returns:
        List of post dictionaries with added analysis fields.
    """
    from detectors import ProblemPhraseDetector
    from categorizers import KeywordCategorizer
    from scorers import ConfidenceScorer

    print_step(2, 5, "Detecting Problems & Categorizing Posts")

    # Initialize detectors
    problem_detector = ProblemPhraseDetector()
    categorizer = KeywordCategorizer()
    scorer = ConfidenceScorer()

    # Process posts
    processed_posts = []
    total = len(posts)
    problem_count = 0
    categorized_count = 0

    print(f"Processing {total} posts...\n")

    for i, post in enumerate(posts):
        post_dict = {
            'title': post.title,
            'body': post.body,
            'url': post.url,
            'subreddit': post.subreddit,
            'upvotes': post.upvotes,
            'num_comments': post.num_comments,
            'posted_date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
        }

        # Problem detection
        if config_instance.use_problem_filter:
            problem_result = problem_detector.score_problem_indicator(
                post.title, post.body
            )
            post_dict['problem_score'] = problem_result['score']
            post_dict['problem_severity'] = problem_result['severity']
            post_dict['problem_phrases'] = problem_result['phrases_found']

            # Filter out low-problem posts
            if problem_result['score'] < config_instance.min_problem_score:
                continue  # Skip this post

            problem_count += 1
        else:
            post_dict['problem_score'] = 0.5
            post_dict['problem_severity'] = 'medium'
            post_dict['problem_phrases'] = []

        # Categorization
        if config_instance.use_keyword_categorizer:
            category_result = categorizer.categorize(post.title, post.body)
            post_dict['category'] = category_result.category
            post_dict['category_score'] = category_result.score
            post_dict['category_keywords'] = category_result.matched_keywords
            categorized_count += 1
        else:
            post_dict['category'] = 'General Business'
            post_dict['category_score'] = 0.5
            post_dict['category_keywords'] = []

        # Calculate confidence score
        confidence_breakdown = scorer.get_confidence_breakdown(
            title=post.title,
            body=post.body,
            category=post_dict['category'],
            category_score=post_dict['category_score'],
            keyword_matches=post_dict['category_keywords'],
            upvotes=post.upvotes,
            num_comments=post.num_comments,
            problem_score=post_dict.get('problem_score', 0.5)
        )
        post_dict['confidence_score'] = confidence_breakdown.overall_score
        post_dict['confidence_breakdown'] = confidence_breakdown

        # Get quality tier
        quality = scorer.rate_post_quality(
            confidence_breakdown.overall_score,
            post.upvotes,
            post.num_comments
        )
        post_dict['quality_tier'] = quality['tier']

        processed_posts.append(post_dict)

        # Progress indicator
        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(f"   Processed {i + 1}/{total} posts...")

    print(f"\n✓ Problem Detection Results:")
    print(f"   - Posts with detected problems: {problem_count}")
    print(f"   - Posts categorized: {categorized_count}")
    print(f"   - Posts after filtering: {len(processed_posts)}")

    return processed_posts


def analyze_with_ai(processed_posts: List[Dict[str, Any]], 
                    config_instance) -> List[Dict[str, Any]]:
    """
    Analyze posts with available AI backend.

    Args:
        processed_posts: List of processed post dictionaries.
        config_instance: Configuration object.

    Returns:
        Updated post dictionaries with AI analysis.
    """
    from analyzers import get_analyzer, AIProvider

    print_step(3, 5, "Analyzing Posts with AI")

    if not processed_posts:
        print("\nNo posts to analyze after filtering.")
        return []

    # Get analyzer using factory
    # Use the smart property from config
    provider_pref = config_instance.ai_provider
    analyzer = get_analyzer(config=config_instance, provider=provider_pref)

    if not analyzer:
        print("\nNo AI backend available. Using keyword-only analysis.")
        return processed_posts

    # Get analyzer info
    model_name = getattr(analyzer, 'model_name', 'unknown')
    
    # Provider display info
    is_cloud = provider_pref == "groq"
    mode_str = "Cloud API" if is_cloud else "Local Model"
    if provider_pref == "keyword": mode_str = "Rule-based"

    print(f"Analyzing {len(processed_posts)} posts with {provider_pref.upper()}...")
    print(f"  Model: {model_name}")
    print(f"  Mode: {mode_str}")
    if config_instance.is_hosted:
        print(f"  Environment: Hosted (Render/Cloud)")
    else:
        print(f"  Environment: Local")

    analyzed_posts = []
    total = len(processed_posts)

    for i, post in enumerate(processed_posts):
        try:
            # Analyze with AI
            analysis = analyzer.analyze_post(
                title=post['title'],
                body=post['body'],
                subreddit=post['subreddit'],
                post_url=post['url']
            )

            if analysis:
                # Add AI results to post
                post['startup_idea'] = analysis.startup_idea
                post['startup_type'] = analysis.startup_type
                post['core_problem_summary'] = analysis.core_problem_summary
                post['target_audience'] = analysis.target_audience
                post['estimated_complexity'] = analysis.estimated_complexity
                post['potential_market_size'] = analysis.potential_market_size
                post['model_used'] = analysis.model_used
                post['analysis_timestamp'] = analysis.analysis_timestamp

                # Blend AI confidence with our score
                if 'confidence_score' in post:
                    post['confidence_score'] = (post['confidence_score'] * 0.4 + 
                                                analysis.confidence_score * 0.6)

            analyzed_posts.append(post)

            # Progress
            if (i + 1) % 5 == 0 or (i + 1) == total:
                print(f"   Analyzed {i + 1}/{total} posts...")

        except Exception as e:
            logger.warning(f"AI analysis failed for post: {e}")
            analyzed_posts.append(post)

    print(f"\n✓ AI analysis complete: {len(analyzed_posts)} posts processed")

    return analyzed_posts


def save_and_export(analyses: List[Dict[str, Any]], 
                    config_instance) -> None:
    """
    Save and export analysis results in multiple formats.

    Args:
        analyses: List of analyzed post dictionaries.
        config_instance: Configuration object.
    """
    from exporters import ExportManager
    from utils.outputs import OutputManager

    print_step(4, 5, "Saving & Exporting Results")

    # Ensure output directories exist
    config_instance.output_directory.mkdir(parents=True, exist_ok=True)
    config_instance.export_directory.mkdir(parents=True, exist_ok=True)

    # Initialize exporters
    export_manager = ExportManager(str(config_instance.export_directory))

    # Export based on configured format
    output_format = config_instance.output_format

    if output_format in ('all', 'csv'):
        csv_result = export_manager.csv_exporter.export(
            analyses,
            config_instance.export_directory / f"reddit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if csv_result.success:
            print(f"✓ CSV export: {csv_result.file_path}")

    if output_format in ('all', 'json'):
        json_result = export_manager.json_exporter.export(
            analyses,
            config_instance.export_directory / f"reddit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        if json_result.success:
            print(f"✓ JSON export: {json_result.file_path}")

    if output_format in ('all', 'markdown'):
        output_manager = OutputManager()
        output_paths = output_manager.save_all_formats(analyses)
        for format_name, filepath in output_paths.items():
            print(f"✓ {format_name.upper()} export: {filepath}")

    # Print summary to console
    if config_instance.print_summary:
        print_step(5, 5, "Analysis Summary")
        export_manager.summary_reporter.print_summary(analyses)

    # Print quick summary
    if analyses:
        print("\n" + "=" * 70)
        print("  TOP STARTUP OPPORTUNITIES")
        print("=" * 70)
        top_posts = export_manager.summary_reporter.get_top_opportunities(
            analyses, limit=5, min_confidence=0.5
        )
        for i, post in enumerate(top_posts, 1):
            title = post.get('title', 'No title')[:60]
            conf = post.get('confidence_score', 0)
            tier = post.get('quality_tier', 'N/A')
            print(f"\n  {i}. [{conf:.0%}] {title}...")
            print(f"     Category: {post.get('category', 'N/A')} | Tier: {tier}")
            print(f"     Idea: {post.get('startup_idea', 'N/A')[:70]}...")

    print("\n" + "=" * 70)
    print("  EXPORT COMPLETE")
    print("=" * 70)


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

        # Print banner
        print_banner()

        # Load configuration
        config_instance = Config()

        # Apply command line overrides
        if args.min_comments:
            config_instance._min_comments = args.min_comments
        if args.subreddits:
            config_instance._target_subreddits = args.subreddits.split(',')
        if args.post_limit:
            config_instance._post_limit = args.post_limit
        if args.ai_provider:
            config_instance._ai_provider = args.ai_provider

        # Validate configuration
        if not validate_config(config_instance):
            return 1

        # Initialize Reddit client
        print("\nInitializing Reddit client...")
        reddit_client = RedditClient(config=config_instance)

        # Test Reddit connection
        print("  Testing Reddit JSON API...", end=" ", flush=True)
        if reddit_client.test_connection():
            print("✓ OK (Free JSON)")
        else:
            print("✗ FAILED")
            print("  Could not connect to Reddit. Check your internet connection.")
            return 1

        # Fetch posts
        print_step(1, 5, "Fetching Posts from Reddit")

        all_posts = reddit_client.fetch_all_subreddits()
        posts: List = []
        for subreddit_name, post_list in all_posts.items():
            posts.extend(post_list)

        print(f"✓ Total posts fetched: {len(posts)}")

        # Apply problem detection and categorization
        processed_posts = detect_problems_and_categorize(posts, config_instance)

        if not processed_posts:
            print("\n✗ No posts found matching problem criteria.")
            print("  Try lowering MIN_PROBLEM_SCORE in .env file or disable USE_PROBLEM_FILTER.")
            return 0

        # Analyze with AI (or keyword fallback)
        analyzed_posts = analyze_with_ai(processed_posts, config_instance)

        if not analyzed_posts:
            print("\n✗ Failed to analyze any posts.")
            return 1

        # Save and export results
        save_and_export(analyzed_posts, config_instance)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Operation cancelled by user.")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n✗ Error: {e}")
        return 1


def main() -> int:
    """
    Main entry point for the application.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Reddit Startup Idea Scraper - FREE AI Options Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
╔═══════════════════════════════════════════════════════════════════════╗
║                     FREE AI OPTIONS (No API Limits!)                   ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  1. OLLAMA (Local - RECOMMENDED)                                      ║
║     - Totally free, runs on your machine                              ║
║     - No API limits, no internet needed                               ║
║     - Setup:                                                          ║
║       1. Install: https://ollama.com/                                 ║
║       2. Run: ollama serve                                            ║
║       3. Pull model: ollama pull llama3.2                             ║
║                                                                       ║
║  2. GROQ (Cloud - FASTEST FREE)                                       ║
║     - Extremely fast inference                                        ║
║     - Generous free tier (no credit card)                             ║
║     - Setup: https://console.groq.com/ (get free API key)             ║
║                                                                       ║
║  3. HUGGINGFACE (Cloud)                                               ║
║     - Free serverless inference                                       ║
║     - No API key needed for basic use                                 ║
║     - Setup: https://huggingface.co/inference                         ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

Examples:
  python main.py                                    # Auto-select best AI
  python main.py --ai-provider ollama              # Use local Ollama
  python main.py --ai-provider groq                # Use free Groq API
  python main.py --ai-provider keyword             # No AI, keyword only
  python main.py --verbose                         # Enable debug logging
  python main.py --min-comments 10                 # Only analyze 10+ comment posts
        """,
    )

    parser.add_argument(
        "--verbose", "-v",
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

    parser.add_argument(
        "--ai-provider",
        type=str,
        default=None,
        choices=["ollama", "groq", "huggingface", "gemini", "keyword"],
        help="AI backend to use (auto-selects best available if not specified)",
    )

    args = parser.parse_args()

    # Apply command line overrides
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    return run_scraper(args)


if __name__ == "__main__":
    sys.exit(main())
