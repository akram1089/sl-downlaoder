from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import CookieProfile, User
from app.schemas import CookieProfileOut
from app.security import encrypt_text, get_current_user

router = APIRouter(prefix="/cookies", tags=["cookies"])
settings = get_settings()


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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CookieProfile:
    raw = (await file.read()).decode("utf-8", errors="ignore")
    if "Netscape" not in raw and "# HttpOnly_" not in raw and "\t" not in raw:
        raise HTTPException(status_code=400, detail="File does not look like a Netscape cookies.txt")
    profile = CookieProfile(user_id=user.id, name=name.strip() or "default", encrypted_blob=encrypt_text(raw))
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # Also write decrypted working copy for workers under cookies dir
    Path(settings.cookies_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.cookies_dir) / f"{profile.id}.txt").write_text(raw, encoding="utf-8")
    return profile


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
