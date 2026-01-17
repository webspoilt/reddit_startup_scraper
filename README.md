# Reddit Startup Idea Scraper

A powerful Python tool that automatically discovers Micro-SaaS and startup opportunities by analyzing pain points and discussions on Reddit. Supports **local AI (Ollama)** and **cloud APIs (Gemini, Groq)**.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Ollama](https://img.shields.io/badge/AI-Ollama-orange.svg)

## 🚀 Features

- **Multi-AI Support**: Use Ollama (local), Groq (free), or Gemini
- **No API Keys Required**: Use Ollama for 100% free local AI analysis
- **Automated Scraping**: Fetches posts from multiple subreddits
- **Problem Detection**: Identifies genuine pain points using keyword matching
- **AI Analysis**: Generates startup ideas, pricing, and validation steps
- **Multiple Outputs**: CSV, JSON, and TXT reports

## 📁 Project Structure

```
reddit_startup_scraper/
├── .env.example              # Environment template (copy to .env)
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── main.py                   # Full-featured scraper (uses existing modules)
├── ollama_scraper.py         # Standalone Ollama-based scraper
├── problem_scanner_local.py  # PRAW-based local problem scanner
├── config.py                 # Configuration management
│
├── analyzers/                # AI analysis modules
│   ├── __init__.py
│   ├── ai_provider.py        # Provider enum
│   ├── ollama_client.py      # Ollama local AI
│   ├── gemini_client.py      # Google Gemini
│   ├── groq_client.py        # Groq (free cloud)
│   └── huggingface_client.py # HuggingFace
│
├── scrapers/                 # Reddit data fetching
│   ├── __init__.py
│   └── reddit_client.py      # Reddit client (web + simulation)
│
├── detectors/                # Problem detection
│   ├── __init__.py
│   └── problem_phrase_detector.py
│
├── categorizers/             # Post categorization
│   ├── __init__.py
│   └── keyword_categorizer.py
│
├── scorers/                  # Confidence scoring
│   ├── __init__.py
│   └── confidence_scorer.py
│
├── exporters/                # Output generation
│   ├── __init__.py
│   └── export_manager.py
│
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── filters.py            # Post filtering
│   └── outputs.py            # Output utilities
│
└── tests/                    # Test files
    ├── test_all_fixes.py
    └── test_reddit_connection.py
```

## ⚡ Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/reddit_startup_scraper.git
cd reddit_startup_scraper
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Ollama (FREE Local AI)

```bash
# Install Ollama: https://ollama.com/
# Then pull a model:
ollama pull deepseek-coder:6.7b
# Or for smaller/faster models:
ollama pull llama3.2:3b
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Run the Scraper

```bash
# Option 1: Standalone Ollama scraper (no API keys needed)
python ollama_scraper.py

# Option 2: Full-featured scraper with all providers
python main.py
```

## 🔧 Configuration

Copy `.env.example` to `.env` and configure:

```env
# Ollama Settings (FREE - Local AI)
USE_OLLAMA=true
OLLAMA_MODEL=deepseek-coder:6.7b
OLLAMA_BASE_URL=http://localhost:11434

# Subreddits to scan
TARGET_SUBREDDITS=Entrepreneur,SaaS,SideProject,smallbusiness,startups

# Scraping settings
POST_LIMIT=10
MIN_COMMENTS=3

# Output
OUTPUT_FORMAT=all
```

## 📊 Output Files

After running, you'll get:

| File | Description |
|------|-------------|
| `startup_ideas.csv` | Excel-compatible spreadsheet |
| `startup_ideas.json` | Structured JSON data |
| `startup_ideas_report.txt` | Human-readable report |

## 🤖 AI Providers

| Provider | Cost | Setup |
|----------|------|-------|
| **Ollama** | FREE | Install Ollama, pull model |
| **Groq** | FREE | Get API key from groq.com |
| **Gemini** | Paid | Get API key from Google AI Studio |

## 🏃 Running Options

### Standalone Ollama Scraper (Recommended)
```bash
python ollama_scraper.py
```
- No Reddit API needed (uses public JSON endpoints)
- Uses local Ollama for AI analysis
- Outputs CSV, JSON, TXT

### Full Pipeline
```bash
python main.py
```
- Uses all configured AI providers
- More configuration options
- Progress tracking

### Problem Scanner (Local Analysis)
```bash
# Requires Reddit API credentials in .env
python problem_scanner_local.py
```
- Uses PRAW for Reddit access
- Local keyword-based analysis
- No AI API needed

## 📦 Requirements

- Python 3.10+
- Ollama (for local AI)
- Internet connection (for Reddit scraping)

## 🐳 Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "ollama_scraper.py"]
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## ⚠️ Disclaimer

This tool is for educational and research purposes. Always verify business ideas through proper market research. Respect Reddit's terms of service.
