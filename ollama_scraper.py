"""
Reddit Startup Idea Scraper
Scans Reddit for startup ideas and analyzes them using local Ollama AI.
Compatible with Python 3.10+

Fixed bugs:
- Uses environment variable for Ollama model
- Added dependency error handling
- Increased timeout for large models like deepseek
"""

import csv
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' module not installed.")
    print("Please run: pip install requests")
    exit(1)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Force GPU usage for Ollama
os.environ["OLLAMA_GPU"] = "true"

# --- Configuration ---
REDDIT_BASE_URL = "https://www.reddit.com/r/{subreddit}/new.json"
OLLAMA_API_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"
# Use lighter model by default as requested
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SUBREDDITS = os.getenv("TARGET_SUBREDDITS", "Entrepreneur,SaaS,SideProject,smallbusiness,startups").split(",")

KEYWORDS = [
    # Pain points
    "struggling with", "hate it when", "is there a tool",
    "wish there was", "frustrated with", "looking for",
    "anyone else", "how do you", "need help with",
    "problem with", "tired of", "annoying", "waste time",
    # Solutions seeking
    "recommend", "alternative to", "better than", "cheaper than",
    "app for", "software for", "tool for", "service for",
    # Trends & opportunities
    "game changer", "trending", "booming", "growing fast",
    "just launched", "new startup", "raised funding", "went viral",
    # Lifestyle & productivity
    "save time", "make money", "side hustle", "passive income",
    "automate", "streamline", "simplify", "easier way",
    # Market gaps
    "doesn't exist", "no good option", "nothing works", "gap in market"
]

HEADERS = {
    "User-Agent": "StartupIdeaScraper/1.0 (Python 3.10+; Windows NT 10.0 Win64 x64)"
}


class RedditScraper:
    """Fetches posts from Reddit without using the official API."""

    def fetch_posts(self, subreddit: str, limit: int = 50) -> List[Dict[str, Any]]:
        posts = []
        try:
            url = REDDIT_BASE_URL.format(subreddit=subreddit)
            params = {"limit": limit}

            print(f"Fetching from r/{subreddit}...")
            response = requests.get(url, headers=HEADERS, params=params, timeout=15)

            if response.status_code != 200:
                print(f"Failed to fetch r/{subreddit}: Status {response.status_code}")
                return []

            data = response.json()

            if "data" not in data or "children" not in data["data"]:
                return []

            for child in data["data"]["children"]:
                post_data = child["data"]
                posts.append({
                    "title": post_data.get("title", ""),
                    "selftext": post_data.get("selftext", ""),
                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                    "num_comments": post_data.get("num_comments", 0),
                    "ups": post_data.get("ups", 0),
                    "subreddit": subreddit
                })

        except requests.exceptions.Timeout:
            print(f"Timeout fetching r/{subreddit}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching r/{subreddit}: {e}")
        except json.JSONDecodeError:
            print(f"Invalid JSON response from r/{subreddit}")

        return posts

    def filter_posts(self, posts: List[Dict[str, Any]], min_comments: int = 5) -> List[Dict[str, Any]]:
        filtered = []
        for post in posts:
            if post["num_comments"] < min_comments:
                continue

            content = (post["title"] + " " + post["selftext"]).lower()
            if any(keyword in content for keyword in KEYWORDS):
                filtered.append(post)

        return filtered


class AIAnalyzer:
    """Analyzes text using Groq Cloud API or local Ollama model."""

    def __init__(self):
        # Configuration
        self.provider = os.getenv("AI_PROVIDER", "ollama").lower()
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        
        # Groq Settings
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = "llama-3.3-70b-versatile"
        
        # Ollama Settings
        self.ollama_url = OLLAMA_API_URL
        self.ollama_model = OLLAMA_MODEL

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None

    def analyze_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        prompt = f"""You are a startup analyst specializing in finding opportunities for the Indian market. Analyze this Reddit post (mostly from US users) and return ONLY a valid JSON object.

Title: {post['title']}
Body: {post['selftext'][:1000]}

Consider:
1. What problem are people facing?
2. Is this solution available in India? If not, it's a market gap opportunity.
3. Is this a trending topic in the US that hasn't reached India yet?

JSON Format:
{{
  "problem": "one sentence describing the pain point",
  "audience": "who faces this problem",
  "startup_idea": "solution that could work in India",
  "us_trend": "is this trending in US? Yes/No",
  "india_gap": "does this exist in India? Yes/No/Partial",
  "india_opportunity": "why this could work in India",
  "pricing_inr": "suggested price in INR for Indian market",
  "revenue_potential": "High/Medium/Low",
  "validation_steps": ["step1", "step2", "step3"],
  "difficulty": 1-10,
  "competition_india": "Low/Medium/High",
  "risks": ["risk1", "risk2"]
}}"""
        
        # Try Groq first if enabled or in smart mode
        if self.groq_key and (self.provider == 'groq' or self.provider == 'smart'):
            try:
                print(f"Analyzing with Groq: '{post['title'][:40]}...'")
                result = self._call_groq(prompt)
                if result: return self._format_result(post, result)
            except Exception as e:
                print(f" -> Groq failed ({e}). Falling back to Ollama...")
        
        # Fallback to Ollama
        try:
            print(f"Analyzing with Ollama ({self.ollama_model}): '{post['title'][:40]}...'")
            result = self._call_ollama(prompt)
            if result: return self._format_result(post, result)
        except Exception as e:
            print(f" -> Ollama analysis error: {e}")
            
        return None

    def _call_groq(self, prompt: str) -> Optional[Dict[str, Any]]:
        payload = {
            "model": self.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        response = requests.post(
            self.groq_url, 
            headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            return self._extract_json(content)
        elif response.status_code == 429:
            raise Exception("Groq Rate Limit Exceeded")
        else:
            raise Exception(f"Groq Error {response.status_code}")

    def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 800}
        }
        response = requests.post(self.ollama_url, json=payload, timeout=120)
        if response.status_code == 200:
            content = response.json().get("response", "")
            return self._extract_json(content)
        return None

    def _format_result(self, post: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": post['title'],
            "url": post['url'],
            "num_comments": post['num_comments'],
            "ups": post['ups'],
            **analysis
        }


def save_to_csv(results: List[Dict[str, Any]], filename: str = "startup_ideas.csv") -> None:
    """Saves results to a CSV file compatible with Excel."""
    if not results:
        print("No results to save to CSV.")
        return

    fieldnames = [
        "Title", "Problem", "Audience", "Startup Idea",
        "US Trend", "India Gap", "India Opportunity", "Competition India",
        "Pricing INR", "Revenue Potential", "Difficulty (1-10)",
        "Risks", "Validation Steps", "Source URL"
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for r in results:
                risks_str = "; ".join(r.get('risks', []) or [])
                steps_str = "; ".join(r.get('validation_steps', []) or [])

                writer.writerow({
                    "Title": r.get('title', ''),
                    "Problem": r.get('problem', ''),
                    "Audience": r.get('audience', ''),
                    "Startup Idea": r.get('startup_idea', ''),
                    "US Trend": r.get('us_trend', ''),
                    "India Gap": r.get('india_gap', ''),
                    "India Opportunity": r.get('india_opportunity', ''),
                    "Competition India": r.get('competition_india', ''),
                    "Pricing INR": r.get('pricing_inr', ''),
                    "Revenue Potential": r.get('revenue_potential', ''),
                    "Difficulty (1-10)": r.get('difficulty', ''),
                    "Risks": risks_str,
                    "Validation Steps": steps_str,
                    "Source URL": r.get('url', '')
                })

        print(f"[OK] Excel-compatible CSV saved to: {filename}")

    except IOError as e:
        print(f"Error saving CSV: {e}")


def save_to_txt(results: List[Dict[str, Any]], filename: str = "startup_ideas_report.txt") -> None:
    """Saves a human-readable text report."""
    if not results:
        print("No results to save to TXT.")
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("       REDDIT STARTUP IDEAS REPORT\n")
            f.write("=" * 80 + "\n\n")

            for i, r in enumerate(results, 1):
                f.write(f"IDEA #{i}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Title:       {r.get('title', '')}\n")
                f.write(f"Problem:     {r.get('problem', '')}\n")
                f.write(f"Audience:    {r.get('audience', '')}\n")
                f.write(f"Startup Idea:{r.get('startup_idea', '')}\n")
                f.write(f"Pricing:     {r.get('pricing', '')}\n")
                f.write(f"Potential:   {r.get('revenue_potential', '')} | Difficulty: {r.get('difficulty', '')}/10\n")

                risks = r.get('risks', []) or []
                if risks:
                    f.write("Risks:\n")
                    for risk in risks:
                        f.write(f"  - {risk}\n")

                steps = r.get('validation_steps', []) or []
                if steps:
                    f.write("Validation Steps:\n")
                    for step in steps:
                        f.write(f"  - {step}\n")

                f.write(f"Source:      {r.get('url', '')}\n")
                f.write("\n" + "=" * 80 + "\n\n")

        print(f"[OK] Text Report saved to: {filename}")

    except IOError as e:
        print(f"Error saving TXT: {e}")


def check_ollama_connection() -> bool:
    """Check if Ollama is running."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def list_ollama_models() -> List[str]:
    """List available Ollama models."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def get_output_folder() -> str:
    """Create and return dated output folder path."""
    from datetime import datetime
    
    # Create scraped_data folder if it doesn't exist
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraped_data")
    os.makedirs(base_dir, exist_ok=True)
    
    # Create dated subfolder: YYYY-MM-DD_HHMMSS
    date_folder = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir = os.path.join(base_dir, date_folder)
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("REDDIT STARTUP IDEA SCRAPER")
    print("Using local Ollama AI for analysis")
    print("=" * 60)

    # Check Ollama connection
    if not check_ollama_connection():
        print(f"\nERROR: Cannot connect to Ollama")
        print(f"URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
        print("Please start Ollama first: ollama serve")
        return

    # List available models
    models = list_ollama_models()
    print(f"\n[OK] Connected to Ollama")
    print(f"Available models: {', '.join(models) if models else 'None found'}")
    print(f"Using model: {OLLAMA_MODEL}")
    
    if OLLAMA_MODEL not in models and models:
        print(f"\nWARNING: Model '{OLLAMA_MODEL}' not found in available models.")
        print(f"Available: {', '.join(models)}")
        print(f"Pull it with: ollama pull {OLLAMA_MODEL}")
    
    print()

    # Get min_comments from env
    min_comments = int(os.getenv("MIN_COMMENTS", "3"))

    scraper = RedditScraper()
    analyzer = OllamaAnalyzer()

    all_valid_posts = []

    print("--- Starting Data Collection ---")
    for sub in SUBREDDITS:
        raw_posts = scraper.fetch_posts(sub.strip())
        valid_posts = scraper.filter_posts(raw_posts, min_comments=min_comments)
        all_valid_posts.extend(valid_posts)
        time.sleep(1)  # Rate limiting

    print(f"\nTotal valid posts found: {len(all_valid_posts)}")

    if not all_valid_posts:
        print("No posts matched criteria. Exiting.")
        return

    print("\n--- Starting AI Analysis ---")
    final_results = []

    for i, post in enumerate(all_valid_posts):
        result = analyzer.analyze_post(post)
        if result:
            final_results.append(result)

        if (i + 1) % 5 == 0:
            print(f"Processed {i + 1}/{len(all_valid_posts)} posts...")

    # --- Output Phase ---
    print("\n--- Saving Results ---")
    
    # Get dated output folder
    output_dir = get_output_folder()
    print(f"[FOLDER] Saving to: {output_dir}")

    # 1. Save JSON
    json_file = os.path.join(output_dir, "startup_ideas.json")
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved JSON to {json_file}")
    except IOError as e:
        print(f"Error saving JSON: {e}")

    # 2. Save CSV
    save_to_csv(final_results, os.path.join(output_dir, "startup_ideas.csv"))

    # 3. Save TXT
    save_to_txt(final_results, os.path.join(output_dir, "startup_ideas_report.txt"))

    # 4. Console Summary
    print("\n--- Top Ideas Summary ---")
    for idea in final_results[:5]:
        print(f"\n[IDEA] {idea.get('startup_idea', 'N/A')}")
        print(f"   Problem: {idea.get('problem', 'N/A')}")
        print(f"   Revenue: {idea.get('revenue_potential', 'N/A')} | Difficulty: {idea.get('difficulty', 'N/A')}/10")

    print("\n" + "=" * 60)
    print(f"[DONE] Scan complete! Data saved to: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
