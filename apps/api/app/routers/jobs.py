import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models import CookieProfile, Job, JobStatus, User
from app.schemas import JobCreate, JobOut, ProbeOut, ProbeRequest
from app.security import decrypt_text, get_current_user
from app.ytdlp_service import aprobe_url

router = APIRouter(tags=["jobs"])
settings = get_settings()


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def _cookie_path(db: AsyncSession, user_id: UUID, cookie_profile_id: UUID | None) -> str | None:
    if not cookie_profile_id:
        return None
    result = await db.execute(
        select(CookieProfile).where(CookieProfile.id == cookie_profile_id, CookieProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Cookie profile not found")
    path = Path(settings.cookies_dir) / f"{profile.id}.txt"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(decrypt_text(profile.encrypted_blob), encoding="utf-8")
    return str(path)


def _is_bot_block(message: str) -> bool:
    lower = message.lower()
    return "sign in to confirm" in lower or "not a bot" in lower or "use --cookies" in lower


@router.post("/jobs/probe", response_model=ProbeOut)
async def probe(
    payload: ProbeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProbeOut:
    cookie_file = await _cookie_path(db, user.id, payload.cookie_profile_id)
    try:
        data = await aprobe_url(str(payload.url), cookie_file)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if _is_bot_block(msg):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "youtube_cookies_required",
                    "message": (
                        "YouTube blocked this datacenter IP. Export logged-in browser cookies "
                        "(Netscape cookies.txt) and upload them under Cookies, or place them at "
                        f"{settings.default_cookies_file} on the server."
                    ),
                    "raw": msg[:500],
                    "guides": [
                        "https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies",
                        "https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp",
                    ],
                },
            ) from exc
        raise HTTPException(status_code=400, detail=f"Probe failed: {msg}") from exc
    return ProbeOut(**data)


@router.post("/jobs", response_model=list[JobOut])
async def create_jobs(
    payload: JobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Job]:
    urls = [str(u) for u in (payload.playlist_urls or [])] or [str(payload.url)]
    if payload.cookie_profile_id:
        await _cookie_path(db, user.id, payload.cookie_profile_id)

    jobs: list[Job] = []
    for url in urls:
        job = Job(
            user_id=user.id,
            url=url,
            format_id=payload.format_id,
            audio_only=payload.audio_only,
            status=JobStatus.queued,
            cookie_profile_id=payload.cookie_profile_id,
        )
        db.add(job)
        jobs.append(job)
    await db.commit()
    for job in jobs:
        await db.refresh(job)

    pool = await create_pool(_redis_settings())
    try:
        for job in jobs:
            await pool.enqueue_job("process_download", str(job.id))
    finally:
        await pool.close()

    return jobs


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Job]:
    result = await db.execute(select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
async def cancel_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.completed, JobStatus.cancelled):
        return job
    job.status = JobStatus.cancelled
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    # signal cancel via redis
    import redis.asyncio as redis

    r = redis.from_url(settings.redis_url)
    await r.set(f"cancel:{job.id}", "1", ex=3600)
    await r.close()
    return job


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
async def retry_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.queued
    job.progress = 0
    job.error = None
    job.speed = None
    job.eta = None
    await db.commit()
    await db.refresh(job)
    pool = await create_pool(_redis_settings())
    try:
        await pool.enqueue_job("process_download", str(job.id))
    finally:
        await pool.close()
    return job


@router.get("/files/{job_id}")
async def download_file(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job or not job.filepath:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(job.filepath)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File expired or missing")
    return FileResponse(path, filename=job.filename or path.name)


@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

    from jose import JWTError, jwt

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError:
        await websocket.close(code=4401)
        return

    import redis.asyncio as redis

    r = redis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    channel = f"job:{job_id}"
    await pubsub.subscribe(channel)

    # Send current snapshot
    async with SessionLocal() as db:
        result = await db.execute(select(Job).where(Job.id == UUID(job_id), Job.user_id == UUID(user_id)))
        job = result.scalar_one_or_none()
        if not job:
            await websocket.close(code=4404)
            await pubsub.unsubscribe(channel)
            await r.close()
            return
        await websocket.send_json(
            {
                "id": str(job.id),
                "status": job.status.value,
                "progress": job.progress,
                "speed": job.speed,
                "eta": job.eta,
                "error": job.error,
                "title": job.title,
                "filename": job.filename,
            }
        )

    async def pump_pubsub():
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data if isinstance(data, str) else json.dumps(data))

    async def pump_client():
        while True:
            await websocket.receive_text()

    try:
        import asyncio

        done, pending = await asyncio.wait(
            [asyncio.create_task(pump_pubsub()), asyncio.create_task(pump_client())],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()
