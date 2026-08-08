import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FormatOut(BaseModel):
    format_id: str
    ext: str | None = None
    resolution: str | None = None
    fps: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    filesize: int | None = None
    note: str | None = None
    is_audio: bool = False


class PlaylistEntry(BaseModel):
    id: str | None = None
    title: str | None = None
    url: str | None = None
    duration: float | None = None
    thumbnail: str | None = None


class ProbeOut(BaseModel):
    id: str | None = None
    title: str | None = None
    thumbnail: str | None = None
    duration: float | None = None
    extractor: str | None = None
    webpage_url: str | None = None
    is_playlist: bool = False
    formats: list[FormatOut] = []
    entries: list[PlaylistEntry] = []
    used_cookies: bool = False


class ProbeRequest(BaseModel):
    url: HttpUrl
    cookie_profile_id: uuid.UUID | None = None


class JobCreate(BaseModel):
    url: HttpUrl
    format_id: str | None = None
    audio_only: bool = False
    cookie_profile_id: uuid.UUID | None = None
    playlist_urls: list[HttpUrl] | None = None


class JobOut(BaseModel):
    id: uuid.UUID
    url: str
    title: str | None
    thumbnail: str | None
    extractor: str | None
    format_id: str | None
    audio_only: bool
    status: str
    progress: float
    speed: str | None
    eta: str | None
    error: str | None
    filename: str | None
    filesize: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CookieProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CookieProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CookieStatusOut(BaseModel):
    has_default: bool
    default_path: str
    profiles: list[CookieProfileOut] = []
