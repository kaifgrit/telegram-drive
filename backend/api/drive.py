from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from backend.services.drive_service import DriveService
from backend.database.mongodb import get_files_collection, get_folders_collection
import io

router = APIRouter(prefix="/api/drive", tags=["Drive"])

class FolderCreateRequest(BaseModel):
    folder_name: str = Field(..., description="The user-defined folder directory label string")
    phone_number: str = Field(..., description="The context execution owner phone link")
    parent_folder_id: str = Field(None, description="The targeted parent folder node UUID identifier string, or null for root workspace")

@router.post("/upload")
async def upload_file(
    phone_number: str = Form(...),
    parent_folder_id: str = Form(None),
    file: UploadFile = File(...)
):
    try:
        # STRICT NULL HANDLING: Convert string "null" or empty strings to Python None
        if not parent_folder_id or str(parent_folder_id).strip().lower() == "null" or parent_folder_id == "":
            actual_parent_id = None
        else:
            actual_parent_id = parent_folder_id

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
        print(f"Upload Error: {e}") # Backend logging for debugging
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/folder/create")
async def create_folder(payload: FolderCreateRequest):
    """
    Injects an explicit virtual structural branch mapping path node into the collection workspace ledger.
    """
    try:
        # STRICT NULL HANDLING
        if not payload.parent_folder_id or str(payload.parent_folder_id).strip().lower() == "null" or payload.parent_folder_id == "":
            actual_parent_id = None
        else:
            actual_parent_id = payload.parent_folder_id
        
        folder_document = {
            "_id": str(uuid.uuid4()),
            "folder_name": payload.folder_name,
            "parent_folder_id": actual_parent_id,
            "owner_phone": payload.phone_number,
            "created_at": datetime.utcnow().isoformat()
        }
        await get_folders_collection().insert_one(folder_document)
        return {"status": "success", "folder": folder_document}
    except Exception as e:
        print(f"Folder Create Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/explorer/nodes")
async def explorer_nodes(phone_number: str, parent_folder_id: str = None):
    """
    Aggregates files and directories sharing the same structural partition depth level.
    """
    try:
        # STRICT NULL HANDLING
        if not parent_folder_id or str(parent_folder_id).strip().lower() == "null" or parent_folder_id == "":
            actual_parent_id = None
        else:
            actual_parent_id = parent_folder_id
        
        # Build query dictionary target match conditions
        match_query = {
            "owner_phone": phone_number,
            "parent_folder_id": actual_parent_id
        }
        
        # Pull distinct subfolders and files in parallel executions
        folders_cursor = get_folders_collection().find(match_query)
        files_cursor = get_files_collection().find(match_query)
        
        folders_list = await folders_cursor.to_list(length=100)
        files_list = await files_cursor.to_list(length=100)
        
        return {
            "status": "success",
            "current_folder_id": actual_parent_id,
            "folders": folders_list,
            "files": files_list
        }
    except Exception as e:
        print(f"Explorer Nodes Error: {e}")
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