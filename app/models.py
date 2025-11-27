from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Optional, List, Generic, TypeVar
from datetime import datetime, timezone, date
from enum import Enum

T = TypeVar("T")


class UserResponse(BaseModel):
    profile_picture: str | None = None
    email: str
    username: str
    name: str
    age: int
    nationality: str
    phone_number: str | None = None
    address: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    username: str
    password: str


class Chat(BaseModel):
    id: Optional[int] = None
    receiver: Optional[str]
    username: Optional[str]
    message: str | None = None
    delivered: bool = False
    pics: str | None = None
    time_of_chat: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)
    conversation_id: str | None = None


class UserRes(BaseModel):
    profile_picture: str | None = None
    email: str
    username: str
    name: str
    nationality: str
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    page: int
    limit: int
    total: int


class PaginatedMetadata(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginatedResponse


class StandardResponse(BaseModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None


class ReactionsSummary(BaseModel):
    like: int = 0
    love: int = 0
    angry: int = 0
    laugh: int = 0
    wow: int = 0
    sad: int = 0


class Commenter(BaseModel):
    id: Optional[int] = None
    blog_id: int
    content: str = Field(..., max_length=180)
    reacts_count: int | None = None
    reactions: ReactionsSummary = Field(default_factory=list)
    time_of_post: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Blogger(BaseModel):
    id: Optional[int] = None
    title: str = Field(..., max_length=50)
    content: str = Field(...)
    reaction: ReactionsSummary = Field(default_factory=list)
    comments_count: int | None = None
    reacts_count: int | None = None
    share_count: int | None = None
    comments: List[Commenter] = Field(default_factory=list)
    time_of_post: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Sharing(Enum):
    love = "love"
    angry = "angry"
    laugh = "laugh"
    wow = "wow"
    sad = "sad"


class Sharer(BaseModel):
    id: Optional[int] = None
    blog_id: int
    type: Optional[Sharing] = None
    content: Optional[str] = None
    blog: Blogger = Field(default_factory=list)
    time_of_share: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class Messenger(BaseModel):
    id: Optional[int] = None
    user_id: int | None = None
    receiver: str | None = None
    username: str | None = None
    message: str | None = None
    pics: str | None = None
    delivered: bool = False
    time_of_chat: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
