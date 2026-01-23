"""
Reddit Client with Simulation Mode
Use sample data when Reddit is not accessible
"""

import time
import logging
import random
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """Data class representing a processed Reddit post."""
    id: str
    title: str
    body: str
    subreddit: str
    url: str
    author: str
    score: int
    num_comments: int
    created_utc: float
    comments: list = None  # Top comments from the post

    def __post_init__(self):
        if self.comments is None:
            self.comments = []

    @property
    def upvotes(self) -> int:
        """Alias for score to maintain compatibility with code using upvotes."""
        return self.score

    def to_dict(self) -> Dict:
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
            "comments": self.comments,
        }


class RedditClient:
    """
    Client for fetching Reddit posts.
    Falls back to simulation mode when Reddit is not accessible.
    """

    # Sample posts for simulation mode
    SAMPLE_POSTS = [
        {
            "subreddit": "Entrepreneur",
            "title": "Struggling with finding reliable contractors for my SaaS business",
            "body": "I've been trying to outsource my development work but keep getting subpar results. How do you guys find good developers who actually deliver on time?",
            "author": "startup_founder_2024",
            "score": 45,
            "num_comments": 23,
        },
        {
            "subreddit": "SaaS",
            "title": "Is there a tool for automating customer onboarding?",
            "body": "My SaaS is growing and onboarding new customers manually is taking too much time. Looking for automation tools or services that can help with this.",
            "author": "saas_owner_99",
            "score": 67,
            "num_comments": 31,
        },
        {
            "subreddit": "SideProject",
            "title": "I hate it when potential customers disappear after free trial",
            "body": "I have a 14-day free trial but 80% of users don't convert. Is there a tool or strategy to improve activation and conversion rates?",
            "author": "indie_hacker_xyz",
            "score": 89,
            "num_comments": 45,
        },
        {
            "subreddit": "Entrepreneur",
            "title": "Looking for a way to automate social media posting for my business",
            "body": "Managing multiple social media accounts is consuming my day. Need an affordable tool that can schedule posts across platforms.",
            "author": "small_biz_owner",
            "score": 34,
            "num_comments": 18,
        },
        {
            "subreddit": "SaaS",
            "title": "Business idea: AI-powered customer support for small businesses",
            "body": "Many small businesses can't afford human customer support 24/7. I'm thinking of building an AI chatbot service. Is there demand for this?",
            "author": "tech_entrepreneur",
            "score": 112,
            "num_comments": 56,
        },
        {
            "subreddit": "SideProject",
            "title": "Manual process for invoicing is wasting my time",
            "body": "I send 20+ invoices per week manually. Current solutions are either too expensive or too complex. Is there a simple, affordable alternative?",
            "author": "freelancer_dave",
            "score": 78,
            "num_comments": 42,
        },
        {
            "subreddit": "Entrepreneur",
            "title": "How do you manage multiple projects at once?",
            "body": "I'm juggling 3 different businesses and losing track of tasks. Looking for project management systems that actually work for entrepreneurs.",
            "author": "busy_founder",
            "score": 156,
            "num_comments": 67,
        },
        {
            "subreddit": "SaaS",
            "title": "Is there a tool for competitor price monitoring?",
            "body": "I want to track my competitors' pricing changes automatically. Current tools are enterprise-level and too expensive for startups.",
            "author": "pricing_guru",
            "score": 43,
            "num_comments": 29,
        },
        {
            "subreddit": "SideProject",
            "title": "Tired of repetitive data entry tasks",
            "body": "I spend 2 hours every day entering the same data into different systems. Looking for automation solutions that don't require coding skills.",
            "author": "automation_seeker",
            "score": 95,
            "num_comments": 51,
        },
        {
            "subreddit": "Entrepreneur",
            "title": "Wish there was an all-in-one business dashboard",
            "body": "I use 10+ different tools for my business. Having a single dashboard to see all metrics in one place would be amazing.",
            "author": "data_dashboard_fan",
            "score": 201,
            "num_comments": 89,
        },
    ]

    def __init__(self, config=None):
        if config is None:
            from config import Config
            config = Config()
        self._config = config
        self._use_simulation = False

    def test_connection(self) -> bool:
        """Test Reddit connection and fall back to simulation if needed."""
        print("   Testing Reddit connection...", end=" ", flush=True)

        # Try to fetch from Reddit
        import requests
        
        sources = [
            "https://api.pushshift.io/reddit/search/submission/?subreddit=Entrepreneur&size=1",
            "https://old.reddit.com/r/Entrepreneur/",
        ]

        for source in sources:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.get(source, headers=headers, timeout=10)
                if response.status_code == 200:
                    print("OK (Live Data)")
                    self._use_simulation = False
                    return True
            except Exception:
                continue

        # Fall back to simulation mode
        print("OK (Simulation Mode)")
        print("   Note: Using sample data because Reddit is not accessible.")
        print("   This can happen if: Reddit is blocking requests from your network,")
        print("   or you're in a region where Reddit is restricted.")
        self._use_simulation = True
        return True

    def fetch_posts(self, subreddit_name: str, limit: int = None) -> List[RedditPost]:
        """Fetch posts from Reddit or simulation mode."""
        if limit is None:
            limit = self._config.post_limit

        print(f"Fetching {limit} posts from r/{subreddit_name}...")

        if self._use_simulation:
            return self._fetch_simulation(subreddit_name, limit)
        else:
            return self._fetch_live(subreddit_name, limit)

    def _fetch_simulation(self, subreddit_name: str, limit: int) -> List[RedditPost]:
        """Generate realistic sample posts for testing."""
        import time
        
        posts = []
        filtered = [p for p in self.SAMPLE_POSTS if p["subreddit"] == subreddit_name]
        
        if not filtered:
            filtered = self.SAMPLE_POSTS.copy()

        # Limit to available posts
        count = min(limit, len(filtered))

        for i in range(count):
            post_data = filtered[i % len(filtered)]
            post = RedditPost(
                id=f"sim_{int(time.time())}_{i}",
                title=post_data["title"],
                body=post_data["body"],
                subreddit=post_data["subreddit"],
                url=f"https://reddit.com/r/{post_data['subreddit']}/comments/sim{i}/",
                author=post_data["author"],
                score=post_data["score"],
                num_comments=post_data["num_comments"],
                created_utc=time.time() - (i * 3600),
            )
            posts.append(post)

        print(f"   Generated {len(posts)} sample posts (simulation mode)")
        return posts

    def _fetch_live(self, subreddit_name: str, limit: int) -> List[RedditPost]:
        """Fetch posts from live sources (Pushshift or old Reddit)."""
        import requests
        from bs4 import BeautifulSoup
        import time as time_module

        # Try Pushshift first
        try:
            url = f"https://api.pushshift.io/reddit/search/submission/?subreddit={subreddit_name}&size={limit}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                posts = []
                for sub in data.get("data", []):
                    posts.append(RedditPost(
                        id=str(sub.get("id", "")),
                        title=sub.get("title", ""),
                        body=sub.get("selftext", "") or sub.get("url", ""),
                        subreddit=sub.get("subreddit", subreddit_name),
                        url=f"https://reddit.com{sub.get('permalink', '')}",
                        author=sub.get("author", "[deleted]"),
                        score=int(sub.get("score", 0)),
                        num_comments=int(sub.get("num_comments", 0)),
                        created_utc=float(sub.get("created_utc", 0)),
                    ))
                return posts
        except Exception:
            pass

        # Fallback to old.reddit.com
        try:
            url = f"https://old.reddit.com/r/{subreddit_name}/new/"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                posts = []
                for row in soup.find_all('div', class_='thing')[:limit]:
                    post = RedditPost(
                        id=row.get('data-id', ''),
                        title=row.find('a', class_='title').get_text(strip=True) if row.find('a', class_='title') else "",
                        body="",
                        subreddit=row.get('data-subreddit', subreddit_name),
                        url=f"https://reddit.com{row.get('data-permalink', '')}",
                        author=row.get('data-author', '[deleted]'),
                        score=int(row.get('data-score', 0)),
                        num_comments=int(row.get('data-comments', 0)),
                        created_utc=time_module.time(),
                    )
                    posts.append(post)
                return posts
        except Exception:
            pass

        return []

    def fetch_post_details(self, post: RedditPost, max_comments: int = 10) -> RedditPost:
        """Fetch full post details including body and top comments using Reddit JSON API."""
        import requests
        import time as time_module
        
        if self._use_simulation:
            # For simulation, add sample comments
            post.comments = [
                {"author": "helpful_user", "body": "Have you tried using XYZ tool? It solved this for me.", "score": 15},
                {"author": "another_user", "body": "I have the same problem. Would pay for a solution!", "score": 8},
            ]
            return post
        
        try:
            # Use Reddit JSON API to get post details and comments
            # Convert URL to .json endpoint
            post_url = post.url.rstrip('/')
            if 'reddit.com' not in post_url:
                print(f"   [DEBUG] Skipping non-reddit URL: {post_url[:50]}", flush=True)
                return post
            
            json_url = post_url + '.json'
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            
            response = requests.get(json_url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # First element is the post, second is comments
                if isinstance(data, list) and len(data) >= 1:
                    # Get post data
                    post_data = data[0].get('data', {}).get('children', [{}])[0].get('data', {})
                    
                    # Update body if we got selftext
                    selftext = post_data.get('selftext', '')
                    if selftext and selftext not in ['[removed]', '[deleted]', '']:
                        post.body = selftext
                        print(f"   [DEBUG] Got body: {len(selftext)} chars", flush=True)
                    
                    # Update num_comments from actual data
                    post.num_comments = post_data.get('num_comments', post.num_comments)
                    
                    # Get comments
                    if len(data) >= 2:
                        comments_data = data[1].get('data', {}).get('children', [])
                        comments = []
                        for comment in comments_data[:max_comments]:
                            if comment.get('kind') == 't1':  # t1 = comment
                                c_data = comment.get('data', {})
                                comment_body = c_data.get('body', '')
                                if comment_body and comment_body not in ['[removed]', '[deleted]']:
                                    comments.append({
                                        'author': c_data.get('author', '[deleted]'),
                                        'body': comment_body,
                                        'score': c_data.get('score', 0),
                                    })
                        post.comments = comments
                        if comments:
                            print(f"   [DEBUG] Got {len(comments)} comments", flush=True)
            else:
                print(f"   [DEBUG] Reddit API returned {response.status_code} for {post.id}", flush=True)
            
            # Small delay to avoid rate limiting
            time_module.sleep(0.3)
            
        except requests.exceptions.Timeout:
            print(f"   [DEBUG] Timeout fetching details for {post.id}", flush=True)
        except requests.exceptions.RequestException as e:
            print(f"   [DEBUG] Request error for {post.id}: {str(e)[:50]}", flush=True)
        except Exception as e:
            print(f"   [DEBUG] Error fetching {post.id}: {str(e)[:50]}", flush=True)
        
        return post

    def fetch_all_subreddits(self) -> Dict[str, List[RedditPost]]:
        """Fetch posts from all configured subreddits."""
        results = {}
        for subreddit in self._config.target_subreddits:
            posts = self.fetch_posts(subreddit)
            results[subreddit] = posts
        return results
