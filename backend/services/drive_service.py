import os
import io
import uuid
import random
from datetime import datetime
from telethon import TelegramClient
from backend.database.mongodb import get_files_collection

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
USE_MOCK_TELEGRAM = os.getenv("USE_MOCK_TELEGRAM", "False").lower() in ("true", "1", "t")

class DriveService:
    @staticmethod
    async def upload_file(file_name: str, file_bytes: bytes, file_size: int, mime_type: str, phone_number: str, parent_folder_id: str = None):
        file_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow().isoformat()

        if USE_MOCK_TELEGRAM:
            print(f"⚙️ [MOCK MODE] Simulating file upload to Telegram: {file_name}")
            telegram_message_id = random.randint(1000, 99999)
        else:
            clean_phone = phone_number.replace('+', '').strip()
            session_path = f"backend/uploads/session_{clean_phone}"
            if not os.path.exists(f"{session_path}.session"):
                raise ValueError("Authorized user session file not found on disk.")

            client = TelegramClient(session_path, int(API_ID), API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                raise PermissionError("Your session is unauthorized or has expired.")
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
        """
        Extracts document arrays. Pulls mock strings if active, or connects to the live Telegram grid.
        """
        filename = file_meta["filename"]
        mime_type = file_meta.get("mime_type", "application/octet-stream")

        if USE_MOCK_TELEGRAM:
            # Simulated binary file fallback array data 
            print(f"⚙️ [MOCK MODE] Generating dummy streaming response for: {filename}")
            mock_data = f"Simulated cloud binary payload content data stream for file: {filename}".encode('utf-8')
            return mock_data, filename, mime_type
        else:
            clean_phone = phone_number.replace('+', '').strip()
            session_path = f"backend/uploads/session_{clean_phone}"
            client = TelegramClient(session_path, int(API_ID), API_HASH)
            await client.connect()
            try:
                # Fetch target message sequence via ID references
                msg = await client.get_messages('me', ids=file_meta["telegram_message_id"])
                file_bytes = await client.download_media(msg.document, bytes)
                return file_bytes, filename, mime_type
            finally:
                await client.disconnect()