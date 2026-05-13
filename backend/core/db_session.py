from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.database import get_database_engine, get_async_database_engine

engine = get_database_engine()
async_engine = get_async_database_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

def get_db():
    """FastAPI Depends — yield DB session (Sync)."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """FastAPI Depends — yield Async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
