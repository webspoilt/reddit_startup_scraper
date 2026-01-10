# Reddit Startup Idea Scraper

A powerful Python tool that automatically discovers Micro-SaaS and startup opportunities by analyzing pain points and discussions on Reddit. It combines Reddit's data with Google Gemini AI to generate actionable business ideas.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Reddit API Credentials](#reddit-api-credentials)
  - [Google Gemini API Key](#google-gemini-api-key)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Command Line Options](#command-line-options)
- [Output Files](#output-files)
- [Project Structure](#project-structure)
- [Customization](#customization)
  - [Adding Keywords](#adding-keywords)
  - [Adjusting Filters](#adjusting-filters)
  - [Custom Prompts](#custom-prompts)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automated Data Collection**: Fetches posts from multiple subreddits (r/Entrepreneur, r/SaaS, r/SideProject)
- **Intelligent Filtering**: Identifies posts with genuine pain points using keyword matching
- **AI-Powered Analysis**: Uses Google Gemini 1.5 Flash to generate startup ideas
- **Multiple Output Formats**: Saves results as Markdown, CSV, and JSON files
- **Rate Limit Handling**: Automatic retry logic for Reddit API rate limits
- **Progress Tracking**: Real-time progress bars during data collection and analysis

## How It Works

1. **Scraping Phase**: The tool fetches the latest posts from configured subreddits using the Reddit API (PRAW)
2. **Filtering Phase**: Posts are filtered based on keyword matching and engagement criteria (minimum comments)
3. **Analysis Phase**: Each filtered post is sent to Google Gemini AI for analysis
4. **Generation Phase**: AI generates startup ideas, identifies target audiences, and assesses market potential
5. **Output Phase**: Results are saved to multiple file formats for easy review

## Prerequisites

- Python 3.8 or higher
- Reddit API credentials (client ID and secret)
- Google Gemini API key
- pip or conda for package management

## Installation

1. **Clone or navigate to the project directory**:

```bash
cd reddit_startup_scraper
```

2. **Create a virtual environment** (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

## Configuration

### Reddit API Credentials

To obtain Reddit API credentials:

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click **"Create App"** or **"Create Another App"**
3. Select **"script"** as the app type
4. Fill in the required fields:
   - **Name**: startup-idea-scraper
   - **Description**: A tool for discovering startup ideas from Reddit
   - **About URL**: `https://github.com/yourusername/reddit_startup_scraper`
   - **Redirect URI**: `http://localhost:8080`
5. Click **"Create app"**
6. Note down the **client ID** (below the app name) and **client secret**

### Google Gemini API Key

To obtain a Gemini API key:

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Create API Key"**
3. Copy the generated API key

### Environment Setup

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and fill in your credentials:

```env
# Reddit API Credentials
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=script:startup-idea-scraper:v1.0 (by /u/your_username)

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Configuration (Optional)
TARGET_SUBREDDITS=Entrepreneur,SaaS,SideProject
POST_LIMIT=50
MIN_COMMENTS=5
OUTPUT_FORMAT=markdown
```

## Usage

### Basic Usage

Run the scraper with default settings:

```bash
python main.py
```

### Command Line Options

The tool supports several command line options:

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose (debug) logging |
| `--min-comments N` | Only analyze posts with N+ comments |
| `--subreddits X,Y,Z` | Comulate-separated list of subreddits |
| `--post-limit N` | Number of posts to fetch per subreddit |

Examples:

```bash
# Verbose mode
python main.py --verbose

# Only high-engagement posts
python main.py --min-comments 10

# Custom subreddits
python main.py --subreddits=SmallBusiness,Startups,WebDev

# Combine options
python main.py --min-comments 5 --subreddits=SaaS,WebDev --post-limit 25
```

## Output Files

The tool generates output files in the `outputs/` directory:

### Markdown Report (`startup_ideas_YYYYMMDD_HHMMSS.md`)

A human-readable report containing:

- Summary statistics
- Each analyzed post with AI-generated insights
- Problem descriptions
- Target audience identification
- Startup idea suggestions
- Complexity and market size assessments

### CSV File (`startup_ideas_YYYYMMDD_HHMMSS.csv`)

Spreadsheet-compatible format with columns:

- original_title
- subreddit
- core_problem_summary
- target_audience
- startup_idea
- startup_type
- estimated_complexity
- potential_market_size
- confidence_score
- post_url

### JSON File (`startup_ideas_YYYYMMDD_HHMMSS.json`)

Structured data format for programmatic access:

```json
{
  "metadata": {
    "generated_at": "2024-01-15T10:30:00",
    "total_analyses": 15,
    "model_used": "gemini-1.5-flash"
  },
  "analyses": [...]
}
```

## Project Structure

```
reddit_startup_scraper/
├── .env.example              # Environment variable template
├── .gitignore
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── main.py                   # Application entry point
├── config.py                 # Configuration management
├── scrapers/
│   ├── __init__.py
│   └── reddit_client.py      # Reddit API client
├── analyzers/
│   ├── __init__.py
│   └── gemini_client.py      # Gemini AI client
├── utils/
│   ├── __init__.py
│   ├── filters.py            # Post filtering logic
│   └── outputs.py            # Output generation
└── outputs/                  # Generated output files (created at runtime)
```

## Customization

### Adding Keywords

To add custom pain point keywords, edit `utils/filters.py` and modify the `PAIN_POINT_KEYWORDS` list:

```python
class PostFilter:
    PAIN_POINT_KEYWORDS = [
        "struggling with",
        "I hate it when",
        # Add your custom keywords here
        "wish there was an app",
        "looking for software",
        "need a solution for",
    ]
```

### Adjusting Filters

Create a custom filter configuration in your script:

```python
from utils.filters import PostFilter

# Custom filter with different settings
custom_filter = PostFilter(
    min_comments=10,  # Higher engagement threshold
    required_keywords=["your custom keywords"],
    exclusion_keywords=["spam", "advertisement"],
)
```

### Custom Prompts

To customize the AI analysis prompt, edit `analyzers/gemini_client.py` and modify the `system_prompt`:

```python
self.system_prompt = """You are an expert startup consultant...
Add your custom instructions here
..."""
```

## Troubleshooting

### Rate Limit Errors (HTTP 429)

Reddit implements rate limits on their API. If you encounter rate limit errors:

- The tool automatically waits 60 seconds when rate limited
- Reduce `POST_LIMIT` in `.env` to make fewer requests
- Avoid running the tool too frequently

### Authentication Errors

If you see authentication errors:

- Verify your Reddit client ID and secret are correct
- Ensure your Reddit app's redirect URI is set to `http://localhost:8080`
- Check that your Gemini API key is valid and has API access enabled

### No Posts Found

If the tool reports no posts:

- Check your subreddit names are correct (without r/ prefix)
- Verify posts with your keywords exist in the subreddits
- Try lowering the `MIN_COMMENTS` threshold

### Gemini API Errors

If Gemini analysis fails:

- Verify your API key has access to Gemini 1.5 Flash
- Check your Google Cloud quota limits
- Ensure the posts have sufficient content for analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and research purposes. Always verify business ideas through proper market research before implementation. Respect Reddit's terms of service and API usage guidelines.
