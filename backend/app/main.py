import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .init_db import init_db
from .routers import closures, config, flights, rehearsal

app = FastAPI(
    title="机场跑道占用冲突预演平台",
    description=(
        "配置航班进离场时刻、滑行路线、跑道关闭区间与安全间隔，"
        "自动识别调度冲突并给出调整方案。"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights.router)
app.include_router(closures.router)
app.include_router(config.router)
app.include_router(rehearsal.router)


@app.on_event("startup")
def _startup() -> None:
    init_db(seed_if_empty=True)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
