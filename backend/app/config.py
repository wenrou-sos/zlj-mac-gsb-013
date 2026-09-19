import os


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://runway:runway@db:5432/runway",
    )
    # Allow cross-origin requests from the dev frontend (vite :5173)
    cors_origins: list[str] = ["*"]


settings = Settings()
