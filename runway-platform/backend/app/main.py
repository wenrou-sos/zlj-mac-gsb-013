import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import closures, flights, runways, simulation
from .seed import seed_if_empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runway-platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if seed_if_empty(db):
            logger.info("已写入演示数据")
    finally:
        db.close()
    yield


app = FastAPI(
    title="机场跑道占用冲突预演平台",
    version="1.0.0",
    description="配置进离场时刻、滑行路线、跑道关闭区间与安全间隔，自动识别调度冲突并给出调整方案。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runways.router)
app.include_router(flights.router)
app.include_router(closures.router)
app.include_router(simulation.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


# 生产环境托管前端构建产物（Docker 镜像中位于 /app/static）
STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))
if STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/", include_in_schema=False)
    def index():
        from fastapi.responses import FileResponse

        return FileResponse(STATIC_DIR / "index.html")
