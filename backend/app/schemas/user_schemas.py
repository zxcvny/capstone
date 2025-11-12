from pydantic import BaseModel, EmailStr
import uuid

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    name: str
    phone_number: str | None = None

class UserPublic(BaseModel):
    user_id: uuid.UUID
    username: str
    email: EmailStr
    name: str

    class Config:
        from_attributes = True