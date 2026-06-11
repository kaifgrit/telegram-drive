import os
import uuid
from datetime import datetime
from telethon import TelegramClient
from backend.database.mongodb import get_files_collection

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

class DriveService:
    @staticmethod
    async def upload_file(file_name: str, file_bytes: bytes, file_size: int, mime_type: str, phone_number: str, parent_folder_id: str = None):
        """
        Uploads an incoming file buffer to Telegram, captures its Message ID, 
        and records the structural metadata into MongoDB.
        """
        # Format the session path based on the user's phone number
        clean_phone = phone_number.replace('+', '')
        session_path = f"backend/uploads/session_{clean_phone}"
        
        if not os.path.exists(f"{session_path}.session"):
            raise ValueError("User session not found. Please log in first.")

        # Re-initialize the active user client session
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            raise PermissionError("Telegram session has expired or is invalid.")

        try:
            # 1. Pipe the file stream to Telegram's "Saved Messages" (entity='me')
            # Using a named BytesIO buffer mimics a real filesystem file object
            import io
            file_buffer = io.BytesIO(file_bytes)
            file_buffer.name = file_name
            
            # Send file to Telegram
            uploaded_msg = await client.send_file('me', file_buffer, force_document=True)
            
            # 2. Extract structural IDs from the upload event response
            telegram_message_id = uploaded_msg.id
            
            # 3. Formulate the VFS mapping schema document
            file_document = {
                "_id": str(uuid.uuid4()),
                "filename": file_name,
                "size": file_size,
                "mime_type": mime_type,
                "telegram_message_id": telegram_message_id,
                "parent_folder_id": parent_folder_id, # link to virtual folder or null for root
                "owner_phone": phone_number,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            # 4. Insert directly into MongoDB files collection
            files_col = get_files_collection()
            await files_col.insert_one(file_document)
            
            return {"status": "success", "file": file_document}
            
        finally:
            await client.disconnect()