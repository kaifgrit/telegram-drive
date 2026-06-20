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
    async def _get_ancestors(parent_folder_id: str):
        """Helper to build the materialized path array."""
        if not parent_folder_id:
            return []
        parent = await get_folders_collection().find_one({"_id": parent_folder_id})
        if parent:
            return parent.get("ancestors", []) + [parent_folder_id]
        return []

    @staticmethod
    async def upload_file(file_name: str, file_bytes: bytes, file_size: int, mime_type: str, phone_number: str, parent_folder_id: str = None):
        file_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow().isoformat()
        ancestors = await DriveService._get_ancestors(parent_folder_id)

        if USE_MOCK_TELEGRAM:
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
            "ancestors": ancestors,
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
            return f"Simulated content data for: {filename}".encode('utf-8'), filename, mime_type
            
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
        file_meta = await get_files_collection().find_one({"_id": file_id, "owner_phone": phone_number})
        if not file_meta:
            raise ValueError("File not found or unauthorized access attempt.")

        # 1. Physically delete from Telegram storage first
        if not USE_MOCK_TELEGRAM:
            clean_phone = phone_number.replace('+', '').strip()
            session_path = f"backend/uploads/session_{clean_phone}"
            client = TelegramClient(session_path, int(API_ID), API_HASH)
            await client.connect()
            try:
                await client.delete_messages('me', [file_meta["telegram_message_id"]])
            finally:
                await client.disconnect()

        # 2. Clear database index
        await get_files_collection().delete_one({"_id": file_id})
        return {"status": "success", "message": "File completely removed."}

    @staticmethod
    async def delete_folder_recursive(folder_id: str, phone_number: str):
        """
        O(1) database deletion utilizing the Ancestors array.
        Warning: Physical Telegram file deletion for massive folder trees is 
        skipped here for performance. In production, consider queuing a background task.
        """
        # Delete all files where this folder is an ancestor
        await get_files_collection().delete_many({
            "ancestors": folder_id, 
            "owner_phone": phone_number
        })

        # Delete all subfolders where this folder is an ancestor
        await get_folders_collection().delete_many({
            "ancestors": folder_id, 
            "owner_phone": phone_number
        })

        # Delete the immediate contents (files directly in it) and the folder itself
        await get_files_collection().delete_many({"parent_folder_id": folder_id, "owner_phone": phone_number})
        await get_folders_collection().delete_one({"_id": folder_id, "owner_phone": phone_number})