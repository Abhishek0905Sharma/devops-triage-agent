from pydantic import BaseModel, EmailStr
from datetime import datetime

class Profile(BaseModel):
    bio: str
    website: str

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str
    profile: Profile | None = None

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    profile: Profile | None = None

class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool = True
    created_at: datetime
    profile: Profile | None = None
