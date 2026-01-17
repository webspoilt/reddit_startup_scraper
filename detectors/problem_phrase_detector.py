"""
Problem Phrase Detector Module
Detects business problems and pain points in Reddit posts using keyword patterns.
This serves as a pre-filter to identify high-potential posts before AI analysis.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProblemMatch:
    """Represents a detected problem indicator in a post."""
    phrase: str
    position: int
    context: str  # Text surrounding the phrase


class ProblemPhraseDetector:
    """
    Detects business problems and pain points using pattern matching.
    
    This module identifies posts that contain common problem indicators
    like frustration phrases, wishlist items, and inefficiency complaints.
    """

    # Business problem indicator phrases
    PROBLEM_PHRASES = [
        # Frustration expressions
        'i hate when',
        "it's so annoying that",
        'frustrated with',
        'frustrating part',
        'annoying problem',
        'this is so frustrating',
        'really bothers me',
        'drives me crazy',
        'pet peeve',
        
        # Wishlist expressions
        'wish there was',
        'wishes there was',
        'wish i could',
        'i wish',
        'someone should make',
        'need a better way',
        
        # Automation/inefficiency
        'how can i automate',
        'tired of doing',
        'waste so much time',
        'manual process',
        'keep forgetting',
        'so inefficient',
        'too complicated',
        'overwhelmed by',
        'bottleneck',
        
        # Seeking solutions
        'is there an app for',
        'looking for a way to',
        'looking for software',
        'anyone know of',
        'can anyone recommend',
        'need help with',
        'how do you handle',
        'does anyone else',
        
        # Problem descriptions
        'problem with',
        'pain point',
        'struggling with',
        'difficult to manage',
        'hard to manage',
        'challenge with',
        'issue with',
    ]

    def __init__(self, custom_phrases: List[str] = None):
        """
        Initialize the detector with optional custom phrases.
        
        Args:
            custom_phrases: Additional phrases to detect (appended to defaults)
        """
        self.phrases = self.PROBLEM_PHRASES.copy()
        if custom_phrases:
            self.phrases.extend(custom_phrases)
        
        # Compile for case-insensitive matching
        self._phrase_set = set(p.lower() for p in self.phrases)

    def contains_problem_phrase(self, text: str) -> bool:
        """
        Check if text contains any problem indicator phrases.
        
        Args:
            text: The text to check (usually post title)
            
        Returns:
            True if any problem phrase is found
        """
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self.phrases)

    def find_all_matches(self, text: str) -> List[ProblemMatch]:
        """
        Find all problem phrases in the given text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of ProblemMatch objects with phrase and context
        """
        matches = []
        text_lower = text.lower()

        for phrase in self.phrases:
            pos = 0
            while True:
                # Find next occurrence
                idx = text_lower.find(phrase.lower(), pos)
                if idx == -1:
                    break

                # Extract context (50 chars before and after)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(phrase) + 50)
                context = text[start:end].strip()

                matches.append(ProblemMatch(
                    phrase=phrase,
                    position=idx,
                    context=context
                ))

                # Search for next occurrence
                pos = idx + 1

        return matches

    def score_problem_indicator(self, title: str, body: str = "") -> Dict[str, Any]:
        """
        Score how strongly a post indicates a business problem.
        
        Args:
            title: Post title
            body: Optional post body text
            
        Returns:
            Dictionary with score, detected phrases, and match details
        """
        full_text = f"{title} {body}".lower()
        
        matches = self.find_all_matches(full_text)
        
        if not matches:
            return {
                "has_problem": False,
                "score": 0.0,
                "phrase_count": 0,
                "phrases_found": [],
                "top_phrases": [],
                "severity": "none"
            }

        # Count unique phrases found
        phrases_found = list(set(m.phrase for m in matches))
        
        # Calculate score based on number and quality of matches
        # More specific/direct phrases score higher
        high_value_phrases = [
            'i hate when', 'frustrated with', 'tired of doing',
            'waste so much time', 'manual process', 'wish there was',
            'is there an app for', 'need a better way', 'so inefficient'
        ]
        
        score = 0.0
        top_phrases = []
        for phrase in phrases_found:
            phrase_score = 1.0  # Base score
            if phrase in high_value_phrases:
                phrase_score = 2.0  # Higher score for direct frustration
            score += phrase_score
            
            if phrase in high_value_phrases:
                top_phrases.append(phrase)

        # Normalize score to 0-1 range
        max_possible = len(high_value_phrases) + (len(phrases_found) - len(top_phrases))
        normalized_score = min(score / max_possible, 1.0) if max_possible > 0 else 0.5

        # Determine severity level
        if normalized_score >= 0.7:
            severity = "high"
        elif normalized_score >= 0.4:
            severity = "medium"
        else:
            severity = "low"

        return {
            "has_problem": True,
            "score": round(normalized_score, 3),
            "phrase_count": len(phrases_found),
            "phrases_found": phrases_found,
            "top_phrases": top_phrases[:3],  # Top 3 phrases
            "severity": severity,
            "all_matches": matches
        }

    def filter_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of posts to only include those with problem indicators.
        
        Args:
            posts: List of post dictionaries with 'title' and optional 'body'
            
        Returns:
            Filtered list of posts that contain problem phrases
        """
        filtered = []
        for post in posts:
            title = post.get('title', '')
            body = post.get('body', '')
            
            if self.contains_problem_phrase(title):
                # Add problem score to post
                post['problem_score'] = self.score_problem_indicator(title, body)
                filtered.append(post)
        
        return filtered

    def get_problem_categories(self, title: str, body: str = "") -> List[str]:
        """
        Suggest problem categories based on detected phrases.
        
        Args:
            title: Post title
            body: Optional post body
            
        Returns:
            List of suggested problem categories
        """
        matches = self.find_all_matches(f"{title} {body}")
        phrases = [m.phrase.lower() for m in matches]
        
        categories = []
        
        # Map phrases to categories
        if any(p in phrases for p in ['i hate when', 'frustrated with', 'annoying problem', 
                                       'frustrating part', 'really bothers me']):
            categories.append('General Frustration')
        
        if any(p in phrases for p in ['tired of doing', 'waste so much time', 'manual process',
                                       'so inefficient', 'too complicated']):
            categories.append('Workflow Inefficiency')
        
        if any(p in phrases for p in ['wish there was', 'wish i could', 'i wish',
                                       'someone should make', 'need a better way']):
            categories.append('Product Gap / Wishlist')
        
        if any(p in phrases for p in ['is there an app for', 'looking for software',
                                       'can anyone recommend', 'anyone know of']):
            categories.append('Product Search')
        
        if any(p in phrases for p in ['how can i automate', 'looking for a way to']):
            categories.append('Automation Need')
        
        if any(p in phrases for p in ['keep forgetting', 'difficult to manage', 
                                       'hard to manage', 'struggling with']):
            categories.append('Management Struggle')
        
        if any(p in phrases for p in ['bottleneck', 'overwhelmed by', 'problem with',
                                       'challenge with', 'issue with']):
            categories.append('Operational Challenge')
        
        if any(p in phrases for p in ['need help with', 'how do you handle',
                                       'does anyone else']):
            categories.append('Advice Seeking')
        
        return categories if categories else ['General Business Problem']
