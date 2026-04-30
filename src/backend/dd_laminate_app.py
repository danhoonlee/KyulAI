"""Standalone DD laminate prediction API.

Run with:
    uvicorn src.backend.dd_laminate_app:app --reload --port 8000

This app avoids the platform database startup path so the research UI can be
used immediately on a local machine.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.v1.dd_laminate import router as dd_laminate_router

app = FastAPI(
    title="KyulAI DD Laminate API",
    version="0.1.0",
    description="Local DD laminate Type prediction API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|[0-9.]+):3000",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dd_laminate_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
