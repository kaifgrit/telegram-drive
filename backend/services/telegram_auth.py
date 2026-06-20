import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from backend.database.mongodb import get_auth_collection
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

class TelegramAuthService:
    @staticmethod
    async def request_otp(phone_number: str):
        clean_phone = phone_number.replace('+', '').strip()
        session_path = f"backend/uploads/session_{clean_phone}"
        
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        try:
            send_code_result = await client.send_code_request(phone_number)
            
            # Persist state to MongoDB instead of RAM
            await get_auth_collection().update_one(
                {"phone_number": phone_number},
                {"$set": {"phone_code_hash": send_code_result.phone_code_hash}},
                upsert=True
            )
            return {"status": "code_sent"}
        except AuthRestartError:
            raise ValueError("Telegram requested an Auth Restart. Please wait a minute and retry.")
        finally:
            await client.disconnect()

    @staticmethod
    async def verify_otp(phone_number: str, otp_code: str):
        auth_record = await get_auth_collection().find_one({"phone_number": phone_number})
        if not auth_record or "phone_code_hash" not in auth_record:
            raise ValueError("No active authentication session found. Request a new code.")
            
        clean_phone = phone_number.replace('+', '').strip()
        session_path = f"backend/uploads/session_{clean_phone}"
        
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.sign_in(
                phone=phone_number, 
                code=otp_code, 
                phone_code_hash=auth_record["phone_code_hash"]
            )
            # Cleanup auth collection after success
            await get_auth_collection().delete_one({"phone_number": phone_number})
            return {"status": "authenticated", "message": "Login complete."}
        except SessionPasswordNeededError:
            return {"status": "two_factor_required", "message": "2FA verification password is required."}
        finally:
            await client.disconnect()