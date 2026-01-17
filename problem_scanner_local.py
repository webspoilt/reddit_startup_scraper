"""
Reddit Business Problem Scanner - Local Edition
Uses advanced local pattern matching, keyword analysis, and heuristics.
Eliminates rate limits by doing all processing locally.

Fixed bugs:
- Method name mismatch: _calculate_problem_severity -> _calculate_problem_severity_score
- Clean imports
"""

import os
import csv
import re
import praw
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Reddit API credentials (loaded from environment variables)
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'ProblemScanner/1.0')

# Subreddits to scan
SUBREDDITS = ['SaaS', 'smallbusiness', 'realestate', 'entrepreneur', 'business', 'startups']

# ============================================================================
# ADVANCED LOCAL PATTERN MATCHING ENGINE
# ============================================================================

class LocalProblemAnalyzer:
    """
    Advanced local analyzer that simulates AI categorization using
    sophisticated pattern matching, keyword weighting, and heuristics.
    No external APIs - all processing done locally.
    """
    
    def __init__(self):
        # Define comprehensive keyword dictionaries for each category
        self.category_keywords = {
            'Compliance & Data': {
                'primary': [
                    'compliance', 'gdpr', 'hipaa', 'legal', 'regulation', 'audit',
                    'data privacy', 'security', 'certification', 'license', 'permit'
                ],
                'secondary': [
                    'paperwork', 'documentation', 'record keeping', 'reporting',
                    'data protection', 'consent', 'cookies', 'privacy policy',
                    'terms of service', 'disclaimer', 'liability', 'contract'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Automated Hiring': {
                'primary': [
                    'hiring', 'recruit', 'job posting', 'resume', 'interview',
                    'candidate', 'talent', 'employee', 'onboarding', 'staffing'
                ],
                'secondary': [
                    'human resources', 'hr', 'payroll', 'benefits', 'hiring process',
                    'job application', 'hiring manager', 'recruiter', 'background check',
                    'reference check', 'job description', 'employment'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Workflow Inefficiency': {
                'primary': [
                    'workflow', 'process', 'efficiency', 'automate', 'manual',
                    'repetitive', 'time consuming', 'bottleneck', 'slow', 'tedious'
                ],
                'secondary': [
                    'streamline', 'optimize', 'productivity', 'task', 'integration',
                    'duplicate work', 'copy paste', 'data entry', 'spreadsheet hell',
                    'disorganized', 'chaotic', 'messy', 'overwhelmed'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Customer Management': {
                'primary': [
                    'customer', 'client', 'relationship', 'crm', 'support',
                    'communication', 'follow up', 'lead', 'sales pipeline'
                ],
                'secondary': [
                    'onboarding', 'retention', 'satisfaction', 'feedback', 'review',
                    'nurture', 'prospect', 'deal', 'closing', 'proposal', 'quote'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Financial Management': {
                'primary': [
                    'invoice', 'payment', 'billing', 'accounting', 'budget',
                    'expense', 'revenue', 'profit', 'cash flow', 'bookkeeping'
                ],
                'secondary': [
                    'finance', 'cost', 'pricing', 'quote', 'estimate', 'financial',
                    'receipt', 'transaction', 'bank', 'credit', 'debit', 'taxes',
                    'quarterly', 'annual', 'forecast', 'p&l', 'balance sheet'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Project Management': {
                'primary': [
                    'project', 'deadline', 'timeline', 'milestone', 'task management',
                    'team collaboration', 'assign', 'track', 'progress'
                ],
                'secondary': [
                    'kanban', 'agile', 'scrum', 'sprint', 'deliverable', 'stakeholder',
                    'gantt', 'resource', 'capacity', 'workload', 'assignment',
                    'due date', 'priority', 'status update', 'standup'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Marketing & Sales': {
                'primary': [
                    'marketing', 'advertising', 'social media', 'seo', 'content',
                    'lead generation', 'conversion', 'campaign', 'brand', 'outreach'
                ],
                'secondary': [
                    'cold call', 'email marketing', 'analytics', 'metrics', 'roi',
                    'funnel', 'landing page', 'cta', 'click', 'impression', 'reach',
                    'engagement', 'follower', 'viral', 'organic', 'paid ads'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Inventory & Operations': {
                'primary': [
                    'inventory', 'stock', 'supply chain', 'logistics', 'shipping',
                    'warehouse', 'order management', 'procurement', 'vendor', 'supplier'
                ],
                'secondary': [
                    'fulfillment', 'tracking', 'delivery', 'manufacturing',
                    'reorder', 'backorder', 'sku', 'barcode', 'lot', 'batch',
                    'quality control', 'inspection', 'customs', 'freight'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
            'Technical & IT': {
                'primary': [
                    'website', 'domain', 'hosting', 'server', 'api', 'integration',
                    'software', 'tool', 'database', 'backup', 'migration'
                ],
                'secondary': [
                    'password', 'authentication', 'cloud', 'cyber', 'technical issue',
                    'bug', 'glitch', 'crash', 'error', 'downtime', 'slow loading',
                    'responsive', 'mobile', 'desktop', 'browser', 'plugin', 'extension'
                ],
                'weight': {'primary': 3, 'secondary': 1}
            },
        }
        
        # Problem intensity indicators
        self.pain_indicators = {
            'high': ['hate', 'annoying', 'frustrated', 'tired', 'worst', 'horrible', 'terrible', 'awful'],
            'medium': ['wish', 'struggling', 'difficult', 'hard', 'challenge', 'problem', 'issue'],
            'low': ['looking for', 'thinking about', 'considering', 'wondering', 'curious'],
        }
        
        # Solution intent indicators
        self.solution_intent = [
            'app for', 'software', 'tool', 'automation', 'system', 'platform',
            'solution', 'service', 'any recommendations', 'can someone', 'how to',
            'best way', 'automate', 'streamline', 'integrate', 'simplify'
        ]
    
    def analyze(self, title: str, body: str) -> Dict:
        """
        Main analysis function that processes a post and returns detailed insights.
        """
        content = f"{title} {body}".lower()
        words = re.findall(r'\b\w+\b', content)
        
        # Calculate category scores
        category_scores = self._calculate_category_scores(content, words)
        
        # Determine primary category
        primary_category = max(category_scores, key=category_scores.get) if category_scores else 'General Business'
        
        # Calculate pain intensity
        pain_intensity = self._calculate_pain_intensity(content)
        
        # Detect solution intent
        has_solution_intent = any(indicator in content for indicator in self.solution_intent)
        
        # Calculate confidence based on keyword density and match quality
        confidence = self._calculate_confidence(category_scores, content, words)
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(content)
        
        # Detect business type
        business_type = self._detect_business_type(content)
        
        return {
            'category': primary_category,
            'category_scores': category_scores,
            'confidence': confidence,
            'pain_intensity': pain_intensity,
            'has_solution_intent': has_solution_intent,
            'key_phrases': key_phrases,
            'business_type': business_type,
            # FIX: Call the correctly named method
            'problem_severity_score': self._calculate_problem_severity_score(category_scores, pain_intensity, has_solution_intent),
        }
    
    def _calculate_category_scores(self, content: str, words: List[str]) -> Dict[str, float]:
        """Calculate weighted scores for each category."""
        scores = {}
        
        for category, data in self.category_keywords.items():
            score = 0
            
            # Check primary keywords (higher weight)
            for keyword in data['primary']:
                if keyword in content:
                    # Count occurrences and calculate proximity bonus
                    count = content.count(keyword)
                    score += count * data['weight']['primary']
            
            # Check secondary keywords (lower weight)
            for keyword in data['secondary']:
                if keyword in content:
                    count = content.count(keyword)
                    score += count * data['weight']['secondary']
            
            # Bonus for keyword combinations within same category
            if score > 0:
                # Check if multiple keywords from same category appear close together
                primary_found = [k for k in data['primary'] if k in content]
                if len(primary_found) >= 2:
                    score *= 1.3  # 30% bonus for category coherence
            
            scores[category] = score
        
        return scores
    
    def _calculate_pain_intensity(self, content: str) -> str:
        """Determine how intense the pain/exasperation is in the post."""
        high_count = sum(1 for word in self.pain_indicators['high'] if word in content)
        medium_count = sum(1 for word in self.pain_indicators['medium'] if word in content)
        low_count = sum(1 for word in self.pain_indicators['low'] if word in content)
        
        if high_count >= 2:
            return 'HIGH'
        elif high_count >= 1 or medium_count >= 3:
            return 'MEDIUM-HIGH'
        elif medium_count >= 1 or low_count >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_confidence(self, scores: Dict, content: str, words: List[str]) -> float:
        """Calculate confidence score based on analysis quality."""
        max_score = max(scores.values()) if scores else 0
        total_score = sum(scores.values())
        
        # Factor 1: Dominance of top category
        dominance = max_score / (total_score + 1) if total_score > 0 else 0
        
        # Factor 2: Content length (more content = more confident)
        length_factor = min(len(content) / 500, 1.0)
        
        # Factor 3: Category signal strength
        signal_strength = min(max_score / 10, 1.0)
        
        # Combine factors with weights
        confidence = (dominance * 0.4) + (length_factor * 0.3) + (signal_strength * 0.3)
        
        return round(min(max(confidence, 0.1), 0.99), 2)
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract meaningful key phrases from the content."""
        phrases = []
        
        # Common business problem patterns
        patterns = [
            r'\b\w+\s+management\b',
            r'\b\w+\s+automation\b',
            r'\b\w+\s+tracking\b',
            r'\b\w+\s+reporting\b',
            r'\b\w+\s+integration\b',
            r'\b\w+\s+workflow\b',
            r'\b\w+\s+process\b',
            r'\bmanual\s+\w+\b',
            r'\btime\s+consuming\b',
            r'\brepetitive\s+\w+\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            phrases.extend([m for m in matches if len(m) > 3])
        
        # Remove duplicates and limit
        unique_phrases = list(set(phrases))[:5]
        return unique_phrases
    
    def _detect_business_type(self, content: str) -> str:
        """Detect the type of business or industry mentioned."""
        business_indicators = {
            'Real Estate': ['property', 'tenant', 'lease', 'mortgage', 'landlord', 'rental', 'listing'],
            'E-commerce': ['shop', 'store', 'product', 'order', 'customer', 'cart', 'checkout'],
            'SaaS': ['software', 'subscription', 'users', 'features', 'dashboard', 'saas'],
            'Consulting': ['client', 'project', 'deliverable', 'proposal', 'billable', 'engagement'],
            'Agency': ['campaign', 'creative', 'client', 'deadline', 'deliverables', 'retainer'],
            'Healthcare': ['patient', 'appointment', 'medical', 'health', 'clinical', 'provider'],
            'Legal': ['client', 'case', 'court', 'filing', 'deadline', 'document', 'contract'],
            'Manufacturing': ['production', 'inventory', 'order', 'supply', 'quality', 'assembly'],
            'Freelance': ['client', 'project', 'hourly', 'rate', 'deadline', 'invoice', 'scope'],
        }
        
        for business_type, indicators in business_indicators.items():
            matches = sum(1 for ind in indicators if ind in content)
            if matches >= 2:
                return business_type
        
        return 'General Business'
    
    def _calculate_problem_severity_score(self, scores: Dict, pain_intensity: str, 
                                         has_solution_intent: bool) -> int:
        """Calculate an overall problem severity score (1-10)."""
        base_score = 5  # Start at middle
        
        # Category score contribution
        max_score = max(scores.values()) if scores else 0
        if max_score >= 10:
            base_score += 2
        elif max_score >= 5:
            base_score += 1
        
        # Pain intensity contribution
        pain_map = {'HIGH': 3, 'MEDIUM-HIGH': 2, 'MEDIUM': 1, 'LOW': 0}
        base_score += pain_map.get(pain_intensity, 0)
        
        # Solution intent contribution
        if has_solution_intent:
            base_score += 1
        
        return min(max(base_score, 1), 10)  # Clamp between 1 and 10


# ============================================================================
# PROBLEM PHRASE DETECTION
# ============================================================================

# Comprehensive list of problem indicator phrases
PROBLEM_PHRASES = [
    # Strong pain indicators
    'i hate when', "i hate that", 'it\'s so annoying', 'so frustrating',
    'drives me crazy', 'this is ridiculous', 'can\'t believe', 'waste so much',
    'tired of doing', 'sick of', 'fed up with', 'worst part is',
    
    # Solution seeking indicators
    'is there an app for', 'looking for a way', 'wish there was',
    'anyone know of', 'can anyone recommend', 'looking for software',
    'need a tool', 'how can i automate', 'how do you handle',
    'what do you use for', 'anyone have a solution', 'best way to',
    
    # Problem description indicators
    'struggling with', 'difficult to manage', 'manual process',
    'keep forgetting', 'time consuming', 'overwhelmed by',
    'too many', 'not enough time', 'can\'t keep up', 'falling behind',
    
    # Inefficiency indicators
    'bottleneck', 'inefficient', 'slow', 'tedious', 'repetitive',
    'duplicating work', 'copy and paste', 'data entry', 'spreadsheet',
    'scattered', 'disorganized', 'no good option', 'nothing works',
    
    # Feature requests
    'wish i could', 'would be nice if', 'should have', 'needs to',
    'wish it had', 'missing feature', 'no easy way', 'hard to',
]

# ============================================================================
# REDDIT API FUNCTIONS
# ============================================================================

def authenticate_reddit() -> Optional[praw.Reddit]:
    """Authenticates with Reddit API using PRAW."""
    try:
        if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
            print("ERROR: Reddit API credentials not found!")
            print("Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in your .env file")
            return None
        
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            check_for_updates=False,
        )
        
        # Test connection
        try:
            _ = reddit.user.me()
            print("✓ Authenticated with Reddit API")
        except Exception:
            print("✓ Connected to Reddit API (read-only mode)")
        
        return reddit
        
    except Exception as e:
        print(f"ERROR: Authentication failed - {e}")
        return None


def contains_problem_phrase(text: str) -> bool:
    """Checks if text contains any problem indicator phrases."""
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in PROBLEM_PHRASES)


def extract_post_data(post, analyzer: LocalProblemAnalyzer) -> Optional[Dict]:
    """Extracts and analyzes data from a Reddit post."""
    try:
        title = post.title
        body = post.selftext if hasattr(post, 'selftext') else ''
        
        # Skip removed/deleted posts
        if body in ['[removed]', '[deleted]']:
            body = ''
        
        # Clean up body text
        body = re.sub(r'http\S+', '', body)  # Remove URLs
        body = re.sub(r'\s+', ' ', body).strip()  # Normalize whitespace
        if len(body) > 1000:
            body = body[:1000] + '...'
        
        # Skip posts that are too short or mostly links
        if len(title) < 20:
            return None
        
        # Analyze the post
        analysis = analyzer.analyze(title, body)
        
        # Build the data dictionary
        return {
            'title': title,
            'body': body,
            'upvotes': post.score,
            'url': f"https://www.reddit.com{post.permalink}",
            'subreddit': post.subreddit.display_name,
            'category': analysis['category'],
            'confidence': analysis['confidence'],
            'pain_intensity': analysis['pain_intensity'],
            'solution_seeking': analysis['has_solution_intent'],
            'problem_severity': analysis['problem_severity_score'],
            'key_phrases': '|'.join(analysis['key_phrases']),
            'business_type': analysis['business_type'],
            'posted_date': datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
            'num_comments': post.num_comments,
        }
        
    except Exception as e:
        print(f"    Warning: Error processing post: {e}")
        return None


def search_subreddit(reddit: praw.Reddit, subreddit_name: str, 
                    analyzer: LocalProblemAnalyzer, limit: int = 100) -> List[Dict]:
    """Searches a subreddit for problem posts."""
    found_problems = []
    subreddit = reddit.subreddit(subreddit_name)
    
    print(f"\nScanning r/{subreddit_name}...")
    
    try:
        # Search multiple sorting methods
        for sort_method, max_limit in [('hot', limit), ('new', limit), ('top', limit)]:
            try:
                if sort_method == 'hot':
                    posts = subreddit.hot(limit=max_limit)
                elif sort_method == 'new':
                    posts = subreddit.new(limit=max_limit)
                else:
                    posts = subreddit.top(limit=max_limit)
                
                for post in posts:
                    if contains_problem_phrase(post.title):
                        post_data = extract_post_data(post, analyzer)
                        if post_data:
                            # Check for duplicates
                            if not any(p['title'] == post.title for p in found_problems):
                                found_problems.append(post_data)
                                print(f"  ✓ Found: {post.title[:55]}...")
                
            except Exception as e:
                print(f"  Warning: Error with {sort_method} sort: {e}")
                continue
                
    except Exception as e:
        print(f"  ERROR scanning r/{subreddit_name}: {e}")
    
    return found_problems


# ============================================================================
# CSV STORAGE AND REPORTING
# ============================================================================

def save_to_csv(data: List[Dict], filename: str = 'market_research.csv') -> None:
    """Saves collected problem data to CSV."""
    if not data:
        print("No data to save!")
        return
    
    fieldnames = [
        'title', 'body', 'upvotes', 'url', 'subreddit', 'category',
        'confidence', 'pain_intensity', 'solution_seeking', 'problem_severity',
        'key_phrases', 'business_type', 'posted_date', 'num_comments'
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            # Sort by upvotes and problem severity
            sorted_data = sorted(data, key=lambda x: (x['upvotes'], x['problem_severity']), reverse=True)
            writer.writerows(sorted_data)
        
        print(f"\n✓ Saved {len(data)} problems to {filename}")
        
    except Exception as e:
        print(f"ERROR saving to CSV: {e}")


def print_summary(data: List[Dict]) -> None:
    """Prints a comprehensive summary of results."""
    if not data:
        print("\nNo problems found!")
        return
    
    # Category breakdown
    category_counts = defaultdict(int)
    severity_totals = defaultdict(list)
    business_types = defaultdict(int)
    
    for item in data:
        category_counts[item['category']] += 1
        severity_totals[item['category']].append(item['problem_severity'])
        business_types[item['business_type']] += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("MARKET RESEARCH SUMMARY - BUSINESS PROBLEM SCANNER")
    print("=" * 70)
    print(f"\nTotal problems found: {len(data)}")
    
    # Problems by category
    print(f"\n📊 Problems by Category:")
    sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    for cat, count in sorted_cats:
        avg_severity = sum(severity_totals[cat]) / len(severity_totals[cat])
        bar = "█" * min(count, 30)
        print(f"  {cat:<25} {bar} {count} (avg severity: {avg_severity:.1f})")
    
    # Business types
    print(f"\n🏢 Business Types Identified:")
    sorted_business = sorted(business_types.items(), key=lambda x: x[1], reverse=True)
    for biz, count in sorted_business[:5]:
        print(f"  • {biz}: {count} problems")
    
    # Pain intensity distribution
    pain_dist = defaultdict(int)
    for item in data:
        pain_dist[item['pain_intensity']] += 1
    print(f"\n😖 Pain Intensity Distribution:")
    for level in ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'LOW']:
        count = pain_dist.get(level, 0)
        bar = "█" * min(count * 2, 30)
        print(f"  {level:<15} {bar} {count}")
    
    # Top opportunities
    print(f"\n🎯 Top Opportunities (High Severity + High Engagement):")
    high_priority = [d for d in data if d['problem_severity'] >= 7 and d['upvotes'] >= 10]
    sorted_priority = sorted(high_priority, key=lambda x: x['upvotes'], reverse=True)[:5]
    for i, item in enumerate(sorted_priority, 1):
        print(f"  {i}. [{item['upvotes']} upvotes, severity {item['problem_severity']}]")
        print(f"     {item['title'][:65]}...")
        print(f"     Category: {item['category']} | Business: {item['business_type']}")
    
    print("=" * 70)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to run the scanner."""
    print("=" * 70)
    print("REDDIT BUSINESS PROBLEM SCANNER - LOCAL AI EDITION")
    print("No external API calls - all processing done locally")
    print("=" * 70)
    
    # Initialize the local analyzer
    analyzer = LocalProblemAnalyzer()
    
    # Authenticate with Reddit
    reddit = authenticate_reddit()
    if not reddit:
        print("\nPlease set up your Reddit API credentials:")
        print("1. Go to https://www.reddit.com/prefs/apps")
        print("2. Create a 'script' app")
        print("3. Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to your .env file")
        return
    
    # Collect all problems
    all_problems = []
    
    for subreddit in SUBREDDITS:
        problems = search_subreddit(reddit, subreddit, analyzer, limit=100)
        all_problems.extend(problems)
    
    # Remove duplicates
    seen_titles = set()
    unique_problems = []
    for problem in all_problems:
        if problem['title'] not in seen_titles:
            seen_titles.add(problem['title'])
            unique_problems.append(problem)
    
    # Print summary and save
    print_summary(unique_problems)
    save_to_csv(unique_problems)
    
    print("\n✅ Scan complete! Check market_research.csv for your data.")


if __name__ == "__main__":
    main()
