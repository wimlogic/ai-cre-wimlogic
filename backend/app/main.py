from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve uploaded property images (and any other files under UPLOAD_ROOT) as
# static assets. This exposes exactly the same directory that
# FilesystemStorageProvider already writes to (settings.UPLOAD_ROOT) - no new
# path, no hardcoded location. Relative paths persisted to
# cre_property_images.cached_path (e.g. "properties/927/original/xyz.jpg")
# resolve to http://<host>/uploads/properties/927/original/xyz.jpg.
app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_ROOT),
    name="uploads",
)

app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_ROOT),
    name="uploads",
)


# Register models
from app.db.database import engine, Base
from app.db import base as db_base  # noqa: F401


@app.get("/")
def root():
    return {"status": "healthy", "service": settings.PROJECT_NAME, "version": "1.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
