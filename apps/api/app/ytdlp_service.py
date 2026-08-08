from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.config import get_settings


def _sanitize_formats(raw_formats: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    formats: list[dict[str, Any]] = []
    for f in raw_formats or []:
        format_id = str(f.get("format_id") or "")
        if not format_id:
            continue
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        is_audio = (vcodec in (None, "none")) and acodec not in (None, "none")
        height = f.get("height")
        width = f.get("width")
        resolution = f.get("resolution")
        if not resolution and height:
            resolution = f"{width or '?'}x{height}" if width else f"{height}p"
        formats.append(
            {
                "format_id": format_id,
                "ext": f.get("ext"),
                "resolution": resolution,
                "fps": f.get("fps"),
                "vcodec": None if vcodec == "none" else vcodec,
                "acodec": None if acodec == "none" else acodec,
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "note": f.get("format_note"),
                "is_audio": bool(is_audio),
            }
        )
    # Prefer unique by format_id, prefer entries with resolution/filesize
    by_id: dict[str, dict[str, Any]] = {}
    for item in formats:
        prev = by_id.get(item["format_id"])
        if not prev or (item.get("filesize") and not prev.get("filesize")):
            by_id[item["format_id"]] = item
    return list(by_id.values())


def probe_url(url: str, cookie_file: str | None = None) -> dict[str, Any]:
    import yt_dlp

    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "noplaylist": False,
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("No metadata returned")

    entries = []
    is_playlist = bool(info.get("_type") == "playlist" or info.get("entries"))
    if is_playlist:
        for entry in info.get("entries") or []:
            if not entry:
                continue
            entries.append(
                {
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "url": entry.get("url")
                    or entry.get("webpage_url")
                    or (f"https://www.youtube.com/watch?v={entry['id']}" if entry.get("id") else None),
                    "duration": entry.get("duration"),
                    "thumbnail": entry.get("thumbnail"),
                }
            )
        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "extractor": info.get("extractor"),
            "webpage_url": info.get("webpage_url") or url,
            "is_playlist": True,
            "formats": [],
            "entries": entries,
        }

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "extractor": info.get("extractor"),
        "webpage_url": info.get("webpage_url") or url,
        "is_playlist": False,
        "formats": _sanitize_formats(info.get("formats")),
        "entries": [],
    }


async def aprobe_url(url: str, cookie_file: str | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(probe_url, url, cookie_file)


def download_job(
    *,
    job_id: str,
    url: str,
    format_id: str | None,
    audio_only: bool,
    cookie_file: str | None,
    progress_callback,
) -> dict[str, Any]:
    import yt_dlp

    settings = get_settings()
    out_dir = Path(settings.download_dir) / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(title).200B [%(id)s].%(ext)s")

    def hook(d: dict[str, Any]) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            pct = (downloaded / total * 100.0) if total else 0.0
            progress_callback(
                {
                    "status": "running",
                    "progress": round(min(pct, 99.0), 2),
                    "speed": d.get("_speed_str"),
                    "eta": d.get("_eta_str"),
                }
            )
        elif status == "finished":
            progress_callback({"status": "running", "progress": 99.0, "speed": None, "eta": "processing"})

    opts: dict[str, Any] = {
        "outtmpl": outtmpl,
        "progress_hooks": [hook],
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file

    if audio_only:
        opts["format"] = format_id or "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    elif format_id:
        # Prefer selected format + best audio merge when video-only
        opts["format"] = f"{format_id}+bestaudio/best/{format_id}/best"
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = "bv*+ba/b"
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # Resolve output file
    files = sorted(out_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file()]
    if not files:
        raise RuntimeError("Download finished but no file found")
    file_path = files[0]
    return {
        "title": (info or {}).get("title"),
        "thumbnail": (info or {}).get("thumbnail"),
        "extractor": (info or {}).get("extractor"),
        "filename": file_path.name,
        "filepath": str(file_path),
        "filesize": file_path.stat().st_size,
    }
