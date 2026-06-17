import os
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# In-memory session pool tracker to hold multi-step network sockets alive
active_auth_sessions = {}

class TelegramAuthService:
    @staticmethod
    async def request_otp(phone_number: str):
        """
        Initializes a distinct Telethon client instance and requests an authentication OTP.
        """
        clean_phone = phone_number.replace('+', '').strip()
        session_path = f"backend/uploads/session_{clean_phone}"
        
        # Recycled client connection validation checks
        if phone_number in active_auth_sessions:
            try:
                client = active_auth_sessions[phone_number]["client"]
                if not client.is_connected():
                    await client.connect()
            except Exception:
                active_auth_sessions.pop(phone_number, None)

        if phone_number not in active_auth_sessions:
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            active_auth_sessions[phone_number] = {"client": client, "phone_code_hash": None}
        else:
            client = active_auth_sessions[phone_number]["client"]

        try:
            send_code_result = await client.send_code_request(phone_number)
            active_auth_sessions[phone_number]["phone_code_hash"] = send_code_result.phone_code_hash
            return {"status": "code_sent"}
        except AuthRestartError:
            raise ValueError("Telegram requested an Auth Restart. Please wait a minute and retry.")

    @staticmethod
    async def verify_otp(phone_number: str, otp_code: str):
        """
        Finalizes authentication using the open channel corresponding to the tracking pool.
        """
        session_data = active_auth_sessions.get(phone_number)
        if not session_data or not session_data["client"]:
            raise ValueError("No active connection stream found. Request a new code.")
            
        client = session_data["client"]
        phone_code_hash = session_data["phone_code_hash"]
        
        if not client.is_connected():
            await client.connect()
        
        try:
            await client.sign_in(phone=phone_number, code=otp_code, phone_code_hash=phone_code_hash)
            await client.disconnect() # Commit connection binary locks onto storage disk
            active_auth_sessions.pop(phone_number, None)
            return {"status": "authenticated", "message": "Login complete."}
        except SessionPasswordNeededError:
            return {"status": "two_factor_required", "message": "2FA verification password is required."}
        except Exception as e:
            if client.is_connected():
                await client.disconnect()
            active_auth_sessions.pop(phone_number, None)
            raise e