from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from backend.services.drive_service import DriveService
from backend.database.mongodb import get_files_collection
import io

router = APIRouter(prefix="/api/drive", tags=["Drive"])

@router.post("/upload")
async def upload_file(
    phone_number: str = Form(...),
    parent_folder_id: str = Form(None),
    file: UploadFile = File(...)
):
    try:
        file_bytes = await file.read()
        return await DriveService.upload_file(
            file_name=file.filename,
            file_bytes=file_bytes,
            file_size=len(file_bytes),
            mime_type=file.content_type,
            phone_number=phone_number,
            parent_folder_id=parent_folder_id
        )
    except ValueError as v:
        raise HTTPException(status_code=401, detail=str(v))
    except PermissionError as p:
        raise HTTPException(status_code=403, detail=str(p))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files")
async def list_files(phone_number: str):
    try:
        cursor = get_files_collection().find({"owner_phone": phone_number})
        files = await cursor.to_list(length=100)
        return {"status": "success", "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{file_id}")
async def download_file(file_id: str, phone_number: str):
    """
    Retrieves and streams the raw binary file context directly back to the client.
    """
    try:
        # Query MongoDB explicitly using the route values
        file_meta = await get_files_collection().find_one({
            "_id": file_id, 
            "owner_phone": phone_number
        })
        
        if not file_meta:
            raise HTTPException(status_code=404, detail="File index mapping not found.")

        # Request bytes payload matrix
        file_bytes, filename, mime_type = await DriveService.download_file_bytes(file_meta, phone_number)
        
        # Stream the file structure out to the browser
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=mime_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))