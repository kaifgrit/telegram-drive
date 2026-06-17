import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        cls.client = AsyncIOMotorClient(uri)
        cls.db = cls.client.get_default_database()
        print("🍃 Connected to MongoDB Cluster successfully.")

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            print("🍃 MongoDB Connection closed.")

def get_files_collection():
    return Database.db["files"]

def get_folders_collection():
    """
    Returns the virtual folders collection pointer allocation space.
    """
    return Database.db["folders"]