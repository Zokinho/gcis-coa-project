# Instructions for Claude Code

## Context

You are building a CoA (Certificate of Analysis) automation system for GCIS, a cannabis consulting company. Read PROJECT_BRIEF.md first for the full architecture and requirements.

## Key Technical Decisions Already Made

1. **Single API call per page** — The Claude Vision prompt does BOTH extraction and redaction identification in one pass. Do not split into two calls.

2. **Percentage-based coordinates** for redaction regions (0-100 as % of page dimensions). This makes them resolution-independent.

3. **SQLite to start** — Keep it simple. The database can be migrated to PostgreSQL later on Railway.

4. **No login for buyers** — Access is controlled via token-based URLs. Each token maps to tier(s).

5. **SharePoint stays as-is** — GCIS team keeps their folder structure. The system bridges to it, not replaces it.

6. **Scanned PDFs** — Many CoAs are scanned documents (images, not text). Vision API handles these natively. Do NOT rely on text extraction — always use image-based analysis.

## Build Priority

Start with a working end-to-end pipeline that can:
1. Accept a PDF upload
2. Unlock it (if owner-password protected)
3. Convert pages to images
4. Send each page to Claude Vision API
5. Parse the structured JSON response
6. Merge data from all pages
7. Save the extracted product data
8. Identify redaction regions
9. Apply redactions and save clean PDF

Get this working with the test CoA (BP_T-003-23_COA__Eurofins_.pdf) before building the frontend.

## Important Implementation Notes

### AI Extractor (services/ai_extractor.py)
- Model: `claude-sonnet-4-5-20250929`
- Max tokens: 4000 per page (combined response is large)
- Images should be resized to max 1568px on longest side before sending
- The prompt is in PROJECT_BRIEF.md — implement the full combined extraction+redaction prompt
- Parse response as JSON, handle markdown code fences in response
- On parse failure, log the raw response and return empty extraction

### PDF Unlock (services/pdf_unlock.py)
- Use pikepdf to attempt opening with empty password
- If that works, save unlocked version — it had an owner password
- If it fails with PasswordError, flag as user-password-protected
- Return tuple: (success: bool, was_locked: bool, error: str | None)

### Redactor (services/redactor.py)
- Convert page to image (if not already)
- Draw white rectangles over approved redaction regions
- Convert coordinates from percentage to pixel values
- Add slight padding (2-3%) around each region for full coverage
- Reassemble pages into a new PDF
- Use Pillow for the actual drawing

### Merger (services/merger.py)
- CoAs span multiple pages with different test types per page
- Take first non-null value for simple fields (product name, lot, lab)
- Accumulate list fields (methodologies, accreditations)
- Each test type section (potency, terpenes, etc.) appears once — take it from whichever page has it
- Concatenate lab notes from multiple pages
- Generate tags automatically (high-thc, limonene-dominant, full-panel, etc.)

### Storage Layout
```
storage/
├── uploads/          # Original uploaded PDFs
├── working/          # Unlocked PDFs + page images  
│   └── {job_id}/
│       ├── unlocked.pdf
│       ├── page_0.png
│       ├── page_1.png
│       └── ...
├── redacted/         # Preview PDFs with redactions applied
│   └── {job_id}/
│       └── preview.pdf
└── published/        # Final clean PDFs served to buyers
    └── {product_id}/
        └── {product_name}_{lot}_{test_type}.pdf
```

## Testing

The real Eurofins CoA (Blue Pavé 7) should be your primary test case. Expected results are documented in PROJECT_BRIEF.md. Verify:
- All 4 client info items are identified for redaction (all on page 1)
- Product name "Blue Pavé 7" is correctly extracted  
- THC total of 24.545% is captured
- Top 3 terpenes match: d-Limonene, Linalool, beta-Myrcene
- All pesticides show as Not Detected
- Heavy metals all below LOQ
- Compliance status: PASS

## Don't Forget
- Always handle API errors gracefully (rate limits, timeouts, malformed responses)
- Log everything — processing steps, API responses, errors
- Set up proper CORS for the FastAPI app
- Use async where possible (FastAPI + httpx for API calls)
- The .env file has the API key — never commit it
