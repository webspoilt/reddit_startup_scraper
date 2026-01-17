"""
Reddit Scraper Web UI
Simple Flask-based control panel with Start/Stop buttons
"""

import os
import sys
import json
import signal
import threading
import subprocess
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Global state
scraper_process = None
scraper_running = False
scraper_logs = []

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
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00d4ff;
            margin-bottom: 30px;
            font-size: 2.5em;
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
            font-size: 1.3em;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
        }
        input[type="text"], input[type="number"], select {
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
        .btn-row {
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }
        .btn {
            flex: 1;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn-start {
            background: linear-gradient(135deg, #00b09b, #00d4ff);
            color: #000;
        }
        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 212, 255, 0.4);
        }
        .btn-stop {
            background: linear-gradient(135deg, #ff416c, #ff4b2b);
            color: #fff;
        }
        .btn-stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 65, 108, 0.4);
        }
        .btn-stop-ollama {
            background: linear-gradient(135deg, #8e2de2, #4a00e0);
            color: #fff;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .status.running {
            background: rgba(0, 212, 255, 0.2);
            border: 1px solid #00d4ff;
        }
        .status.stopped {
            background: rgba(255, 65, 108, 0.2);
            border: 1px solid #ff416c;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        .status.running .status-dot { background: #00ff88; }
        .status.stopped .status-dot { background: #ff4444; animation: none; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .log-box {
            background: #0a0a0a;
            border-radius: 10px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            color: #00ff88;
            border: 1px solid rgba(0, 255, 136, 0.2);
        }
        .log-box p { margin: 3px 0; }
        .results-link {
            display: inline-block;
            color: #00d4ff;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 8px;
            margin: 5px;
        }
        .helper-text {
            color: #888;
            font-size: 12px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Reddit Startup Scraper</h1>
        
        <div class="card">
            <div class="status {{ 'running' if status == 'Running' else 'stopped' }}">
                <div class="status-dot"></div>
                <span><strong>Status:</strong> {{ status }}</span>
            </div>
        </div>
        
        <div class="card">
            <h2>⚙️ Configuration</h2>
            <form id="scraperForm">
                <div class="form-group">
                    <label>Subreddits (comma-separated)</label>
                    <input type="text" id="subreddits" name="subreddits" 
                           value="Entrepreneur,SaaS,SideProject,smallbusiness,startups"
                           placeholder="e.g., Entrepreneur,SaaS,startups">
                    <p class="helper-text">Or paste a Reddit URL like: https://reddit.com/r/SaaS</p>
                </div>
                <div class="form-group">
                    <label>Ollama Model</label>
                    <select id="model" name="model">
                        <option value="deepseek-coder:6.7b">deepseek-coder:6.7b</option>
                        <option value="llama3.2:3b">llama3.2:3b</option>
                        <option value="llama3.2:1b">llama3.2:1b (Faster)</option>
                        <option value="phi3:3.8b">phi3:3.8b</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Posts per Subreddit</label>
                    <input type="number" id="limit" name="limit" value="10" min="1" max="100">
                </div>
                <div class="form-group">
                    <label>Minimum Comments</label>
                    <input type="number" id="minComments" name="minComments" value="3" min="0" max="50">
                </div>
            </form>
            
            <div class="btn-row">
                <button class="btn btn-start" onclick="startScraper()" id="startBtn">
                    ▶️ Start Scraper
                </button>
                <button class="btn btn-stop" onclick="stopScraper()" id="stopBtn" disabled>
                    ⏹️ Stop Scraper
                </button>
            </div>
            <div class="btn-row">
                <button class="btn btn-stop-ollama" onclick="stopOllama()">
                    🔌 Kill Ollama (Free Resources)
                </button>
            </div>
        </div>
        
        <div class="card">
            <h2>📜 Live Logs</h2>
            <div class="log-box" id="logBox">
                <p>Waiting for scraper to start...</p>
            </div>
        </div>
        
        <div class="card">
            <h2>📁 Output Files</h2>
            <p>Results are saved to:</p>
            <a class="results-link" href="#" onclick="openFile('startup_ideas.csv')">📊 startup_ideas.csv</a>
            <a class="results-link" href="#" onclick="openFile('startup_ideas.json')">📄 startup_ideas.json</a>
            <a class="results-link" href="#" onclick="openFile('startup_ideas_report.txt')">📝 startup_ideas_report.txt</a>
        </div>
    </div>
    
    <script>
        let pollInterval = null;
        
        function parseSubreddits(input) {
            // Handle Reddit URLs
            const urlMatch = input.match(/reddit\\.com\\/r\\/([\\w]+)/g);
            if (urlMatch) {
                return urlMatch.map(u => u.split('/r/')[1]).join(',');
            }
            return input;
        }
        
        async function startScraper() {
            const subreddits = parseSubreddits(document.getElementById('subreddits').value);
            const model = document.getElementById('model').value;
            const limit = document.getElementById('limit').value;
            const minComments = document.getElementById('minComments').value;
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('logBox').innerHTML = '<p>Starting scraper...</p>';
            
            const response = await fetch('/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subreddits, model, limit, minComments})
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
            const response = await fetch('/stop', {method: 'POST'});
            const data = await response.json();
            
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('logBox').innerHTML += '<p style="color:orange;">Scraper stopped by user.</p>';
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
        
        function openFile(filename) {
            fetch('/open-file?file=' + filename);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    global scraper_running
    status = "Running" if scraper_running else "Stopped"
    return render_template_string(HTML_TEMPLATE, status=status)

@app.route('/start', methods=['POST'])
def start_scraper():
    global scraper_process, scraper_running, scraper_logs
    
    if scraper_running:
        return jsonify({'success': False, 'error': 'Already running'})
    
    data = request.json
    subreddits = data.get('subreddits', 'Entrepreneur,SaaS')
    model = data.get('model', 'deepseek-coder:6.7b')
    limit = data.get('limit', '10')
    min_comments = data.get('minComments', '3')
    
    # Update environment
    os.environ['TARGET_SUBREDDITS'] = subreddits
    os.environ['OLLAMA_MODEL'] = model
    os.environ['POST_LIMIT'] = str(limit)
    os.environ['MIN_COMMENTS'] = str(min_comments)
    
    scraper_logs = []
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting scraper...")
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Subreddits: {subreddits}")
    scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Model: {model}")
    
    try:
        # Start Ollama first
        subprocess.Popen(['ollama', 'serve'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama started")
        
        # Start scraper in background
        scraper_process = subprocess.Popen(
            [sys.executable, 'ollama_scraper.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        scraper_running = True
        
        # Start log reader thread
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
def stop_ollama():
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/IM', 'ollama.exe', '/F'], 
                         capture_output=True, check=False)
        else:
            subprocess.run(['pkill', 'ollama'], capture_output=True, check=False)
        return jsonify({'success': True, 'message': 'Ollama stopped! Resources freed.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logs')
def get_logs():
    global scraper_logs, scraper_running
    return jsonify({'logs': scraper_logs[-50:], 'running': scraper_running})

@app.route('/open-file')
def open_file():
    filename = request.args.get('file', '')
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(filepath):
        if os.name == 'nt':
            os.startfile(filepath)
        else:
            subprocess.run(['xdg-open', filepath])
    return jsonify({'success': True})

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Reddit Scraper Control Panel")
    print("=" * 50)
    print("Open in browser: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
