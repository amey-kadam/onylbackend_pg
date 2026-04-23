from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.routes import auth, tenants, rooms, beds, payments, complaints, notices, dashboard, pgs
from app.routes import cash_payments, maintenance, staff, upload, password_reset
from app.routes import admin_features
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utils.limiter import limiter
from fastapi.responses import JSONResponse
from fastapi import Request
from app.utils.logger import logger

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="PG (Paying Guest) Management System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.opt(exception=exc).error(f"Unhandled error on {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# CORS - configure explicitly instead of wildcard with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], # Add production URLs here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(rooms.router)
app.include_router(beds.router)
app.include_router(payments.router)
app.include_router(complaints.router)
app.include_router(notices.router)
app.include_router(dashboard.router)
app.include_router(pgs.router)
app.include_router(cash_payments.router)
app.include_router(maintenance.router)
app.include_router(staff.router)
app.include_router(upload.router)
app.include_router(password_reset.router)
app.include_router(admin_features.router)

import os
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
def on_startup():
    """Initialize database tables on startup."""
    init_db()


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": "1.0.0"}


@app.get("/api/health", tags=["Health"])
def api_health():
    return {"status": "ok"}
