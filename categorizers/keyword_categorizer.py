"""
Keyword Categorizer Module
Categorizes business posts into industry/category buckets using keyword analysis.
Provides AI-free categorization as a fallback when Gemini API is unavailable.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CategoryMatch:
    """Represents a category match with scoring information."""
    category: str
    score: float
    matched_keywords: List[str]


class KeywordCategorizer:
    """
    Categorizes posts into business categories using keyword matching.
    
    Uses a comprehensive keyword dictionary to score posts against
    predefined business categories. Returns the highest-scoring category.
    """

    # Business category keywords
    CATEGORIES = {
        'Compliance & Data': [
            'compliance', 'gdpr', 'hipaa', 'legal', 'regulation', 'audit',
            'data privacy', 'security', 'certification', 'license', 'permit',
            'tax', 'paperwork', 'documentation', 'record keeping', 'reporting',
            'sox', 'pci', 'data protection', 'privacy policy', 'terms of service',
            'liability', 'insurance', 'permit', 'zoning', 'permitting'
        ],
        'Automated Hiring': [
            'hiring', 'recruit', 'recruiting', 'job posting', 'resume', 'interview',
            'candidate', 'talent', 'employee', 'employees', 'onboarding', 'staffing',
            'human resources', 'hr', 'payroll', 'benefits', 'hiring process',
            'recruitment', 'headhunter', 'staff', 'workforce', 'labor', 'contractor',
            'job description', 'hiring manager', 'talent acquisition'
        ],
        'Workflow Inefficiency': [
            'workflow', 'process', 'efficiency', 'efficiencies', 'manual', 'automate',
            'automated', 'automation', 'repetitive', 'time consuming', 'bottleneck',
            'slow', 'tedious', 'streamline', 'optimize', 'optimization', 'productivity',
            'task', 'tasks', 'integration', 'integrations', 'connecting', 'connect',
            'sync', 'synchronize', 'data entry', 'copy paste', 'copying', 'pasting'
        ],
        'Customer Management': [
            'customer', 'client', 'clients', 'relationship', 'crm', 'support',
            'communication', 'email', 'emails', 'follow up', 'follow-up', 'lead', 'leads',
            'sales pipeline', 'onboarding', 'retention', 'satisfaction', 'feedback',
            'review', 'reviews', 'referral', 'referrals', 'churn', 'acquisition',
            'account management', 'customer success', 'support ticket', 'help desk'
        ],
        'Financial Management': [
            'invoice', 'invoicing', 'payment', 'payments', 'billing', 'accounting',
            'budget', 'budgeting', 'expense', 'expenses', 'revenue', 'profit',
            'cash flow', 'bookkeeping', 'finance', 'financial', 'cost', 'costs',
            'pricing', 'quote', 'estimate', 'financial', 'taxes', 'tax return',
            'bookkeeper', 'quickbooks', 'xero', 'expense report', 'reimbursement'
        ],
        'Project Management': [
            'project', 'projects', 'deadline', 'deadlines', 'timeline', 'timelines',
            'milestone', 'task management', 'team collaboration', 'collaborate',
            'assign', 'tracking', 'track', 'progress', 'kanban', 'agile', 'scrum',
            'sprint', 'deliverable', 'stakeholder', 'stakeholders', 'gantt',
            'resource allocation', 'capacity planning', 'workload', 'prioritization',
            'roadmap', 'planning', 'scheduling', 'calendar', 'reminder', 'reminders'
        ],
        'Marketing & Sales': [
            'marketing', 'advertising', 'social media', 'seo', 'content', 'contents',
            'lead generation', 'conversion', 'conversions', 'campaign', 'brand',
            'outreach', 'cold call', 'cold calling', 'email marketing', 'analytics',
            'metrics', 'roi', 'return on investment', 'facebook', 'instagram',
            'linkedin', 'twitter', 'tiktok', 'youtube', 'television', 'tv',
            'print advertising', 'google ads', 'marketing automation', 'crm',
            'pipeline', 'closing deals', 'sales', 'selling', 'proposal', 'proposals'
        ],
        'Inventory & Operations': [
            'inventory', 'stock', 'supply chain', 'logistics', 'shipping',
            'warehouse', 'order management', 'procurement', 'vendor', 'supplier',
            'fulfillment', 'tracking', 'track', 'delivery', 'manufacturing',
            'production', 'assembly', 'components', 'parts', 'materials',
            'order fulfillment', 'dropshipping', 'ecommerce', 'online store',
            'product catalog', 'sku', 'barcode', 'qr code', 'inventory management'
        ],
        'Technical & IT': [
            'website', 'websites', 'domain', 'hosting', 'server', 'servers', 'api',
            'integration', 'integrations', 'software', 'tool', 'tools', 'database',
            'backup', 'migration', 'password', 'passwords', 'authentication',
            'cloud', 'cyber', 'technical issue', 'bug', 'bugs', 'glitch',
            'website builder', 'wordpress', 'shopify', 'host', 'domain name',
            'ssl', 'certificate', 'dns', 'redirect', 'page speed', 'loading',
            'mobile app', 'ios', 'android', 'application', 'app', 'apps',
            'software as a service', 'saas', 'subscription', 'licensing', 'license'
        ],
        'Real Estate & Property': [
            'real estate', 'property', 'properties', 'tenant', 'tenants', 'landlord',
            'rental', 'rentals', 'lease', 'leasing', 'mortgage', 'home', 'homes',
            'commercial', 'residential', 'investment property', 'flip', 'flipping',
            'renovation', 'remodel', 'construction', 'building', 'listings',
            'mls', 'realtor', 'broker', 'real estate agent', 'showings', 'viewings'
        ],
        'Food & Hospitality': [
            'restaurant', 'restaurants', 'food', 'cafe', 'café', 'coffee', 'catering',
            'menu', 'ordering', 'online ordering', 'delivery', 'takeout', 'pickup',
            'reservations', 'table management', 'point of sale', 'pos', 'hospitality',
            'hotel', 'hotels', 'motel', 'accommodation', 'booking', 'guest', 'guests',
            'kitchen', 'chef', 'cooking', 'recipe', 'recipes', 'inventory', 'food cost'
        ],
        'Health & Wellness': [
            'health', 'healthcare', 'medical', 'doctor', 'clinic', 'hospital',
            'patient', 'patients', 'wellness', 'fitness', 'gym', 'workout',
            'nutrition', 'diet', 'supplement', 'supplements', 'therapy', 'mental health',
            'telemedicine', 'health insurance', 'appointment', 'scheduling', 'billing',
            'electronic health records', 'ehr', 'emr', 'prescription', 'pharmacy'
        ],
        'Education & Training': [
            'education', 'learning', 'course', 'courses', 'training', 'tutorial',
            'tutorials', 'class', 'classes', 'student', 'students', 'teacher',
            'teachers', 'school', 'schools', 'university', 'college', 'university',
            'curriculum', 'syllabus', 'assignment', 'homework', 'grading', 'lms',
            'learning management', 'elearning', 'online course', 'certification',
            'certificate', 'workshop', 'webinar', 'knowledge base', 'help center'
        ],
        'General Business': [
            'business', 'businesses', 'company', 'companies', 'startup', 'startups',
            'entrepreneur', 'entrepreneurs', 'small business', 'owner', 'owners',
            'manager', 'management', 'operate', 'operating', 'running a business',
            'grow business', 'scale business', 'revenue', 'income', 'expense'
        ],
    }

    def __init__(self, custom_categories: Dict[str, List[str]] = None):
        """
        Initialize the categorizer with optional custom categories.
        
        Args:
            custom_categories: Dictionary of category -> keywords mappings
        """
        self.categories = self.CATEGORIES.copy()
        if custom_categories:
            self.categories.update(custom_categories)

    def categorize(self, title: str, body: str = "") -> CategoryMatch:
        """
        Categorize a post based on its content.
        
        Args:
            title: Post title
            body: Optional post body text
            
        Returns:
            CategoryMatch object with category, score, and matched keywords
        """
        content = f"{title} {body}".lower()
        
        # Score each category
        scores: Dict[str, float] = {}
        matched_keywords: Dict[str, List[str]] = {}

        for category, keywords in self.categories.items():
            category_score = 0.0
            found_keywords = []

            for keyword in keywords:
                # Check for keyword match (word boundary aware)
                if keyword in content:
                    found_keywords.append(keyword)
                    # Higher weight for multi-word phrases
                    if ' ' in keyword:
                        category_score += 2.0
                    else:
                        category_score += 1.0

            if found_keywords:
                scores[category] = category_score
                matched_keywords[category] = found_keywords

        if not scores:
            return CategoryMatch(
                category='General Business',
                score=0.1,
                matched_keywords=[]
            )

        # Get highest scoring category
        best_category = max(scores, key=scores.get)
        
        # Normalize score
        max_score = max(scores.values())
        normalized_score = scores[best_category] / max_score if max_score > 0 else 0.5

        return CategoryMatch(
            category=best_category,
            score=round(normalized_score, 3),
            matched_keywords=matched_keywords.get(best_category, [])
        )

    def categorize_with_details(self, title: str, body: str = "") -> Dict[str, Any]:
        """
        Get detailed categorization results including all category scores.
        
        Args:
            title: Post title
            body: Optional post body text
            
        Returns:
            Dictionary with primary category, all scores, and metadata
        """
        content = f"{title} {body}".lower()
        
        all_scores: Dict[str, Dict[str, Any]] = {}
        
        for category, keywords in self.categories.items():
            found_keywords = []
            
            for keyword in keywords:
                if keyword in content:
                    found_keywords.append(keyword)
            
            if found_keywords:
                # Calculate weighted score
                score = sum(2.0 if ' ' in kw else 1.0 for kw in found_keywords)
                
                all_scores[category] = {
                    'score': score,
                    'keyword_count': len(found_keywords),
                    'keywords': found_keywords
                }

        if not all_scores:
            return {
                'primary_category': 'General Business',
                'all_scores': {},
                'total_matches': 0,
                'categorization_confidence': 'low'
            }

        # Sort by score
        sorted_scores = sorted(all_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        primary = sorted_scores[0]
        primary_score = primary[1]['score']
        
        # Calculate confidence based on margin between top categories
        if len(sorted_scores) > 1:
            second_score = sorted_scores[1][1]['score']
            margin = primary_score - second_score
            if margin > 3:
                confidence = 'high'
            elif margin > 1:
                confidence = 'medium'
            else:
                confidence = 'low'
        else:
            confidence = 'high' if primary_score > 3 else 'medium'

        return {
            'primary_category': primary[0],
            'all_scores': dict(sorted_scores),
            'total_matches': sum(s['keyword_count'] for s in all_scores.values()),
            'categorization_confidence': confidence
        }

    def batch_categorize(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Categorize a batch of posts.
        
        Args:
            posts: List of post dictionaries with 'title' and optional 'body'
            
        Returns:
            Posts with added 'category' field
        """
        categorized = []
        
        for post in posts:
            title = post.get('title', '')
            body = post.get('body', '')
            
            result = self.categorize(title, body)
            
            # Add category info to post
            post['category'] = result.category
            post['category_score'] = result.score
            post['category_keywords'] = result.matched_keywords
            
            categorized.append(post)
        
        return categorized

    def get_category_keywords(self, category: str) -> List[str]:
        """Get keywords for a specific category."""
        return self.categories.get(category, [])

    def list_categories(self) -> List[str]:
        """List all available categories."""
        return list(self.categories.keys())

    def find_posts_by_category(self, posts: List[Dict[str, Any]], 
                                category: str) -> List[Dict[str, Any]]:
        """
        Filter posts to only those in a specific category.
        
        Args:
            posts: List of post dictionaries
            category: Category name to filter by
            
        Returns:
            Filtered list of posts in the specified category
        """
        return [p for p in posts if p.get('category') == category]

    def get_category_distribution(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get the distribution of categories across posts.
        
        Args:
            posts: List of categorized posts
            
        Returns:
            Dictionary of category -> count mappings
        """
        distribution: Dict[str, int] = {}
        
        for post in posts:
            cat = post.get('category', 'Uncategorized')
            distribution[cat] = distribution.get(cat, 0) + 1
        
        return distribution
