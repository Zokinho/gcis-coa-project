"""FastAPI application entry point for GCIS CoA Automation."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routers import access, admin, jobs, products, upload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="GCIS CoA Automation",
    description="Certificate of Analysis processing and product catalog API",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(products.router)
app.include_router(access.router)


@app.on_event("startup")
def on_startup():
    init_db()
    logging.getLogger(__name__).info("Database initialized")


@app.get("/health")
def health():
    return {"status": "ok"}
