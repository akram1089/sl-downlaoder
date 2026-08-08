from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-secret-change-me"
    cookie_encryption_key: str = "dev-cookie-key-change-me-32b!!"
    database_url: str = "postgresql+asyncpg://streamline:streamline@localhost:5432/streamline"
    redis_url: str = "redis://localhost:6379/0"
    public_url: str = "http://localhost:3000"
    domain: str = "localhost"
    admin_email: str = "admin@spikeiq.cloud"
    admin_password: str = "admin123456"
    max_concurrent_downloads: int = 2
    retention_hours: int = 72
    download_dir: str = "/data/downloads"
    cookies_dir: str = "/data/cookies"
    # Shared YouTube cookies (Netscape cookies.txt). Used when user does not pick a profile.
    default_cookies_file: str = "/data/cookies/youtube.txt"
    # Clients that honor browser cookies (avoid ios — it ignores cookie files).
    youtube_player_clients: str = "tv,tv_embedded,web,mweb,android"
    access_token_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000,https://download.spikeiq.cloud"


@lru_cache
def get_settings() -> Settings:
    return Settings()
