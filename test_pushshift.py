"""
Test script for Pushshift API (backup data source for Reddit)
"""

import requests

def test_pushshift():
    """Test Pushshift API connection."""
    print("Testing Pushshift API...")
    print("-" * 50)

    url = "https://api.pushshift.io/reddit/search/submission/?subreddit=Entrepreneur&size=5"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        print(f"URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("SUCCESS!")
            data = response.json()
            posts = data.get("data", [])
            print(f"Posts retrieved: {len(posts)}")

            for i, post in enumerate(posts[:3], 1):
                print(f"\n{i}. {post.get('title', 'N/A')[:60]}...")
                print(f"   Author: {post.get('author', 'N/A')}")
                print(f"   Score: {post.get('score', 0)}")
                print(f"   Comments: {post.get('num_comments', 0)}")
        else:
            print(f"Error: {response.text[:200]}")

    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "-" * 50)

if __name__ == "__main__":
    test_pushshift()
