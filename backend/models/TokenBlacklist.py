from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from core.base import Base


class TokenBlacklist(Base):
    __tablename__ = "TokenBlacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)

    jti = Column(String(255), unique=True, nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    def __repr__(self):
        return f"<TokenBlacklist(jti={self.jti})>"

    async def save(self, session):
        session.add(self)
        await session.commit()
        await session.refresh(self)
