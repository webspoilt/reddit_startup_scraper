"""
Reddit Scraper Web UI - Password Protected
Features:
- Password protection (set in .env)
- Default to env subreddits if none specified
- Single Reddit link analysis
- Start/Stop controls
- Ollama kill switch
"""

import os
import sys
import json
import re
import hashlib
import secrets
import threading
import subprocess
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Password from environment (default: startup123)
UI_PASSWORD = os.getenv("UI_PASSWORD", "startup123")

# Global state
scraper_process = None
scraper_running = False
scraper_logs = []

# Get default subreddits from env
DEFAULT_SUBREDDITS = os.getenv("TARGET_SUBREDDITS", "Entrepreneur,SaaS,SideProject,smallbusiness,startups")

# Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Startup Scraper</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 {
            text-align: center;
            color: #00d4ff;
            margin-bottom: 30px;
            font-size: 2.2em;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #aaa; font-size: 14px; }
        input[type="text"], input[type="number"], input[type="password"], select {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            font-size: 14px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
        }
        .btn-row { display: flex; gap: 15px; margin-top: 20px; flex-wrap: wrap; }
        .btn {
            flex: 1;
            min-width: 140px;
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
        }
        .btn-start { background: linear-gradient(135deg, #00b09b, #00d4ff); color: #000; }
        .btn-stop { background: linear-gradient(135deg, #ff416c, #ff4b2b); color: #fff; }
        .btn-analyze { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; }
        .btn-kill { background: linear-gradient(135deg, #8e2de2, #4a00e0); color: #fff; }
        .btn-logout { background: rgba(255,255,255,0.1); color: #aaa; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }
        .status {
            display: flex; align-items: center; gap: 10px;
            padding: 12px; border-radius: 10px; margin-bottom: 15px;
        }
        .status.running { background: rgba(0, 212, 255, 0.2); border: 1px solid #00d4ff; }
        .status.stopped { background: rgba(255, 65, 108, 0.2); border: 1px solid #ff416c; }
        .status-dot {
            width: 10px; height: 10px; border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        .status.running .status-dot { background: #00ff88; }
        .status.stopped .status-dot { background: #ff4444; animation: none; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .log-box {
            background: #0a0a0a;
            border-radius: 10px;
            padding: 15px;
            height: 180px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            color: #00ff88;
            border: 1px solid rgba(0, 255, 136, 0.2);
        }
        .log-box p { margin: 2px 0; }
        .helper-text { color: #666; font-size: 11px; margin-top: 5px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            cursor: pointer;
            color: #aaa;
        }
        .tab.active { background: rgba(0, 212, 255, 0.2); border-color: #00d4ff; color: #00d4ff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .result-box {
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            font-size: 13px;
            line-height: 1.6;
        }
        .result-box h3 { color: #00d4ff; margin-bottom: 10px; }
        .result-box .field { margin: 8px 0; }
        .result-box .label { color: #888; }
        .result-box .value { color: #fff; }
        .india-badge { 
            display: inline-block; padding: 3px 8px; border-radius: 4px;
            font-size: 11px; font-weight: bold;
        }
        .india-badge.gap { background: #00ff88; color: #000; }
        .india-badge.partial { background: #ffaa00; color: #000; }
        .india-badge.exists { background: #ff4444; color: #fff; }
        /* Login page */
        .login-container {
            max-width: 400px;
            margin: 100px auto;
        }
        .login-title {
            text-align: center;
            color: #00d4ff;
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Reddit Startup Scraper</h1>
        
        <div style="text-align: right; margin-bottom: 10px;">
            <button class="btn btn-logout" onclick="logout()" style="padding: 8px 15px; min-width: auto;">Logout</button>
        </div>
        
        <div class="card">
            <div class="status {{ 'running' if status == 'Running' else 'stopped' }}">
                <div class="status-dot"></div>
                <span><strong>Status:</strong> {{ status }}</span>
            </div>
        </div>
        
        <div class="card">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('bulk')">Bulk Scrape</div>
                <div class="tab" onclick="switchTab('single')">Analyze Single Link</div>
            </div>
            
            <!-- Bulk Scrape Tab -->
            <div class="tab-content active" id="tab-bulk">
                <div class="form-group">
                    <label>Subreddits (leave empty for defaults from .env)</label>
                    <input type="text" id="subreddits" name="subreddits" 
                           placeholder="{{ default_subs }}">
                    <p class="helper-text">Default: {{ default_subs[:60] }}...</p>
                </div>
                <div class="form-group">
                    <label>AI Provider</label>
                    <select id="provider" onchange="updateModels()">
                        <option value="smart" selected>Smart Mode (Groq -> Ollama)</option>
                        <option value="groq">Groq Cloud (Fast)</option>
                        <option value="ollama">Ollama (Local)</option>
                        
                    </select>
                    <p class="helper-text" id="providerHelp">Smart Mode: Tries Groq (fast). If it fails/limits, auto-switches to Ollama (free).</p>
                </div>
                <div class="form-group">
                    <label>Model</label>
                    <select id="model">
                        <option value="llama3.2:3b">llama3.2:3b (Recommended)</option>
                        <option value="deepseek-coder:6.7b">deepseek-coder:6.7b</option>
                        <option value="llama3.2:1b">llama3.2:1b (Fast)</option>
                    </select>
                </div>
                <div style="display: flex; gap: 15px;">
                    <div class="form-group" style="flex:1">
                        <label>Posts per Subreddit</label>
                        <input type="number" id="limit" value="10" min="1" max="50">
                    </div>
                    <div class="form-group" style="flex:1">
                        <label>Min Comments</label>
                        <input type="number" id="minComments" value="3" min="0" max="50">
                    </div>
                </div>
                <div class="btn-row">
                    <button class="btn btn-start" onclick="startScraper()" id="startBtn">Start Scraper</button>
                    <button class="btn btn-stop" onclick="stopScraper()" id="stopBtn" disabled>Stop</button>
                </div>
            </div>
            
            <!-- Single Link Tab -->
            <div class="tab-content" id="tab-single">
                <div class="form-group">
                    <label>Reddit Post URL</label>
                    <input type="text" id="singleUrl" placeholder="https://reddit.com/r/SaaS/comments/...">
                    <p class="helper-text">Paste any Reddit post URL to analyze it for startup ideas</p>
                </div>
                <div class="btn-row">
                    <button class="btn btn-analyze" onclick="analyzeSingle()" id="analyzeBtn">Analyze Post</button>
                </div>
                <div id="singleResult"></div>
            </div>
        </div>
        
        <div class="card">
            <div class="btn-row">
                <button class="btn btn-kill" onclick="stopOllama()">Kill Ollama (Free RAM)</button>
            </div>
        </div>
        
        <div class="card">
            <h2>Live Logs</h2>
            <div class="log-box" id="logBox">
                <p>Waiting for scraper to start...</p>
            </div>
        </div>
    </div>
    
    <script>
        let pollInterval = null;
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        
        function updateModels() {
            const provider = document.getElementById('provider').value;
            const modelSelect = document.getElementById('model');
            const helpText = document.getElementById('providerHelp');
            
            if (provider === 'groq') {
                modelSelect.innerHTML = `
                    <option value="llama-3.3-70b-versatile">llama-3.3-70b (Best)</option>
                    <option value="llama-3.1-8b-instant">llama-3.1-8b (Fast)</option>
                    <option value="mixtral-8x7b-32768">mixtral-8x7b (Good)</option>
                `;
                helpText.textContent = 'Groq: 5x faster, works on cloud hosting, FREE tier available.';
            } else if (provider === 'smart') {
                modelSelect.innerHTML = `
                    <option value="auto">Auto-Select (Groq: Llama3-70b -> Ollama: Configured)</option>
                `;
                helpText.textContent = 'Smart Mode: Tries Graq (Fast/Best). If it fails/limits, auto-switches to local Ollama.';
            } else {
                modelSelect.innerHTML = `
                    <option value="llama3.2:3b">llama3.2:3b (Recommended)</option>
                    <option value="deepseek-coder:6.7b">deepseek-coder:6.7b</option>
                    <option value="llama3.2:1b">llama3.2:1b (Fast)</option>
                `;
                helpText.textContent = 'Ollama runs locally. No internet needed, 100% private.';
            }
        }
        
        async function startScraper() {
            let subreddits = document.getElementById('subreddits').value.trim();
            if (!subreddits) {
                subreddits = '{{ default_subs }}';
            }
            
            const provider = document.getElementById('provider').value;
            const model = document.getElementById('model').value;
            const limit = document.getElementById('limit').value;
            const minComments = document.getElementById('minComments').value;
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('logBox').innerHTML = '<p>Starting scraper with ' + provider.toUpperCase() + '...</p>';
            
            const response = await fetch('/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subreddits, provider, model, limit, minComments})
            });
            
            const data = await response.json();
            if (data.success) {
                pollInterval = setInterval(pollLogs, 2000);
            } else {
                document.getElementById('logBox').innerHTML = '<p style="color:red;">Error: ' + data.error + '</p>';
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
            }
        }
        
        async function stopScraper() {
            await fetch('/stop', {method: 'POST'});
            if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('logBox').innerHTML += '<p style="color:orange;">Stopped by user.</p>';
        }
        
        async function stopOllama() {
            const response = await fetch('/stop-ollama', {method: 'POST'});
            const data = await response.json();
            alert(data.message);
        }
        
        async function pollLogs() {
            const response = await fetch('/logs');
            const data = await response.json();
            const logBox = document.getElementById('logBox');
            logBox.innerHTML = data.logs.map(l => '<p>' + l + '</p>').join('');
            logBox.scrollTop = logBox.scrollHeight;
            if (!data.running) {
                clearInterval(pollInterval);
                pollInterval = null;
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
            }
        }
        
        async function analyzeSingle() {
            const url = document.getElementById('singleUrl').value.trim();
            if (!url) { alert('Please enter a Reddit URL'); return; }
            
            document.getElementById('analyzeBtn').disabled = true;
            document.getElementById('singleResult').innerHTML = '<p style="color:#888;">Analyzing... (this may take 30-60 seconds)</p>';
            
            const response = await fetch('/analyze-single', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            });
            
            const data = await response.json();
            document.getElementById('analyzeBtn').disabled = false;
            
            if (data.success) {
                const r = data.result;
                const gapClass = r.india_gap === 'No' ? 'gap' : (r.india_gap === 'Partial' ? 'partial' : 'exists');
                document.getElementById('singleResult').innerHTML = `
                    <div class="result-box">
                        <h3>${r.startup_idea || 'Startup Idea'}</h3>
                        <div class="field"><span class="label">Problem:</span> <span class="value">${r.problem || 'N/A'}</span></div>
                        <div class="field"><span class="label">Audience:</span> <span class="value">${r.audience || 'N/A'}</span></div>
                        <div class="field">
                            <span class="label">India Gap:</span> 
                            <span class="india-badge ${gapClass}">${r.india_gap || 'Unknown'}</span>
                        </div>
                        <div class="field"><span class="label">India Opportunity:</span> <span class="value">${r.india_opportunity || 'N/A'}</span></div>
                        <div class="field"><span class="label">Competition:</span> <span class="value">${r.competition_india || 'N/A'}</span></div>
                        <div class="field"><span class="label">Pricing (INR):</span> <span class="value">${r.pricing_inr || 'N/A'}</span></div>
                        <div class="field"><span class="label">Revenue Potential:</span> <span class="value">${r.revenue_potential || 'N/A'}</span></div>
                        <div class="field"><span class="label">Difficulty:</span> <span class="value">${r.difficulty || 'N/A'}/10</span></div>
                    </div>
                `;
            } else {
                document.getElementById('singleResult').innerHTML = '<p style="color:red;">Error: ' + data.error + '</p>';
            }
        }
        
        function logout() {
            window.location.href = '/logout';
        }
    </script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Reddit Scraper</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        h1 { color: #00d4ff; text-align: center; margin-bottom: 30px; }
        input {
            width: 100%;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.3);
            color: #fff;
            font-size: 16px;
            margin-bottom: 20px;
        }
        input:focus { outline: none; border-color: #00d4ff; }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #00b09b, #00d4ff);
            border: none;
            border-radius: 8px;
            color: #000;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        .error { color: #ff4444; text-align: center; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Reddit Scraper</h1>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Password" required autofocus>
            <button type="submit">Unlock</button>
        </form>
    </div>
</body>
</html>
"""

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


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
    global scraper_process, scraper_running, scraper_logs
    
    if scraper_running:
        return jsonify({'success': False, 'error': 'Already running'})
    
    data = request.json
    subreddits = data.get('subreddits', DEFAULT_SUBREDDITS)
    model = data.get('model', 'llama3.2:3b')
    limit = data.get('limit', '10')
    min_comments = data.get('minComments', '3')
    provider = data.get('provider', 'ollama')
    
    os.environ['TARGET_SUBREDDITS'] = subreddits
    os.environ['OLLAMA_MODEL'] = model
    os.environ['POST_LIMIT'] = str(limit)
    os.environ['MIN_COMMENTS'] = str(min_comments)
    os.environ['AI_PROVIDER'] = provider
    
    scraper_logs = []
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scraper...")
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Subreddits: {subreddits[:50]}...")
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Model: {model}")
    
    try:
        subprocess.Popen(['ollama', 'serve'], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama started")
        
        scraper_process = subprocess.Popen(
            [sys.executable, 'ollama_scraper.py'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        scraper_running = True
        
        def read_logs():
            global scraper_running, scraper_logs
            for line in scraper_process.stdout:
                scraper_logs.append(line.strip())
                if len(scraper_logs) > 100:
                    scraper_logs = scraper_logs[-100:]
            scraper_running = False
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Scraper finished!")
        
        threading.Thread(target=read_logs, daemon=True).start()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/stop', methods=['POST'])
@login_required
def stop_scraper():
    global scraper_process, scraper_running
    if scraper_process:
        try:
            scraper_process.terminate()
            scraper_process.wait(timeout=5)
        except:
            scraper_process.kill()
        scraper_process = None
    scraper_running = False
    return jsonify({'success': True})


@app.route('/stop-ollama', methods=['POST'])
@login_required
def stop_ollama():
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/IM', 'ollama.exe', '/F'], capture_output=True, check=False)
        else:
            subprocess.run(['pkill', 'ollama'], capture_output=True, check=False)
        return jsonify({'success': True, 'message': 'Ollama stopped! RAM freed.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/logs')
@login_required
def get_logs():
    global scraper_logs, scraper_running
    return jsonify({'logs': scraper_logs[-50:], 'running': scraper_running})


@app.route('/analyze-single', methods=['POST'])
@login_required
def analyze_single():
    """Analyze a single Reddit post URL using Ollama or Groq."""
    import requests as req
    
    data = request.json
    url = data.get('url', '')
    provider = data.get('provider', 'ollama')
    
    try:
        if 'reddit.com' not in url:
            return jsonify({'success': False, 'error': 'Invalid Reddit URL'})
        
        # Fetch Reddit post
        json_url = url.rstrip('/') + '.json'
        headers = {'User-Agent': 'StartupScraper/1.0'}
        response = req.get(json_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Could not fetch Reddit post'})
        
        post_data = response.json()[0]['data']['children'][0]['data']
        title = post_data.get('title', '')
        body = post_data.get('selftext', '')[:1000]
        
        prompt = f"""You are a startup analyst specializing in finding opportunities for the Indian market. Analyze this Reddit post and return ONLY a valid JSON object.

Title: {title}
Body: {body}

Return JSON:
{{
  "problem": "one sentence",
  "audience": "who faces this",
  "startup_idea": "solution for India",
  "us_trend": "Yes/No",
  "india_gap": "Yes/No/Partial",
  "india_opportunity": "why it could work in India",
  "pricing_inr": "price in INR",
  "revenue_potential": "High/Medium/Low",
  "competition_india": "Low/Medium/High",
  "difficulty": 1-10
}}"""
        
        result_text = ""
        
        # Use Groq if API key is available and selected
        if GROQ_API_KEY and provider == 'groq':
            groq_response = req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=60
            )
            
            if groq_response.status_code == 200:
                result_text = groq_response.json()['choices'][0]['message']['content']
            else:
                return jsonify({'success': False, 'error': f'Groq error: {groq_response.status_code}'})
        else:
            # Use Ollama
            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/generate"
            model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
            
            ollama_response = req.post(ollama_url, json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }, timeout=120)
            
            if ollama_response.status_code == 200:
                result_text = ollama_response.json().get('response', '')
            else:
                return jsonify({'success': False, 'error': 'Ollama not running. Start with: ollama serve'})
        
        # Extract JSON from response
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
            return jsonify({'success': True, 'result': result})
        
        return jsonify({'success': False, 'error': 'Could not parse AI response'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# MongoDB API Endpoints (for saved data access)
# ============================================================================

@app.route('/api/db/status')
@login_required
def db_status():
    """Check MongoDB connection status."""
    try:
        from utils.database import MongoDBStorage
        storage = MongoDBStorage()
        stats = storage.get_stats()
        return jsonify({'success': True, **stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'available': False})


@app.route('/api/db/sessions')
@login_required
def get_sessions():
    """Get recent scraping sessions."""
    try:
        from utils.database import MongoDBStorage
        storage = MongoDBStorage()
        sessions = storage.get_recent_sessions(limit=20)
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/db/ideas')
@login_required
def get_ideas():
    """Get saved startup ideas."""
    try:
        from utils.database import MongoDBStorage
        storage = MongoDBStorage()
        
        limit = request.args.get('limit', 50, type=int)
        session_id = request.args.get('session_id', None)
        min_confidence = request.args.get('min_confidence', 0.0, type=float)
        
        ideas = storage.get_ideas(limit=limit, session_id=session_id, min_confidence=min_confidence)
        return jsonify({'success': True, 'ideas': ideas, 'count': len(ideas)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/db/top-ideas')
@login_required
def get_top_ideas():
    """Get top-rated ideas from recent days."""
    try:
        from utils.database import MongoDBStorage
        storage = MongoDBStorage()
        
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 7, type=int)
        
        ideas = storage.get_top_ideas(limit=limit, days=days)
        return jsonify({'success': True, 'ideas': ideas, 'count': len(ideas)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/db/search')
@login_required
def search_ideas():
    """Search ideas by keyword."""
    try:
        from utils.database import MongoDBStorage
        storage = MongoDBStorage()
        
        keyword = request.args.get('q', '')
        limit = request.args.get('limit', 20, type=int)
        
        if not keyword:
            return jsonify({'success': False, 'error': 'Missing search query (q parameter)'})
        
        ideas = storage.search_ideas(keyword=keyword, limit=limit)
        return jsonify({'success': True, 'ideas': ideas, 'count': len(ideas)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("=" * 50)
    print("Reddit Scraper - Password Protected")
    print("=" * 50)
    print(f"Password: {UI_PASSWORD}")
    print("Open: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Check MongoDB status on startup
    try:
        from utils.database import is_mongodb_available
        if is_mongodb_available():
            print("✓ MongoDB Atlas: Connected")
        else:
            print("⚠ MongoDB Atlas: Not configured (data will be local only)")
    except ImportError:
        print("⚠ MongoDB module not available")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

