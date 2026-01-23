"""
Reddit Scraper Web UI - Password Protected
Fixed for Render deployment with threading and proper environment detection
Modernized UI with glassmorphism design
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

# HTML Template - Modernized with Glassmorphism Design
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Startup Scraper</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-tertiary: #1f2937;
            --card-bg: rgba(31, 41, 55, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #818cf8;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
            --gradient-danger: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            --shadow-card: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
            --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 40%);
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
        }

        .logo {
            font-size: 3rem;
            margin-bottom: 10px;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: inline-block;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(to right, #f9fafb, #d1d5db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .status-bar {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 20px;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--card-bg);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid var(--card-border);
            font-size: 0.9rem;
        }

        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }

        .status-running .status-indicator {
            background: var(--success);
            box-shadow: 0 0 10px var(--success);
        }

        .status-stopped .status-indicator {
            background: var(--danger);
            box-shadow: 0 0 10px var(--danger);
        }

        .card {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 16px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid var(--card-border);
            box-shadow: var(--shadow-card);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.6);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--card-border);
        }

        .card-icon {
            font-size: 1.5rem;
            color: var(--primary-light);
        }

        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        input[type="text"], select {
            width: 100%;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--card-border);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 1rem;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        input[type="text"]:focus, select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            margin: 5px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }

        .btn:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn-primary {
            background: var(--gradient-primary);
            color: white;
            box-shadow: var(--shadow-glow);
        }

        .btn-danger {
            background: var(--gradient-danger);
            color: white;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
            box-shadow: none !important;
        }

        .btn-full {
            width: 100%;
            justify-content: center;
        }

        .logs-container {
            background: var(--bg-secondary);
            padding: 15px;
            border-radius: 8px;
            height: 300px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            border: 1px solid var(--card-border);
        }

        .log-entry {
            padding: 4px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .log-time {
            color: var(--text-muted);
            margin-right: 10px;
        }

        .log-info {
            color: var(--info);
        }

        .log-success {
            color: var(--success);
        }

        .log-error {
            color: var(--danger);
        }

        .log-warning {
            color: var(--warning);
        }

        .result-box {
            margin-top: 15px;
            padding: 15px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            border: 1px solid var(--card-border);
        }

        .result-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: var(--text-primary);
        }

        .result-item {
            margin-bottom: 8px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }

        .result-label {
            font-weight: 500;
            color: var(--text-secondary);
            min-width: 100px;
        }

        .result-value {
            color: var(--text-primary);
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
            
            .logo {
                font-size: 2rem;
            }
            
            .status-bar {
                flex-direction: column;
                align-items: stretch;
            }
        }

        .fade-in {
            animation: fadeIn 0.5s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🚀</div>
            <h1>Reddit Startup Idea Scraper</h1>
            <div class="status-bar">
                <div class="status-item">
                    <i class="material-icons" style="color: var(--primary-light)">smart_toy</i>
                    <span id="ai-provider">Groq (Cloud)</span>
                </div>
                <div class="status-item">
                    <i class="material-icons" style="color: var(--info)">cloud</i>
                    <span id="deployment-mode">Cloud Hosting</span>
                </div>
                <div class="status-item status-stopped" id="status-indicator">
                    <span class="status-indicator"></span>
                    <span id="status-text">Stopped</span>
                </div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="card fade-in">
                <div class="card-header">
                    <i class="material-icons card-icon">settings</i>
                    <h2 class="card-title">Scraper Controls</h2>
                </div>
                
                <div class="form-group">
                    <label for="subreddits">Subreddits (comma-separated)</label>
                    <input type="text" id="subreddits" value="{{ default_subs }}">
                </div>
                
                <div class="grid-2">
                    <div class="form-group">
                        <label for="post-limit">Post Limit</label>
                        <input type="text" id="post-limit" value="25">
                    </div>
                    
                    <div class="form-group">
                        <label for="min-comments">Minimum Comments</label>
                        <input type="text" id="min-comments" value="3">
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <button class="btn btn-primary" id="start-btn" onclick="startScraper()">
                        <i class="material-icons">play_arrow</i> Start Scraper
                    </button>
                    <button class="btn btn-danger" id="stop-btn" onclick="stopScraper()" disabled>
                        <i class="material-icons">stop</i> Stop
                    </button>
                </div>
            </div>
            
            <div class="card fade-in">
                <div class="card-header">
                    <i class="material-icons card-icon">search</i>
                    <h2 class="card-title">Analyze Single Post</h2>
                </div>
                
                <div class="form-group">
                    <label for="single-url">Reddit Post URL</label>
                    <input type="text" id="single-url" placeholder="https://www.reddit.com/r/...">
                </div>
                
                <button class="btn btn-primary btn-full" onclick="analyzeSingle()">
                    <i class="material-icons">analytics</i> Analyze
                </button>
                
                <div id="single-result"></div>
            </div>
        </div>
        
        <div class="card fade-in">
            <div class="card-header">
                <i class="material-icons card-icon">terminal</i>
                <h2 class="card-title">Logs</h2>
                <button class="btn" style="margin-left: auto; padding: 6px 12px; font-size: 0.85rem;" onclick="clearLogs()">
                    <i class="material-icons" style="font-size: 0.85rem;">clear_all</i> Clear
                </button>
            </div>
            <div class="logs-container" id="log-container"></div>
        </div>
    </div>
    
    <script>
        let logs = [];
        let running = false;
        
        function addLog(msg, type = 'info') {
            const time = new Date().toLocaleTimeString();
            const logClass = `log-${type}`;
            logs.push({ time, msg, type });
            updateLogDisplay();
        }
        
        function updateLogDisplay() {
            const logContainer = document.getElementById('log-container');
            logContainer.innerHTML = logs.slice(-50).map(log => 
                `<div class="log-entry">
                    <span class="log-time">[${log.time}]</span>
                    <span class="log-${log.type}">${log.msg}</span>
                </div>`
            ).join('');
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function clearLogs() {
            logs = [];
            updateLogDisplay();
        }
        
        async function startScraper() {
            const subreddits = document.getElementById('subreddits').value;
            const postLimit = document.getElementById('post-limit').value;
            const minComments = document.getElementById('min-comments').value;
            
            addLog('Starting scraper with Groq API...', 'info');
            addLog(`Subreddits: ${subreddits}`, 'info');
            
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
                    addLog('Scraper started successfully!', 'success');
                    pollLogs();
                } else {
                    addLog('Error: ' + result.error, 'error');
                }
            } catch (e) {
                addLog('Network error: ' + e.message, 'error');
            }
        }
        
        async function stopScraper() {
            try {
                addLog('Stopping scraper...', 'warning');
                const response = await fetch('/stop', {method: 'POST'});
                const result = await response.json();
                if (result.success) {
                    running = false;
                    updateUI();
                    addLog('Scraper stopped.', 'success');
                }
            } catch (e) {
                addLog('Error stopping: ' + e.message, 'error');
            }
        }
        
        async function analyzeSingle() {
            const url = document.getElementById('single-url').value;
            if (!url) return addLog('Please enter a URL', 'error');
            
            addLog('Analyzing single post...', 'info');
            
            try {
                const response = await fetch('/analyze-single', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                
                const result = await response.json();
                if (result.success) {
                    document.getElementById('single-result').innerHTML = `
                        <div class="result-box fade-in">
                            <h3 class="result-title">💡 Analysis Result</h3>
                            <div class="result-item">
                                <span class="result-label">Startup Idea:</span>
                                <span class="result-value">${result.idea}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Type:</span>
                                <span class="result-value">${result.type}</span>
                            </div>
                            <div class="result-item">
                                <span class="result-label">Confidence:</span>
                                <span class="result-value">${(result.confidence * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                    `;
                    addLog('Analysis complete!', 'success');
                } else {
                    addLog('Analysis error: ' + result.error, 'error');
                }
            } catch (e) {
                addLog('Error: ' + e.message, 'error');
            }
        }
        
        function updateUI() {
            document.getElementById('start-btn').disabled = running;
            document.getElementById('stop-btn').disabled = !running;
            
            const statusIndicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('status-text');
            
            if (running) {
                statusIndicator.classList.remove('status-stopped');
                statusIndicator.classList.add('status-running');
                statusText.textContent = 'Running';
            } else {
                statusIndicator.classList.remove('status-running');
                statusIndicator.classList.add('status-stopped');
                statusText.textContent = 'Stopped';
            }
        }
        
        async function pollLogs() {
            while (running) {
                try {
                    const response = await fetch('/logs');
                    const data = await response.json();
                    if (data.logs && data.logs.length > logs.length) {
                        for (let i = logs.length; i < data.logs.length; i++) {
                            // Parse the log format to determine the type
                            const logMsg = data.logs[i];
                            let logType = 'info';
                            
                            if (logMsg.toLowerCase().includes('error')) {
                                logType = 'error';
                            } else if (logMsg.toLowerCase().includes('complete') || logMsg.toLowerCase().includes('success')) {
                                logType = 'success';
                            } else if (logMsg.toLowerCase().includes('warning') || logMsg.toLowerCase().includes('stopping')) {
                                logType = 'warning';
                            }
                            
                            // Extract the message part (after the timestamp)
                            const msgMatch = logMsg.match(/\[.*?\]\s*(.*)/);
                            const msg = msgMatch ? msgMatch[1] : logMsg;
                            
                            addLog(msg, logType);
                        }
                    }
                    running = data.running;
                    updateUI();
                } catch (e) {
                    // Silently handle network errors
                }
                await new Promise(r => setTimeout(r, 2000));
            }
        }
        
        // Initial status check
        updateUI();
        addLog('Web UI ready. Mode: Cloud (Groq API)', 'success');
    </script>
</body>
</html>
'''

# Login Template - Modernized Design
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Reddit Scraper</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-tertiary: #1f2937;
            --card-bg: rgba(31, 41, 55, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #818cf8;
            --error: #ef4444;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            --shadow-card: 0 20px 40px -10px rgba(0, 0, 0, 0.7);
            --shadow-glow: 0 0 30px rgba(99, 102, 241, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 40%);
            padding: 20px;
        }

        .login-container {
            width: 100%;
            max-width: 420px;
            padding: 40px;
            background: var(--card-bg);
            border-radius: 20px;
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            box-shadow: var(--shadow-card);
            text-align: center;
        }

        .logo {
            font-size: 3.5rem;
            margin-bottom: 20px;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: inline-block;
        }

        h1 {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(to right, #f9fafb, #d1d5db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            color: var(--text-secondary);
            margin-bottom: 30px;
            font-size: 0.95rem;
        }

        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .input-container {
            position: relative;
        }

        .input-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-secondary);
        }

        input[type="password"] {
            width: 100%;
            padding: 14px 16px 14px 42px;
            border-radius: 10px;
            border: 1px solid var(--card-border);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 1rem;
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        input[type="password"]:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        .btn {
            width: 100%;
            padding: 14px;
            background: var(--gradient-primary);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: var(--shadow-glow);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }

        .btn:active {
            transform: translateY(0);
        }

        .error-message {
            color: var(--error);
            margin-bottom: 20px;
            padding: 12px;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .footer {
            margin-top: 30px;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        @media (max-width: 480px) {
            .login-container {
                padding: 30px 20px;
            }
            
            h1 {
                font-size: 1.5rem;
            }
            
            .logo {
                font-size: 2.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🔐</div>
        <h1>Reddit Scraper</h1>
        <p class="subtitle">Enter your password to access the dashboard</p>
        
        {% if error %}
        <div class="error-message">
            <i class="material-icons">error_outline</i>
            {{ error }}
        </div>
        {% endif %}
        
        <form method="POST">
            <div class="form-group">
                <label for="password">Password</label>
                <div class="input-container">
                    <i class="material-icons input-icon">lock</i>
                    <input type="password" id="password" name="password" placeholder="Enter your password" required>
                </div>
            </div>
            <button type="submit" class="btn">
                Login <i class="material-icons" style="vertical-align: middle; font-size: 1.1rem;">arrow_forward</i>
            </button>
        </form>
        
        <div class="footer">
            <p>Secure access to Reddit Startup Idea Scraper</p>
        </div>
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
    Run the scraper in a thread - imports and runs main.py with proper environment.
    Fixed: Saves results to MongoDB and properly logs all output.
    """
    global scraper_running, scraper_logs
    
    def log(msg, level='INFO'):
        """Thread-safe logging that adds to scraper_logs"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        scraper_logs.append(f"[{timestamp}] [{level}] {msg}")
        print(f"[{timestamp}] [{level}] {msg}", flush=True)
    
    scraper_logs.clear()
    log("Starting scraper thread...")
    log(f"Mode: {'Cloud (Groq API)' if GROQ_API_KEY else 'Local (Keyword)'}")
    log(f"Subreddits: {subreddits}")
    log(f"Post Limit: {post_limit}, Min Comments: {min_comments}")
    
    analyzed = []
    
    try:
        # Check MongoDB availability early
        try:
            from utils.database import is_mongodb_available, save_scrape_results
            mongodb_available = is_mongodb_available()
            log(f"MongoDB: {'Connected' if mongodb_available else 'Not configured'}")
        except ImportError as e:
            log(f"MongoDB module not available: {e}", 'WARN')
            mongodb_available = False
            save_scrape_results = None
        
        # Create a simple config-like object
        class MockConfig:
            def __init__(self):
                self.target_subreddits = [s.strip() for s in subreddits.split(',')]
                self.post_limit = int(post_limit)
                self.min_comments = int(min_comments)
                self.use_problem_filter = True
                self.use_keyword_categorizer = True
                self.ai_fallback_enabled = True
                self.output_format = 'all'
                self.print_summary = False
                self.deployment_mode = 'cloud'
        
        config = MockConfig()
        log(f"Config loaded: {len(config.target_subreddits)} subreddits")
        
        # Import RedditClient and analyzer
        from scrapers.reddit_client import RedditClient
        from analyzers import get_analyzer, AIProvider
        
        log("Initializing Reddit client...")
        reddit_client = RedditClient(config=config)
        
        if not reddit_client.test_connection():
            log("ERROR: Cannot connect to Reddit", 'ERROR')
            scraper_running = False
            return
        
        log("Connected to Reddit, fetching posts...")
        
        all_posts = reddit_client.fetch_all_subreddits()
        posts = []
        for subreddit_name, post_list in all_posts.items():
            log(f"  r/{subreddit_name}: {len(post_list)} posts")
            posts.extend(post_list)
        
        log(f"Fetched {len(posts)} posts total")
        
        if not posts:
            log("ERROR: No posts found matching criteria", 'ERROR')
            scraper_running = False
            return
        
        # Get analyzer (use Groq for cloud deployment)
        provider = AIProvider.GROQ if GROQ_API_KEY else AIProvider.KEYWORD
        log(f"Initializing AI analyzer: {provider.value.upper()}")
        
        analyzer = get_analyzer(config=config, provider=provider)
        
        if analyzer:
            model_name = getattr(analyzer, 'model_name', 'unknown')
            log(f"AI analyzer ready: {model_name}")
        else:
            log("No AI available, using keyword-only analysis", 'WARN')
        
        # Analyze posts
        total_to_analyze = min(len(posts), int(post_limit))
        log(f"Starting analysis of {total_to_analyze} posts...")
        
        for i, post in enumerate(posts[:int(post_limit)]):
            if stop_scraper_flag.is_set():
                log("Stop requested, ending early", 'WARN')
                break
            
            # Get full post data including comments (fetches from Reddit JSON API)
            if (i + 1) % 5 == 1:  # Log every 5 posts
                log(f"Fetching details for posts {i+1}-{min(i+5, total_to_analyze)}...")
            post = reddit_client.fetch_post_details(post, max_comments=10)
            post_body = post.body if post.body else ''
            post_comments = post.comments if post.comments else []
            top_comments = post_comments[:5] if post_comments else []
            
            # Log what we got
            if (i + 1) % 5 == 0:  # Log status every 5 posts
                body_info = f"{len(post_body)} chars" if post_body else "empty"
                comments_info = f"{len(post_comments)} comments" if post_comments else "none"
                log(f"  Post {i+1}: body={body_info}, {comments_info}")
            
            # Simple keyword-based analysis as fallback
            analysis = {
                'title': post.title,
                'body': post_body,  # Full body content
                'body_preview': post_body[:500] if post_body else '',  # Short preview
                'url': post.url,
                'subreddit': post.subreddit,
                'author': getattr(post, 'author', 'unknown'),
                'created_utc': getattr(post, 'created_utc', None),
                'startup_idea': f"Opportunity from: {post.title[:50]}...",
                'startup_type': 'Micro-SaaS',
                'confidence_score': 0.6,
                'category': 'General Business',
                'upvotes': getattr(post, 'upvotes', 0),
                'num_comments': getattr(post, 'num_comments', 0),
                'top_comments': [
                    {
                        'body': c.get('body', c) if isinstance(c, dict) else str(c),
                        'author': c.get('author', 'unknown') if isinstance(c, dict) else 'unknown',
                        'score': c.get('score', 0) if isinstance(c, dict) else 0
                    } for c in top_comments
                ],
            }
            
            # Try AI analysis
            if analyzer:
                try:
                    ai_result = analyzer.analyze_post(
                        title=post.title,
                        body=post.body or '',
                        subreddit=post.subreddit,
                        post_url=post.url
                    )
                    if ai_result:
                        analysis['startup_idea'] = ai_result.startup_idea
                        analysis['startup_type'] = ai_result.startup_type
                        analysis['confidence_score'] = ai_result.confidence_score
                        analysis['core_problem_summary'] = getattr(ai_result, 'core_problem_summary', '')
                        analysis['target_audience'] = getattr(ai_result, 'target_audience', '')
                        analysis['tags'] = getattr(ai_result, 'tags', [])  # Tags like ["frustration", "india", "b2b"]
                except Exception as e:
                    log(f"AI error on post {i+1}: {str(e)[:50]}", 'WARN')
            
            analyzed.append(analysis)
            
            # Progress update every 5 posts
            if (i + 1) % 5 == 0 or (i + 1) == total_to_analyze:
                log(f"Analyzed {i+1}/{total_to_analyze} posts...")
        
        log(f"Analysis complete! Found {len(analyzed)} opportunities")
        
        # --- SAVE TO MONGODB ---
        if mongodb_available and analyzed and save_scrape_results:
            log("Saving results to MongoDB Atlas...")
            try:
                session_id = save_scrape_results(
                    ideas=analyzed,
                    subreddits=config.target_subreddits,
                    provider=provider.value,
                    model=getattr(analyzer, 'model_name', 'unknown') if analyzer else 'keyword'
                )
                if session_id:
                    log(f"SUCCESS: Saved {len(analyzed)} ideas to MongoDB (session: {session_id[:8]}...)")
                else:
                    log("WARNING: MongoDB save returned no session ID", 'WARN')
            except Exception as e:
                log(f"MongoDB save error: {str(e)}", 'ERROR')
        elif not mongodb_available:
            log("MongoDB not configured - results NOT saved to cloud", 'WARN')
        
        # Log top ideas summary
        log("=== TOP STARTUP IDEAS ===")
        for i, idea in enumerate(analyzed[:5]):
            log(f"#{i+1}: {idea['startup_idea'][:60]}...")
        
        log("Scraper completed successfully!")
        
    except Exception as e:
        import traceback
        log(f"ERROR: {str(e)}", 'ERROR')
        log(f"Traceback: {traceback.format_exc()}", 'ERROR')
    finally:
        scraper_running = False
        stop_scraper_flag.clear()
        log(f"Thread finished. Analyzed {len(analyzed)} posts.")


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
