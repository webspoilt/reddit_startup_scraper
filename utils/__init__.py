# Utils package for Reddit Startup Idea Scraper

from .outputs import OutputManager, print_summary, save_quick_summary
from .filters import PostFilter

# Database module (optional - requires pymongo)
try:
    from .database import (
        MongoDBStorage,
        save_scrape_results,
        is_mongodb_available,
        get_database,
    )
except ImportError:
    # pymongo not installed
    MongoDBStorage = None
    save_scrape_results = None
    is_mongodb_available = lambda: False
    get_database = lambda: None

__all__ = [
    'OutputManager',
    'print_summary',
    'save_quick_summary',
    'PostFilter',
    'MongoDBStorage',
    'save_scrape_results',
    'is_mongodb_available',
    'get_database',
]
