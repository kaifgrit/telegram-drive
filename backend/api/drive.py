from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uuid
from datetime import datetime
from backend.services.drive_service import DriveService
from backend.database.mongodb import get_files_collection, get_folders_collection
import io

router = APIRouter(prefix="/api/drive", tags=["Drive"])

def parse_null_string(val: str) -> Optional[str]:
    if not val or str(val).strip().lower() == "null":
        return None
    return val

class FolderCreateRequest(BaseModel):
    folder_name: str
    phone_number: str
    parent_folder_id: Optional[str] = None

    @field_validator('parent_folder_id', mode='before')
    def parse_parent_id(cls, v):
        return parse_null_string(v)

@router.post("/upload")
async def upload_file(
    phone_number: str = Form(...),
    parent_folder_id: str = Form(None),
    file: UploadFile = File(...)
):
    try:
        actual_parent_id = parse_null_string(parent_folder_id)
        file_bytes = await file.read()
        return await DriveService.upload_file(
            file_name=file.filename,
            file_bytes=file_bytes,
            file_size=len(file_bytes),
            mime_type=file.content_type,
            phone_number=phone_number,
            parent_folder_id=actual_parent_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/folder/create")
async def create_folder(payload: FolderCreateRequest):
    try:
        ancestors = await DriveService._get_ancestors(payload.parent_folder_id)
        
        folder_document = {
            "_id": str(uuid.uuid4()),
            "folder_name": payload.folder_name,
            "parent_folder_id": payload.parent_folder_id,
            "ancestors": ancestors,
            "owner_phone": payload.phone_number,
            "created_at": datetime.utcnow().isoformat()
        }
        await get_folders_collection().insert_one(folder_document)
        return {"status": "success", "folder": folder_document}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/explorer/nodes")
async def explorer_nodes(phone_number: str, parent_folder_id: str = None):
    try:
        actual_parent_id = parse_null_string(parent_folder_id)
        match_query = {
            "owner_phone": phone_number,
            "parent_folder_id": actual_parent_id
        }
        
        folders_list = await get_folders_collection().find(match_query).to_list(length=100)
        files_list = await get_files_collection().find(match_query).to_list(length=100)
        
        return {
            "status": "success",
            "current_folder_id": actual_parent_id,
            "folders": folders_list,
            "files": files_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{file_id}")
async def download_file(file_id: str, phone_number: str):
    try:
        file_meta = await get_files_collection().find_one({"_id": file_id, "owner_phone": phone_number})
        if not file_meta:
            raise HTTPException(status_code=404, detail="File metadata structure not found.")

        file_bytes, filename, mime_type = await DriveService.download_file_bytes(file_meta, phone_number)
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

@router.delete("/file/{file_id}")
async def delete_file_endpoint(file_id: str, phone_number: str):
    try:
        return await DriveService.delete_file(file_id, phone_number)
    except ValueError as v:
        raise HTTPException(status_code=404, detail=str(v))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/folder/{folder_id}")
async def delete_folder_endpoint(folder_id: str, phone_number: str):
    try:
        await DriveService.delete_folder_recursive(folder_id, phone_number)
        return {"status": "success", "detail": "Directory branch cascade deletion complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))