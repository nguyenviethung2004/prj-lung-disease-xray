from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.db_session import get_async_db
from utils.jwt_manager import get_current_user
from services.chat_service import (
    handle_chat_query,
    get_conversations_list,
    create_new_conversation,
    load_conversation_history,
)
from core.exceptions import NotFoundException, ValidationException
from services.document_service import upload_pdf_service
from services.rag_service import process_document_to_qdrant, delete_qdrant_points_by_document_id
from utils.jwt_manager import get_current_payload
import asyncio
from schemas.conversation_schema import (
    ConversationCreateSchema,
    ConversationListResponseSchema,
    ConversationResponseSchema,
    RenameConversationRequest,
    RenameConversationResponse,
)
from schemas.message_schema import ConversationHistoryResponseSchema, MessageItemSchema
from schemas.chat_schema import ChatRequestSchema, ChatResponseSchema
from core.logger import logger

router = APIRouter(prefix="", tags=["Chat"])


@router.get("/conversations", response_model=ConversationListResponseSchema)
async def get_conversations(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    items = await get_conversations_list(db, user_id)
    return ConversationListResponseSchema(conversations=items)


@router.post("/conversations/new", response_model=ConversationResponseSchema, status_code=201)
async def new_conversation(
    payload: ConversationCreateSchema,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    conv_id = await create_new_conversation(db, user_id, payload.title)
    return ConversationResponseSchema(
        conversation_id=conv_id,
        title=payload.title,
        message="New conversation created",
    )


@router.get("/conversations/{conv_id}/history", response_model=ConversationHistoryResponseSchema)
async def load_history_conversation(
    conv_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    check_query = text("""
        SELECT ConversationID
        FROM Conversations
        WHERE ConversationID = :conv_id AND UserID = :user_id
    """)
    result = (await db.execute(check_query, {"conv_id": conv_id, "user_id": user_id})).fetchone()
    if not result:
        raise NotFoundException("Conversation not found or access denied")

    try:
        messages = await load_conversation_history(db, conv_id, offset=offset, limit=limit)

        if not messages:
            return ConversationHistoryResponseSchema(
                conversation_id=conv_id,
                messages=[],
                has_more=False,
            )

        count_query = text("""
            SELECT COUNT(*) AS total
            FROM Messages
            WHERE ConversationID = :conv_id
        """)
        total_msgs = (await db.execute(count_query, {"conv_id": conv_id})).scalar()
        has_more = (offset + limit) < total_msgs

        return ConversationHistoryResponseSchema(
            conversation_id=conv_id,
            messages=[MessageItemSchema(**m) for m in messages],
            has_more=has_more,
        )
    except Exception as e:
        logger.error(f"Error loading chat history for conv {conv_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    check_query = text("""
        SELECT ConversationID FROM Conversations
        WHERE ConversationID = :conversation_id AND UserID = :user_id
    """)
    result = (await db.execute(check_query, {"conversation_id": conversation_id, "user_id": user_id})).fetchone()
    if not result:
        raise NotFoundException("Conversation not found or not owned by user")

    await db.execute(text("DELETE FROM Messages WHERE ConversationID = :cid"), {"cid": conversation_id})
    await db.execute(text("DELETE FROM VectorMemorySummary WHERE ConversationID = :cid"), {"cid": conversation_id})
    await db.execute(text("DELETE FROM Conversations WHERE ConversationID = :cid"), {"cid": conversation_id})
    await db.commit()
    return {"message": "Conversation deleted successfully", "conversation_id": conversation_id}


@router.put("/conversations/{conversation_id}", response_model=RenameConversationResponse)
async def rename_conversation(
    conversation_id: int,
    data: RenameConversationRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    new_title = data.title.strip()
    if not new_title:
        raise ValidationException("Title cannot be empty")

    check_query = text("""
        SELECT ConversationID FROM Conversations
        WHERE ConversationID = :conversation_id AND UserID = :user_id
    """)
    result = (await db.execute(check_query, {"conversation_id": conversation_id, "user_id": user_id})).fetchone()
    if not result:
        raise NotFoundException("Conversation not found or not owned by user")

    await db.execute(
        text("""
            UPDATE Conversations
            SET Title = :new_title, UpdatedAt = NOW()
            WHERE ConversationID = :conversation_id
        """),
        {"new_title": new_title, "conversation_id": conversation_id},
    )
    await db.commit()
    return RenameConversationResponse(
        message="Conversation renamed successfully",
        conversation_id=conversation_id,
        new_title=new_title,
    )


@router.post("/chat", response_model=ChatResponseSchema)
async def chat(
    data: ChatRequestSchema,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await handle_chat_query(
        session=db,
        user_id=user_id,
        query_text=data.query_text,
        conversation_id=data.conversation_id,
        title=data.title,
        document_ids=data.document_ids
    )
    return ChatResponseSchema(
        conversation_id=result["conversation_id"],
        response=result["response"],
    )


@router.post("/conversations/{conv_id}/upload")
async def chat_upload_document(
    conv_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    payload: dict = Depends(get_current_payload)
):
    """
    Bác sĩ upload PDF trực tiếp trong Chat. 
    Chunk luôn và sẽ tự động xóa sau 1 giờ.
    """
    user_id = payload.get("sub")
    role = payload.get("role")
    
    file_bytes = await file.read()
    
    # 1. Lưu metadata và file vào DB
    upload_result = await upload_pdf_service(
        session=db,
        file_bytes=file_bytes,
        file_name=file.filename,
        uploaded_by=user_id,
        role=role,
        submit_now=True
    )
    
    doc_id = upload_result["document_id"]
    
    # 2. Chunk và đưa lên Qdrant ngay lập tức
    # Gắn thêm namespace chat_{conv_id} để phân biệt nếu cần
    await process_document_to_qdrant(
        session=db,
        file_bytes=file_bytes,
        user_id=str(user_id),
        document_id=doc_id,
        file_name=file.filename,
        namespace=f"chat_{conv_id}"
    )
    
    # 3. Tạo task chạy ngầm để xóa chunk sau 1 giờ
    from core.db_session import AsyncSessionLocal
    async def schedule_deletion_safe(d_id: int):
        await asyncio.sleep(3600)
        await delete_qdrant_points_by_document_id(d_id)
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("UPDATE Documents SET Status = 'Expired' WHERE DocumentID = :d_id"),
                {"d_id": d_id}
            )
            await session.commit()
            
    asyncio.create_task(schedule_deletion_safe(doc_id))

    return {
        "success": True, 
        "document_id": doc_id, 
        "message": "File uploaded and processed. Chunks will be deleted after 1 hour."
    }

