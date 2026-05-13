import asyncio
import json
from celery import shared_task
from core.celery_app import celery_app
from core.db_session import AsyncSessionLocal
from utils.pdf_loader import load_pdf_text_from_bytes, split_text_into_chunks
from utils.text_preprocess import preprocess_text
from utils.pinecone_service import upsert_chunks, upsert_summary, delete_namespace

from sqlalchemy import text
from core.logger import logger
from llm.prompt_builder import summarize_conversation

# Helper to run async functions in a sync task (for Celery)

def run_async(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    else:
        return asyncio.run(coro)

@celery_app.task(name="process_pdf_task")
def process_pdf_task(document_id: int, pdf_bytes: str, uploaded_by: str, namespace: str = None, extra_metadata: dict = None):
    """
    Background task to parse PDF, chunk it, save to DB, and upsert to Pinecone.
    extra_metadata includes: session_id, source, created_at, expire_at
    """
    if isinstance(pdf_bytes, str):
        import base64
        pdf_bytes = base64.b64decode(pdf_bytes)

    async def _process():
        async with AsyncSessionLocal() as session:
            try:
                logger.info(f"Task started: Processing document {document_id}")
                
                # PDF parsing
                pages_data = await asyncio.to_thread(load_pdf_text_from_bytes, pdf_bytes)
                chunks = await asyncio.to_thread(split_text_into_chunks, pages_data)

                chunk_ids = []
                texts = []

                for chunk in chunks:
                    processed_text = await asyncio.to_thread(preprocess_text, chunk['text'])
                    metadata = json.dumps({
                        "page": chunk['page_num'],
                        "start_pos": chunk['start_pos']
                    })

                    insert_stmt = text("""
                        INSERT INTO DocumentChunks (DocumentID, ChunkText, Metadata, CreatedAt)
                        VALUES (:document_id, :chunk_text, :metadata, NOW())
                    """)

                    result = await session.execute(insert_stmt, {
                        "document_id": document_id,
                        "chunk_text": processed_text,
                        "metadata": metadata,
                    })

                    cid = result.lastrowid
                    if cid:
                        chunk_ids.append(cid)
                        texts.append(processed_text)

                await session.commit()
                logger.info(f"Saved {len(chunk_ids)} chunks for document {document_id}")

                if chunk_ids:
                    logger.info(f"Upserting to Pinecone for document {document_id}...")
                    await asyncio.to_thread(
                        upsert_chunks, 
                        chunk_ids, 
                        texts, 
                        user_id=uploaded_by, 
                        document_id=document_id,
                        namespace=namespace,
                        extra_metadata=extra_metadata
                    )
                    logger.info(f"Pinecone indexing completed for document {document_id} (namespace: {namespace})")

                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in Celery task for doc {document_id}: {e}")
                raise e

    return run_async(_process())



@celery_app.task(name="summarize_conversation_task")
def summarize_conversation_task(conversation_id: int, user_id: str):
    """
    Background task to generate a summary of the conversation and store it in DB and Vector DB.
    """
    async def _summarize():
        async with AsyncSessionLocal() as session:
            try:
                # 1. Lấy tất cả tin nhắn của hội thoại
                query = text("""
                    SELECT Role, Text FROM Messages 
                    WHERE ConversationID = :conv_id 
                    ORDER BY MessageID ASC
                """)
                result = await session.execute(query, {"conv_id": conversation_id})
                messages = result.fetchall()
                
                if not messages:
                    return "No messages to summarize"

                history_str = "\n".join([f"{m[0]}: {m[1]}" for m in messages])
                
                # 2. Gọi LLM để tóm tắt
                summary_text = await asyncio.to_thread(summarize_conversation, history_str)

                # 3. Lưu vào DB
                insert_summary = text("""
                    INSERT INTO VectorMemorySummary (ConversationID, SummaryText, CreatedAt)
                    VALUES (:conv_id, :summary_text, NOW())
                """)
                res = await session.execute(insert_summary, {
                    "conv_id": conversation_id,
                    "summary_text": summary_text
                })
                summary_id = res.lastrowid
                await session.commit()

                # 4. Lưu vào Pinecone
                if summary_id:
                    await asyncio.to_thread(
                        upsert_summary, 
                        summary_text=summary_text, 
                        summary_id=summary_id, 
                        user_id=user_id, 
                        conv_id=conversation_id
                    )
                
                logger.info(f"Summary generated and indexed for conversation {conversation_id}")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in summarize task for conv {conversation_id}: {e}")
                raise e

@celery_app.task(name="cleanup_expired_namespaces_task")
def cleanup_expired_namespaces_task():
    """
    Tìm các namespace đã hết hạn trong DB và xóa khỏi Pinecone.
    """
    async def _cleanup():
        async with AsyncSessionLocal() as session:
            try:
                now = datetime.now()
                # 1. Tìm các bản ghi đã hết hạn
                query = text("""
                    SELECT NamespaceID, NamespacePath FROM PrivateNamespaces 
                    WHERE ExpireAt <= :now
                """)
                result = await session.execute(query, {"now": now})
                expired = result.fetchall()

                for row in expired:
                    ns_id, ns_path = row
                    logger.info(f"Cleaning up expired namespace: {ns_path}")
                    
                    # 2. Xóa khỏi Pinecone
                    await asyncio.to_thread(delete_namespace, ns_path, index_type="chunk")
                    await asyncio.to_thread(delete_namespace, ns_path, index_type="summary")

                    # 3. Xóa khỏi DB
                    await session.execute(
                        text("DELETE FROM PrivateNamespaces WHERE NamespaceID = :ns_id"),
                        {"ns_id": ns_id}
                    )
                
                await session.commit()
                if expired:
                    logger.info(f"Successfully cleaned up {len(expired)} expired namespaces.")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in cleanup task: {e}")
                raise e

    from datetime import datetime
    return run_async(_cleanup())
