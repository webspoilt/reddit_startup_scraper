"""
MongoDB Client for Reddit Startup Scraper
Stores scraped startup ideas and analyses in MongoDB Atlas
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client for storing and retrieving startup ideas.
    Requires MongoDB Atlas connection string in MONGODB_URI environment variable.
    """
    
    def __init__(self, connection_string: str = None, database_name: str = "reddit_startup_scraper"):
        """
        Initialize MongoDB client.
        
        Args:
            connection_string: MongoDB Atlas connection string
            database_name: Name of the database to use
        """
        import os
        
        if connection_string is None:
            connection_string = os.getenv("MONGODB_URI", "")
        
        self._connection_string = connection_string
        self._database_name = database_name
        self._client: Optional[MongoClient] = None
        self._db = None
    
    def connect(self) -> bool:
        """
        Establish connection to MongoDB Atlas.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self._connection_string:
            logger.warning("MONGODB_URI not set - database features disabled")
            return False
        
        try:
            # Connect with timeout to prevent hanging
            self._client = MongoClient(
                self._connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            
            # Verify connection
            self._client.admin.command('ping')
            
            # Get database
            self._db = self._client[self._database_name]
            
            logger.info(f"Connected to MongoDB database: {self._database_name}")
            return True
            
        except ServerSelectionTimeoutError:
            logger.error("MongoDB connection timeout - check network connectivity")
            return False
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Disconnected from MongoDB")
    
    def is_connected(self) -> bool:
        """Check if connected to MongoDB."""
        if self._client is None:
            return False
        try:
            self._client.admin.command('ping')
            return True
        except Exception:
            return False
    
    # Collection Methods
    
    def get_collection(self, name: str):
        """Get a collection by name."""
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB")
        return self._db[name]
    
    # CRUD Operations for Startup Ideas
    
    def save_startup_idea(self, analysis_data: Dict[str, Any]) -> Optional[str]:
        """
        Save a startup idea analysis to the database.
        
        Args:
            analysis_data: Dictionary containing analysis results
            
        Returns:
            Inserted document ID as string, or None if failed
        """
        try:
            collection = self.get_collection("startup_ideas")
            
            # Add metadata
            document = {
                **analysis_data,
                "saved_at": datetime.utcnow(),
                "source": "reddit_startup_scraper"
            }
            
            # Insert and return ID
            result = collection.insert_one(document)
            logger.debug(f"Saved startup idea with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save startup idea: {e}")
            return None
    
    def save_startup_ideas_batch(self, analyses: List[Dict[str, Any]]) -> int:
        """
        Save multiple startup idea analyses.
        
        Args:
            analyses: List of analysis dictionaries
            
        Returns:
            Number of successfully inserted documents
        """
        if not analyses:
            return 0
        
        try:
            collection = self.get_collection("startup_ideas")
            
            # Prepare documents with metadata
            documents = []
            for analysis in analyses:
                doc = {
                    **analysis,
                    "saved_at": datetime.utcnow(),
                    "source": "reddit_startup_scraper"
                }
                documents.append(doc)
            
            # Bulk insert
            result = collection.insert_many(documents)
            count = len(result.inserted_ids)
            logger.info(f"Saved {count} startup ideas to MongoDB")
            return count
            
        except Exception as e:
            logger.error(f"Failed to save batch: {e}")
            return 0
    
    def get_startup_ideas(
        self,
        limit: int = 50,
        skip: int = 0,
        min_confidence: float = None,
        subreddit: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve startup ideas with optional filters.
        
        Args:
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            min_confidence: Minimum confidence score filter
            subreddit: Filter by specific subreddit
            
        Returns:
            List of analysis documents
        """
        try:
            collection = self.get_collection("startup_ideas")
            
            # Build query
            query = {}
            if min_confidence is not None:
                query["confidence_score"] = {"$gte": min_confidence}
            if subreddit:
                query["subreddit"] = subreddit
            
            # Execute query
            cursor = collection.find(query).sort(
                "confidence_score", -1
            ).skip(skip).limit(limit)
            
            # Convert to list with string IDs
            results = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve startup ideas: {e}")
            return []
    
    def count_startup_ideas(self, subreddit: str = None) -> int:
        """
        Count total startup ideas.
        
        Args:
            subreddit: Optional subreddit filter
            
        Returns:
            Document count
        """
        try:
            collection = self.get_collection("startup_ideas")
            query = {"subreddit": subreddit} if subreddit else {}
            return collection.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    def delete_old_ideas(self, days_old: int = 30) -> int:
        """
        Delete startup ideas older than specified days.
        
        Args:
            days_old: Delete ideas older than this many days
            
        Returns:
            Number of deleted documents
        """
        try:
            from datetime import timedelta
            collection = self.get_collection("startup_ideas")
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            result = collection.delete_many({"saved_at": {"$lt": cutoff_date}})
            
            logger.info(f"Deleted {result.deleted_count} old startup ideas")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete old ideas: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with collection stats
        """
        try:
            collection = self.get_collection("startup_ideas")
            
            total = collection.count_documents({})
            by_subreddit = list(collection.aggregate([
                {"$group": {"_id": "$subreddit", "count": {"$sum": 1}}}
            ]))
            avg_confidence_result = list(collection.aggregate([
                {"$group": {"_id": None, "avg": {"$avg": "$confidence_score"}}}
            ]))
            
            avg_confidence = avg_confidence_result[0]["avg"] if avg_confidence_result else 0
            
            return {
                "total_ideas": total,
                "by_subreddit": {item["_id"]: item["count"] for item in by_subreddit if item["_id"]},
                "average_confidence": avg_confidence
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


def create_mongodb_client() -> Optional[MongoDBClient]:
    """
    Factory function to create MongoDB client from environment.
    
    Returns:
        MongoDBClient instance, or None if connection string not available
    """
    import os
    connection_string = os.getenv("MONGODB_URI", "")
    
    if not connection_string:
        logger.debug("MONGODB_URI not set in environment")
        return None
    
    client = MongoDBClient(connection_string=connection_string)
    
    if client.connect():
        return client
    
    return None
