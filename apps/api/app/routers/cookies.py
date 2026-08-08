from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import CookieProfile, User
from app.schemas import CookieProfileOut, CookieStatusOut
from app.security import encrypt_text, get_current_user

router = APIRouter(prefix="/cookies", tags=["cookies"])
settings = get_settings()


def _looks_like_netscape(raw: str) -> bool:
    return "Netscape" in raw or "# HttpOnly_" in raw or "\t" in raw


@router.get("/status", response_model=CookieStatusOut)
async def cookie_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CookieStatusOut:
    result = await db.execute(
        select(CookieProfile).where(CookieProfile.user_id == user.id).order_by(CookieProfile.created_at.desc())
    )
    profiles = list(result.scalars().all())
    default = Path(settings.default_cookies_file)
    return CookieStatusOut(
        has_default=default.exists() and default.stat().st_size > 0,
        default_path=settings.default_cookies_file,
        profiles=profiles,
    )


@router.get("", response_model=list[CookieProfileOut])
async def list_cookies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CookieProfile]:
    result = await db.execute(
        select(CookieProfile).where(CookieProfile.user_id == user.id).order_by(CookieProfile.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=CookieProfileOut)
async def upload_cookies(
    name: str = Form(...),
    file: UploadFile = File(...),
    as_default: bool = Form(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CookieProfile:
    raw = (await file.read()).decode("utf-8", errors="ignore")
    if not _looks_like_netscape(raw):
        raise HTTPException(status_code=400, detail="File does not look like a Netscape cookies.txt")

    Path(settings.cookies_dir).mkdir(parents=True, exist_ok=True)

    if as_default:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can set the server default cookies")
        Path(settings.default_cookies_file).write_text(raw, encoding="utf-8")

    profile = CookieProfile(user_id=user.id, name=name.strip() or "default", encrypted_blob=encrypt_text(raw))
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    (Path(settings.cookies_dir) / f"{profile.id}.txt").write_text(raw, encoding="utf-8")
    return profile


@router.post("/default")
async def upload_default_cookies(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can set the server default cookies")
    raw = (await file.read()).decode("utf-8", errors="ignore")
    if not _looks_like_netscape(raw):
        raise HTTPException(status_code=400, detail="File does not look like a Netscape cookies.txt")
    Path(settings.cookies_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.default_cookies_file).write_text(raw, encoding="utf-8")
    return {"ok": True, "path": settings.default_cookies_file}


@router.delete("/{profile_id}")
async def delete_cookie(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(CookieProfile).where(CookieProfile.id == profile_id, CookieProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Cookie profile not found")
    path = Path(settings.cookies_dir) / f"{profile.id}.txt"
    if path.exists():
        path.unlink()
    await db.delete(profile)
    await db.commit()
    return {"ok": True}
