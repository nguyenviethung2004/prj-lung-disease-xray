from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-default-secret-key")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))
    MYSQL_HOST=os.getenv("MYSQL_HOST")
    MYSQL_PORT=os.getenv("MYSQL_PORT")
    MYSQL_DB=os.getenv("MYSQL_DB")
    MYSQL_USER=os.getenv("MYSQL_USER")
    MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD")
    REDIS_HOST=os.getenv("REDIS_HOST")
    REDIS_PORT=os.getenv("REDIS_PORT")
    REDIS_DB=os.getenv("REDIS_DB")
    REDIS_URL=os.getenv("REDIS_URL")
    CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND")
    PINECONE_API_KEY=os.getenv("PINECONE_API_KEY")
    GROQ_API_KEY=os.getenv("GROQ_API_KEY")
    BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    # AI Models
    CLASSIFICATION_MODEL_PATH = os.getenv("CLASSIFICATION_MODEL_PATH")
    DETECTION_MODEL_PATH = os.getenv("DETECTION_MODEL_PATH")
    SEGMENTATION_MODEL_PATH = os.getenv("SEGMENTATION_MODEL_PATH")
    DETECTION_THRESHOLD = float(os.getenv("DETECTION_THRESHOLD", 0.5))
    IMAGE_SIZE_CLASSIFICATION = int(os.getenv("IMAGE_SIZE_CLASSIFICATION", 380))

settings = Settings()