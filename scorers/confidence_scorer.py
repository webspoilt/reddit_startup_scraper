"""
Confidence Scorer Module
Calculates confidence scores for post analysis based on multiple factors.
Used for both keyword-based and AI-based analysis results.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceBreakdown:
    """Breakdown of confidence score components."""
    overall_score: float
    keyword_confidence: float
    content_quality_confidence: float
    engagement_confidence: float
    category_confidence: float
    factors: Dict[str, float]


class ConfidenceScorer:
    """
    Calculates confidence scores for analyzed posts.
    
    Combines multiple factors to produce a single confidence score
    that indicates how reliable the analysis is.
    """

    def __init__(self):
        """Initialize the confidence scorer with default weights."""
        # Weights for different confidence factors
        self.weights = {
            'keyword_match': 0.25,
            'content_length': 0.20,
            'category_strength': 0.20,
            'engagement': 0.15,
            'text_quality': 0.10,
            'problem_clarity': 0.10,
        }

    def calculate_confidence(
        self,
        title: str,
        body: str,
        category: str,
        category_score: float = 0.5,
        keyword_matches: list = None,
        upvotes: int = 0,
        num_comments: int = 0,
        problem_score: float = None,
        ai_confidence: float = None
    ) -> float:
        """
        Calculate overall confidence score for a post analysis.
        
        Args:
            title: Post title
            body: Post body text
            category: Assigned category
            category_score: Category match confidence (0-1)
            keyword_matches: List of matched keywords
            upvotes: Number of upvotes
            num_comments: Number of comments
            problem_score: Problem indicator score if available
            ai_confidence: AI-provided confidence if available
            
        Returns:
            Confidence score between 0 and 1
        """
        factors = {}

        # Keyword match confidence
        if keyword_matches:
            keyword_conf = min(len(keyword_matches) / 5, 1.0)  # Cap at 5 keywords
        else:
            keyword_conf = 0.3  # Default low confidence if no keywords
        factors['keyword_match'] = keyword_conf

        # Content quality confidence
        content_length = len(title) + len(body)
        if content_length < 50:
            content_conf = 0.3
        elif content_length < 200:
            content_conf = 0.6
        elif content_length < 1000:
            content_conf = 0.8
        else:
            content_conf = 1.0
        factors['content_length'] = content_conf

        # Category strength confidence
        factors['category_strength'] = category_score

        # Engagement confidence (upvotes + comments)
        engagement_score = min((upvotes + num_comments * 2) / 100, 1.0)
        factors['engagement'] = engagement_score

        # Text quality (has proper structure, not all caps, etc.)
        text_quality = self._assess_text_quality(title, body)
        factors['text_quality'] = text_quality

        # Problem clarity (if problem score available)
        if problem_score is not None:
            factors['problem_clarity'] = problem_score
        else:
            factors['problem_clarity'] = 0.5

        # If AI provided a confidence, blend it with our calculation
        if ai_confidence is not None:
            # Weight AI confidence higher (60%) vs our calculation (40%)
            our_confidence = self._weighted_average(factors)
            return (our_confidence * 0.4) + (ai_confidence * 0.6)

        return self._weighted_average(factors)

    def _assess_text_quality(self, title: str, body: str) -> float:
        """Assess the quality of the text content."""
        quality = 0.5  # Base quality

        # Positive factors
        if title and title[0].isupper():
            quality += 0.1
        if len(title) > 10:
            quality += 0.1
        if body and len(body) > 50:
            quality += 0.1
        if body and '.' in body:
            quality += 0.1

        # Negative factors
        if title.isupper():
            quality -= 0.2  # All caps suggests low quality
        if 'http' in body.lower() or 'www' in body.lower():
            quality += 0.05  # Links might indicate useful content
        if body.count('!') > 2:
            quality -= 0.1  # Too much exclamation

        return max(0.0, min(1.0, quality))

    def _weighted_average(self, factors: Dict[str, float]) -> float:
        """Calculate weighted average of confidence factors."""
        total_weight = 0.0
        weighted_sum = 0.0

        for factor, value in factors.items():
            weight = self.weights.get(factor, 0.1)
            weighted_sum += value * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5

        return weighted_sum / total_weight

    def get_confidence_breakdown(
        self,
        title: str,
        body: str,
        category: str,
        category_score: float = 0.5,
        keyword_matches: list = None,
        upvotes: int = 0,
        num_comments: int = 0,
        problem_score: float = None
    ) -> ConfidenceBreakdown:
        """
        Get detailed breakdown of confidence calculation.
        
        Args:
            Same as calculate_confidence()
            
        Returns:
            ConfidenceBreakdown with all factors and scores
        """
        factors = {}

        # Keyword match confidence
        if keyword_matches:
            keyword_conf = min(len(keyword_matches) / 5, 1.0)
        else:
            keyword_conf = 0.3
        factors['keyword_match'] = keyword_conf

        # Content length confidence
        content_length = len(title) + len(body)
        if content_length < 50:
            content_conf = 0.3
        elif content_length < 200:
            content_conf = 0.6
        elif content_length < 1000:
            content_conf = 0.8
        else:
            content_conf = 1.0
        factors['content_length'] = content_conf

        # Category strength confidence
        factors['category_strength'] = category_score

        # Engagement confidence
        engagement_score = min((upvotes + num_comments * 2) / 100, 1.0)
        factors['engagement'] = engagement_score

        # Text quality
        text_quality = self._assess_text_quality(title, body)
        factors['text_quality'] = text_quality

        # Problem clarity
        if problem_score is not None:
            factors['problem_clarity'] = problem_score
        else:
            factors['problem_clarity'] = 0.5

        overall = self._weighted_average(factors)

        return ConfidenceBreakdown(
            overall_score=round(overall, 3),
            keyword_confidence=round(keyword_conf, 3),
            content_quality_confidence=round(content_conf, 3),
            engagement_confidence=round(engagement_score, 3),
            category_confidence=round(category_score, 3),
            factors={k: round(v, 3) for k, v in factors.items()}
        )

    def calculate_ai_confidence(self, ai_response: Dict[str, Any]) -> float:
        """
        Extract confidence from AI response if provided.
        
        Args:
            ai_response: Dictionary returned by AI analysis
            
        Returns:
            Confidence score if found, None otherwise
        """
        # Check for confidence_score field
        if 'confidence_score' in ai_response:
            return float(ai_response['confidence_score'])

        # Check for nested confidence
        if 'analysis' in ai_response:
            if 'confidence' in ai_response['analysis']:
                return float(ai_response['analysis']['confidence'])

        return None

    def interpret_confidence(self, score: float) -> str:
        """
        Convert numeric confidence to descriptive label.
        
        Args:
            score: Confidence score between 0 and 1
            
        Returns:
            Descriptive label: 'very low', 'low', 'medium', 'high', 'very high'
        """
        if score >= 0.9:
            return 'very high'
        elif score >= 0.7:
            return 'high'
        elif score >= 0.5:
            return 'medium'
        elif score >= 0.3:
            return 'low'
        else:
            return 'very low'

    def rate_post_quality(self, confidence: float, 
                          upvotes: int = 0,
                          num_comments: int = 0) -> Dict[str, Any]:
        """
        Rate overall post quality combining multiple factors.
        
        Args:
            confidence: Confidence score
            upvotes: Post upvotes
            num_comments: Number of comments
            
        Returns:
            Quality rating dictionary
        """
        # Engagement score
        engagement_score = min((upvotes + num_comments * 2) / 200, 1.0)
        
        # Combined quality score
        quality_score = (confidence * 0.6) + (engagement_score * 0.4)
        
        # Determine quality tier
        if quality_score >= 0.8:
            tier = 'A - High Quality'
            description = 'Strong analysis potential - good problem signal'
        elif quality_score >= 0.6:
            tier = 'B - Good Quality'
            description = 'Decent analysis potential - worth reviewing'
        elif quality_score >= 0.4:
            tier = 'C - Average Quality'
            description = 'Moderate analysis potential - may need more context'
        elif quality_score >= 0.2:
            tier = 'D - Low Quality'
            description = 'Weak analysis potential - limited problem signal'
        else:
            tier = 'F - Poor Quality'
            description = 'Not suitable for analysis - unclear or low quality'
        
        return {
            'quality_score': round(quality_score, 3),
            'tier': tier,
            'description': description,
            'confidence_label': self.interpret_confidence(confidence),
            'engagement_score': round(engagement_score, 3)
        }
