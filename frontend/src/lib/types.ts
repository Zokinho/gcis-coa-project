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

export interface RedactionUpdate {
  approved?: boolean;
  x_pct?: number;
  y_pct?: number;
  w_pct?: number;
  h_pct?: number;
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
