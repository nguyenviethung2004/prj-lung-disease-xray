import os
import redis
from redis import asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

_sync_client = None
_async_client = None

def get_redis_client():
    global _sync_client
    if _sync_client is None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))

        _sync_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db, 
            decode_responses=True
        )
        print(f"Khởi tạo Connection Pool Redis ({redis_host}:{redis_port}) thành công (Sync)")
    return _sync_client

async def get_async_redis_client():
    global _async_client
    if _async_client is None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))

        _async_client = aioredis.from_url(
            f"redis://{redis_host}:{redis_port}/{redis_db}", 
            decode_responses=True
        )
        
        # Backward compatibility in case their specific aioredis version needs await
        import inspect
        if inspect.isawaitable(_async_client):
            _async_client = await _async_client
            
        print(f"Khởi tạo Connection Pool Redis ({redis_host}:{redis_port}) thành công (Async)")
    return _async_client

def get_redis_key(user_id: str, conv_id: int, suffix: str = 'messages') -> str:

    return f"user:{user_id}:conv:{conv_id}:{suffix}"

# if __name__ == "__main__":
#     r = get_redis_client()
#     r.set("test_key", "Hello Upstash Redis!")
#     print("test_key =", r.get("test_key"))
