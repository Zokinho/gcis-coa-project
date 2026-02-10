export type JobStatus = "queued" | "processing" | "review" | "published" | "flagged" | "error";
export type ProductStatus = "draft" | "review" | "published" | "archived";
export type Confidence = "high" | "medium" | "low";

export interface Job {
  id: string;
  filename: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  page_count: number;
  product_id: string | null;
}

export interface RedactionRegion {
  id: string;
  page: number;
  x_pct: number;
  y_pct: number;
  w_pct: number;
  h_pct: number;
  reason: string;
  confidence: Confidence;
  approved: boolean;
}

export interface Product {
  id: string;
  name: string;
  strain_type: string | null;
  lot_number: string;
  producer: string | null;
  lab: string;
  test_date: string | null;
  report_number: string | null;
  tier: string;
  status: ProductStatus;
  available: boolean;
  tags: string[];
  client_name: string | null;
  created_at: string;
}

export interface ProductTestData {
  id: string;
  test_type: string;
  data: Record<string, unknown>;
  lab: string;
  test_date: string | null;
  method: string | null;
  overall_result: string | null;
}

export interface ProductDetail extends Product {
  test_data: ProductTestData[];
}

export interface AccessToken {
  id: string;
  token: string;
  label: string;
  tiers: string[];
  active: boolean;
  created_at: string;
  last_used: string | null;
  use_count: number;
}

// ── SharePoint ──────────────────────────────────────────────────

export interface SharePointSite { id: string; name: string; web_url: string }
export interface SharePointDrive { id: string; name: string }
export interface SharePointFolder { id: string; name: string }
export interface SharePointUploadResult { id: string; name: string; web_url: string }

// ── Zoho CRM ───────────────────────────────────────────────────

export interface ZohoProductPreview {
  fields: Record<string, string | number | null>;
  pdf_filename: string;
}
export interface ZohoPushResult {
  record_id: string;
  record_url: string;
}

export interface RedactionUpdate {
  approved?: boolean;
  x_pct?: number;
  y_pct?: number;
  w_pct?: number;
  h_pct?: number;
}

// ── Email Ingestion ─────────────────────────────────────────────

export type EmailIngestionStatus = "pending" | "processing" | "review" | "completed" | "error";
export type AttachmentType = "coa_pdf" | "coa_photo" | "product_photo";

export interface EmailAttachment {
  id: string;
  original_filename: string;
  stored_filename: string;
  attachment_type: AttachmentType;
  file_size: number;
  job_id: string | null;
}

export interface EmailIngestion {
  id: string;
  message_id: string;
  subject: string;
  sender: string;
  body_text: string | null;
  received_at: string | null;
  status: EmailIngestionStatus;
  suggested_client: string | null;
  confirmed_client: string | null;
  error_message: string | null;
  created_at: string;
  attachments: EmailAttachment[];
}

// ── Evernote ────────────────────────────────────────────────────

export interface EvernotePreview {
  note_title: string;
  is_new_note: boolean;
  content_html: string;
}

export interface EvernotePushResult {
  note_guid: string;
  note_title: string;
  note_url: string;
}

// ── Sync Tracking ──────────────────────────────────────────────

export type SyncTarget = "evernote" | "sharepoint" | "zoho";

export interface SyncLog {
  id: string;
  product_id: string;
  target: SyncTarget;
  external_id: string;
  external_url: string;
  extra: Record<string, unknown>;
  synced_at: string;
}

export interface ProductPhoto {
  id: string;
  product_id: string;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  file_size: number;
  source: string;
  created_at: string;
}

// ── Evernote Import ────────────────────────────────────────────

export type EvernoteImportStatus = "pending" | "processing" | "completed" | "error";

export interface EvernoteNoteListItem {
  guid: string;
  title: string;
  updated: string | null;
  resource_count: number;
  already_imported: boolean;
}

export interface EvernoteNoteResource {
  guid: string;
  filename: string;
  mime: string;
  size: number;
  is_pdf: boolean;
  is_image: boolean;
}

export interface EvernoteNoteDetail {
  guid: string;
  title: string;
  client_name: string;
  resources: EvernoteNoteResource[];
  pdf_count: number;
  photo_count: number;
}

export interface EvernoteImportRecord {
  id: string;
  note_guid: string;
  note_title: string;
  client_name: string;
  status: EvernoteImportStatus;
  pdfs_found: number;
  photos_found: number;
  pdfs_imported: number;
  photos_imported: number;
  error_message: string | null;
  created_at: string;
}

// ── Curated Shares ─────────────────────────────────────────────

export interface CuratedShare {
  id: string;
  token: string;
  label: string;
  product_ids: string[];
  active: boolean;
  expires_at: string | null;
  created_at: string;
  last_used: string | null;
  use_count: number;
}

// ── Client Records ──────────────────────────────────────────────

export interface ClientSummary {
  client_name: string;
  product_count: number;
  latest_test_date: string | null;
  tiers: string[];
}

export interface ClientProduct {
  id: string;
  name: string;
  strain_type: string | null;
  lot_number: string;
  lab: string;
  test_date: string | null;
  tier: string;
  status: ProductStatus;
  pdf_filename: string | null;
  pdf_page_count: number;
  pdf_file_size: number;
  job_id: string | null;
  syncs: SyncLog[];
  photos: ProductPhoto[];
}

export interface PdfInfo {
  filename: string;
  file_size: number;
  page_count: number;
}

export interface DashboardStats {
  total_jobs: number;
  queued: number;
  processing: number;
  review: number;
  published: number;
  flagged: number;
  error: number;
  total_products: number;
  products_published: number;
  total_tokens: number;
}
