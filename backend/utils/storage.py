import os
from tinydb import TinyDB, Query
from loguru import logger
from typing import List, Dict, Any

class Storage:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self.db = TinyDB(storage_path)

    def save_all(self, data: List[Dict[str, Any]]):
        """Overwrites the entire database with new data."""
        self.db.truncate()
        if data:
            self.db.insert_multiple(data)
        logger.info(f"Saved {len(data)} records to {self.storage_path}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieves all records from the database."""
        return self.db.all()

def get_storage(path: str) -> Storage:
    return Storage(path)
