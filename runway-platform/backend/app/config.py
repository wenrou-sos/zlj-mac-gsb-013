import os


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./runway.db",
    )
    cors_origins: list[str] = ["*"]


settings = Settings()
