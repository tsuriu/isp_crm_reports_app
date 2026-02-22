import time
import os
import json
import hashlib
from typing import Any, Optional
from tinydb import TinyDB, Query
from loguru import logger

class PersistentCache:
    """
    A persistent disk-based cache using TinyDB.
    Supports TTL (Time To Live) for stored records.
    """
    def __init__(self, cache_path: str, ttl_hours: int):
        self.cache_path = cache_path
        self.ttl_seconds = ttl_hours * 3600
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        self.db = TinyDB(cache_path)
        logger.info(f"Initialized PersistentCache at {cache_path} (TTL: {ttl_hours}h)")

    def _generate_key(self, identifier: str, params: Optional[dict] = None) -> str:
        """Generates a unique key based on identifier and parameters."""
        data = identifier
        if params:
            # Sort keys to ensure consistent hashing
            data += json.dumps(params, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    def get(self, identifier: str, params: Optional[dict] = None, ttl_seconds: Optional[int] = None) -> Optional[Any]:
        """
        Retrieves a value from cache if it exists and hasn't expired.
        :param ttl_seconds: Optional override for TTL check. If None, uses default instance TTL.
        """
        key = self._generate_key(identifier, params)
        Record = Query()
        result = self.db.get(Record.key == key)
        
        if result:
            timestamp = result.get('timestamp', 0)
            threshold = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
            
            if (time.time() - timestamp) < threshold:
                logger.debug(f"Cache hit: {identifier} (age: {int(time.time() - timestamp)}s)")
                return result.get('value')
            else:
                if ttl_seconds is None:
                    # Only remove if checking against standard TTL, otherwise we might remove valid long-term cache 
                    # just because we did a short-term check. 
                    # Actually, if we ask "is it younger than 5s" and it's 10s old, we shouldn't delete it
                    # because it might still be valid for the 24h check later.
                    logger.debug(f"Cache expired (Standard TTL): {identifier}")
                    self.db.remove(Record.key == key)
                else:
                    logger.debug(f"Cache missed (Short-term TTL): {identifier}")
        
        return None

    def set(self, identifier: str, value: Any, params: Optional[dict] = None):
        """Stores a value in the cache with the current timestamp."""
        key = self._generate_key(identifier, params)
        Record = Query()
        
        data = {
            'key': key,
            'identifier': identifier,
            'value': value,
            'timestamp': time.time()
        }
        
        self.db.upsert(data, Record.key == key)
        logger.debug(f"Cache saved: {identifier}")

    def clear(self):
        """Clears all records from the cache."""
        self.db.truncate()
        logger.info("Cache cleared")
