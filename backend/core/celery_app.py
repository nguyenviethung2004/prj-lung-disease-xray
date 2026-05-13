import os
from celery import Celery
from core.config import settings


# Lấy cấu hình từ .env

BROKER_URL = settings.BROKER_URL
RESULT_BACKEND = settings.RESULT_BACKEND
# Khởi tạo Celery
celery_app = Celery(
    "lung_disease_tasks",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["services.tasks"]  # Tự động tìm tasks trong file này
)

# Cấu hình bổ sung
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Trên Windows thường cần solo pool hoặc gevent/eventlet
    worker_prefetch_multiplier=1,
)

if __name__ == "__main__":
    celery_app.start()
