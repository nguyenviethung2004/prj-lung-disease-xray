from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.db_session import get_async_db
from models.TokenBlacklist import TokenBlacklist
from core.exceptions import AppException, UnauthorizedException, ForbiddenException
from typing import List, Dict, Any

from core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

bearer_scheme = HTTPBearer()


def create_access_token(identity: str, additional_claims: dict = None, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": identity,
        "exp": expire,
        "type": "access",
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(identity: str, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": identity,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode token, trả về payload dict. Raise JWTError nếu invalid."""
    if not token or token.lower() in ["null", "undefined"]:
        raise JWTError("Token is missing or invalid")
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_payload(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Dependency trả về toàn bộ payload đã decode từ access token.
    Kiểm tra Blacklist để hủy token đã logout.
    Kiểm tra flag must_change_password để chặn các request trái phép.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException("Access token required")

        # Kiểm tra Blacklist
        jti = payload.get("jti")
        if jti:
            query = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
            result = await db.execute(query)
            if result.scalar_one_or_none():
                raise UnauthorizedException("Token has been revoked (logged out)")
        
        # Kiểm tra yêu cầu đổi mật khẩu (Forced Change Password)
        if payload.get("must_change_password"):
            # Chỉ cho phép access endpoint đổi mật khẩu hoặc logout
            allowed_paths = [
                "/api/v1/auth/change-password", 
                "/api/v1/auth/logout-token",
                "/api/v1/auth/me"
            ]
            
            # Chuẩn hóa path: xóa dấu gạch chéo cuối cùng để so sánh chính xác
            current_path = request.url.path.rstrip('/')
            
            if current_path not in allowed_paths:
                raise ForbiddenException(
                    "Mật khẩu của bạn cần được thay đổi trước khi truy cập các tính năng khác."
                )

        return payload
    except ExpiredSignatureError:
        raise UnauthorizedException("Token expired")
    except JWTError:
        raise UnauthorizedException("Could not validate credentials")


def get_current_user(payload: dict = Depends(get_current_payload)) -> str:
    """
    Dependency trả về user_id (str) từ JWT.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid user ID in token")
    return user_id


def get_current_user_refresh(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    Dependency trả về toàn bộ payload từ refresh token.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Refresh token required")
        return payload
    except JWTError:
        raise UnauthorizedException("Invalid or expired refresh token")


class RoleChecker:
    """
    Dependency factory để kiểm tra quyền truy cập dựa trên Role.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, payload: dict = Depends(get_current_payload)):
        user_role = payload.get("role")
        if user_role not in self.allowed_roles:
            raise ForbiddenException(
                message=f"Quyền '{user_role}' không được phép truy cập tài nguyên này. Yêu cầu: {self.allowed_roles}"
            )
        return user_role