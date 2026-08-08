# StreamLine

Production multi-user media downloader for SpikeIQ — branded web UI around [akram1089/yt-dlp](https://github.com/akram1089/yt-dlp).

**Live domain:** https://download.spikeiq.cloud

## Stack

- Next.js UI (`apps/web`)
- FastAPI + ARQ workers (`apps/api`)
- Postgres, Redis, ffmpeg, Caddy TLS
- Engine: yt-dlp from `akram1089/yt-dlp`

## Features

- Multi-user auth
- URL probe + format picker
- Audio/video downloads
- Playlist batch queue
- Live progress (WebSocket)
- Cookie upload (Netscape `cookies.txt`)
- History + file retention cleanup

## Quick deploy (VPS)

```bash
git clone https://github.com/akram1089/sl-downlaoder.git /opt/streamline
cd /opt/streamline
cp .env.example .env
# edit secrets in .env
docker compose up -d --build
```

DNS for `download.spikeiq.cloud` must point to the VPS. Caddy issues TLS automatically.

## Local

```bash
cp .env.example .env
docker compose up -d --build
```

## Admin seed

Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`. The API creates that account on first boot.
