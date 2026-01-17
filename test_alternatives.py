"""
Test script for alternative Reddit data sources
"""

import requests

def test_alternatives():
    """Test various Reddit data sources."""
    print("Testing alternative Reddit data sources...")
    print("-" * 60)

    sources = [
        ("Pushshift v2", "https://api2.pushshift.io/reddit/search/submission/?subreddit=Entrepreneur&size=3"),
        ("Pushshift Reddit Archive", "https://gql.pushshift.io/reddit/search/submission?subreddit=Entrepreneur&size=3"),
        ("Reddit Media", "https://www.reddit.com/media/r/Entrepreneur/new.json"),
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for name, url in sources:
        print(f"\nTesting: {name}")
        print(f"URL: {url[:80]}...")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("SUCCESS!")
                try:
                    data = response.json()
                    if isinstance(data, list):
                        posts = data
                    elif isinstance(data, dict):
                        posts = data.get("data", [])
                    else:
                        posts = []
                    print(f"Posts found: {len(posts)}")
                    return True
                except Exception as e:
                    print(f"Parse error: {e}")
            elif response.status_code == 403:
                print("BLOCKED by Reddit")
            elif response.status_code == 522:
                print("SERVER DOWN (Pushshift)")
            else:
                print(f"Error: {response.status_code}")
        except Exception as e:
            print(f"Connection error: {e}")

    print("\n" + "-" * 60)
    print("All sources failed. Reddit may be blocking all automated access.")
    return False

if __name__ == "__main__":
    test_alternatives()
