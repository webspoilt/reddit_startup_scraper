"""
Database module for Reddit Startup Scraper
Supports MongoDB Atlas for cloud database storage
"""
from database.mongodb_client import (
    MongoDBClient,
    create_mongodb_client
)

__all__ = ['MongoDBClient', 'create_mongodb_client']
