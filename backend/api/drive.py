from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.services.drive_service import DriveService

router = APIRouter(prefix="/api/drive", tags=["Drive Management"])

@router.post("/upload")
async def upload_file(
    phone_number: str = Form(..., description="The logged-in user phone string"),
    parent_folder_id: str = Form(None, description="Target destination folder UUID string"),
    file: UploadFile = File(...)
):
    try:
        # Read the file data asynchronously from incoming web requests
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        result = await DriveService.upload_file(
            file_name=file.filename,
            file_bytes=file_bytes,
            file_size=file_size,
            mime_type=file.content_type,
            phone_number=phone_number,
            parent_folder_id=parent_folder_id
        )
        return result
    except ValueError as v_err:
        raise HTTPException(status_code=401, detail=str(v_err))
    except PermissionError as p_err:
        raise HTTPException(status_code=403, detail=str(p_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))