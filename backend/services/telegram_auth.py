import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# In-memory storage to hold active client instances during the auth handshake.
# Key: phone_number -> Value: {"client": TelegramClient, "phone_code_hash": str}
active_auth_sessions = {}

class TelegramAuthService:
    @staticmethod
    async def request_otp(phone_number: str):
        """
        Initializes a temporary Telethon client and requests an OTP code from Telegram.
        """
        # We name the session file based on the phone number to support unique files
        session_path = f"backend/uploads/session_{phone_number.replace('+', '')}"
        
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        
        # Request the code from Telegram
        send_code_result = await client.send_code_request(phone_number)
        
        # Save client and hash to memory so the verification step can access them
        active_auth_sessions[phone_number] = {
            "client": client,
            "phone_code_hash": send_code_result.phone_code_hash
        }
        return {"status": "code_sent", "phone_code_hash": send_code_result.phone_code_hash}

    @staticmethod
    async def verify_otp(phone_number: str, otp_code: str):
        """
        Submits the OTP code to complete the login handshake.
        """
        session_data = active_auth_sessions.get(phone_number)
        if not session_data:
            raise ValueError("No active authentication session found for this phone number.")
            
        client = session_data["client"]
        phone_code_hash = session_data["phone_code_hash"]
        
        try:
            # Attempt to log in using the submitted code
            await client.sign_in(phone=phone_number, code=otp_code, phone_code_hash=phone_code_hash)
            
            # Clean up the memory tracker once authorization is successful
            active_auth_sessions.pop(phone_number)
            return {"status": "authenticated", "message": "Successfully logged in to Telegram Drive!"}
            
        except SessionPasswordNeededError:
            # This triggers if the user has 2-Step Verification (Two-Factor Auth) enabled
            return {"status": "two_factor_required", "message": "Two-factor authentication password required."}