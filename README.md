# StreamLine

Production multi-user media downloader for SpikeIQ — branded web UI around [akram1089/yt-dlp](https://github.com/akram1089/yt-dlp).

**Live domain:** https://download.spikeiq.cloud  
**Sitemap:** https://download.spikeiq.cloud/sitemap.xml  
**Robots:** https://download.spikeiq.cloud/robots.txt

## Stack

- Next.js UI (`apps/web`)
- FastAPI + ARQ workers (`apps/api`)
- Postgres, Redis, ffmpeg
- Host nginx + Certbot (matches SpikeIQ VPS pattern)
- Engine: yt-dlp from `akram1089/yt-dlp`

## Features

- Multi-user auth
- URL probe + format picker
- Audio/video downloads
- Playlist batch queue
- Live progress (WebSocket)
- Cookie upload (Netscape `cookies.txt`)
- History + file retention cleanup

## Deploy on SpikeIQ VPS

```bash
git clone https://github.com/akram1089/sl-downlaoder.git /opt/streamline
cd /opt/streamline
cp .env.example .env
# edit secrets in .env

docker compose up -d --build

# nginx + TLS
cp deploy/nginx/download.spikeiq.cloud.conf /etc/nginx/sites-available/download.spikeiq.cloud
ln -sf /etc/nginx/sites-available/download.spikeiq.cloud /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d download.spikeiq.cloud --non-interactive --agree-tos -m admin@spikeiq.cloud --redirect
```

Published ports (localhost only): web `3030`, api `8030`.

## YouTube cookies (required on VPS)

YouTube often blocks datacenter IPs with “Sign in to confirm you’re not a bot”.

1. Export Netscape `cookies.txt` from a logged-in YouTube browser session  
   ([guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies))
2. In StreamLine, upload that file (or Admin → **Set server default**)
3. Inspect again

Engine package: `yt-dlp[default]` from [`akram1089/yt-dlp`](https://github.com/akram1089/yt-dlp) with Deno + `player_client=web,mweb,tv,android`.
