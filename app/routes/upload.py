from fastapi import APIRouter, UploadFile, File, HTTPException, status
import os
import uuid
import shutil

router = APIRouter(prefix="/api/upload", tags=["Uploads"])

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

MAX_FILE_SIZE = 100 * 1024  # 100 KB

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 100KB limit."
        )
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".bin"
    new_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    # Return the URL path
    return {"url": f"/uploads/{new_filename}"}
