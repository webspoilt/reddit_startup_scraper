"""
Ollama Local AI Analyzer
Runs AI models locally using Ollama.
Totally free, no API limits, runs on your machine.

Setup:
1. Install Ollama: https://ollama.com/
2. Run: ollama serve
3. Pull a model: ollama pull llama3.2
   Or for smaller models: ollama pull phi3 or ollama pull tinyllama

Recommended models for this task:
- llama3.2:3b (best balance of speed and quality)
- phi3:3.8b (Microsoft's efficient model)
- gemma2:2b (Google's lightweight model)
- tinyllama:1.1b (fastest, lowest resource usage)
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

logger = logging.getLogger(__name__)


@dataclass
class PostAnalysis:
    """Data class representing AI analysis of a Reddit post."""
    original_title: str
    original_body: str
    subreddit: str
    post_url: str
    core_problem_summary: str
    target_audience: str
    startup_idea: str
    startup_type: str
    estimated_complexity: str
    potential_market_size: str
    confidence_score: float
    model_used: str
    analysis_timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_title": self.original_title,
            "original_body": self.original_body,
            "subreddit": self.subreddit,
            "post_url": self.post_url,
            "core_problem_summary": self.core_problem_summary,
            "target_audience": self.target_audience,
            "startup_idea": self.startup_idea,
            "startup_type": self.startup_type,
            "estimated_complexity": self.estimated_complexity,
            "potential_market_size": self.potential_market_size,
            "confidence_score": self.confidence_score,
            "model_used": self.model_used,
            "analysis_timestamp": self.analysis_timestamp,
        }

    def to_markdown(self) -> str:
        return f"""
### Original Post
**Title:** {self.original_title}

**Source:** [Reddit Link]({self.post_url})

**Subreddit:** r/{self.subreddit}

---

### Problem Analysis
**Core Problem:** {self.core_problem_summary}

**Target Audience:** {self.target_audience}

---

### Startup Idea
**Suggested Solution:** {self.startup_idea}

**Type:** {self.startup_type}

**Complexity:** {self.estimated_complexity}

**Market Size:** {self.potential_market_size}

**Confidence Score:** {self.confidence_score:.2f}
"""


class OllamaAnalyzer:
    """
    Local AI analyzer using Ollama.
    
    Benefits:
    - Totally free (no API costs)
    - No rate limits
    - Runs offline
    - Privacy-friendly (data stays on your machine)
    
    Setup:
    1. Install Ollama: https://ollama.com/
    2. Run: ollama serve
    3. Pull a model: ollama pull llama3.2
    """

    # Recommended models (ordered by quality/speed ratio)
    RECOMMENDED_MODELS = [
        "llama3.2:3b",      # Best balance, ~2GB RAM
        "llama3.2:1b",      # Faster, ~1GB RAM
        "phi3:3.8b",        # Microsoft's efficient model, ~2GB RAM
        "gemma2:2b",        # Google's model, ~2GB RAM
        "tinyllama:1.1b",   # Lightest option, ~700MB RAM
        "mistral:7b",       # Higher quality, ~4GB RAM
    ]

    def __init__(self, base_url: str = "http://localhost:11434", model: str = None):
        """
        Initialize the Ollama analyzer.
        
        Args:
            base_url: Ollama server URL
            model: Model name to use (auto-detects if None)
        """
        self._base_url = base_url.rstrip('/')
        self._model = model
        self._selected_model = None

        # Load from environment if not provided
        if not self._model:
            import os
            self._model = os.getenv("OLLAMA_MODEL", "")

        # Auto-detect available model
        self._selected_model = self._detect_model()

    def _detect_model(self) -> Optional[str]:
        """Detect which Ollama model is available."""
        # If user specified a model, try that first
        if self._model:
            available = self._list_models()
            if self._model in available:
                logger.info(f"Using specified model: {self._model}")
                return self._model
            elif self._model in self.RECOMMENDED_MODELS:
                # Try pulling or using anyway
                logger.info(f"Attempting to use model: {self._model}")
                return self._model

        # Try recommended models in order
        for model_name in self.RECOMMENDED_MODELS:
            try:
                # Check if model exists
                response = self._ollama_request("/api/show", {"name": model_name})
                if response:
                    logger.info(f"Found installed model: {model_name}")
                    return model_name
            except Exception:
                continue

        # Try any running model
        try:
            response = self._ollama_request("/api/tags")
            if response and "models" in response:
                if response["models"]:
                    model = response["models"][0]["name"]
                    logger.info(f"Using running model: {model}")
                    return model
        except Exception as e:
            logger.debug(f"Failed to list models: {e}")

        return None

    def _list_models(self) -> List[str]:
        """List installed Ollama models."""
        try:
            response = self._ollama_request("/api/tags")
            if response and "models" in response:
                return [m["name"] for m in response["models"]]
        except Exception as e:
            logger.debug(f"Failed to list models: {e}")
        return []

    def _ollama_request(self, endpoint: str, data: Dict = None, timeout: int = 120) -> Optional[Dict]:
        """Make a request to the Ollama API."""
        url = f"{self._base_url}{endpoint}"
        
        try:
            import os
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            if data:
                import json
                data = json.dumps(data).encode('utf-8')
                req = Request(url, data=data, headers={'Content-Type': 'application/json'})
            else:
                req = Request(url)

            with urlopen(req, timeout=timeout, context=ssl_context) as response:
                content = response.read().decode('utf-8')
                return json.loads(content) if content else None
        except HTTPError as e:
            logger.debug(f"Ollama HTTP error {e.code}: {e.reason}")
            return None
        except URLError as e:
            logger.debug(f"Ollama connection error: {e.reason}")
            return None
        except Exception as e:
            logger.debug(f"Ollama request failed: {e}")
            return None

    def _generate(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Generate response from Ollama."""
        data = {
            "model": self._selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 800,  # Limit response length
                "top_k": 40,
                "top_p": 0.9,
            }
        }

        response = self._ollama_request("/api/generate", data)

        if response and "response" in response:
            return response["response"]

        return None

    def _create_prompt(self, title: str, body: str) -> str:
        """Create the prompt for analysis."""
        return f"""You are an expert startup consultant. Analyze this Reddit post and output ONLY valid JSON:

Title: {title}
Content: {body}

Respond with this JSON structure (no markdown):
{{
  "core_problem_summary": "2-3 sentence summary",
  "target_audience": "specific group",
  "startup_idea": "Micro-SaaS idea",
  "startup_type": "Micro-SaaS",
  "estimated_complexity": "Low",
  "potential_market_size": "Medium",
  "confidence_score": 0.75
}}

JSON:"""

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the AI response into a dictionary."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            try:
                # Try to extract JSON
                cleaned = response_text.strip()
                
                # Remove common prefixes
                for prefix in ["```json", "```", "Here is the JSON:", "JSON:"]:
                    if cleaned.lower().startswith(prefix.lower()):
                        cleaned = cleaned[len(prefix):].strip()
                
                # Remove suffixes
                for suffix in ["```", "\n"]:
                    if cleaned.endswith(suffix):
                        cleaned = cleaned[:-len(suffix)].strip()
                
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Ollama response as JSON")
                return None

    def analyze_post(self, title: str, body: str, subreddit: str, post_url: str) -> Optional[PostAnalysis]:
        """Analyze a single post using local AI."""
        if not self._selected_model:
            logger.error("No Ollama model available")
            return None

        try:
            prompt = self._create_prompt(title, body)
            response_text = self._generate(prompt)

            if not response_text:
                logger.warning(f"No response from Ollama for: {title[:50]}...")
                return None

            analysis_data = self._parse_response(response_text)

            if analysis_data is None:
                logger.warning(f"Failed to parse response for: {title[:50]}...")
                return None

            return PostAnalysis(
                original_title=title,
                original_body=body,
                subreddit=subreddit,
                post_url=post_url,
                core_problem_summary=analysis_data.get("core_problem_summary", "Unable to identify problem"),
                target_audience=analysis_data.get("target_audience", "Unknown audience"),
                startup_idea=analysis_data.get("startup_idea", "No idea generated"),
                startup_type=analysis_data.get("startup_type", "Unknown"),
                estimated_complexity=analysis_data.get("estimated_complexity", "Unknown"),
                potential_market_size=analysis_data.get("potential_market_size", "Unknown"),
                confidence_score=analysis_data.get("confidence_score", 0.5),
                model_used=f"ollama/{self._selected_model}",
                analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        except Exception as e:
            logger.error(f"Error analyzing post with Ollama: {e}")
            return None

    def analyze_posts_batch(self, posts: list, progress_callback=None) -> List[PostAnalysis]:
        """Analyze multiple posts."""
        analyses: List[PostAnalysis] = []
        total = len(posts)

        for i, post in enumerate(posts):
            if progress_callback:
                progress_callback(i + 1, total)

            analysis = self.analyze_post(
                title=post.title,
                body=post.body,
                subreddit=post.subreddit,
                post_url=post.url,
            )

            if analysis:
                analyses.append(analysis)

            # Small delay between requests
            if i < total - 1:
                time.sleep(1)

        return analyses

    def test_connection(self) -> bool:
        """Test the Ollama connection."""
        if not self._selected_model:
            return False

        try:
            response = self._generate("Respond with 'OK'.")
            return response and "OK" in response.upper()
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False

    @property
    def model_name(self) -> str:
        """Return the selected model name."""
        return self._selected_model or "unknown"

    @property
    def is_available(self) -> bool:
        """Check if Ollama is running and has a model."""
        return self._selected_model is not None


def create_ollama_analyzer(config=None) -> Optional[OllamaAnalyzer]:
    """Factory function to create Ollama analyzer."""
    try:
        import os

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "")

        if config:
            base_url = getattr(config, 'ollama_base_url', base_url)
            model = getattr(config, 'ollama_model', model)

        analyzer = OllamaAnalyzer(base_url=base_url, model=model)

        if analyzer.is_available:
            logger.info(f"Ollama analyzer ready with model: {analyzer.model_name}")
            return analyzer
        else:
            logger.debug("Ollama not available (no model detected)")
            return None

    except Exception as e:
        logger.warning(f"Failed to create Ollama analyzer: {e}")
        return None
