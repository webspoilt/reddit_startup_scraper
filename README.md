<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:FF4500,50:FF6B35,100:FF8C00&height=200&section=header&text=Reddit%20Startup%20Scraper&fontSize=60&fontColor=fff&animation=fadeIn&fontAlignY=35&desc=Startup%20Intelligence%20from%20Reddit&descAlignY=55&descSize=16"/>

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)]()
[![Reddit](https://img.shields.io/badge/Reddit-FF4500?style=for-the-badge&logo=reddit&logoColor=white)]()
[![Data](https://img.shields.io/badge/Data-Intelligence-00D9FF?style=for-the-badge)]()

**Extract Insights. Discover Startups. Analyze Markets.**

</div>

---

## 🎯 Overview

Reddit Startup Scraper is an automated tool that extracts startup-related data from Reddit for market research and competitive analysis. It monitors subreddits like r/startups, r/SideProject, and r/entrepreneur to identify emerging trends and opportunities.

---

## ✨ Features

- 🔍 **Subreddit Monitoring** - Track multiple startup-focused subreddits
- 📊 **Data Extraction** - Pull posts, comments, and metadata
- 🤖 **Sentiment Analysis** - Understand community reactions
- 📈 **Trend Detection** - Identify rising topics
- 💾 **Data Export** - CSV, JSON, and database output
- ⏰ **Scheduled Scraping** - Automated data collection

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/webspoilt/reddit_startup_scraper.git
cd reddit_startup_scraper

# Install dependencies
pip install -r requirements.txt

# Setup Reddit API credentials
cp config.example.py config.py
# Edit config.py with your Reddit API credentials

# Run scraper
python scraper.py --subreddit startups --limit 100

# Export data
python export.py --format csv --output startups.csv
```

---

## 📊 Monitored Subreddits

| Subreddit | Purpose |
|-----------|---------|
| r/startups | Startup discussions and launches |
| r/SideProject | Side project showcases |
| r/entrepreneur | Entrepreneur advice |
| r/SaaS | SaaS business discussions |
| r/indiehackers | Indie hacker stories |

---

## 📁 Project Structure

```
reddit_startup_scraper/
├── scraper.py           # Main scraper
├── analyzer.py          # Data analysis
├── export.py            # Export utilities
├── config.py            # Configuration
├── data/                # Scraped data storage
└── requirements.txt     # Dependencies
```

---

## 🤝 Contributing

Contributions welcome!

---

## 📄 License

MIT License

---

<div align="center">

**Happy Scraping! 🕷️**

**Created by [webspoilt](https://github.com/webspoilt)**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:FF8C00,50:FF6B35,100:FF4500&height=100&section=footer"/>

</div>
