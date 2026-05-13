from datetime import timedelta
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.db_session import get_async_db
from models.Users import User
from models.TokenBlacklist import TokenBlacklist
from schemas.user_schema import (
    UserLoginSchema, 
    UserRegisterSchema,
    AdminUserCreateSchema, 
    ChangePasswordSchema,
    UserOutSchema,
    UserUpdateSchema
)
from services.user_service import (
    login_service, 
    register_service,
    admin_create_user_service, 
    change_password_service,
    get_me_service,
    get_all_users_service,
    update_user_service,
    delete_user_service
)
from utils.jwt_manager import (
    create_access_token,
    decode_token,
    get_current_user,
    get_current_user_refresh,
    RoleChecker
)
_bearer = HTTPBearer()
router = APIRouter(prefix="", tags=["Auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegisterSchema, db: AsyncSession = Depends(get_async_db)):
    return await register_service(db, data)


@router.get("/me", response_model=UserOutSchema)
async def get_me(
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user)
):
    return await get_me_service(db, int(user_id))



@router.post("/login")
async def login(data: UserLoginSchema, db: AsyncSession = Depends(get_async_db)):
    return await login_service(db, data)


@router.post(
    "/admin/create-user", 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["Superadmin"]))]
)
async def admin_create_user(
    data: AdminUserCreateSchema,
    db: AsyncSession = Depends(get_async_db)
):
    return await admin_create_user_service(db, data)


@router.get(
    "/admin/users", 
    response_model=List[UserOutSchema],
    dependencies=[Depends(RoleChecker(["Superadmin"]))]
)
async def get_all_users(
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    return await get_all_users_service(db, role)


@router.patch(
    "/admin/update-user/{user_id}", 
    response_model=UserOutSchema,
    dependencies=[Depends(RoleChecker(["Superadmin"]))]
)
async def update_user(
    user_id: int,
    data: UserUpdateSchema,
    db: AsyncSession = Depends(get_async_db)
):
    return await update_user_service(db, user_id, data)


@router.delete(
    "/admin/delete-user/{user_id}",
    dependencies=[Depends(RoleChecker(["Superadmin"]))]
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user_id: str = Depends(get_current_user)
):
    return await delete_user_service(db, user_id, int(current_user_id))



@router.post("/change-password")
async def change_password(
    data: ChangePasswordSchema,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user)
):
    return await change_password_service(db, int(user_id), data)


@router.post("/refresh")
async def refresh_token(
    payload: dict = Depends(get_current_user_refresh),
    db: AsyncSession = Depends(get_async_db),
):
    current_user_id = payload.get("sub")
    jti = payload.get("jti")

    # Kiểm tra refresh token có bị blacklist không
    if jti:
        query = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token đã bị thu hồi"
            )

    user = await User.get_by_emails(db, payload.get("email", "")) # User ID might be better but let's see if we have email in refresh payload
    # actually current_user_id was sub. Let's try finding by ID or use User helper if available.
    # The models/Users logic usually works with Email in my previous refactor.
    # Let's check if User has get_by_id or just use select
    
    query_user = select(User).where(User.UserID == int(current_user_id))
    result_user = await db.execute(query_user)
    user = result_user.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy user")

    new_access_token = create_access_token(
        identity=str(user.UserID),
        additional_claims={
            "username": user.UserName,
            "role": user.Role,
            "refresh_jti": jti,
        },
        expires_delta=timedelta(minutes=10),
    )

    return {
        "message": "Access token refreshed successfully",
        "access_token": new_access_token,
    }


@router.post("/logout")
async def logout(
    user_id: str = Depends(get_current_user),
    # FIX 2: Cập nhật type hint chuẩn xác cho Docs
    payload: Optional[Dict[str, Any]] = None, 
    db: AsyncSession = Depends(get_async_db),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Dùng endpoint /logout-token"
    )


@router.post("/logout-token")
async def logout_with_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_async_db),
):
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required")

    jti_access = payload.get("jti")
    jti_refresh = payload.get("refresh_jti")

    try:
        if jti_access:
            # Kiểm tra xem đã có trong blacklist chưa
            q_access = select(TokenBlacklist).where(TokenBlacklist.jti == jti_access)
            if not (await db.execute(q_access)).scalar_one_or_none():
                db.add(TokenBlacklist(jti=jti_access))
                
        if jti_refresh:
            # Kiểm tra xem đã có trong blacklist chưa
            q_refresh = select(TokenBlacklist).where(TokenBlacklist.jti == jti_refresh)
            if not (await db.execute(q_refresh)).scalar_one_or_none():
                db.add(TokenBlacklist(jti=jti_refresh))
                
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"message": "Successfully logged out"}