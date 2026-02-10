const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...opts?.headers },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────

export async function login(username: string, password: string) {
  return request<{ ok: boolean; username: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function logout() {
  return request<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
}

export async function getMe() {
  return request<{ username: string }>("/api/auth/me");
}

// ── Jobs ─────────────────────────────────────────────────────────

import type {
  Job,
  RedactionRegion,
  RedactionUpdate,
  Product,
  ProductDetail,
  AccessToken,
  DashboardStats,
  SharePointSite,
  SharePointDrive,
  SharePointFolder,
  SharePointUploadResult,
  ZohoProductPreview,
  ZohoPushResult,
  EmailIngestion,
  EmailIngestionStatus,
  EmailAttachment,
  AttachmentType,
  EvernotePreview,
  EvernotePushResult,
} from "./types";

export async function listJobs(): Promise<Job[]> {
  return request("/api/jobs");
}

export async function getJob(id: string): Promise<Job> {
  return request(`/api/jobs/${id}`);
}

export async function getRedactions(jobId: string): Promise<RedactionRegion[]> {
  return request(`/api/jobs/${jobId}/redactions`);
}

export async function toggleRedaction(jobId: string, redactionId: string, approved: boolean) {
  return request<RedactionRegion>(`/api/jobs/${jobId}/redactions/${redactionId}`, {
    method: "PATCH",
    body: JSON.stringify({ approved }),
  });
}

export async function updateRedaction(jobId: string, redactionId: string, data: RedactionUpdate) {
  return request<RedactionRegion>(`/api/jobs/${jobId}/redactions/${redactionId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function getPageImageUrl(jobId: string, page: number): string {
  return `${API}/api/jobs/${jobId}/pages/${page}`;
}

export async function getJobProduct(jobId: string): Promise<Product> {
  return request(`/api/jobs/${jobId}/product`);
}

export async function uploadCoA(file: File): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/api/upload`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

// ── Admin ────────────────────────────────────────────────────────

export async function publishJob(jobId: string): Promise<Job> {
  return request(`/api/admin/jobs/${jobId}/publish`, { method: "POST" });
}

export async function rescanJob(jobId: string): Promise<Job> {
  return request(`/api/admin/jobs/${jobId}/rescan`, { method: "POST" });
}

export async function updateProduct(productId: string, data: Partial<Product>): Promise<ProductDetail> {
  return request(`/api/admin/products/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getStats(): Promise<DashboardStats> {
  return request("/api/admin/stats");
}

// ── Products ─────────────────────────────────────────────────────

export async function listProducts(params?: {
  q?: string;
  tier?: string;
  tag?: string;
  page?: number;
  per_page?: number;
  token?: string;
}): Promise<Product[]> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  if (params?.tier) qs.set("tier", params.tier);
  if (params?.tag) qs.set("tag", params.tag);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  if (params?.token) qs.set("token", params.token);
  return request(`/api/products?${qs.toString()}`);
}

export async function getProduct(id: string, token?: string): Promise<ProductDetail> {
  const qs = token ? `?token=${token}` : "";
  return request(`/api/products/${id}${qs}`);
}

export function getProductPdfUrl(id: string, token?: string): string {
  const qs = token ? `?token=${token}` : "";
  return `${API}/api/products/${id}/pdf${qs}`;
}

// ── Access Tokens ────────────────────────────────────────────────

export async function createAccessToken(label: string, tiers: string[]): Promise<AccessToken> {
  return request("/api/access/tokens", {
    method: "POST",
    body: JSON.stringify({ label, tiers }),
  });
}

export async function listAccessTokens(): Promise<AccessToken[]> {
  return request("/api/access/tokens");
}

export async function updateAccessToken(id: string, data: Partial<AccessToken>): Promise<AccessToken> {
  return request(`/api/access/tokens/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAccessToken(id: string) {
  return request(`/api/access/tokens/${id}`, { method: "DELETE" });
}

export async function validateToken(token: string) {
  return request<{ valid: boolean; label: string; tiers: string[] }>(`/api/access/validate/${token}`);
}

// ── SharePoint ──────────────────────────────────────────────────

export async function listSharePointSites(): Promise<SharePointSite[]> {
  return request("/api/sharepoint/sites");
}

export async function listSharePointDrives(siteId: string): Promise<SharePointDrive[]> {
  return request(`/api/sharepoint/sites/${encodeURIComponent(siteId)}/drives`);
}

export async function listSharePointFolders(
  siteId: string,
  driveId: string,
  folderId: string = "root",
): Promise<SharePointFolder[]> {
  const qs = new URLSearchParams({ folder_id: folderId });
  return request(`/api/sharepoint/sites/${encodeURIComponent(siteId)}/drives/${encodeURIComponent(driveId)}/folders?${qs}`);
}

export async function createSharePointFolder(
  driveId: string,
  parentFolderId: string,
  folderName: string,
): Promise<SharePointFolder> {
  return request("/api/sharepoint/folders", {
    method: "POST",
    body: JSON.stringify({ drive_id: driveId, parent_folder_id: parentFolderId, folder_name: folderName }),
  });
}

export async function uploadToSharePoint(
  jobId: string,
  siteId: string,
  driveId: string,
  folderId: string,
): Promise<SharePointUploadResult> {
  return request("/api/sharepoint/upload", {
    method: "POST",
    body: JSON.stringify({ job_id: jobId, site_id: siteId, drive_id: driveId, folder_id: folderId }),
  });
}

// ── Zoho CRM ────────────────────────────────────────────────────

export async function getZohoPreview(jobId: string): Promise<ZohoProductPreview> {
  return request(`/api/zoho/preview/${jobId}`);
}

export async function pushToZoho(jobId: string): Promise<ZohoPushResult> {
  return request("/api/zoho/push", {
    method: "POST",
    body: JSON.stringify({ job_id: jobId }),
  });
}

// ── Email Ingestion ─────────────────────────────────────────────

export async function listEmailIngestions(status?: EmailIngestionStatus): Promise<EmailIngestion[]> {
  const qs = status ? `?status=${status}` : "";
  return request(`/api/email/ingestions${qs}`);
}

export async function getEmailIngestion(id: string): Promise<EmailIngestion> {
  return request(`/api/email/ingestions/${id}`);
}

export async function confirmEmailClient(ingestionId: string, clientName: string): Promise<EmailIngestion> {
  return request(`/api/email/ingestions/${ingestionId}/client`, {
    method: "PATCH",
    body: JSON.stringify({ client_name: clientName }),
  });
}

export async function reclassifyAttachment(
  attachmentId: string,
  attachmentType: AttachmentType,
): Promise<EmailAttachment> {
  return request(`/api/email/attachments/${attachmentId}/reclassify`, {
    method: "PATCH",
    body: JSON.stringify({ attachment_type: attachmentType }),
  });
}

export function getAttachmentFileUrl(attachmentId: string): string {
  return `${API}/api/email/attachments/${attachmentId}/file`;
}

export async function triggerEmailPoll(): Promise<{ polled: boolean; new_emails: number }> {
  return request("/api/email/poll", { method: "POST" });
}

// ── Evernote ────────────────────────────────────────────────────

export async function getEvernotePreview(jobId: string): Promise<EvernotePreview> {
  return request(`/api/evernote/preview/${jobId}`);
}

export async function pushToEvernote(jobId: string, clientName?: string): Promise<EvernotePushResult> {
  return request("/api/evernote/push", {
    method: "POST",
    body: JSON.stringify({ job_id: jobId, client_name: clientName }),
  });
}
