"""
Filtering Utilities Module
Contains logic for filtering Reddit posts based on keywords and engagement criteria.
"""

import logging
import re
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """
    Result of filtering a post.
    """
    post: object
    passed: bool
    reason: str  # Explanation for why post was included or excluded


class PostFilter:
    """
    Filters Reddit posts based on keyword matching and engagement criteria.
    """

    # Keywords that indicate a pain point or startup idea discussion
    PAIN_POINT_KEYWORDS: List[str] = [
        "struggling with",
        "i hate it when",
        "is there a tool",
        "business idea",
        "how do i",
        "how does one",
        "looking for a way",
        "tired of",
        "frustrated with",
        "wish there was",
        "anyone know of",
        "does anyone know",
        "help me find",
        "can't find",
        "missing feature",
        "wish apps",
        "too expensive",
        "waste of time",
        "manual process",
        "repetitive task",
        "automate",
        "need a better",
        "current solutions",
        "alternative to",
        "replacing",
        "better than",
        "free alternative",
        "cheap alternative",
    ]

    # Keywords to exclude (spam, low-quality posts)
    EXCLUSION_KEYWORDS: List[str] = [
        "click here",
        "sign up now",
        "limited time",
        "act now",
        "make money fast",
        "work from home",
        "easy money",
        "crypto",
        "nft",
        "buy now",
        "discount code",
        "affiliate link",
    ]

    def __init__(
        self,
        min_comments: int = 5,
        required_keywords: List[str] = None,
        exclusion_keywords: List[str] = None,
        case_sensitive: bool = False,
    ):
        """
        Initialize the post filter.

        Args:
            min_comments: Minimum number of comments required for a post.
            required_keywords: List of keywords that must appear. Uses defaults if None.
            exclusion_keywords: List of keywords that exclude a post. Uses defaults if None.
            case_sensitive: Whether to perform case-sensitive matching.
        """
        self.min_comments = min_comments
        if required_keywords is not None:
            self.required_keywords = required_keywords
        else:
            self.required_keywords = self.PAIN_POINT_KEYWORDS

        if exclusion_keywords is not None:
            self.exclusion_keywords = exclusion_keywords
        else:
            self.exclusion_keywords = self.EXCLUSION_KEYWORDS

        self.case_sensitive = case_sensitive

    def check_comments(self, post) -> bool:
        """
        Check if a post meets the minimum comment threshold.

        Args:
            post: RedditPost to check.

        Returns:
            True if post has enough comments, False otherwise.
        """
        try:
            num_comments = getattr(post, 'num_comments', 0)
            return int(num_comments) >= self.min_comments
        except (ValueError, TypeError):
            return False

    def check_keywords(self, post) -> tuple[bool, List[str]]:
        """
        Check if a post contains any of the required keywords.

        Args:
            post: RedditPost to check.

        Returns:
            Tuple of (has_keyword, list_of_matched_keywords).
        """
        # Get title and body safely
        title = getattr(post, 'title', '')
        body = getattr(post, 'body', '')

        # Combine title and body for checking
        title_str = str(title) if title is not None else ""
        body_str = str(body) if body is not None else ""
        text_to_check = title_str + " " + body_str

        if not self.case_sensitive:
            text_to_check = text_to_check.lower()
            keywords = [kw.lower() for kw in self.required_keywords]
        else:
            keywords = self.required_keywords

        matched: List[str] = []
        for keyword in keywords:
            if keyword in text_to_check:
                matched.append(keyword)

        return len(matched) > 0, matched

    def check_exclusions(self, post) -> tuple[bool, str]:
        """
        Check if a post contains any exclusion keywords.

        Args:
            post: RedditPost to check.

        Returns:
            Tuple of (should_exclude, matched_exclusion_keyword).
        """
        # Get title and body safely
        title = getattr(post, 'title', '')
        body = getattr(post, 'body', '')

        # Combine title and body for checking
        title_str = str(title) if title is not None else ""
        body_str = str(body) if body is not None else ""
        text_to_check = title_str + " " + body_str

        if not self.case_sensitive:
            text_to_check = text_to_check.lower()
            keywords = [kw.lower() for kw in self.exclusion_keywords]
        else:
            keywords = self.exclusion_keywords

        for keyword in keywords:
            if keyword in text_to_check:
                return True, keyword

        return False, ""

    def should_include(self, post) -> FilterResult:
        """
        Determine if a post should be included for analysis.

        Args:
            post: RedditPost to evaluate.

        Returns:
            FilterResult indicating whether the post passed and why.
        """
        # Check for exclusion keywords first
        has_exclusion, exclusion_match = self.check_exclusions(post)
        if has_exclusion:
            return FilterResult(
                post=post,
                passed=False,
                reason=f"Contains exclusion keyword: '{exclusion_match}'",
            )

        # Check minimum comments
        if not self.check_comments(post):
            num_comments = getattr(post, 'num_comments', 0)
            return FilterResult(
                post=post,
                passed=False,
                reason=f"Only has {num_comments} comments (minimum: {self.min_comments})",
            )

        # Check for required keywords
        has_keyword, matches = self.check_keywords(post)
        if not has_keyword:
            return FilterResult(
                post=post,
                passed=False,
                reason="No pain point keywords found",
            )

        return FilterResult(
            post=post,
            passed=True,
            reason=f"Matched keywords: {', '.join(matches)}",
        )

    def filter_posts(self, posts: List) -> tuple[List, List[FilterResult]]:
        """
        Filter a list of posts and return results.

        Args:
            posts: List of RedditPost objects to filter.

        Returns:
            Tuple of (included_posts, all_filter_results).
        """
        results = [self.should_include(post) for post in posts]

        included = [r.post for r in results if r.passed]

        return included, results

    def get_filter_stats(self, results: List[FilterResult]) -> Dict:
        """
        Get statistics about the filtering results.

        Args:
            results: List of FilterResult objects.

        Returns:
            Dictionary with filtering statistics.
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        # Count reasons for failure
        failure_reasons: Dict[str, int] = {}
        for r in results:
            if not r.passed:
                reason = r.reason
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        return {
            "total_posts": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "failure_reasons": failure_reasons,
        }

    def display_filter_stats(self, results: List[FilterResult]) -> None:
        """
        Display filtering statistics to the console.

        Args:
            results: List of FilterResult objects.
        """
        stats = self.get_filter_stats(results)

        print("\nFiltering Statistics:")
        print(f"   Total posts scanned: {stats['total_posts']}")
        print(f"   Posts passed filter: {stats['passed']}")
        print(f"   Posts filtered out: {stats['failed']}")
        print(f"   Pass rate: {stats['pass_rate']:.1%}")

        if stats['failure_reasons']:
            print("\n   Top reasons for filtering out:")
            sorted_reasons = sorted(
                stats['failure_reasons'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            for reason, count in sorted_reasons:
                # Truncate long reasons for display
                display_reason = reason[:60] + "..." if len(reason) > 60 else reason
                print(f"   - {display_reason}: {count}")


def create_default_filter(min_comments: int = 5) -> PostFilter:
    """
    Create a PostFilter with default settings.

    Args:
        min_comments: Minimum comments required.

    Returns:
        Configured PostFilter instance.
    """
    return PostFilter(min_comments=min_comments)


# Regex-based filter for more advanced keyword matching
class RegexPostFilter(PostFilter):
    """
    Extended filter that supports regex patterns for keyword matching.
    """

    def __init__(
        self,
        min_comments: int = 5,
        required_patterns: List[str] = None,
        exclusion_patterns: List[str] = None,
    ):
        """
        Initialize the regex-based filter.

        Args:
            min_comments: Minimum number of comments required.
            required_patterns: List of regex patterns that must match.
            exclusion_patterns: List of regex patterns that exclude a post.
        """
        super().__init__(min_comments=min_comments)

        self.required_patterns = [
            re.compile(p, re.IGNORECASE) for p in (required_patterns or [])
        ]
        self.exclusion_patterns = [
            re.compile(p, re.IGNORECASE) for p in (exclusion_patterns or [])
        ]

    def check_regex_patterns(self, text: str, patterns: List[re.Pattern]) -> bool:
        """
        Check if any of the regex patterns match the text.

        Args:
            text: Text to check against patterns.
            patterns: List of compiled regex patterns.

        Returns:
            True if any pattern matches, False otherwise.
        """
        for pattern in patterns:
            if pattern.search(text):
                return True
        return False

    def check_keywords(self, post) -> tuple[bool, List[str]]:
        """
        Check if a post contains any of the required regex patterns.

        Args:
            post: RedditPost to check.

        Returns:
            Tuple of (has_match, list_of_matched_patterns).
        """
        # Get title and body safely
        title = getattr(post, 'title', '')
        body = getattr(post, 'body', '')

        title_str = str(title) if title is not None else ""
        body_str = str(body) if body is not None else ""
        text_to_check = title_str + " " + body_str

        matched: List[str] = []

        for pattern in self.required_patterns:
            if pattern.search(text_to_check):
                matched.append(pattern.pattern)

        return len(matched) > 0, matched
