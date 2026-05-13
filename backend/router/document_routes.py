from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from core.db_session import get_async_db
from utils.jwt_manager import RoleChecker, get_current_payload, get_current_user
from services import document_service
from schemas.document_schema import DocumentResponseSchema, DocumentUpdateSchema
from services.rag_service import process_document_to_qdrant
from core.exceptions import AppException


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

# ──────────────────────────────────────────────────────────────────────────────
# DOCTOR ENDPOINTS (Also accessible by Admin)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/doctor/upload", status_code=status.HTTP_201_CREATED)
async def doctor_upload_document(       
    file: UploadFile = File(...),
    description: str = Form("pdf"),
    db: AsyncSession = Depends(get_async_db),
    payload: dict = Depends(get_current_payload)
):
    """Doctor uploads a document (Initially not submitted to Admin)"""
    user_id = payload.get("sub")
    role = payload.get("role")
    
    file_bytes = await file.read()
    
    result = await document_service.upload_pdf_service(
        session=db,
        file_bytes=file_bytes,
        file_name=file.filename,
        uploaded_by=user_id,
        role=role,
        description=description,
        submit_now=False
    )
    return result

@router.get("/doctor/me", response_model=List[DocumentResponseSchema])
async def list_my_documents(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List documents uploaded by the current doctor"""
    return await document_service.get_all_documents(db, user_id=int(user_id), is_admin=False)

@router.patch("/doctor/{document_id}/submit")
async def submit_document_to_admin(
    document_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Submit a document for Admin review"""
    success = await document_service.submit_document(db, document_id, int(user_id))
    return {"success": success, "message": "Document submitted to Admin for review"}




@router.get("/admin/pending", response_model=List[DocumentResponseSchema], dependencies=[Depends(RoleChecker(["admin", "Superadmin"]))])
async def list_pending_documents(db: AsyncSession = Depends(get_async_db)):
    """Admin lists all documents submitted by doctors for review"""
    return await document_service.get_pending_submitted_documents(db)

from urllib.parse import quote

@router.get("/admin/{document_id}/download", dependencies=[Depends(RoleChecker(["admin", "Superadmin"]))])
async def download_document(document_id: int, db: AsyncSession = Depends(get_async_db)):
    """Admin downloads the PDF content from the database"""
    doc = await document_service.get_document_by_id(db, document_id)
    
    # Encode filename for Content-Disposition to support Vietnamese characters
    encoded_filename = quote(doc.FileName)
    
    return Response(
        content=doc.FileData,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )



@router.post("/admin/upload", status_code=status.HTTP_201_CREATED, dependencies=[Depends(RoleChecker(["admin", "Superadmin"]))])
async def admin_upload_document(
    file: UploadFile = File(...),
    description: str = Form("pdf"),
    db: AsyncSession = Depends(get_async_db),
    payload: dict = Depends(get_current_payload)
):
    """Admin uploads a document (Automatically submitted)"""
    user_id = payload.get("sub")
    role = payload.get("role")
    
    file_bytes = await file.read()
    
    result = await document_service.upload_pdf_service(
        session=db,
        file_bytes=file_bytes,
        file_name=file.filename,
        uploaded_by=user_id,
        role=role,
        description=description,
        submit_now=True # Admin uploads are pre-submitted
    )
    return result

# ──────────────────────────────────────────────────────────────────────────────
# GENERAL CRUD (Admin only)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[DocumentResponseSchema], dependencies=[Depends(RoleChecker(["admin", "Superadmin"]))])
async def list_documents(db: AsyncSession = Depends(get_async_db)):
    """List all documents submitted by doctors (Admin only)"""
    return await document_service.get_all_submitted_documents(db)

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker(["admin", "Superadmin", "Doctors"]))])
async def delete_document(
    document_id: int, 
    db: AsyncSession = Depends(get_async_db),
    payload: dict = Depends(get_current_payload)
):
    """Delete a document (Admin can delete any, Doctor can only delete their own)"""
    user_id = int(payload.get("sub"))
    role = payload.get("role")
    
    is_admin = role in ["admin", "Superadmin"]
    await document_service.delete_document(db, document_id, user_id=user_id, is_admin=is_admin)
    return None

@router.patch("/{document_id}", response_model=DocumentResponseSchema, dependencies=[Depends(RoleChecker(["admin", "Superadmin"]))])
async def update_document(
    document_id: int,
    update_data: DocumentUpdateSchema,
    db: AsyncSession = Depends(get_async_db)
):
    """Update document metadata (Admin only)"""
    return await document_service.update_document(db, document_id, update_data.dict(exclude_unset=True))



@router.post("/admin/{document_id}/process", dependencies=[Depends(RoleChecker(["admin", "Superadmin"]))])
async def process_document_now(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    payload: dict = Depends(get_current_payload)
):
    """
    Trực tiếp chunk PDF, nhúng và đưa lên Pinecone + DB.
    """
    
    
    user_id = payload.get("sub")
    doc = await document_service.get_document_by_id(db, document_id)
    
    if not doc.FileData:
        return {"success": False, "message": "Document file data is missing"}

    if doc.Status == 'Done':
        raise AppException(message="Document already processed", status_code=400)
    result = await process_document_to_qdrant(
        session=db,
        file_bytes=doc.FileData,
        user_id=str(user_id),
        document_id=document_id,
        file_name=doc.FileName,
        namespace="global",
        is_public=True
    )
    
    # Cập nhật trạng thái
    doc.Status = 'Done'
    await db.commit()
    
    return result

from services.rag_service import search_hybrid_qdrant
from typing import List, Dict, Any

@router.get("/search", response_model=List[Dict[str, Any]])
async def hybrid_search(
    query: str, 
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(5, ge=1, le=20),
    user_id: str = Depends(get_current_user)
):
    # Truyền db vào hàm để nó có thể query lấy ChunkText
    return await search_hybrid_qdrant(query, db, None, limit)
    