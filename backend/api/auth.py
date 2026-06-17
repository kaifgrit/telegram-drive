from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os
from backend.services.telegram_auth import TelegramAuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class PhoneRequest(BaseModel):
    phone_number: str = Field(..., description="Phone in international string format")

class VerifyRequest(BaseModel):
    phone_number: str
    otp_code: str

@router.post("/check-session")
async def check_session(payload: PhoneRequest):
    clean_phone = payload.phone_number.replace('+', '').strip()
    session_path = f"backend/uploads/session_{clean_phone}.session"
    if os.path.exists(session_path):
        return {"status": "authenticated"}
    return {"status": "no_session"}

USE_MOCK_TELEGRAM = os.getenv("USE_MOCK_TELEGRAM", "False").lower() in ("true", "1", "t")

@router.post("/send-code")
async def send_code(payload: PhoneRequest):
    if USE_MOCK_TELEGRAM:
        print(f"⚙️ [MOCK MODE] Auto-approving OTP trigger for phone: {payload.phone_number}")
        return {"status": "code_sent", "mode": "mock"}

    clean_phone = payload.phone_number.replace('+', '').strip()
    if os.path.exists(f"backend/uploads/session_{clean_phone}.session"):
        return {"status": "already_authenticated"}
    try:
        return await TelegramAuthService.request_otp(payload.phone_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-code")
async def verify_code(payload: VerifyRequest):
    if USE_MOCK_TELEGRAM:
        print(f"⚙️ [MOCK MODE] Auto-validating passcode verification sequence.")
        return {"status": "authenticated", "message": "Mock auth success."}

    try:
        return await TelegramAuthService.verify_otp(payload.phone_number, payload.otp_code)
    except ValueError as v_err:
        raise HTTPException(status_code=400, detail=str(v_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal verification error: {str(e)}")