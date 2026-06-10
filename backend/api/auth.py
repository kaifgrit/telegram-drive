from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.services.telegram_auth import TelegramAuthService
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class PhoneRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number in international format (e.g., +1234567890)")

class VerifyRequest(BaseModel):
    phone_number: str
    otp_code: str

@router.post("/send-code")
async def send_code(payload: PhoneRequest):
    try:
        result = await TelegramAuthService.request_otp(payload.phone_number)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-code")
async def verify_code(payload: VerifyRequest):
    try:
        result = await TelegramAuthService.verify_otp(payload.phone_number, payload.otp_code)
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))