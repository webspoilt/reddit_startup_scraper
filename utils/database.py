"""
MongoDB Database Module
Provides persistent data storage using MongoDB Atlas.

Free tier: 512MB storage - perfect for scraped startup ideas.
Setup: https://www.mongodb.com/cloud/atlas/register
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)

# MongoDB connection instance (singleton)
_db_instance = None


def get_database():
    """
    Get the MongoDB database instance (singleton pattern).
    
    Returns:
        MongoDB database instance or None if not configured.
    """
    global _db_instance
    
    if _db_instance is not None:
        return _db_instance
    
    mongo_uri = os.getenv("MONGODB_URI", "")
    
    if not mongo_uri:
        logger.warning("MONGODB_URI not set. Data will NOT be saved to database.")
        return None
    
    try:
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi
        
        # Create client with connection pooling
        client = MongoClient(
            mongo_uri,
            server_api=ServerApi('1'),
            maxPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("✓ Connected to MongoDB Atlas")
        
        # Get database (default: reddit_scraper)
        db_name = os.getenv("MONGODB_DATABASE", "reddit_scraper")
        _db_instance = client[db_name]
        
        return _db_instance
        
    except ImportError:
        logger.error("pymongo not installed. Run: pip install pymongo")
        return None
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None


def is_mongodb_available() -> bool:
    """Check if MongoDB is configured and available."""
    return get_database() is not None


class MongoDBStorage:
    """
    MongoDB storage manager for scraped data.
    
    Collections:
    - scrape_sessions: Metadata about each scraping run
    - startup_ideas: Individual analyzed posts/ideas
    - raw_posts: Original Reddit posts (optional)
    """
    
    def __init__(self):
        self.db = get_database()
        
    @property
    def is_available(self) -> bool:
        """Check if MongoDB is connected."""
        return self.db is not None
    
    # =========================================================================
    # SCRAPE SESSIONS
    # =========================================================================
    
    def create_session(self, subreddits: List[str], provider: str, model: str) -> Optional[str]:
        """
        Create a new scraping session.
        
        Returns:
            Session ID (string) or None if DB unavailable.
        """
        if not self.is_available:
            return None
        
        session = {
            "created_at": datetime.utcnow(),
            "subreddits": subreddits,
            "ai_provider": provider,
            "ai_model": model,
            "status": "running",
            "posts_scraped": 0,
            "ideas_generated": 0,
            "completed_at": None,
        }
        
        result = self.db.scrape_sessions.insert_one(session)
        session_id = str(result.inserted_id)
        
        logger.info(f"Created scrape session: {session_id}")
        return session_id
    
    def update_session(self, session_id: str, posts_count: int, ideas_count: int, 
                       status: str = "completed") -> bool:
        """Update session with final counts."""
        if not self.is_available:
            return False
        
        from bson import ObjectId
        
        self.db.scrape_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "status": status,
                    "posts_scraped": posts_count,
                    "ideas_generated": ideas_count,
                    "completed_at": datetime.utcnow(),
                }
            }
        )
        return True
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent scraping sessions."""
        if not self.is_available:
            return []
        
        sessions = list(self.db.scrape_sessions.find().sort("created_at", -1).limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for s in sessions:
            s["_id"] = str(s["_id"])
            if s.get("created_at"):
                s["created_at"] = s["created_at"].isoformat()
            if s.get("completed_at"):
                s["completed_at"] = s["completed_at"].isoformat()
        
        return sessions
    
    # =========================================================================
    # STARTUP IDEAS
    # =========================================================================
    
    def save_idea(self, idea: Dict[str, Any], session_id: Optional[str] = None) -> Optional[str]:
        """
        Save a single startup idea to the database.
        
        Args:
            idea: Dictionary containing the analyzed post data.
            session_id: Optional session ID to link this idea to.
            
        Returns:
            Idea ID or None if save failed.
        """
        if not self.is_available:
            return None
        
        # Add metadata
        idea_doc = {
            **idea,
            "session_id": session_id,
            "saved_at": datetime.utcnow(),
        }
        
        # Handle dataclass objects
        if hasattr(idea, 'to_dict'):
            idea_doc = {**idea.to_dict(), "session_id": session_id, "saved_at": datetime.utcnow()}
        
        result = self.db.startup_ideas.insert_one(idea_doc)
        return str(result.inserted_id)
    
    def save_ideas_batch(self, ideas: List[Dict[str, Any]], 
                         session_id: Optional[str] = None) -> int:
        """
        Save multiple startup ideas at once.
        
        Args:
            ideas: List of idea dictionaries.
            session_id: Optional session ID to link all ideas to.
            
        Returns:
            Number of ideas saved.
        """
        if not self.is_available or not ideas:
            return 0
        
        # Prepare documents
        docs = []
        for idea in ideas:
            doc = dict(idea) if isinstance(idea, dict) else asdict(idea)
            doc["session_id"] = session_id
            doc["saved_at"] = datetime.utcnow()
            
            # Remove non-serializable fields
            if "confidence_breakdown" in doc:
                del doc["confidence_breakdown"]
            
            docs.append(doc)
        
        result = self.db.startup_ideas.insert_many(docs)
        count = len(result.inserted_ids)
        
        logger.info(f"Saved {count} startup ideas to MongoDB")
        return count
    
    def get_ideas(self, limit: int = 50, session_id: Optional[str] = None,
                  min_confidence: float = 0.0) -> List[Dict]:
        """
        Retrieve startup ideas from the database.
        
        Args:
            limit: Maximum number of ideas to return.
            session_id: Filter by session ID (optional).
            min_confidence: Minimum confidence score filter.
            
        Returns:
            List of idea dictionaries.
        """
        if not self.is_available:
            return []
        
        query = {}
        
        if session_id:
            query["session_id"] = session_id
        
        if min_confidence > 0:
            query["confidence_score"] = {"$gte": min_confidence}
        
        ideas = list(
            self.db.startup_ideas
            .find(query)
            .sort("saved_at", -1)
            .limit(limit)
        )
        
        # Convert ObjectId and datetime for JSON serialization
        for idea in ideas:
            idea["_id"] = str(idea["_id"])
            if idea.get("saved_at"):
                idea["saved_at"] = idea["saved_at"].isoformat()
        
        return ideas
    
    def get_top_ideas(self, limit: int = 10, days: int = 7) -> List[Dict]:
        """
        Get top-rated ideas from the last N days.
        
        Args:
            limit: Number of ideas to return.
            days: Only include ideas from the last N days.
            
        Returns:
            List of idea dictionaries sorted by confidence.
        """
        if not self.is_available:
            return []
        
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        ideas = list(
            self.db.startup_ideas
            .find({"saved_at": {"$gte": cutoff}})
            .sort("confidence_score", -1)
            .limit(limit)
        )
        
        for idea in ideas:
            idea["_id"] = str(idea["_id"])
            if idea.get("saved_at"):
                idea["saved_at"] = idea["saved_at"].isoformat()
        
        return ideas
    
    def search_ideas(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        Search ideas by keyword in title or startup_idea fields.
        
        Args:
            keyword: Search term.
            limit: Maximum results.
            
        Returns:
            List of matching ideas.
        """
        if not self.is_available:
            return []
        
        # Text search (requires text index)
        ideas = list(
            self.db.startup_ideas
            .find({
                "$or": [
                    {"title": {"$regex": keyword, "$options": "i"}},
                    {"startup_idea": {"$regex": keyword, "$options": "i"}},
                    {"core_problem_summary": {"$regex": keyword, "$options": "i"}},
                ]
            })
            .sort("confidence_score", -1)
            .limit(limit)
        )
        
        for idea in ideas:
            idea["_id"] = str(idea["_id"])
            if idea.get("saved_at"):
                idea["saved_at"] = idea["saved_at"].isoformat()
        
        return ideas
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with stats like total ideas, sessions, etc.
        """
        if not self.is_available:
            return {"available": False}
        
        return {
            "available": True,
            "total_ideas": self.db.startup_ideas.count_documents({}),
            "total_sessions": self.db.scrape_sessions.count_documents({}),
            "database": self.db.name,
        }
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its ideas."""
        if not self.is_available:
            return False
        
        from bson import ObjectId
        
        # Delete ideas
        self.db.startup_ideas.delete_many({"session_id": session_id})
        
        # Delete session
        self.db.scrape_sessions.delete_one({"_id": ObjectId(session_id)})
        
        return True


# Convenience function
def save_scrape_results(ideas: List[Dict[str, Any]], 
                        subreddits: List[str],
                        provider: str = "unknown",
                        model: str = "unknown") -> Optional[str]:
    """
    Convenience function to save scrape results.
    
    Args:
        ideas: List of analyzed ideas/posts.
        subreddits: List of subreddits scraped.
        provider: AI provider used.
        model: AI model used.
        
    Returns:
        Session ID if saved, None otherwise.
    """
    storage = MongoDBStorage()
    
    if not storage.is_available:
        logger.warning("MongoDB not available. Results NOT saved to database.")
        return None
    
    # Create session
    session_id = storage.create_session(subreddits, provider, model)
    
    if not session_id:
        return None
    
    # Save ideas
    count = storage.save_ideas_batch(ideas, session_id)
    
    # Update session with counts
    storage.update_session(session_id, len(ideas), count, "completed")
    
    logger.info(f"Saved {count} ideas to MongoDB (session: {session_id})")
    
    return session_id
