import os
import io
import uuid
import random
from datetime import datetime
from telethon import TelegramClient
from backend.database.mongodb import get_files_collection, get_folders_collection

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
USE_MOCK_TELEGRAM = os.getenv("USE_MOCK_TELEGRAM", "False").lower() in ("true", "1", "t")

class DriveService:
    @staticmethod
    async def upload_file(file_name: str, file_bytes: bytes, file_size: int, mime_type: str, phone_number: str, parent_folder_id: str = None):
        file_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow().isoformat()

        if USE_MOCK_TELEGRAM:
            print(f"⚙️ [MOCK] Simulating upload: {file_name}")
            telegram_message_id = random.randint(1000, 99999)
        else:
            clean_phone = phone_number.replace('+', '').strip()
            session_path = f"backend/uploads/session_{clean_phone}"
            client = TelegramClient(session_path, int(API_ID), API_HASH)
            await client.connect()
            try:
                file_buffer = io.BytesIO(file_bytes)
                file_buffer.name = file_name
                uploaded_msg = await client.send_file('me', file_buffer, force_document=True)
                telegram_message_id = uploaded_msg.id
            finally:
                await client.disconnect()

        file_document = {
            "_id": file_id,
            "filename": file_name,
            "size": file_size,
            "mime_type": mime_type,
            "telegram_message_id": telegram_message_id,
            "parent_folder_id": parent_folder_id,
            "owner_phone": phone_number,
            "uploaded_at": uploaded_at
        }
        await get_files_collection().insert_one(file_document)
        return {"status": "success", "file": file_document}

    @staticmethod
    async def download_file_bytes(file_meta: dict, phone_number: str):
        filename = file_meta["filename"]
        mime_type = file_meta.get("mime_type", "application/octet-stream")

        if USE_MOCK_TELEGRAM:
            print(f"⚙️ [MOCK] Generating payload download for: {filename}")
            mock_data = f"Simulated content data for: {filename}".encode('utf-8')
            return mock_data, filename, mime_type
        else:
            clean_phone = phone_number.replace('+', '').strip()
            session_path = f"backend/uploads/session_{clean_phone}"
            client = TelegramClient(session_path, int(API_ID), API_HASH)
            await client.connect()
            try:
                msg = await client.get_messages('me', ids=file_meta["telegram_message_id"])
                file_bytes = await client.download_media(msg.document, bytes)
                return file_bytes, filename, mime_type
            finally:
                await client.disconnect()

    @staticmethod
    async def delete_file(file_id: str, phone_number: str):
        """
        Removes a file's metadata index link from MongoDB.
        """
        result = await get_files_collection().delete_one({"_id": file_id, "owner_phone": phone_number})
        if result.deleted_count == 0:
            raise ValueError("File not found or unauthorized access attempt.")
        return {"status": "success", "message": "File deleted successfully."}

    @staticmethod
    async def delete_folder_recursive(folder_id: str, phone_number: str):
        """
        Recursively travels down the virtual directory tree, clearing all 
        nested subfolders and files to prevent database orphaning.
        """
        # 1. Clear all immediate files sitting inside this folder level
        await get_files_collection().delete_many({"parent_folder_id": folder_id, "owner_phone": phone_number})

        # 2. Find all subfolders nested directly under this folder
        cursor = get_folders_collection().find({"parent_folder_id": folder_id, "owner_phone": phone_number})
        subfolders = await cursor.to_list(length=100)

        # 3. Drill down deeper into each subfolder recursively
        for folder in subfolders:
            await DriveService.delete_folder_recursive(folder["_id"], phone_number)

        # 4. Finally, remove the parent folder element document itself
        await get_folders_collection().delete_one({"_id": folder_id, "owner_phone": phone_number})