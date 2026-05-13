import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from router.user_routes import router as user_routes
from router.chat_routes import router as chat_router
from router.document_routes import router as document_router
from router.inference_routes import router as inference_router
from router.review_routes import router as review_router
import models # Ensure all models are imported for Base.metadata.create_all
import os
from fastapi.staticfiles import StaticFiles
from core.base import Base
from core.db_session import engine
from core.exceptions import AppException
from starlette.exceptions import HTTPException as StarletteHTTPException
from core.logger import logger  
from core.ai_models import AIModelManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo database (tạo bảng nếu chưa có)
    Base.metadata.create_all(bind=engine)
    logger.info("Kết nối MySQL thành công (Sync)")
    logger.info("Kết nối MySQL thành công (Async - Ready)")
    
    # Khởi tạo Qdrant Collection
    try:
        from utils.qdrant_client_utils import init_qdrant
        init_qdrant()
        logger.info("Khởi tạo Qdrant Collection thành công")
    except Exception as e:
        logger.error(f"Lỗi khởi tạo Qdrant: {e}")
        
    # Khởi tạo và load AI Models
    model_manager = AIModelManager()
    # Chạy load_models trong thread riêng nếu nó quá nặng (blocking)
    # Tuy nhiên FastAPI startup có thể đợi được (lifespan)
    model_manager.load_models()
    app.state.model_manager = model_manager
    
    yield
    # Cleanup logic (nếu cần) có thể để ở đây sau yield

app = FastAPI(
    title="Lung Disease X-Ray AI System",
    description="Backend API cho hệ thống phân tích X-quang phổi với AI & RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "code": exc.status_code
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "code": exc.status_code
        }
    )

# ── CORS ──────────────────────────────────────────────────────────────────────
# ── Static Files ──────────────────────────────────────────────────────────────
# Mount static folder to serve uploaded images and results
if not os.path.exists("static"):
    os.makedirs("static")
    os.makedirs("static/uploads")
    os.makedirs("static/results")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user_routes, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(inference_router, prefix="/api/v1/inference", tags=["AI Inference"])
app.include_router(review_router, prefix="/api/v1", tags=["Doctor Reviews"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
# app.include_router(upload_router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(document_router, prefix="/api/v1", tags=["Documents"])


@app.get("/", tags=["Health"])
def health_check():
    logger.info("Health check")
    return {"status": "ok", "message": "Lung Disease X-Ray API is running"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)