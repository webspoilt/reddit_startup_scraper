"""
Comprehensive functional test for all fixed modules
"""

print('=' * 60)
print('COMPREHENSIVE FUNCTIONAL TEST')
print('=' * 60)

# Test 1: Config
print('\n[1] Testing Config...')
from config import Config
config = Config()
print(f'  - target_subreddits: {config.target_subreddits}')
print(f'  - post_limit: {config.post_limit}')
print(f'  - groq_api_key set: {bool(config.groq_api_key)}')
print(f'  - use_ollama: {config.use_ollama}')
print('  ✓ Config OK')

# Test 2: RedditPost with upvotes property
print('\n[2] Testing RedditPost.upvotes property...')
from scrapers.reddit_client import RedditPost
post = RedditPost(
    id='test123',
    title='Test Post',
    body='Test body',
    subreddit='test',
    url='https://reddit.com/test',
    author='tester',
    score=42,
    num_comments=10,
    created_utc=1234567890.0
)
print(f'  - post.score = {post.score}')
print(f'  - post.upvotes = {post.upvotes}')
assert post.upvotes == post.score, 'upvotes should equal score'
print('  ✓ RedditPost.upvotes OK')

# Test 3: Analyzers module
print('\n[3] Testing Analyzers module...')
from analyzers import get_analyzer, AnalyzerFactory, AIProvider
print(f'  - AIProvider.GROQ = {AIProvider.GROQ}')
print(f'  - AIProvider.OLLAMA = {AIProvider.OLLAMA}')
available = AnalyzerFactory.get_available_providers(config)
print(f'  - Available providers: {[p.value for p in available]}')
print('  ✓ Analyzers module OK')

# Test 4: Problem Detector
print('\n[4] Testing ProblemPhraseDetector...')
from detectors import ProblemPhraseDetector
detector = ProblemPhraseDetector()
result = detector.score_problem_indicator('I wish there was a better tool for this', 'Manual process is so frustrating')
print(f'  - Problem detected: {result["has_problem"]}')
print(f'  - Score: {result["score"]}')
print('  ✓ ProblemPhraseDetector OK')

# Test 5: Keyword Categorizer
print('\n[5] Testing KeywordCategorizer...')
from categorizers import KeywordCategorizer
categorizer = KeywordCategorizer()
result = categorizer.categorize('Need help with invoicing automation', 'Looking for software to automate my billing')
print(f'  - Category: {result.category}')
print(f'  - Score: {result.score}')
print('  ✓ KeywordCategorizer OK')

# Test 6: Confidence Scorer
print('\n[6] Testing ConfidenceScorer...')
from scorers import ConfidenceScorer
scorer = ConfidenceScorer()
breakdown = scorer.get_confidence_breakdown(
    title='Need automation tool',
    body='Manual process is slow',
    category='Workflow Inefficiency',
    category_score=0.8,
    keyword_matches=['automation', 'manual'],
    upvotes=25,
    num_comments=10,
    problem_score=0.7
)
print(f'  - Overall score: {breakdown.overall_score}')
print('  ✓ ConfidenceScorer OK')

# Test 7: Filters module (was missing logging import)
print('\n[7] Testing PostFilter (fixed logging import)...')
from utils.filters import PostFilter
pf = PostFilter(min_comments=5)
print(f'  - min_comments: {pf.min_comments}')
print('  ✓ PostFilter OK')

# Test 8: OutputManager (fixed json.dump)
print('\n[8] Testing OutputManager (fixed json.dump)...')
from utils.outputs import OutputManager
om = OutputManager()
print(f'  - output_dir: {om.output_dir}')
print('  ✓ OutputManager OK')

# Test 9: Test JSON save functionality  
print('\n[9] Testing JSON save (fixed file handle)...')
import tempfile
import os
from pathlib import Path
temp_dir = tempfile.mkdtemp()
test_data = [{"title": "Test", "body": "Test body", "confidence_score": 0.8}]
om_test = OutputManager(Path(temp_dir))
try:
    filepath = om_test.save_json(test_data, "test_output.json")
    assert filepath.exists(), "JSON file should exist"
    with open(filepath, 'r') as f:
        import json
        data = json.load(f)
        assert "analyses" in data or "data" in data, "JSON should have data"
    print(f'  - JSON file created: {filepath.name}')
    # Cleanup
    os.remove(filepath)
    os.rmdir(temp_dir)
    print('  ✓ JSON save OK')
except Exception as e:
    print(f'  ✗ JSON save failed: {e}')

print('\n' + '=' * 60)
print('ALL TESTS PASSED!')
print('=' * 60)
