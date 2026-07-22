# GCIS CoA Project

Cannabis Certificate of Analysis automation system. Accepts CoA PDFs, extracts product data via Claude Vision API, identifies client info for redaction, publishes to buyer marketplace.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy/SQLite, Anthropic Claude Sonnet 4.5
- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS
- **PDF Processing**: pikepdf (unlock), pdf2image/poppler (images), Pillow (redaction)
- **Task Queue**: Celery + Redis (graceful thread fallback if Redis is down)
- **Integrations**: SharePoint (Graph API), Zoho CRM (REST v8), Evernote (NoteStore), IMAP email

## Quick Start

```bash
# Backend
source venv/bin/activate
uvicorn backend.main:app --reload          # API on :8000

# Frontend
cd frontend && npm run dev                  # UI on :3000

# Run pipeline directly
python run_pipeline.py test_data/BP_T-003-23_COA__Eurofins_.pdf

# Celery (optional, falls back to threads)
celery -A backend.celery_app:celery worker --loglevel=info
celery -A backend.celery_app:celery beat --loglevel=info

# Tests
pytest backend/tests/ -q                    # 54 tests
cd frontend && npx tsc --noEmit             # TypeScript check
```

## Environment (.env)

```
DATABASE_URL=sqlite:///./gcis.db
ANTHROPIC_API_KEY=...
ADMIN_USER=... ADMIN_PASSWORD=... ADMIN_SECRET_KEY=...

# Optional integrations
MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET          # SharePoint
ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_DATA_CENTER  # Zoho
EVERNOTE_DEVELOPER_TOKEN, EVERNOTE_IS_BUSINESS, EVERNOTE_NOTEBOOK_GUID    # Evernote
IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, EMAIL_INGESTION_ENABLED  # Email
EMAIL_SENDER_ALLOWLIST                                                   # Email security (comma-separated domains/addresses)
MAX_PDF_FILE_SIZE_MB, MAX_PDF_PAGE_COUNT, PDF_CONVERSION_TIMEOUT_SECONDS # PDF security limits
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL          # Notifications
NOTIFICATIONS_ENABLED, NOTIFICATION_ADMIN_EMAIL
```

## Architecture

### Pipeline Flow
1. Upload PDF → `CoAJob` created (queued)
2. `process_coa` task: unlock → images → AI extraction (per page) → merge → redact → publish
3. Publisher auto-matches to `ProductGroup` by normalized name + client
4. Admin reviews redactions, publishes → product visible to buyers

### Key Design Decisions
- Single Claude API call per page (extraction + redaction combined)
- Percentage-based redaction coordinates (resolution-independent)
- Images resized to max 1568px before sending to Vision API
- ProductGroup layer groups multiple CoAs under one strain/SKU identity

### Email Ingestion Security
- **Sender allowlist** — `EMAIL_SENDER_ALLOWLIST` restricts accepted senders by address or domain (empty = accept all)
- **File size cap** — `MAX_PDF_FILE_SIZE_MB` (default 50) rejects oversized attachments
- **PDF magic byte validation** — checks `%PDF-` header at email ingestion, upload endpoint, and pipeline unlock stages
- **Page count limit** — `MAX_PDF_PAGE_COUNT` (default 100) enforced in `pdf_unlock.py` and `pdf_to_images.py`
- **Conversion timeout** — `PDF_CONVERSION_TIMEOUT_SECONDS` (default 120) kills hung poppler subprocesses
- **Pipeline cleanup** — working directories are removed on pipeline failure to prevent disk accumulation
- **Upload endpoint** — validates file size (413) and magic bytes (400) before writing to disk

### Database Tables
- `coa_jobs` — processing pipeline state
- `products` — individual CoA records (linked to product_groups)
- `product_groups` — strain/SKU identity grouping multiple CoAs
- `product_test_data` — potency, terpenes, pesticides, etc.
- `redaction_regions` — client info coordinates for redaction
- `access_tokens` — buyer token-gated catalog access
- `curated_shares` — admin-created shareable product selections
- `email_ingestions`, `email_attachments` — IMAP inbox processing
- `evernote_imports` — Evernote note import tracking
- `product_photos` — product images from various sources
- `sync_logs` — external system sync tracking
- `notification_logs` — email notification audit trail

### Backend Structure
```
backend/
  config.py, database.py, models.py, auth.py, utils.py, celery_app.py
  services/
    pdf_unlock.py, pdf_to_images.py, ai_extractor.py, merger.py,
    redactor.py, publisher.py, sharepoint.py, zoho_crm.py,
    evernote_service.py, evernote_import.py, email_ingestion.py,
    email_notification.py
  routers/
    upload.py, jobs.py, admin.py, products.py, product_groups.py,
    access.py, sharepoint.py, zoho.py, email.py, evernote.py,
    evernote_import.py, shares.py
  tasks/
    process_coa.py, dispatch.py, email_tasks.py, evernote_tasks.py,
    notification_tasks.py
  migrations/
    migrate_product_groups.py
  tests/
    test_pdf_unlock.py, test_extractor.py, test_merger.py,
    test_notifications.py, test_product_groups.py
```

### Frontend Structure
```
frontend/src/
  lib/types.ts, api.ts
  components/
    ProductCard.tsx, SearchBar.tsx, FilterChips.tsx, TerpeneBar.tsx,
    CollapsiblePdf.tsx, SharePointPicker.tsx, ZohoPushModal.tsx,
    EvernotePushModal.tsx, EvernoteImportModal.tsx, SyncBadges.tsx,
    PhotoThumbnails.tsx
  app/
    admin/  — login, dashboard, upload, review, tokens, clients, shares, inbox
    browse/[token]/  — buyer catalog + product detail (product groups)
    share/[token]/   — curated share catalog + product detail
```

## API Routes (67 total)

### Public (buyer)
- `GET /api/products` — list published products
- `GET /api/products/{id}` — product detail with test data
- `GET /api/products/{id}/pdf` — download PDF
- `GET /api/product-groups` — list published product groups
- `GET /api/product-groups/{id}` — group detail with CoA history
- `GET /api/product-groups/{id}/coas/{pid}/pdf` — specific CoA PDF
- `GET /api/access/validate/{token}` — validate buyer token
- `GET /api/shares/validate/{token}` — validate share link
- `GET /api/shares/{token}/products` — shared products
- `GET /api/shares/{token}/products/{id}/pdf` — shared product PDF

### Admin (auth-protected)
- Auth: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
- Jobs: publish, rescan
- Products: update (tier, tags, group reassignment)
- Product Groups: list, detail, update, reassign product, set latest CoA
- Stats: `GET /api/admin/stats`
- Clients: list, client products
- Access Tokens: CRUD
- Shares: CRUD with product_group_ids support
- Upload: `POST /api/upload` with optional client_name
- SharePoint: sites, drives, folders, upload
- Zoho: preview, push
- Evernote: preview, push, notes list, note detail, import, imports list
- Email: ingestions list/detail, client confirm, reclassify, poll

## Migrations

Run after schema changes:
```bash
python -m backend.migrations.migrate_product_groups
```

## Test Data
- `test_data/BP_T-003-23_COA__Eurofins_.pdf` — 6-page Eurofins CoA for Blue Pave 7
- Expected: THC 24.545%, top terpenes d-Limonene/Linalool/beta-Myrcene, all pesticides ND
- Redact: client "Culture des Sommets", address, account #, quote #

## Phase History

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core pipeline (extract, redact, publish) | Complete |
| 2 | Admin + buyer frontend, auth, tokens | Complete |
| 3 | SharePoint, Zoho, email ingestion, Evernote, Celery, notifications | Complete |
| 4b | Sync tracking, Evernote import, curated shares, enhanced clients | Complete |
| 5 | Multi-CoA per product (ProductGroup architecture) | Complete |
| 6 | Email ingestion security hardening (sender allowlist, file/page limits, magic bytes, timeouts, cleanup) | Complete |
