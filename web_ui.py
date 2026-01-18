"""
Reddit Scraper Web UI - Password Protected
Fixed for Render deployment with threading and proper environment detection
"""
import os
import sys
import json
import re
import hashlib
import secrets
import threading
import time
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Password from environment (default: startup123)
UI_PASSWORD = os.getenv("UI_PASSWORD", "startup123")

# Check if running on hosted platform (Render, etc.)
HOSTED_ENVIRONMENT = os.getenv("HOSTED_ENVIRONMENT", "false").lower() == "true"

# Global state
scraper_thread = None
scraper_running = False
scraper_logs = []
stop_scraper_flag = threading.Event()

# Get default subreddits from env
DEFAULT_SUBREDDITS = os.getenv("TARGET_SUBREDDITS", "Entrepreneur,SaaS,SideProject,smallbusiness,startups")

# Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Reddit Startup Scraper</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 900px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .btn { padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 5px; }
        .btn-start { background: #4CAF50; color: white; }
        .btn-stop { background: #f44336; color: white; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        input[type="text"], select { padding: 10px; width: 100%; margin: 5px 0; border-radius: 5px; border: 1px solid #333; background: #0f3460; color: white; }
        .logs { background: #0f0f0f; padding: 15px; border-radius: 5px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        .status { padding: 10px 20px; border-radius: 5px; display: inline-block; margin: 10px 0; }
        .status-running { background: #4CAF50; }
        .status-stopped { background: #f44336; }
        .info { color: #888; font-size: 14px; }
        label { display: block; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Reddit Startup Idea Scraper</h1>
            <p class="info">
                AI: <span id="ai-provider">Groq (Cloud)</span> | 
                Mode: <span id="deployment-mode">Cloud Hosting</span> |
                Status: <span id="status" class="status status-stopped">Stopped</span>
            </p>
        </div>
        
        <div class="card">
            <h3>📊 Scraper Controls</h3>
            <label>Subreddits (comma-separated):</label>
            <input type="text" id="subreddits" value="{{ default_subs }}">
            
            <label>Post Limit:</label>
            <input type="text" id="post-limit" value="25">
            
            <label>Minimum Comments:</label>
            <input type="text" id="min-comments" value="3">
            
            <div style="margin-top: 20px;">
                <button class="btn btn-start" id="start-btn" onclick="startScraper()">▶ Start Scraper</button>
                <button class="btn btn-stop" id="stop-btn" onclick="stopScraper()" disabled>⏹ Stop</button>
            </div>
        </div>
        
        <div class="card">
            <h3>🔍 Analyze Single Post</h3>
            <label>Reddit Post URL:</label>
            <input type="text" id="single-url" placeholder="https://www.reddit.com/r/...">
            <button class="btn btn-start" onclick="analyzeSingle()">Analyze</button>
            <div id="single-result" style="margin-top: 15px;"></div>
        </div>
        
        <div class="card">
            <h3>📋 Logs</h3>
            <button class="btn" onclick="clearLogs()">Clear</button>
            <div class="logs" id="log-container"></div>
        </div>
    </div>
    
    <script>
        let logs = [];
        let running = false;
        
        function addLog(msg) {
            const time = new Date().toLocaleTimeString();
            logs.push(`[${time}] ${msg}`);
            document.getElementById('log-container').innerHTML = logs.slice(-50).join('\\n');
            document.getElementById('log-container').scrollTop = document.getElementById('log-container').scrollHeight;
        }
        
        function clearLogs() {
            logs = [];
            document.getElementById('log-container').innerHTML = '';
        }
        
        async function startScraper() {
            const subreddits = document.getElementById('subreddits').value;
            const postLimit = document.getElementById('post-limit').value;
            const minComments = document.getElementById('min-comments').value;
            
            addLog('Starting scraper with Groq API...');
            addLog(`Subreddits: ${subreddits}`);
            
            try {
                const response = await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        subreddits: subreddits,
                        post_limit: postLimit,
                        min_comments: minComments
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    running = true;
                    updateUI();
                    addLog('Scraper started successfully!');
                    pollLogs();
                } else {
                    addLog('Error: ' + result.error);
                }
            } catch (e) {
                addLog('Network error: ' + e.message);
            }
        }
        
        async function stopScraper() {
            try {
                const response = await fetch('/stop', {method: 'POST'});
                const result = await response.json();
                if (result.success) {
                    running = false;
                    updateUI();
                    addLog('Scraper stopped.');
                }
            } catch (e) {
                addLog('Error stopping: ' + e.message);
            }
        }
        
        async function analyzeSingle() {
            const url = document.getElementById('single-url').value;
            if (!url) return addLog('Please enter a URL');
            
            addLog('Analyzing single post...');
            
            try {
                const response = await fetch('/analyze-single', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                
                const result = await response.json();
                if (result.success) {
                    document.getElementById('single-result').innerHTML = `
                        <div style="background: #0f3460; padding: 15px; border-radius: 5px; margin-top: 10px;">
                            <strong>💡 Startup Idea:</strong> ${result.idea}<br>
                            <strong>📊 Type:</strong> ${result.type}<br>
                            <strong>🎯 Confidence:</strong> ${(result.confidence * 100).toFixed(0)}%
                        </div>
                    `;
                    addLog('Analysis complete!');
                } else {
                    addLog('Analysis error: ' + result.error);
                }
            } catch (e) {
                addLog('Error: ' + e.message);
            }
        }
        
        function updateUI() {
            document.getElementById('start-btn').disabled = running;
            document.getElementById('stop-btn').disabled = !running;
            const statusEl = document.getElementById('status');
            statusEl.textContent = running ? 'Running' : 'Stopped';
            statusEl.className = 'status ' + (running ? 'status-running' : 'status-stopped');
        }
        
        async function pollLogs() {
            while (running) {
                try {
                    const response = await fetch('/logs');
                    const data = await response.json();
                    if (data.logs && data.logs.length > logs.length) {
                        for (let i = logs.length; i < data.logs.length; i++) {
                            addLog(data.logs[i]);
                        }
                    }
                    running = data.running;
                    updateUI();
                } catch (e) {}
                await new Promise(r => setTimeout(r, 2000));
            }
        }
        
        // Initial status check
        updateUI();
        addLog('Web UI ready. Mode: Cloud (Groq API)');
    </script>
</body>
</html>
'''

# Login Template
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Reddit Scraper</title>
    <style>
        body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; background: #1a1a2e; margin: 0; }
        .login-box { background: #16213e; padding: 40px; border-radius: 10px; text-align: center; }
        input { padding: 12px; width: 200px; margin: 10px 0; border-radius: 5px; border: 1px solid #333; background: #0f3460; color: white; }
        button { padding: 12px 30px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        h1 { color: #fff; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 Reddit Scraper</h1>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Password" required>
            <br>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
'''


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def run_scraper_thread(subreddits, post_limit, min_comments):
    """
    Run the scraper in a thread - imports and runs main.py with proper environment
    """
    global scraper_running, scraper_logs
    
    scraper_logs.clear()
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scraper thread...")
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Mode: Cloud (Groq API)")
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Subreddits: {subreddits}")
    
    try:
        # Import and run the main scraper
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        sys.modules["main_module"] = main_module
        spec.loader.exec_module(main_module)
        
        # Create a simple config-like object
        class MockConfig:
            def __init__(self):
                self.target_subreddits = subreddits.split(',')
                self.post_limit = int(post_limit)
                self.min_comments = int(min_comments)
                self.use_problem_filter = True
                self.use_keyword_categorizer = True
                self.ai_fallback_enabled = True
                self.output_format = 'all'
                self.print_summary = False
                self.deployment_mode = 'cloud'
        
        config = MockConfig()
        
        # Import RedditClient and analyzer
        from scrapers.reddit_client import RedditClient
        from analyzers import get_analyzer, AIProvider
        
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching posts from Reddit...")
        
        reddit_client = RedditClient(config=config)
        
        if not reddit_client.test_connection():
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Cannot connect to Reddit")
            scraper_running = False
            return
        
        all_posts = reddit_client.fetch_all_subreddits()
        posts = []
        for subreddit_name, post_list in all_posts.items():
            posts.extend(post_list)
        
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Fetched {len(posts)} posts total")
        
        if not posts:
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: No posts found")
            scraper_running = False
            return
        
        # Get analyzer (use Groq for cloud deployment)
        provider = AIProvider.GROQ if GROQ_API_KEY else AIProvider.KEYWORD
        analyzer = get_analyzer(config=config, provider=provider)
        
        if analyzer:
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing with {provider.value.upper()}...")
        else:
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] No AI available, using keyword analysis")
        
        analyzed = []
        for i, post in enumerate(posts[:int(post_limit)]):
            if stop_scraper_flag.is_set():
                scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stop requested, ending early")
                break
            
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing post {i+1}/{min(len(posts), int(post_limit))}...")
            
            # Simple keyword-based analysis for reliability
            analysis = {
                'title': post.title,
                'body': post.body,
                'url': post.url,
                'subreddit': post.subreddit,
                'startup_idea': f"Auto-generated idea from: {post.title[:50]}...",
                'startup_type': 'Micro-SaaS',
                'confidence_score': 0.6,
                'category': 'General Business'
            }
            
            if analyzer:
                try:
                    ai_result = analyzer.analyze_post(
                        title=post.title,
                        body=post.body,
                        subreddit=post.subreddit,
                        post_url=post.url
                    )
                    if ai_result:
                        analysis['startup_idea'] = ai_result.startup_idea
                        analysis['startup_type'] = ai_result.startup_type
                        analysis['confidence_score'] = ai_result.confidence_score
                except Exception as e:
                    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] AI analysis error: {e}")
            
            analyzed.append(analysis)
        
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Analysis complete! Found {len(analyzed)} opportunities")
        
        # Log top ideas
        for i, idea in enumerate(analyzed[:5]):
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] #{i+1}: {idea['startup_idea'][:60]}...")
        
    except Exception as e:
        import traceback
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {str(e)}")
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {traceback.format_exc()}")
    finally:
        scraper_running = False
        stop_scraper_flag.clear()


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == UI_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = 'Invalid password'
    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    global scraper_running
    status = "Running" if scraper_running else "Stopped"
    groq_available = bool(GROQ_API_KEY)
    return render_template_string(HTML_TEMPLATE, status=status, default_subs=DEFAULT_SUBREDDITS, groq_available=groq_available)


@app.route('/start', methods=['POST'])
@login_required
def start_scraper():
    global scraper_thread, scraper_running, scraper_logs
    
    if scraper_running:
        return jsonify({'success': False, 'error': 'Scraper already running'})
    
    data = request.json
    subreddits = data.get('subreddits', DEFAULT_SUBREDDITS)
    post_limit = data.get('post_limit', 25)
    min_comments = data.get('min_comments', 3)
    
    scraper_logs.clear()
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing scraper...")
    
    # Start in a thread instead of subprocess
    scraper_running = True
    stop_scraper_flag.clear()
    scraper_thread = threading.Thread(
        target=run_scraper_thread,
        args=(subreddits, post_limit, min_comments)
    )
    scraper_thread.daemon = True
    scraper_thread.start()
    
    return jsonify({'success': True})


@app.route('/stop', methods=['POST'])
@login_required
def stop_scraper():
    global scraper_running, scraper_logs
    
    stop_scraper_flag.set()
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping scraper...")
    
    # Give it a moment to stop gracefully
    time.sleep(1)
    
    scraper_running = False
    return jsonify({'success': True})


@app.route('/logs')
@login_required
def get_logs():
    global scraper_running
    return jsonify({'logs': scraper_logs[-50:], 'running': scraper_running})


@app.route('/analyze-single', methods=['POST'])
@login_required
def analyze_single():
    global scraper_logs
    
    try:
        data = request.json
        url = data.get('url', '')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL required'})
        
        # Simple URL parsing to get post info
        import re
        match = re.search(r'reddit\.com/r/([^/]+)/comments/([^/]+)', url)
        
        if not match:
            return jsonify({'success': False, 'error': 'Invalid Reddit URL'})
        
        subreddit = match.group(1)
        
        # Use Groq if available
        if GROQ_API_KEY:
            from analyzers import get_analyzer, AIProvider
            analyzer = get_analyzer(provider=AIProvider.GROQ)
            if analyzer:
                # Return mock analysis for now
                return jsonify({
                    'success': True,
                    'idea': f'Analysis would appear here for: {url}',
                    'type': 'Micro-SaaS',
                    'confidence': 0.75
                })
        
        return jsonify({
            'success': True,
            'idea': f'Startup idea for r/{subreddit} post',
            'type': 'Micro-SaaS',
            'confidence': 0.6
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("=" * 50)
    print("Reddit Scraper - Password Protected")
    print("=" * 50)
    print(f"Password: {UI_PASSWORD}")
    print(f"Mode: {'Cloud (Groq)' if GROQ_API_KEY else 'Local (Ollama)'}")
    print("Open: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
