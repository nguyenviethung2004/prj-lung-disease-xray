from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr
class UserRegisterSchema(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6)

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserOutSchema(BaseModel):
    UserID: int
    UserName: str
    Email: EmailStr
    Role: str
    MustChangePassword: bool
    CreatedAt: datetime
    UpdatedAt: datetime

    class Config:
        from_attributes = True

class AdminUserCreateSchema(BaseModel):
    email: EmailStr
    username: str
    role: Literal["Superadmin", "Doctors"]

class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[Literal["Superadmin", "Doctors"]] = None
    must_change_password: Optional[bool] = None

class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)




