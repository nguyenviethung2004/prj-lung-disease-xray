import os
import json
import asyncio
import tempfile
from typing import Optional, List, Dict
from qdrant_client.http.models import PointStruct, SparseVector 
from sqlalchemy.ext.asyncio import AsyncSession
from rag.pipeline import chunk_files
from utils.embedding_utils import get_embeddings, get_sparse_embeddings
from utils.qdrant_client_utils import get_qdrant_client, COLLECTION_NAME
from qdrant_client.http.models import PointStruct
import uuid
from models.DocumentChunks import DocumentChunks
from core.logger import logger
from qdrant_client import models
from sqlalchemy import select
from models.DocumentChunks import DocumentChunks
from llm.prompt_builder import translate_query_to_english
import time


async def process_document_to_qdrant(
    session: AsyncSession,
    file_bytes: bytes,
    user_id: str,
    document_id: int,
    file_name: str = "document.pdf",
    namespace: Optional[str] = None,
    is_public: bool = False,
    chunk_size: int = 600,
    chunk_overlap: int = 50,
):
    """
    Service để chunk PDF, nhúng (embed), đưa lên Pinecone và lưu MySQL.
    """
    # Tạo một file tạm từ bytes để pipeline.py có thể đọc được
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_file_path = tmp_file.name

    try:
        logger.info(f"Bắt đầu quá trình chunk cho Document {document_id}")
        
        # 1. Gọi pipeline.py để chunk files
        chunks = await asyncio.to_thread(
            chunk_files,
            input_path=tmp_file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            overwrite_outputs=True
        )

        if not chunks:
            logger.warning(f"Không tìm thấy nội dung để chunk cho Document {document_id}")
            return {
                "success": False,
                "message": "Không tìm thấy nội dung để chunk",
                "chunk_count": 0,
                "document_id": document_id
            }

        logger.info(f"Hoàn thành chunk, thu được {len(chunks)} chunks. Đang chuẩn bị đưa lên Qdrant và DB...")

        # 2. Lấy văn bản
        texts = [chunk["chunk_text"] for chunk in chunks]
        
        logger.info("Bắt đầu lấy embeddings cho các chunks...")
        embeddings = await get_embeddings(texts)
        sparse_embeddings = await get_sparse_embeddings(texts)
        
        logger.info("Bắt đầu chuẩn bị dữ liệu lưu DB và Qdrant...")
        qdrant_client = get_qdrant_client()
        points = []
        
        for chunk, embedding, sparse_emb in zip(chunks, embeddings, sparse_embeddings):
            chunk_index = str(chunk["chunk_index"])
            
            # Qdrant yêu cầu ID là chuỗi UUID hợp lệ hoặc Integer. 
            # Ta tạo UUID định danh duy nhất cho chunk này:
            raw_id = f"pdf_{user_id}_{document_id}_{chunk_index}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))
            
            payload = {
                "user_id": str(user_id),
                "document_id": document_id,
                "is_public": is_public,
                "chunk_id": str(chunk.get("chunk_id", chunk_index)),
                "pages": str(chunk.get("chunk_pages", chunk.get("pages", ""))),
                "titles_context": chunk.get("titles_context", "")
            }
                
            points.append(
                PointStruct(
                    id=point_id,
                    vector={
                        "text-dense": embedding.tolist(),
                        "text-sparse": SparseVector(
                            indices=sparse_emb["indices"],
                            values=sparse_emb["values"]
                        )
                    },
                    payload=payload
                )
            )
            
            # Lưu vào Database (DocumentChunks)
            doc_chunk = DocumentChunks(
                DocumentID=document_id,
                QdrantPointID=point_id, # Đổi tên cột sau nếu cần, hiện tại lưu Qdrant ID
                ChunkText=chunk["chunk_text"],
                Metadata=json.dumps(payload)
            )
            session.add(doc_chunk)

        # Lưu tất cả các chunk xuống DB
        await session.commit()
        logger.info("Thành công lưu các chunk vào MySQL.")

        # Ghi các vector lên Qdrant (Chia nhỏ thành từng batch để tránh Timeout)
        BATCH_SIZE = 50
        for i in range(0, len(points), BATCH_SIZE):
            batch_points = points[i : i + BATCH_SIZE]
            await asyncio.to_thread(
                qdrant_client.upsert,
                collection_name=COLLECTION_NAME,
                points=batch_points
            )
            logger.info(f"Đã upsert batch {i // BATCH_SIZE + 1} ({len(batch_points)} points) lên Qdrant")
            
        logger.info(f"Thành công tổng cộng upsert {len(points)} chunk lên Qdrant (Collection: {COLLECTION_NAME})")
        
        return {
            "success": True,
            "message": "Hoàn tất xử lý tài liệu, đã lưu DB và Qdrant.",
            "chunk_count": len(points),
            "document_id": document_id
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"Lỗi trong quá trình process_document_to_qdrant: {e}")
        raise e
    finally:
        # Xoá file tạm sau khi đã xử lý xong
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)



async def search_hybrid_qdrant(query: str, session: AsyncSession, user_id: str = None, limit: int = 5, document_ids: List[int] = None):
    """
    Tìm kiếm kết hợp (Hybrid Search) sử dụng Qdrant.
    Kết hợp Vector Ngữ nghĩa (Dense) và Vector Từ khóa (Sparse - BM25).
    """
    logger.info(f"Bắt đầu Hybrid Search (BM25 + Semantic) cho query: '{query}'")
    
    start_time = time.time()
    if document_ids:
        logger.info(f"Đang thực hiện Hybrid Search giới hạn trong các Document IDs: {document_ids}")
    else:
        logger.info("Đang thực hiện Hybrid Search trên toàn bộ kho dữ liệu (Global).")

    # Chuyển đổi câu hỏi sang tiếng Anh và nhận diện ngôn ngữ
    language, english_query = await translate_query_to_english(query)
    if english_query != query:
        logger.info(f"Đã phát hiện ngôn ngữ '{language}', chuyển đổi câu hỏi sang tiếng Anh để tìm kiếm: '{english_query}'")
        
    qdrant_client = get_qdrant_client()
    logger.info(f"Câu hỏi sau khi chuyển sang tiếng Anh: {english_query}")
    # 1. Nhúng câu hỏi (Query) ra 2 loại vector bằng câu hỏi tiếng Anh
    dense_emb_list = await get_embeddings(english_query)
    dense_emb = dense_emb_list[0].tolist()
    
    sparse_emb_list = await get_sparse_embeddings(english_query)
    sparse_emb = sparse_emb_list[0]
    
    # TẠO BỘ LỌC CHUNG (Để đảm bảo tính riêng tư và không loãng thông tin)
    must_conditions = []
    
    if document_ids and len(document_ids) > 0:
        # 1. Trường hợp tìm trong tài liệu cụ thể:
        # Chỉ lấy trong list ID này
        must_conditions.append(
            models.FieldCondition(
                key="document_id", match=models.MatchAny(any=document_ids)
            )
        )
    else:
        # 2. Trường hợp tìm kiếm Global (không truyền doc_ids):
        # CHỈ lấy các tài liệu công khai (is_public = True)
        # Điều này giúp bác sĩ này không tìm thấy file tạm của bác sĩ kia
        must_conditions.append(
            models.FieldCondition(
                key="is_public", match=models.MatchValue(value=True)
            )
        )
    
    user_filter = models.Filter(must=must_conditions) if must_conditions else None
    
    # 2. Cấu hình Prefetch để query song song 2 Vector
    prefetch = [
        models.Prefetch(
            query=dense_emb,
            using="text-dense",
            filter=user_filter, # Sẽ không lọc nếu user_filter là None
            limit=limit * 2, 
        ),
        models.Prefetch(
            query=models.SparseVector(
                indices=sparse_emb["indices"], 
                values=sparse_emb["values"],
            ),
            using="text-sparse",
            filter=user_filter, # Sẽ không lọc nếu user_filter là None
            limit=limit * 2,
        ),
    ]
    
    # 3. Chạy Query bằng Qdrant với Fusion RRF
    response = await asyncio.to_thread(
        qdrant_client.query_points,
        collection_name=COLLECTION_NAME,
        prefetch=prefetch,
        query=models.FusionQuery(
            fusion=models.Fusion.RRF
        ),
        # ĐÃ XOÁ query_filter Ở ĐÂY để tránh lọc sai logic
        limit=limit,
    )
    
    # Lấy danh sách ID từ Qdrant
    if not response.points:
        return [], language
        
    point_ids = [str(point.id) for point in response.points]
    
    # Truy vấn DB để lấy ChunkText
    stmt = select(DocumentChunks).where(DocumentChunks.QdrantPointID.in_(point_ids))
    db_result = await session.execute(stmt)
    db_chunks = {chunk.QdrantPointID: chunk.ChunkText for chunk in db_result.scalars().all()}
    
    # Lọc kết quả theo ngưỡng điểm (Score Threshold)
    # Ngưỡng 0.7 để đảm bảo chỉ lấy kết quả thực sự liên quan
    SCORE_THRESHOLD = 0.5
    
    results = []
    for point in response.points:
        if point.score < SCORE_THRESHOLD:
            continue
            
        pid = str(point.id)
        results.append({
            "point_id": pid,
            "score": point.score,
            "payload": point.payload,
            "chunk_text": db_chunks.get(pid, "")
        })
        
    logger.info(f"Hybrid Search tìm thấy {len(results)} kết quả đạt ngưỡng (>{SCORE_THRESHOLD}).")
    
    end_time = time.time()
    logger.info(f"Hybrid Search completed in {end_time - start_time:.2f} seconds.")
    for result in results:
        print(f"Point ID: {result['point_id']}, Score: {result['score']:.4f}, Payload: {result['payload']}")
        print(result['chunk_text'])
    return results, language

async def delete_qdrant_points_by_document_id(document_id: int):
    """Xóa các points của một document cụ thể khỏi Qdrant."""
    qdrant_client = get_qdrant_client()
    try:
        await asyncio.to_thread(
            qdrant_client.delete,
            collection_name=COLLECTION_NAME,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    ),
                ]
            ),
        )
        logger.info(f"Đã xóa points của Document {document_id} khỏi Qdrant.")
    except Exception as e:
        logger.error(f"Lỗi khi xóa points của Document {document_id}: {e}")