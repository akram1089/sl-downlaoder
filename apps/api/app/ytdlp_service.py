from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.config import get_settings

QUALITY_PRESETS: list[dict[str, str]] = [
    {
        "id": "best",
        "label": "Best available",
        "format": "bv*+ba/b",
        "note": "Highest video + audio merge",
    },
    {
        "id": "2160",
        "label": "4K · 2160p",
        "format": "bv*[height<=2160]+ba/b[height<=2160]/b",
        "note": "Ultra HD when offered",
    },
    {
        "id": "1440",
        "label": "1440p",
        "format": "bv*[height<=1440]+ba/b[height<=1440]/b",
        "note": "QHD",
    },
    {
        "id": "1080",
        "label": "1080p",
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "note": "Full HD",
    },
    {
        "id": "720",
        "label": "720p",
        "format": "bv*[height<=720]+ba/b[height<=720]/b",
        "note": "HD",
    },
    {
        "id": "480",
        "label": "480p",
        "format": "bv*[height<=480]+ba/b[height<=480]/b",
        "note": "SD",
    },
]


def _is_storyboard(f: dict[str, Any]) -> bool:
    fmt_id = str(f.get("format_id") or "").lower()
    ext = str(f.get("ext") or "").lower()
    note = str(f.get("format_note") or "").lower()
    protocol = str(f.get("protocol") or "").lower()
    if ext == "mhtml" or protocol == "mhtml":
        return True
    if fmt_id.startswith("sb") or "storyboard" in note:
        return True
    return False


def _sanitize_formats(raw_formats: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    formats: list[dict[str, Any]] = []
    for f in raw_formats or []:
        if _is_storyboard(f):
            continue
        format_id = str(f.get("format_id") or "")
        if not format_id:
            continue
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        is_audio = (vcodec in (None, "none")) and acodec not in (None, "none")
        # Skip pure images / unknown junk without codecs
        if not is_audio and vcodec in (None, "none") and acodec in (None, "none"):
            continue
        height = f.get("height")
        width = f.get("width")
        resolution = f.get("resolution")
        if not resolution and height:
            resolution = f"{height}p"
        elif resolution and "x" in str(resolution) and height:
            resolution = f"{height}p"
        formats.append(
            {
                "format_id": format_id,
                "ext": f.get("ext"),
                "resolution": resolution,
                "height": height,
                "fps": f.get("fps"),
                "vcodec": None if vcodec == "none" else vcodec,
                "acodec": None if acodec == "none" else acodec,
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "note": f.get("format_note"),
                "is_audio": bool(is_audio),
            }
        )

    by_id: dict[str, dict[str, Any]] = {}
    for item in formats:
        prev = by_id.get(item["format_id"])
        if not prev or (item.get("filesize") and not prev.get("filesize")):
            by_id[item["format_id"]] = item

    result = list(by_id.values())

    def sort_key(item: dict[str, Any]) -> tuple:
        height = item.get("height") or 0
        try:
            height = int(height)
        except (TypeError, ValueError):
            height = 0
        return (0 if item.get("is_audio") else 1, height, item.get("filesize") or 0)

    result.sort(key=sort_key, reverse=True)
    return result


def resolve_cookie_file(explicit: str | None = None) -> str | None:
    """Prefer explicit profile path, else default shared youtube.txt if present."""
    if explicit and Path(explicit).exists():
        return explicit
    settings = get_settings()
    default = Path(settings.default_cookies_file)
    if default.exists() and default.stat().st_size > 0:
        return str(default)
    return explicit if explicit else None


def base_ydl_opts(
    *,
    cookie_file: str | None = None,
    clients: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if clients is None:
        clients = [c.strip() for c in settings.youtube_player_clients.split(",") if c.strip()]
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_args": {
            "youtube": {
                # Prefer TV/web clients that return adaptive (DASH) formats + honor cookies.
                "player_client": clients,
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }
    resolved = resolve_cookie_file(cookie_file)
    if resolved:
        opts["cookiefile"] = resolved
    if extra:
        opts.update(extra)
    return opts


def _max_video_height(formats: list[dict[str, Any]]) -> int:
    heights: list[int] = []
    for f in formats:
        if f.get("is_audio"):
            continue
        h = f.get("height")
        if h:
            try:
                heights.append(int(h))
            except (TypeError, ValueError):
                pass
    return max(heights) if heights else 0


def probe_url(url: str, cookie_file: str | None = None) -> dict[str, Any]:
    import yt_dlp

    settings = get_settings()
    configured = [c.strip() for c in settings.youtube_player_clients.split(",") if c.strip()]
    # Try richer client sets until we get adaptive HD formats (YouTube often hides them).
    client_attempts = [
        configured,
        ["tv", "tv_embedded", "web", "mweb"],
        ["android", "web", "mweb"],
        ["web"],
    ]
    # de-dupe while preserving order
    seen: set[tuple[str, ...]] = set()
    attempts: list[list[str]] = []
    for attempt in client_attempts:
        key = tuple(attempt)
        if key and key not in seen:
            seen.add(key)
            attempts.append(attempt)

    best_info: dict[str, Any] | None = None
    best_formats: list[dict[str, Any]] = []
    used_cookie = False
    last_opts: dict[str, Any] = {}

    for clients in attempts:
        opts = base_ydl_opts(
            cookie_file=cookie_file,
            clients=clients,
            extra={
                "skip_download": True,
                "extract_flat": "in_playlist",
                "noplaylist": False,
            },
        )
        last_opts = opts
        used_cookie = bool(opts.get("cookiefile"))
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            continue
        best_info = info
        if info.get("_type") == "playlist" or info.get("entries"):
            break
        formats = _sanitize_formats(info.get("formats"))
        if _max_video_height(formats) > _max_video_height(best_formats):
            best_formats = formats
        if _max_video_height(formats) >= 1080:
            best_formats = formats
            break

    if not best_info:
        raise ValueError("No metadata returned")

    entries = []
    is_playlist = bool(best_info.get("_type") == "playlist" or best_info.get("entries"))
    if is_playlist:
        for entry in best_info.get("entries") or []:
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
            "id": best_info.get("id"),
            "title": best_info.get("title"),
            "thumbnail": best_info.get("thumbnail"),
            "duration": best_info.get("duration"),
            "extractor": best_info.get("extractor"),
            "webpage_url": best_info.get("webpage_url") or url,
            "is_playlist": True,
            "formats": [],
            "presets": QUALITY_PRESETS,
            "entries": entries,
            "used_cookies": used_cookie,
            "max_height": 0,
        }

    if not best_formats:
        best_formats = _sanitize_formats(best_info.get("formats"))

    return {
        "id": best_info.get("id"),
        "title": best_info.get("title"),
        "thumbnail": best_info.get("thumbnail"),
        "duration": best_info.get("duration"),
        "extractor": best_info.get("extractor"),
        "webpage_url": best_info.get("webpage_url") or url,
        "is_playlist": False,
        "formats": best_formats,
        "presets": QUALITY_PRESETS,
        "entries": [],
        "used_cookies": bool(last_opts.get("cookiefile")),
        "max_height": _max_video_height(best_formats),
    }


async def aprobe_url(url: str, cookie_file: str | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(probe_url, url, cookie_file)


def _is_format_expression(value: str) -> bool:
    return any(ch in value for ch in "+*/[]")


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

    opts = base_ydl_opts(
        cookie_file=cookie_file,
        clients=["tv", "tv_embedded", "web", "mweb", "android"],
        extra={
            "outtmpl": outtmpl,
            "progress_hooks": [hook],
            "noprogress": True,
            "concurrent_fragment_downloads": 4,
            "merge_output_format": "mp4",
        },
    )

    if audio_only:
        opts["format"] = format_id if (format_id and _is_format_expression(format_id)) else (format_id or "bestaudio/best")
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    elif format_id and _is_format_expression(format_id):
        opts["format"] = format_id
    elif format_id:
        # YouTube video-only itags need an audio merge for true HD/4K.
        opts["format"] = f"{format_id}+bestaudio/best/{format_id}/best"
    else:
        opts["format"] = "bv*+ba/b"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

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
