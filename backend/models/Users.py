from sqlalchemy import Column, Integer, String, DateTime, select, Boolean
from sqlalchemy.sql import func
from core.base import Base
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "Users"

    UserID = Column(Integer, primary_key=True, autoincrement=True)

    UserName = Column(String(100), nullable=False, unique=True)
    Email = Column(String(255), unique=True)
    PasswordHash = Column(String(255))

    CreatedAt = Column(
        DateTime,
        server_default=func.now()
    )

    Role = Column(
        String(20),
        nullable=False,
        server_default="Doctors"
    )
    CreatedAt = Column(DateTime, server_default=func.now())
    UpdatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

    MustChangePassword = Column(Boolean, default=True)
    IsDeleted = Column(Boolean, default=False, nullable=False, server_default="0")

    def __repr__(self):
        return f"<User(UserName={self.UserName}, Email={self.Email})>"

    def set_password(self, password):
        self.PasswordHash = pwd_context.hash(password)

    def check_password(self, password):
        return pwd_context.verify(password, self.PasswordHash)

    @classmethod
    async def get_by_emails(cls, session: AsyncSession, email: str):
        query = select(cls).where(cls.Email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_username(cls, session: AsyncSession, username: str):
        query = select(cls).where(cls.UserName == username)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def save(self, session: AsyncSession):
        session.add(self)
        await session.commit()
        await session.refresh(self)

    async def delete(self, session: AsyncSession):
        self.IsDeleted = True
        await session.commit()
