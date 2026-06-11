import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/telegram_drive")

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(MONGO_URI)
        # Extracts database name from URI or defaults to telegram_drive
        cls.db = cls.client.get_default_database()
        print("🔌 Successfully connected to MongoDB database.")

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            print("🛑 MongoDB connection closed.")

# Helper functions to access collections quickly
def get_files_collection():
    return Database.db["files"]

def get_folders_collection():
    return Database.db["folders"]