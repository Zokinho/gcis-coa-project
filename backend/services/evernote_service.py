"""Evernote integration — find/create/append client notes via NoteStore API."""

import logging
from html import escape as html_escape

from evernote.api.client import EvernoteClient
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import Note

from backend.config import settings
from backend.models import Product, ProductTestData

logger = logging.getLogger(__name__)

_note_store = None

# ── ENML helpers ─────────────────────────────────────────────────

ENML_HEADER = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
ENML_OPEN = "<en-note>"
ENML_CLOSE = "</en-note>"


def _get_note_store():
    """Get (and cache) the Evernote NoteStore client."""
    global _note_store
    if _note_store is not None:
        return _note_store

    if not settings.evernote_developer_token:
        raise RuntimeError("Evernote developer token not configured")

    client = EvernoteClient(
        token=settings.evernote_developer_token,
        sandbox=settings.evernote_sandbox,
    )

    if settings.evernote_is_business:
        _note_store = client.get_business_note_store()
    else:
        _note_store = client.get_note_store()

    return _note_store


def _reset_note_store():
    """Reset cached NoteStore (useful after errors)."""
    global _note_store
    _note_store = None


# ── Note lookup ──────────────────────────────────────────────────


def find_client_note(client_name: str) -> tuple[str | None, str | None]:
    """Find an existing note for this client. Returns (guid, title) or (None, None)."""
    note_store = _get_note_store()

    note_filter = NoteFilter()
    note_filter.words = f'intitle:"{client_name}"'
    if settings.evernote_notebook_guid:
        note_filter.notebookGuid = settings.evernote_notebook_guid

    spec = NotesMetadataResultSpec()
    spec.includeTitle = True

    results = note_store.findNotesMetadata(note_filter, 0, 5, spec)

    for note_meta in results.notes:
        if client_name.lower() in note_meta.title.lower():
            return note_meta.guid, note_meta.title

    return None, None


def get_note_content(guid: str) -> str:
    """Retrieve the ENML content of a note."""
    note_store = _get_note_store()
    note = note_store.getNote(guid, True, False, False, False)
    return note.content or ""


# ── ENML building ────────────────────────────────────────────────


def _format_value(val) -> str:
    """Format a value for display, escaping HTML."""
    if val is None:
        return "—"
    return html_escape(str(val))


def build_product_enml(product: Product, test_data: list[ProductTestData]) -> str:
    """Build an ENML fragment for a product (heading + info table + test summary)."""
    lines = []
    lines.append("<hr/>")
    lines.append(f"<h2>{_format_value(product.name)}</h2>")

    # Product info table
    lines.append('<table border="1" style="border-collapse:collapse; width:100%;">')
    info_rows = [
        ("Lot Number", product.lot_number),
        ("Lab", product.lab),
        ("Test Date", product.test_date),
        ("Strain Type", product.strain_type),
        ("Producer", product.producer),
        ("Report #", product.report_number),
    ]
    for label, value in info_rows:
        lines.append(
            f"<tr><td><b>{html_escape(label)}</b></td>"
            f"<td>{_format_value(value)}</td></tr>"
        )

    # Extract key test results
    for td in test_data:
        if td.test_type == "potency" and td.data:
            thc = td.data.get("thc_total") or td.data.get("THC_total") or td.data.get("thc")
            cbd = td.data.get("cbd_total") or td.data.get("CBD_total") or td.data.get("cbd")
            if thc is not None:
                lines.append(f"<tr><td><b>THC %</b></td><td>{_format_value(thc)}</td></tr>")
            if cbd is not None:
                lines.append(f"<tr><td><b>CBD %</b></td><td>{_format_value(cbd)}</td></tr>")

        elif td.test_type == "terpenes" and td.data:
            terpene_strs = []
            items = td.data.get("results", td.data)
            if isinstance(items, dict):
                for name, val in items.items():
                    if name != "results" and val:
                        terpene_strs.append(f"{html_escape(str(name))}: {_format_value(val)}")
            if terpene_strs:
                lines.append(
                    f"<tr><td><b>Terpenes</b></td>"
                    f"<td>{', '.join(terpene_strs[:10])}</td></tr>"
                )

    # Overall compliance
    for td in test_data:
        if td.overall_result:
            lines.append(
                f"<tr><td><b>{html_escape(td.test_type)} Result</b></td>"
                f"<td>{_format_value(td.overall_result)}</td></tr>"
            )

    lines.append("</table>")
    lines.append(f"<p><i>Added {_format_value(product.created_at)}</i></p>")

    return "\n".join(lines)


# ── Note operations ──────────────────────────────────────────────


def append_to_note(guid: str, enml_fragment: str) -> None:
    """Append an ENML fragment to an existing note."""
    note_store = _get_note_store()
    content = get_note_content(guid)

    # Insert fragment before closing </en-note> tag
    if ENML_CLOSE in content:
        content = content.replace(ENML_CLOSE, f"\n{enml_fragment}\n{ENML_CLOSE}")
    else:
        content += f"\n{enml_fragment}\n{ENML_CLOSE}"

    note = Note()
    note.guid = guid
    note.content = content
    note_store.updateNote(note)


def create_client_note(client_name: str, enml_fragment: str) -> tuple[str, str]:
    """Create a new note for a client. Returns (guid, title)."""
    note_store = _get_note_store()

    title = f"{client_name} — CoA Records"
    content = (
        f"{ENML_HEADER}\n{ENML_OPEN}\n"
        f"<h1>{html_escape(client_name)} — CoA Records</h1>\n"
        f"<p>Automated Certificate of Analysis records for {html_escape(client_name)}.</p>\n"
        f"{enml_fragment}\n"
        f"{ENML_CLOSE}"
    )

    note = Note()
    note.title = title
    note.content = content
    if settings.evernote_notebook_guid:
        note.notebookGuid = settings.evernote_notebook_guid

    created = note_store.createNote(note)
    return created.guid, title


# ── Public API ───────────────────────────────────────────────────


def preview_evernote_push(
    product: Product,
    test_data: list[ProductTestData],
    client_name: str,
) -> dict:
    """Preview what will be pushed to Evernote (without making changes)."""
    enml_fragment = build_product_enml(product, test_data)

    try:
        guid, title = find_client_note(client_name)
        is_new = guid is None
        note_title = title or f"{client_name} — CoA Records"
    except Exception:
        _reset_note_store()
        # If we can't connect, assume new note
        is_new = True
        note_title = f"{client_name} — CoA Records"

    # Convert ENML to simple HTML for preview
    content_html = enml_fragment.replace("<hr/>", "<hr>")

    return {
        "note_title": note_title,
        "is_new_note": is_new,
        "content_html": content_html,
    }


def push_to_evernote(
    product: Product,
    test_data: list[ProductTestData],
    client_name: str,
) -> dict:
    """Push product data to Evernote. Creates or appends to client note."""
    try:
        enml_fragment = build_product_enml(product, test_data)
        guid, title = find_client_note(client_name)

        if guid:
            append_to_note(guid, enml_fragment)
            note_title = title
        else:
            guid, note_title = create_client_note(client_name, enml_fragment)

        # Build note URL
        if settings.evernote_sandbox:
            base = "https://sandbox.evernote.com"
        else:
            base = "https://www.evernote.com"
        note_url = f"{base}/shard/s1/nl/{guid}"

        return {
            "note_guid": guid,
            "note_title": note_title,
            "note_url": note_url,
        }
    except Exception:
        _reset_note_store()
        raise
