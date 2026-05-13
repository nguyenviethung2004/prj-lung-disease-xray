
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.Users import User
from utils.jwt_manager import create_access_token, create_refresh_token, decode_token
from core.exceptions import AppException, ValidationException, ConflictException, UnauthorizedException, NotFoundException
from typing import Optional, Any
import secrets
import string

async def register_service(session: AsyncSession, data):
    try:
        email = data.email
        username = data.username
        password = data.password

        # Kiểm tra trùng lặp
        if await User.get_by_emails(session, email):
            raise ConflictException("Email đã được sử dụng")
        
        if await User.get_by_username(session, username):
            raise ConflictException("Username đã được sử dụng")

        new_user = User(
            UserName=username,
            Email=email,
            Role="Doctors",
            MustChangePassword=False
        )
        new_user.set_password(password)
        await new_user.save(session)

        return {
            "status": "success",
            "message": "User registered successfully",
            "user": {
                "id": new_user.UserID,
                "email": new_user.Email,
                "username": new_user.UserName,
                "role": new_user.Role
            }
        }

    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        raise e


async def admin_create_user_service(session: AsyncSession, data):
    try:
        email = data.email
        username = data.username
        role = data.role
        
        # Generate random 8-character password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(8))

        if await User.get_by_emails(session, email):
            raise ConflictException("Email already exists")

        new_user = User(
            UserName=username,
            Email=email,
            Role=role,
            MustChangePassword=True # Forced change
        )
        new_user.set_password(password)
        await new_user.save(session)

        return {"message": "Doctor account created successfully", "default_password": password}

    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        raise e


async def login_service(session: AsyncSession, data):
    try:
        email = data.email
        password = data.password

        user = await User.get_by_emails(session, email)
        if not user or not user.check_password(password):
            raise UnauthorizedException("Invalid email or password")

        refresh_token = create_refresh_token(identity=str(user.UserID))
        jti_refresh = decode_token(refresh_token).get("jti", refresh_token[:16])

        additional_claims = {
            "username": user.UserName,
            "role": user.Role,
            "refresh_jti": jti_refresh,
            "must_change_password": user.MustChangePassword
        }

        access_token = create_access_token(
            identity=str(user.UserID),
            additional_claims=additional_claims,
            expires_delta=timedelta(minutes=10)
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.UserID,
                "email": user.Email,
                "username": user.UserName,
                "role": user.Role,
                "must_change_password": user.MustChangePassword
            }
        }

    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        raise e


async def change_password_service(session: AsyncSession, user_id: int, data):
    try:
        query = select(User).where(User.UserID == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("User not found")

        if not user.check_password(data.old_password):
            raise ValidationException("Mật khẩu cũ không chính xác")

        user.set_password(data.new_password)
        user.MustChangePassword = False
        user.UpdatedAt = datetime.now()
        await user.save(session)

        # Trả về token mới để xóa flag must_change_password trong JWT
        refresh_token = create_refresh_token(identity=str(user.UserID))
        jti_refresh = decode_token(refresh_token).get("jti", refresh_token[:16])

        additional_claims = {
            "username": user.UserName,
            "role": user.Role,
            "refresh_jti": jti_refresh,
            "must_change_password": user.MustChangePassword
        }

        access_token = create_access_token(
            identity=str(user.UserID),
            additional_claims=additional_claims,
            expires_delta=timedelta(minutes=10)
        )

        return {
            "message": "Password updated successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.UserID,
                "email": user.Email,
                "username": user.UserName,
                "role": user.Role,
                "must_change_password": user.MustChangePassword
            }
        }

    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        raise e



async def get_me_service(session: AsyncSession, user_id: int):
    try:
        query = select(User).where(User.UserID == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("User not found")
        
        return user
    except Exception as e:
        raise e


async def get_all_users_service(session: AsyncSession, role: Optional[str] = None):
    try:
        query = select(User).order_by(User.CreatedAt.desc())
        
        if role:
            query = query.where(User.Role == role)
            
        result = await session.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise e

async def update_user_service(session: AsyncSession, user_id: int, data: Any):
    try:
        query = select(User).where(User.UserID == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User not found")
        
        # Check for duplicates if email/username changes
        if data.email and data.email != user.Email:
            if await User.get_by_emails(session, data.email):
                raise ConflictException("Email already exists")
            user.Email = data.email
        
        if data.username and data.username != user.UserName:
            if await User.get_by_username(session, data.username):
                raise ConflictException("Username already exists")
            user.UserName = data.username

        if data.role is not None:
            user.Role = data.role
            
        if data.must_change_password is not None:
            user.MustChangePassword = data.must_change_password
            
        # Cập nhật UpdatedAt tại thời điểm hiện tại
        user.UpdatedAt = datetime.now()
            
        await user.save(session)
        return user
    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        raise e

async def delete_user_service(session: AsyncSession, user_id: int, current_user_id: int):
    try:
        # Ngăn chặn admin tự xóa chính mình
        if int(user_id) == int(current_user_id):
            raise ValidationException("Bạn không thể tự xóa tài khoản của chính mình")

        query = select(User).where(User.UserID == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User not found")
        
        await user.delete(session)
        return {"message": "User deleted successfully", "id": user_id}
    except AppException:
        raise
    except Exception as e:
        await session.rollback()
        raise e
