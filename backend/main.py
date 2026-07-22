"""FastAPI application entry point for GCIS CoA Automation."""

import fcntl
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.auth_apikey import verify_api_key
from backend.config import settings
from backend.database import init_db
from backend.routers import access, admin, email, evernote, evernote_import, jobs, product_groups, products, sharepoint, shares, upload, zoho

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

# API key middleware (optional — only enforced if COA_API_KEY is set)
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    await verify_api_key(request)
    return await call_next(request)

# Routers
app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(products.router)
app.include_router(access.router)
app.include_router(sharepoint.router)
app.include_router(zoho.router)
app.include_router(email.router)
app.include_router(evernote.router)
app.include_router(evernote_import.router)
app.include_router(shares.router)
app.include_router(product_groups.router)


@app.on_event("startup")
def on_startup():
    init_db()
    logging.getLogger(__name__).info("Database initialized")

    # Start email poller if enabled — use file lock so only one worker runs it
    try:
        lock_file = open("/tmp/gcis-coa-poller.lock", "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        # Keep reference to prevent GC closing the fd and releasing the lock
        app.state.poller_lock = lock_file

        from backend.services.email_ingestion import start_email_poller
        start_email_poller()
    except (IOError, OSError):
        logging.getLogger(__name__).info("Email poller already running in another worker, skipping")


@app.get("/health")
def health():
    return {"status": "ok"}
