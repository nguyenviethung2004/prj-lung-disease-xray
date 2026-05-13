import asyncio
from core.db_session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict
import json
from sqlalchemy.exc import SQLAlchemyError
from core.logger import logger
from core.exceptions import AppException
from utils.redis import get_async_redis_client, get_redis_key
from datetime import datetime
from llm.prompt_builder import summarize_conversation, generate_answer
from services.rag_service import search_hybrid_qdrant
from utils.text_preprocess import clean_text


async def get_last_messages_from_redis(user_id: str, conv_id: int, count:int = 5)->List[Dict]:
        client = await get_async_redis_client()
        redis_key = get_redis_key(user_id, conv_id)
        last_msgs_jsonn = await client.lrange(redis_key, -count, -1)
        if not last_msgs_jsonn:
            print(f"No messages found in Redis for conv {conv_id}.")
            return []
        last_messages  = [json.loads(msg) for msg in last_msgs_jsonn]
        print(f"Lấy {len(last_messages )} tin cuối của conv {conv_id} từ Redis")
        return last_messages



async def create_new_conversation(session: AsyncSession, user_id: str, title: str = 'New Chat')->int:
    insert_conversation = text("""
        INSERT INTO Conversations (UserID, Title, CreatedAt, UpdatedAt)
        VALUES (:user_id, :title, NOW(), NOW())
    """)
    try:
        result = await session.execute(insert_conversation,{
                                    'user_id': user_id, 
                                    'title': title
                                 })
        conv_id = result.lastrowid
        if not conv_id:
            raise AppException("Failed to create conversation")
        await session.commit()
        return conv_id
    except SQLAlchemyError as e:
        await session.rollback()
        print(f"Database error: {e}")
        raise e


async def get_conversations_list(session: AsyncSession, user_id: str, limit: int = 20)->List[Dict]:
    select_conversations_list = text("""
        SELECT ConversationID, Title
        FROM Conversations
        WHERE UserID = :user_id
        ORDER BY UpdatedAt DESC
        LIMIT :limit
    """)
    result = await session.execute(select_conversations_list, {'user_id': user_id, 'limit': limit})
    rows = result.mappings().all()
    return [
        {
            "conversation_id": row["ConversationID"],
            "title": row["Title"]
        }
        for row in rows
    ]


async def load_conversation_history(session: AsyncSession, conversation_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    query = text("""
        SELECT Role, Text, Timestamp
        FROM Messages
        WHERE ConversationID = :conversation_id
        ORDER BY Timestamp DESC, MessageID DESC
        LIMIT :limit OFFSET :offset
    """)

    result = (await session.execute(query, {
            "conversation_id": conversation_id,
            "limit": limit,
            "offset": offset
        })).mappings().all()

    messages = [
            {"role": row["Role"], "text": row["Text"], "timestamp": row["Timestamp"]}
            for row in result
        ][::-1]

    return messages


async def get_summarys_by_ids(session: AsyncSession, summary_ids: List[int]) -> List[str]:
    if not summary_ids:
        return []

    placeholders = ", ".join([f":id{i}" for i in range(len(summary_ids))])

    query = text(f"""
        SELECT SummaryText
        FROM VectorMemorySummary
        WHERE SummaryID IN ({placeholders})
    """)

    params = {f"id{i}": summary_ids[i] for i in range(len(summary_ids))}

    result = await session.execute(query, params)

    return [row[0] for row in result.fetchall()]


def join_message_texts(messages: List[Dict]) -> str | None:
    if not messages:
        return None
    return "\n".join([f"{m.get('role', 'unknown').capitalize()}: {m.get('text', '')}" for m in messages])


async def save_message_sql_and_cache(
    session: AsyncSession, 
    user_id: str, 
    conv_id: int, 
    role: str, 
    text_message: str
) -> Dict:
    """
    Lưu tin nhắn vào MySQL và cập nhật cache Redis (5 tin gần nhất).
    """
    client = await get_async_redis_client()  
    redis_key = get_redis_key(user_id, conv_id)
    
    # 1. Lưu vào MySQL
    insert_query = text("""
        INSERT INTO Messages (ConversationID, Role, Text, Timestamp)
        VALUES (:conv_id, :role, :text, :timestamp)
    """)
    
    timestamp = datetime.now()
    await session.execute(insert_query, {
        'conv_id': conv_id,
        'role': role,
        'text': text_message,
        'timestamp': timestamp
    })
    await session.commit()

    # 2. Cập nhật Cache Redis
    message_data = {
        'role': role,
        'text': text_message,
        'timestamp': timestamp.isoformat()
    }
    
    async with client.pipeline(transaction=True) as pipe:
        await pipe.rpush(redis_key, json.dumps(message_data))
        await pipe.ltrim(redis_key, -5, -1)
        await pipe.expire(redis_key, 3600)
        await pipe.execute()

    return {"success": True}


# async def handle_chat_query(session: AsyncSession, user_id: str, query_text: str, conversation_id: int = None, title: str = 'New Chat') -> Dict:
    
#     # 1. Tạo conversation mới nếu chưa có
#     import time
#     start = time.time()
#     if not conversation_id:
#         conversation_id = await create_new_conversation(session, user_id, title)
#     else:
#         logger.info(f"Using existing ConversationID: {conversation_id}")
    
#     context = []
    
#     # 2. Tìm kiếm Context từ Vector DB (RAG) sử dụng Qdrant Hybrid Search
#     try:
#         qdrant_results, detected_language = await search_hybrid_qdrant(
#             query=query_text, 
#             session=session, 
#             user_id=None, 
#             limit=5
#         )
#         logger.info(f"User is asking in: {detected_language}")
        
#         if qdrant_results:
#             for res in qdrant_results:
#                 payload = res.get("payload", {})
#                 page = payload.get("pages", "N/A")
#                 doc_id = payload.get("document_id", "unknown")
#                 text_snippet = res.get("chunk_text", "")
                
#                 context.append(f"[Page {page}] {text_snippet}")
            
#             logger.info(f"Found {len(qdrant_results)} chunks.")
#         else:
#             logger.warning("No relevant context found.")
            
#     except Exception as e:
#         logger.error(f"Error searching Qdrant: {e}")
    
#     # 3. Lấy lịch sử chat gần nhất từ Redis
#     get_last_messages = await get_last_messages_from_redis(user_id, conversation_id, count=3)
#     messages_recently = join_message_texts(get_last_messages)
#     logger.info(f"Conversation summary: {len(get_last_messages)}")

#     # 4. Gọi LLM Groq
#     logger.info("Calling LLM...")
#     try:
#         llm_response = await generate_answer(
#             user_query=query_text,  
#             retrieved_context="\n".join(context) if context else None,
#             conversation_summary=None,
#             messages_recently=messages_recently,
#             detected_language=detected_language
#         )
#         logger.info("LLM trả về phản hồi thành công.")
#     except Exception as e:
#         logger.error(f"Error calling LLM: {e}")
#         llm_response = "Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn."

#     # 5. Lưu tin nhắn User và Assistant vào MySQL & Redis
#     try:
#         await save_message_sql_and_cache(
#             session=session, user_id=user_id, conv_id=conversation_id, role='user', text_message=query_text
#         )
#         await save_message_sql_and_cache(
#             session=session, user_id=user_id, conv_id=conversation_id, role='assistant', text_message=llm_response
#         )
        
        
#     except Exception as e:
#         logger.error(f"Error saving messages or triggering tasks: {e}")
#     end = time.time()
#     logger.info(f"Total time for handling chat query: {end - start:.2f} seconds")
#     return {
#         "response": llm_response,
#         "conversation_id": conversation_id
#     }

async def handle_chat_query(session: AsyncSession, user_id: str, query_text: str, conversation_id: int = None, title: str = 'New Chat', document_ids: List[int] = None) -> Dict:
    import time
    start = time.time()
    
    # 1. Tạo conversation mới nếu chưa có (Phải await vì cần ID để chuẩn bị cho các bước sau)
    if not conversation_id:
        conversation_id = await create_new_conversation(session, user_id, title)
    else:
        logger.info(f"Using existing ConversationID: {conversation_id}")
    
    # 2. CHẠY SONG SONG: Tìm kiếm RAG và Lấy lịch sử chat từ Redis
    # Max(RAG, Redis) thay vì RAG + Redis
    tasks = [
        search_hybrid_qdrant(query=query_text, session=session, user_id=user_id, limit=8, document_ids=document_ids),
        get_last_messages_from_redis(user_id, conversation_id, count=3)
    ]
    
    # Đợi cả 2 task hoàn thành đồng thời
    (qdrant_data, get_last_messages) = await asyncio.gather(*tasks)
    
    # Phân tách kết quả Qdrant
    qdrant_results, detected_language = qdrant_data
    logger.info(f"User is asking in: {detected_language}")
    
    # Xử lý context
    context = []
    if qdrant_results:
        for res in qdrant_results:
            payload = res.get("payload", {})
            page = payload.get("pages", "N/A")
            text_snippet = res.get("chunk_text", "")
            context.append(f"[Page {page}] {text_snippet}")
    
    # Xử lý history
    messages_recently = join_message_texts(get_last_messages)

    # 3. Gọi LLM Groq (Chuẩn bị đầy đủ context và history trước khi gọi)
    logger.info("Calling LLM...")
    try:
        llm_response = await generate_answer(
            user_query=query_text,  
            retrieved_context="\n".join(context) if context else None,
            conversation_summary=None,
            messages_recently=messages_recently,
            detected_language=detected_language
        )
        logger.info("LLM trả về phản hồi thành công.")
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        llm_response = "Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn."

    # 4. LƯU DỮ LIỆU CHẠY NGẦM (NON-BLOCKING)
    # Trả về kết quả cho User ngay lập tức, việc lưu DB/Cache sẽ chạy sau
    async def background_save_tasks():
        async with AsyncSessionLocal() as bg_session:
            try:
                # Lưu tin nhắn User và Bot vào MySQL & Redis (Dùng bg_session độc lập)
                await save_message_sql_and_cache(
                    session=bg_session, user_id=user_id, conv_id=conversation_id, role='user', text_message=query_text
                )
                await save_message_sql_and_cache(
                    session=bg_session, user_id=user_id, conv_id=conversation_id, role='assistant', text_message=llm_response
                )
                logger.info(f"Successfully saved messages for conversation {conversation_id} in background.")
            except Exception as e:
                logger.error(f"Error in background_save_tasks: {e}")

    # Kích hoạt task chạy ngầm không chặn luồng chính
    asyncio.create_task(background_save_tasks())

    end = time.time()
    logger.info(f"Total time for handling chat query (to client): {end - start:.2f} seconds")
    
    return {
        "response": llm_response,
        "conversation_id": conversation_id
    }