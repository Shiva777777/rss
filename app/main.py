from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
import os
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.routers import auth, users, attendance, admin
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="RSS Attendance & User Management System",
    description="A production-ready attendance tracking system with JWT auth, admin panel, and monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics ──────────────────────────────────────────────────────
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    # Always expose /metrics so Prometheus can scrape without extra env toggles.
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    inprogress_name="rss_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app).expose(app, endpoint="/metrics", tags=["monitoring"])

# ── API Routers ─────────────────────────────────────────────────────────────
app.include_router(auth.router,       prefix="/api/auth",       tags=["Authentication"])
app.include_router(users.router,      prefix="/api/users",      tags=["Users"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(admin.router,      prefix="/api/admin",      tags=["Admin"])

# ── Static Files (Frontend) ─────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("app/static/index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    file_path = f"app/static/{full_path}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse("app/static/index.html")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "RSS Attendance System"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
