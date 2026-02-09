# GCIS CoA Automation & Product Catalog

## Project Overview

Build an automated Certificate of Analysis (CoA) processing system for GCIS, a cannabis consulting firm. The system:

1. **Accepts CoA PDFs** (uploaded manually or eventually via email)
2. **Unlocks password-protected PDFs** (owner passwords only — flag user-password PDFs)
3. **Uses Claude Vision API** to scan each page and simultaneously:
   - **Extract** all product data (potency, terpenes, microbial, pesticides, heavy metals, etc.)
   - **Identify** client information that must be redacted
4. **Presents results** to GCIS staff for review (approve/reject individual redactions)
5. **Publishes** clean, redacted CoAs + structured product data to a searchable buyer marketplace
6. **Controls buyer access** via token-based URLs (no login) mapped to tiers (EU-GMP, GACP Small, GACP Medium/Large)

## Architecture

```
[Upload CoA PDF]
       ↓
[PDF Unlock] — pikepdf strips owner passwords
       ↓
[Convert to Images] — pdf2image, one image per page
       ↓
[Claude Vision API] — Single call per page:
  → Extracts product data (THC, CBD, terpenes, test results...)
  → Identifies client info regions to redact
       ↓
[Merge Pages] — Combine extracted data from all pages into one product record
       ↓
[Review Queue] — GCIS staff reviews:
  → Toggle individual redactions on/off
  → Re-scan if needed
  → Manual edit flag for edge cases
       ↓
[Publish] — Apply approved redactions → save clean PDF + product record
       ↓
[Buyer Marketplace] — Token-based access, searchable catalog
```

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Celery, Redis
- **PDF Processing:** pikepdf, pdf2image (requires poppler), Pillow
- **AI/Vision:** Anthropic Claude API (Sonnet 4.5) 
- **Database:** SQLite (start simple, migrate to PostgreSQL later)
- **Frontend:** Next.js or React (for admin dashboard + buyer marketplace)
- **Storage:** SharePoint (existing) via Microsoft Graph API, local filesystem for processing
- **Hosting:** Railway.app (Pro plan, ~$20/month)

## Folder Structure

```
gcis-coa/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings, env vars, paths
│   ├── models.py                # SQLAlchemy/Pydantic models
│   ├── database.py              # DB connection + session
│   ├── routers/
│   │   ├── upload.py            # POST /api/upload — accept CoA PDFs
│   │   ├── jobs.py              # GET/POST /api/jobs — job status, actions
│   │   ├── products.py          # GET /api/products — catalog queries
│   │   ├── access.py            # GET/POST /api/access — manage buyer tokens
│   │   └── admin.py             # Admin endpoints
│   ├── services/
│   │   ├── pdf_unlock.py        # Password removal with pikepdf
│   │   ├── pdf_to_images.py     # Convert PDF pages to images
│   │   ├── ai_extractor.py      # Claude Vision API — extract + redact
│   │   ├── redactor.py          # Apply white-box redactions to PDF
│   │   ├── merger.py            # Merge multi-page extractions
│   │   └── publisher.py         # Publish clean PDF + product record
│   ├── tasks/
│   │   └── process_coa.py       # Celery task — full pipeline
│   ├── storage/
│   │   ├── uploads/             # Raw uploaded PDFs
│   │   ├── working/             # Unlocked + page images
│   │   ├── redacted/            # Preview redacted PDFs (for review)
│   │   └── published/           # Final clean PDFs (served to buyers)
│   └── tests/
│       ├── test_pdf_unlock.py
│       ├── test_extractor.py
│       └── test_redactor.py
├── frontend/                    # Next.js app (Phase 2)
│   ├── app/
│   │   ├── admin/               # GCIS internal dashboard
│   │   │   ├── upload/          # Upload + processing queue
│   │   │   ├── review/          # Review redactions
│   │   │   └── access/          # Manage buyer access tokens
│   │   └── browse/
│   │       └── [token]/         # Buyer marketplace (token-based access)
│   └── components/
│       ├── ProductCard.tsx
│       ├── ProductDetail.tsx
│       ├── TerpeneBar.tsx
│       ├── SearchBar.tsx
│       └── FilterChips.tsx
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Local dev (API + Redis + Worker)
├── Dockerfile                   # Production container
├── railway.toml                 # Railway deployment config
└── README.md
```

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
DATABASE_URL=sqlite:///./gcis_coa.db
REDIS_URL=redis://localhost:6379/0
STORAGE_PATH=./backend/storage
ALLOWED_ORIGINS=http://localhost:3000,https://catalog.gciscan.com

# Optional — for SharePoint integration (Phase 3)
MS_TENANT_ID=
MS_CLIENT_ID=
MS_CLIENT_SECRET=
SHAREPOINT_SITE_ID=
```

## Data Models

### CoAJob
```
id: UUID
filename: str
status: enum (queued, processing, review, published, flagged, error)
created_at: datetime
updated_at: datetime
error_message: str | None
page_count: int
product_id: UUID | None (link to extracted product)
```

### Product
```
id: UUID
name: str
strain_type: str | None
lot_number: str
producer: str | None (seller codename for GCIS internal)
lab: str
test_date: date | None
report_number: str | None
tier: str (eu-gmp, gacp-small, gacp-medium-large)
status: enum (draft, review, published, archived)
available: bool
tags: list[str]
search_text: str (flat text for full-text search)
created_at: datetime
```

### ProductTestData
```
id: UUID
product_id: UUID (FK)
test_type: str (potency, terpene, microbial, pesticide, heavy_metal, residual_solvent, mycotoxin)
data: JSON (flexible — stores whatever the lab tested)
lab: str
test_date: date
method: str | None
overall_result: str | None (PASS/FAIL for applicable tests)
```

### RedactionRegion
```
id: UUID
job_id: UUID (FK)
page: int
x_pct: float
y_pct: float
w_pct: float
h_pct: float
reason: str
confidence: str (high, medium, low)
approved: bool (default True — GCIS can toggle off)
```

### AccessToken
```
id: UUID
token: str (unique, URL-safe, unguessable)
label: str (e.g., "Buyer group A - GACP Small")
tiers: list[str]
active: bool
created_at: datetime
last_used: datetime | None
use_count: int
```

## AI Extraction Prompt

The Claude Vision prompt sends one image per page and asks for TWO things in a single response:

### Task 1: Extract product data
- Product name, lot, producer, lab, dates
- Cannabinoid profile (THC, THCA, CBD, CBG, CBN, etc.)
- Terpene profile (all individual terpenes + total)
- Microbial results (yeast/mold, E. coli, Salmonella, etc.)
- Pesticide panel (list all tested, note any detected)
- Heavy metals (Pb, As, Cd, Hg — values and limits)
- Residual solvents
- Mycotoxins / Aflatoxins
- Moisture / Water activity
- Compliance status

### Task 2: Identify client info to redact
- Client company name, address, contact info
- Client account/license/PO numbers
- "Ship To" / "Bill To" / "Submitted By" blocks
- Return bounding boxes as percentage coordinates

Response format: JSON with `extraction` and `redaction` keys.

## Real CoA Example (Eurofins — Blue Pavé 7)

We have a real 6-page Eurofins CoA (file: BP_T-003-23_COA__Eurofins_.pdf) for testing.

**What to redact (all on Page 1):**
- Client name: "Culture des Sommets"
- Client address: "60 Rue Brissette, Saint-Mathieu-De-Beloeil, QC J3G 0G2, CA"
- Client Account Number: A01649090CNO
- Eurofins Quote Number: GOX2PH23017103

**What to extract:**
- Product: Blue Pavé 7
- Lot: T-003-23-BP7
- Lab: Eurofins Experchem Laboratories Inc. (Toronto)
- Report: ABI07230
- Test types: microbial, potency, terpenes, heavy metals, mycotoxins, pesticides (Health Canada full panel), residual solvents
- Total THC: 24.545%
- Top terpenes: d-Limonene (0.3838%), Linalool (0.2374%), beta-Myrcene (0.1103%)
- All pesticides: Not Detected (90+ analytes)
- Heavy metals: All below LOQ
- Residual solvents: Ethanol 170 ppm, others not detected
- Compliance: PASS

## Build Order (Phase 1 — start here)

1. **Set up project scaffolding** — FastAPI app, config, database models
2. **PDF unlock service** — pikepdf owner-password removal
3. **PDF to images service** — pdf2image conversion
4. **AI extractor service** — Claude Vision API integration with combined prompt
5. **Multi-page merger** — Combine extraction results across pages
6. **Redaction engine** — Apply white boxes to PDF pages
7. **Upload endpoint** — Accept PDF, create job, kick off processing
8. **Job status endpoint** — Poll/check processing status
9. **Review endpoints** — Toggle redactions, re-scan, approve, publish
10. **Test with real CoA** — Run the Eurofins Blue Pavé 7 through the full pipeline

## API Costs
- Model: claude-sonnet-4-5-20250929
- ~$0.10 per CoA (6 pages)
- 5-10 CoAs/week = $2-4/month
- $5 free credits = ~50 CoAs for testing

## Notes
- The sample CoA is a scanned document (images, not text-based PDF), which is why Vision API is ideal
- Owner passwords on PDFs are trivially removable; user passwords require flagging for manual handling
- Eurofins is one of the most common labs GCIS works with, but the system must handle varied formats
- Buyer marketplace uses token-based URLs (no login) — each token maps to one or more access tiers
- GCIS team keeps working in SharePoint as-is; the system reads from it via Microsoft Graph API
- Hosting target: Railway.app Pro ($20/month) + Anthropic API ($2-4/month)
