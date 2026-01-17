"""
Hugging Face Inference API Analyzer
Uses Hugging Face's free serverless inference API.
No API keys needed for basic usage, generous free tier.

Get started: https://huggingface.co/inference
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


class HuggingFaceAnalyzer:
    """
    AI analyzer using Hugging Face Inference API.
    
    Benefits:
    - Free tier available
    - No credit card required
    - Multiple model options
    
    Note: Free tier has rate limits and can be slower than paid.
    Best for: testing and small projects.
    
    Get started: https://huggingface.co/inference
    """

    # Models suitable for text analysis (inference API compatible)
    AVAILABLE_MODELS = [
        "microsoft/Phi-3-mini-4k-instruct",  # Efficient, high quality
        "mistralai/Mistral-7B-Instruct-v0.3",  # Good balance
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",  # Fastest, lowest resources
        "google/gemma-2b-it",  # Google's instruction-tuned model
        "HuggingFaceH4/zephyr-7b-beta",  # Good quality
    ]

    def __init__(self, api_token: str = None, model: str = None):
        """
        Initialize the Hugging Face analyzer.
        
        Args:
            api_token: Hugging Face API token (optional for public models)
            model: Model to use
        """
        self._api_token = api_token
        self._model = model
        self._selected_model = None

        # Load from environment
        if not self._api_token:
            import os
            self._api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")

        # Select model
        self._selected_model = self._select_model()

    def _select_model(self) -> Optional[str]:
        """Select best available model."""
        if self._model and self._model in self.AVAILABLE_MODELS:
            return self._model

        # Return first model as default
        return self.AVAILABLE_MODELS[0] if self.AVAILABLE_MODELS else None

    def _hf_request(self, endpoint: str, data: Dict = None, timeout: int = 60) -> Optional[Dict]:
        """Make a request to Hugging Face Inference API."""
        base_url = "https://api-inference.huggingface.co/models/"
        url = base_url + self._selected_model.replace("/", "%2F")

        headers = {"Content-Type": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        try:
            import json
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            if data:
                data = json.dumps(data).encode('utf-8')
                req = Request(url, data=data, headers=headers)
            else:
                req = Request(url, headers=headers)

            with urlopen(req, timeout=timeout, context=ssl_context) as response:
                content = response.read().decode('utf-8')
                return json.loads(content) if content else None

        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ""
            logger.debug(f"HF HTTP {e.code}: {error_body}")
            return None
        except URLError as e:
            logger.debug(f"HF connection error: {e.reason}")
            return None
        except Exception as e:
            logger.debug(f"HF request failed: {e}")
            return None

    def _query_model(self, inputs: str, parameters: Dict = None) -> Optional[str]:
        """Query the model for text generation."""
        data = {
            "inputs": inputs,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "return_full_text": False,
            }
        }
        if parameters:
            data["parameters"].update(parameters)

        response = self._hf_request("", data)

        if response:
            if "error" in response:
                logger.debug(f"HF model error: {response['error']}")
                return None
            if isinstance(response, list) and len(response) > 0:
                if "generated_text" in response[0]:
                    return response[0]["generated_text"]

        return None

    def _create_prompt(self, title: str, body: str) -> str:
        """Create the prompt for analysis."""
        return f"""<|system|>You are an expert startup consultant. Analyze this Reddit post and output ONLY valid JSON.</s>
<|user|>
Title: {title}
Content: {body}

Output this JSON format:
{{"core_problem_summary":"2-3 sentence summary","target_audience":"specific group","startup_idea":"Micro-SaaS idea","startup_type":"Micro-SaaS","estimated_complexity":"Low","potential_market_size":"Medium","confidence_score":0.75}}</s>
<|assistant|>"""

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the AI response into a dictionary."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            try:
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
                logger.error(f"Failed to parse HF response as JSON")
                return None

    def analyze_post(self, title: str, body: str, subreddit: str, post_url: str) -> Optional[PostAnalysis]:
        """Analyze a single post."""
        if not self._selected_model:
            logger.error("No Hugging Face model selected")
            return None

        try:
            prompt = self._create_prompt(title, body)
            response_text = self._query_model(prompt)

            if not response_text:
                logger.warning(f"No response from HF for: {title[:50]}...")
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
                model_used=f"hf/{self._selected_model}",
                analysis_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        except Exception as e:
            logger.error(f"Error analyzing post with HF: {e}")
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

            # Rate limiting (be respectful of free tier)
            if i < total - 1:
                time.sleep(2)

        return analyses

    def test_connection(self) -> bool:
        """Test the Hugging Face connection."""
        if not self._selected_model:
            return False

        try:
            response = self._query_model("Respond with 'OK'.", {"max_new_tokens": 10})
            return response and "OK" in response.upper()
        except Exception as e:
            logger.error(f"HuggingFace connection test failed: {e}")
            return False

    @property
    def model_name(self) -> str:
        """Return the selected model name."""
        return self._selected_model or "unknown"


def create_huggingface_analyzer(config=None) -> Optional[HuggingFaceAnalyzer]:
    """Factory function to create HuggingFace analyzer."""
    try:
        import os
        api_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        model = getattr(config, 'huggingface_model', None) if config else None

        analyzer = HuggingFaceAnalyzer(api_token=api_token, model=model)

        logger.info(f"HuggingFace analyzer ready with model: {analyzer.model_name}")
        return analyzer

    except Exception as e:
        logger.warning(f"Failed to create HuggingFace analyzer: {e}")
        return None
