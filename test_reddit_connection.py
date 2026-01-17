"""
Simple Reddit Connection Test Script
Run this to diagnose connection issues
"""

import requests

def test_reddit_connection():
    """Test basic Reddit JSON endpoint connectivity."""
    print("Testing Reddit JSON API connection...")
    print("-" * 50)

    # Test URLs
    test_urls = [
        ("Reddit JSON (new)", "https://www.reddit.com/r/test/new.json?limit=1"),
        ("Reddit JSON (hot)", "https://www.reddit.com/r/test/hot.json?limit=1"),
        ("Reddit HTML", "https://www.reddit.com/r/test/"),
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for name, url in test_urls:
        print(f"\nTesting: {name}")
        print(f"URL: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            if response.status_code == 200:
                print("SUCCESS!")
                if "json" in response.headers.get('Content-Type', ''):
                    data = response.json()
                    children = data.get("data", {}).get("children", [])
                    print(f"Posts found: {len(children)}")
            elif response.status_code == 429:
                print("RATE LIMITED - Too many requests")
            elif response.status_code == 403:
                print("FORBIDDEN - Access denied")
            elif response.status_code == 502:
                print("BAD GATEWAY - Reddit server error")
            else:
                print(f"Error: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"CONNECTION ERROR: {e}")
        except requests.exceptions.Timeout:
            print("TIMEOUT - Request took too long")
        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "-" * 50)
    print("Test complete!")

if __name__ == "__main__":
    test_reddit_connection()
