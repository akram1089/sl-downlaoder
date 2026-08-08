from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
import json
import asyncio

import redis as sync_redis
import redis.asyncio as redis
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import CookieProfile, Job, JobStatus
from app.security import decrypt_text
from app.ytdlp_service import download_job

settings = get_settings()


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


def publish_progress_sync(job_id: str, payload: dict) -> None:
    r = sync_redis.from_url(settings.redis_url)
    try:
        r.publish(f"job:{job_id}", json.dumps(payload))
    finally:
        r.close()


async def publish_progress(job_id: str, payload: dict) -> None:
    r = redis.from_url(settings.redis_url)
    try:
        await r.publish(f"job:{job_id}", json.dumps(payload))
    finally:
        await r.aclose()


async def process_download(ctx, job_id: str) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
        job = result.scalar_one_or_none()
        if not job or job.status == JobStatus.cancelled:
            return

        cookie_file = None
        if job.cookie_profile_id:
            cp = await db.execute(select(CookieProfile).where(CookieProfile.id == job.cookie_profile_id))
            profile = cp.scalar_one_or_none()
            if profile:
                path = Path(settings.cookies_dir) / f"{profile.id}.txt"
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(decrypt_text(profile.encrypted_blob), encoding="utf-8")
                cookie_file = str(path)

        url = job.url
        format_id = job.format_id
        audio_only = job.audio_only
        job.status = JobStatus.running
        job.progress = 1
        await db.commit()

    await publish_progress(job_id, {"id": job_id, "status": "running", "progress": 1})

    def on_progress(update: dict) -> None:
        r = sync_redis.from_url(settings.redis_url)
        try:
            if r.get(f"cancel:{job_id}"):
                raise RuntimeError("cancelled")
        finally:
            r.close()

        progress = float(update.get("progress") or 0)
        publish_progress_sync(
            job_id,
            {
                "id": job_id,
                "status": "running",
                "progress": progress,
                "speed": update.get("speed"),
                "eta": update.get("eta"),
            },
        )

        # Best-effort DB update from sync hook via another connection would be heavy;
        # final state is written after download. Intermediate UI uses Redis pubsub.

    try:
        r = redis.from_url(settings.redis_url)
        cancelled = await r.get(f"cancel:{job_id}")
        await r.aclose()
        if cancelled:
            async with SessionLocal() as db:
                result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
                job = result.scalar_one_or_none()
                if job:
                    job.status = JobStatus.cancelled
                    await db.commit()
            return

        result_meta = await asyncio.to_thread(
            download_job,
            job_id=job_id,
            url=url,
            format_id=format_id,
            audio_only=audio_only,
            cookie_file=cookie_file,
            progress_callback=on_progress,
        )

        async with SessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
            job = result.scalar_one_or_none()
            if not job or job.status == JobStatus.cancelled:
                return
            job.status = JobStatus.completed
            job.progress = 100
            job.title = result_meta.get("title") or job.title
            job.thumbnail = result_meta.get("thumbnail") or job.thumbnail
            job.extractor = result_meta.get("extractor") or job.extractor
            job.filename = result_meta.get("filename")
            job.filepath = result_meta.get("filepath")
            job.filesize = result_meta.get("filesize")
            job.completed_at = datetime.now(timezone.utc)
            job.error = None
            await db.commit()

        await publish_progress(
            job_id,
            {
                "id": job_id,
                "status": "completed",
                "progress": 100,
                "filename": result_meta.get("filename"),
                "title": result_meta.get("title"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        status = JobStatus.cancelled if "cancelled" in msg.lower() else JobStatus.failed
        async with SessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
            job = result.scalar_one_or_none()
            if job and job.status != JobStatus.cancelled:
                job.status = status
                job.error = None if status == JobStatus.cancelled else msg[:2000]
                await db.commit()
                await publish_progress(
                    job_id,
                    {
                        "id": job_id,
                        "status": status.value,
                        "progress": job.progress,
                        "error": job.error,
                    },
                )


async def cleanup_expired(ctx) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.retention_hours)
    async with SessionLocal() as db:
        result = await db.execute(
            select(Job).where(
                Job.status == JobStatus.completed,
                Job.completed_at.is_not(None),
                Job.completed_at < cutoff,
            )
        )
        jobs = list(result.scalars().all())
        for job in jobs:
            if job.filepath:
                path = Path(job.filepath)
                if path.exists():
                    path.unlink(missing_ok=True)
                parent = path.parent
                if parent.exists() and parent != Path(settings.download_dir):
                    for remnant in parent.glob("*"):
                        remnant.unlink(missing_ok=True)
                    try:
                        parent.rmdir()
                    except OSError:
                        pass
            job.filepath = None
            job.filename = None
        await db.commit()


class WorkerSettings:
    functions = [process_download]
    cron_jobs = [cron(cleanup_expired, hour={0, 6, 12, 18}, minute=15)]
    redis_settings = _redis_settings()
    max_jobs = settings.max_concurrent_downloads
    job_timeout = 60 * 60 * 3
