from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from core.db_session import get_async_db
from utils.jwt_manager import get_current_user, get_current_payload, RoleChecker
from services.document_service import upload_pdf_service1
from schemas.uploadpdf_schema import (
    UploadPDFResponseSchema,
    UploadPDFResultSchema,
)

router = APIRouter(prefix="", tags=["Upload"])


@router.post(
    "/upload_pdf/{conversation_id}",
    response_model=UploadPDFResponseSchema,
    status_code=201,
)
async def upload_pdf_for_conversation(
    conversation_id: int,
    files: List[UploadFile] = File(...),
    description: str = Form(default="pdf"),
    payload: dict = Depends(get_current_payload),
    db: AsyncSession = Depends(get_async_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No file selected")

    user_id = payload.get("sub")
    role = payload.get("role")

    # Kiểm tra conversation thuộc user (chỉ cần nếu không phải admin/superadmin)
    if role not in ["admin", "Superadmin"]:
        check_query = text("""
            SELECT ConversationID
            FROM Conversations
            WHERE ConversationID = :cid AND UserID = :uid
        """)
        result = await db.execute(check_query, {"cid": conversation_id, "uid": user_id})
        owned = result.fetchone()
        if not owned:
            raise HTTPException(status_code=404, detail="Conversation not found or not owned by user")

    results = []
    success_count = 0

    try:
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                results.append(
                    UploadPDFResultSchema(
                        success=False,
                        error=f"Invalid file: {file.filename}. Only PDF allowed.",
                    ).model_dump()
                )
                continue

            file_bytes = await file.read()

            try:
                # Gọi service với thông tin role và conversation_id
                upload_result = await upload_pdf_service1(
                    session=db,
                    file_bytes=file_bytes,
                    file_name=file.filename,
                    uploaded_by=user_id,
                    role=role,
                    conversation_id=conversation_id,
                    description=description,
                )

                document_id = upload_result["document_id"]
                success_count += 1

                results.append(
                    UploadPDFResultSchema(
                        success=True,
                        document_id=document_id,
                        file_url=None,
                        message=f"Uploaded to {upload_result['namespace']}: {file.filename}",
                    ).model_dump()
                )
            except Exception as e:
                results.append(
                    UploadPDFResultSchema(
                        success=False,
                        error=str(e),
                    ).model_dump()
                )
                continue

        await db.commit()

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    response = UploadPDFResponseSchema(
        success=success_count > 0,
        conversation_id=conversation_id,
        results=results,
    )

    if success_count == 0:
        raise HTTPException(status_code=400, detail=response.model_dump())

    return response
