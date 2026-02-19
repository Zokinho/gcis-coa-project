# GCIS CoA Automation

AI-powered Certificate of Analysis (CoA) processing platform for cannabis consulting. Automates extraction of lab test data from PDF reports, identifies and redacts client information, and publishes results to a token-gated buyer marketplace.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite/PostgreSQL
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **AI**: Anthropic Claude Sonnet (Vision API for PDF extraction)
- **PDF Processing**: pikepdf, pdf2image, Pillow
- **Task Queue**: Celery + Redis
- **Integrations**: SharePoint (Graph API), Zoho CRM, Evernote, IMAP email
- **Auth**: JWT + API keys
- **Deployment**: Docker, Railway

## Features

**PDF Pipeline**
- Unlock password-protected PDFs
- AI extraction of potency, terpenes, microbials, pesticides, heavy metals
- Client info detection and redaction with coordinate-based regions
- Review and publish workflow

**Admin Dashboard**
- Upload and process CoA PDFs
- Review/toggle redactions before publishing
- Manage buyer access tokens (tier-based)
- Product catalog with tags and status tracking
- Multi-CoA product groups (multiple reports per strain/SKU)

**Buyer Marketplace**
- Token-gated access (no login required)
- Searchable catalog with detailed test data
- Curated share links for custom product selections
- PDF download of published CoAs

**Integrations**
- SharePoint file browsing and upload
- Zoho CRM data push
- Evernote import/export
- Email inbox polling for CoA attachments
- Sync tracking and audit trail

## Project Structure

```
backend/
  main.py               # FastAPI entry point
  services/             # PDF unlock, Vision API, redaction
  routers/              # API endpoints
  tasks/                # Celery async tasks
  tests/                # 52+ unit tests

frontend/
  src/
    app/
      admin/            # Dashboard, upload, review, tokens
      browse/[token]/   # Buyer catalog
      share/[token]/    # Curated share links
    components/         # ProductCard, SearchBar, FilterChips
```

## Getting Started

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload     # API on :8000

# Frontend
cd frontend && npm install
npm run dev                           # UI on :3000

# Test pipeline
python run_pipeline.py test_data/sample_coa.pdf
```

## Environment Variables

Copy `.env.example` to `.env` and configure:
- `ANTHROPIC_API_KEY` - Claude Vision API
- `DATABASE_URL` - SQLite or PostgreSQL
- `REDIS_URL` - Task queue (optional, falls back to threading)
- `SHAREPOINT_*`, `ZOHO_*`, `EVERNOTE_*` - Integration credentials

## License

Proprietary
