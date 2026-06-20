from datetime import datetime

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = ""
    priority: str = "normal"


class TodoUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    completed: bool | None = None
    priority: str | None = None


class TodoOut(BaseModel):
    id: int
    owner_id: int
    title: str
    notes: str
    completed: bool
    priority: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
