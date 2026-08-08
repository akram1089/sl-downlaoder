from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import cookies, jobs
from app.routers.auth import ensure_admin, router as auth_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.download_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.cookies_dir).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await ensure_admin(db)
    yield


app = FastAPI(title="StreamLine API", version="1.0.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(cookies.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "streamline"}
