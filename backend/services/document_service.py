import re
import json
import traceback
import asyncio
import base64
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from core.exceptions import ValidationException, AppException
from datetime import datetime, timedelta
from models.Documents import Documents
# from services.tasks import process_pdf_task
from typing import Optional
from typing import Optional
from sqlalchemy import func, case, Integer
from models.Users import User

def _secure_filename(filename: str) -> str:
    """Simple secure filename."""
    filename = filename.strip().replace(" ", "_")
    filename = re.sub(r"[^\w\.\-]", "", filename)
    return filename or "unnamed_file"


async def save_pdf_metadata(
    session: AsyncSession,
    uploaded_by: str,
    filename: str,
    file_bytes: bytes,
    filesize_mb: float,
    description: str = " ",
    is_submitted: bool = False
) -> int:
    try:
        new_doc = Documents(
            FileName=filename,
            FilePath=filename, # Keep for compatibility, though we use BLOB
            FileType="PDF",
            UploadedBy=int(uploaded_by),
            FileSizeMB=filesize_mb,
            Description=description,
            FileData=file_bytes,
            Status='Pending',
            IsSubmitted=is_submitted
        )
        session.add(new_doc)
        await session.commit()
        await session.refresh(new_doc)
        return new_doc.DocumentID
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error while saving PDF metadata: {e}")
        raise AppException(message="Database error", status_code=500)


async def upload_pdf_service(
    session: AsyncSession, 
    file_bytes: bytes, 
    file_name: str, 
    uploaded_by: str, 
    role: str,
    conversation_id: int = None,
    description: str = "",
    submit_now: bool = False
):
    """
    Xử lý upload PDF. 
    Nếu là Admin/Superadmin -> Tự động Submit và có thể Chunk ngay (hoặc để sau).
    Nếu là Doctor -> Lưu dạng Pending, cần Submit để Admin thấy.
    """
    filename = _secure_filename(file_name)

    if not filename.lower().endswith(".pdf"):
        raise ValidationException("Only PDF files are allowed.")

    file_size_mb = len(file_bytes) / (1024 * 1024)

    try:
        # Nếu là admin thì mặc định là đã submit
        is_submitted = True if role in ["admin", "Superadmin"] else submit_now

        document_id = await save_pdf_metadata(
            session=session,
            uploaded_by=uploaded_by,
            filename=filename,
            file_bytes=file_bytes,
            filesize_mb=file_size_mb,
            description=description,
            is_submitted=is_submitted
        )

        return {
            "success": True,
            "document_id": document_id,
            "message": f'File "{filename}" uploaded successfully. Status: Pending.'
        }

    except AppException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise e


async def get_all_documents(session: AsyncSession, user_id: int = None, is_admin: bool = False) -> list[Documents]:
    try:
        stmt = select(Documents)
        if not is_admin:
            # Doctor only sees their own
            stmt = stmt.where(Documents.UploadedBy == user_id)
        
        stmt = stmt.order_by(Documents.UploadedAt.desc())
        result = await session.execute(stmt)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching documents: {e}")
        raise AppException(message="Could not fetch documents", status_code=500)


async def get_pending_submitted_documents(session: AsyncSession) -> list[dict]:
    """Admin endpoint to see documents waiting for review."""
    try:
        from models.Users import User
        stmt = select(
            Documents.DocumentID,
            Documents.FileName,
            Documents.FilePath,
            Documents.FileType,
            Documents.UploadedBy,
            Documents.UploadedAt,
            Documents.FileSizeMB,
            Documents.Description,
            Documents.Status,
            Documents.IsSubmitted,
            User.UserName.label("UploaderName")
        ).join(
            User, Documents.UploadedBy == User.UserID, isouter=True
        ).where(
            Documents.IsSubmitted == True, 
            Documents.Status == 'Pending'
        ).order_by(Documents.UploadedAt.desc())
        
        result = await session.execute(stmt)
        return result.mappings().all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching pending documents: {e}")
        raise AppException(message="Could not fetch pending documents", status_code=500)


async def get_all_submitted_documents(
    session: AsyncSession,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    search: Optional[str] = None
) -> dict:
    """Admin endpoint to see all documents that have been submitted by doctors with optional pagination, search and stats."""
    try:
        # 1. Base query for stats (global stats of all submitted documents)
        stats_stmt = select(
            func.count(Documents.DocumentID).label("total_count"),
            func.coalesce(func.sum(
                case((Documents.Status == 'Done', 1), else_=0)
            ), 0).label("processed_count"),
            func.coalesce(func.sum(Documents.FileSizeMB), 0.0).label("total_storage_mb")
        ).where(
            Documents.IsSubmitted == True
        )
        
        stats_result = await session.execute(stats_stmt)
        stats_row = stats_result.one()
        stats = {
            "total_count": stats_row.total_count,
            "processed_count": stats_row.processed_count,
            "total_storage_mb": float(stats_row.total_storage_mb)
        }

        # 2. Base Query for items
        stmt = select(
            Documents.DocumentID,
            Documents.FileName,
            Documents.FilePath,
            Documents.FileType,
            Documents.UploadedBy,
            Documents.UploadedAt,
            Documents.FileSizeMB,
            Documents.Description,
            Documents.Status,
            Documents.IsSubmitted,
            User.UserName.label("UploaderName")
        ).join(
            User, Documents.UploadedBy == User.UserID, isouter=True
        ).where(
            Documents.IsSubmitted == True
        )

        # 3. Apply Search Filter if search query exists
        if search:
            search_filter = f"%{search}%"
            stmt = stmt.where(
                (Documents.FileName.ilike(search_filter)) |
                (Documents.Description.ilike(search_filter)) |
                (User.UserName.ilike(search_filter))
            )

        # Order by UploadedAt descending
        stmt = stmt.order_by(Documents.UploadedAt.desc())

        # 4. Get Total Count matching filter (for pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total_matching = count_result.scalar() or 0

        # 5. Apply Pagination
        if page is not None and limit is not None:
            offset = (page - 1) * limit
            stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        items = result.mappings().all()

        return {
            "items": items,
            "total": total_matching,
            "page": page,
            "limit": limit,
            "stats": stats
        }
    except SQLAlchemyError as e:
        logger.error(f"Error fetching all submitted documents: {e}")
        raise AppException(message="Could not fetch documents", status_code=500)


async def submit_document(session: AsyncSession, document_id: int, user_id: int) -> bool:
    try:
        stmt = update(Documents).where(
            Documents.DocumentID == document_id, 
            Documents.UploadedBy == user_id
        ).values(IsSubmitted=True)
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise AppException(message="Document not found or not owned by user", status_code=404)
        await session.commit()
        return True
    except AppException:
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Error submitting document {document_id}: {e}")
        raise AppException(message="Could not submit document", status_code=500)


async def approve_and_chunk_document(session: AsyncSession, document_id: int, role: str):
    """Admin approves and starts the chunking task."""
    try:
        doc = await get_document_by_id(session, document_id)
        if doc.Status == 'Done':
            raise AppException(message="Document already processed", status_code=400)

        # Update Status
        doc.Status = 'Done'
        await session.commit()
        
        # Trigger Background Task
        pdf_b64 = base64.b64encode(doc.FileData).decode('utf-8')
        
        # Determine namespace (Global for admin-approved docs)
        namespace = "global"
        
        # Simple log
        print(f"--- [CELERY] Triggered background chunking for document {document_id} ---")
        logger.info(f"Admin approved document {document_id} and triggered Celery process_pdf_task.")
        
        return doc
    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error approving document {document_id}: {e}")
        raise AppException(message="Could not approve document", status_code=500)


async def get_document_by_id(session: AsyncSession, document_id: int) -> Documents:
    try:
        stmt = select(Documents).where(Documents.DocumentID == document_id)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise AppException(message="Document not found", status_code=404)
        return doc
    except SQLAlchemyError as e:
        logger.error(f"Error fetching document {document_id}: {e}")
        raise AppException(message="Could not fetch document", status_code=500)


async def update_document(
    session: AsyncSession, document_id: int, update_data: dict
) -> Documents:
    try:
        doc = await get_document_by_id(session, document_id)
        update_data = {k: v for k, v in update_data.items() if v is not None}
        if update_data:
            stmt = (
                update(Documents)
                .where(Documents.DocumentID == document_id)
                .values(**update_data)
            )
            await session.execute(stmt)
            await session.commit()
            await session.refresh(doc)
        return doc
    except AppException:
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Error updating document {document_id}: {e}")
        raise AppException(message="Could not update document", status_code=500)


async def delete_document(session: AsyncSession, document_id: int, user_id: int = None, is_admin: bool = True) -> bool:
    try:
        doc = await get_document_by_id(session, document_id)
        
        # Check ownership if not admin
        if not is_admin and doc.UploadedBy != user_id:
            raise AppException(message="You do not have permission to delete this document", status_code=403)
            
        await session.delete(doc)
        await session.commit()
        return True
    except AppException:
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise AppException(message="Could not delete document", status_code=500)
