"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getJob,
  getJobProduct,
  getPageImageUrl,
  getRedactions,
  toggleRedaction,
  updateRedaction,
  publishJob,
  rescanJob,
} from "@/lib/api";
import type { Job, Product, RedactionRegion } from "@/lib/types";
import RedactionPreview from "@/components/RedactionPreview";

export default function ReviewDetailPage() {
  const params = useParams<{ jobId: string }>();
  const router = useRouter();
  const jobId = params.jobId;

  const [job, setJob] = useState<Job | null>(null);
  const [product, setProduct] = useState<Product | null>(null);
  const [regions, setRegions] = useState<RedactionRegion[]>([]);
  const [activePage, setActivePage] = useState(0);
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [rescanning, setRescanning] = useState(false);

  const load = useCallback(async () => {
    try {
      const [j, r] = await Promise.all([
        getJob(jobId),
        getRedactions(jobId),
      ]);
      setJob(j);
      setRegions(r);
      if (j.product_id) {
        const p = await getJobProduct(jobId);
        setProduct(p);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  }, [jobId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleToggle(redactionId: string, approved: boolean) {
    try {
      const updated = await toggleRedaction(jobId, redactionId, approved);
      setRegions((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
    } catch {
      /* ignore */
    }
  }

  async function handleUpdate(
    redactionId: string,
    coords: { x_pct: number; y_pct: number; w_pct: number; h_pct: number }
  ) {
    try {
      const updated = await updateRedaction(jobId, redactionId, coords);
      setRegions((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
    } catch {
      /* ignore */
    }
  }

  async function handlePublish() {
    setPublishing(true);
    try {
      const updated = await publishJob(jobId);
      setJob(updated);
      router.push("/admin/review");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  async function handleRescan() {
    setRescanning(true);
    try {
      const updated = await rescanJob(jobId);
      setJob(updated);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Rescan failed");
    } finally {
      setRescanning(false);
    }
  }

  if (error && !job) {
    return <p className="text-red-600">{error}</p>;
  }

  if (!job) {
    return <p className="text-gray-500">Loading...</p>;
  }

  const pages = Array.from({ length: job.page_count }, (_, i) => i);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{job.filename}</h1>
        <div className="flex gap-2">
          <button
            onClick={handleRescan}
            disabled={rescanning}
            className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 transition"
          >
            {rescanning ? "Rescanning..." : "Rescan"}
          </button>
          <button
            onClick={handlePublish}
            disabled={publishing}
            className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition"
          >
            {publishing ? "Publishing..." : "Publish"}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
          {error}
        </p>
      )}

      {/* Product info */}
      {product && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-900 mb-2">Product Info</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Name</span>
              <p className="font-medium text-gray-900">{product.name}</p>
            </div>
            <div>
              <span className="text-gray-500">Lot</span>
              <p className="font-medium text-gray-900">{product.lot_number}</p>
            </div>
            <div>
              <span className="text-gray-500">Lab</span>
              <p className="font-medium text-gray-900">{product.lab}</p>
            </div>
            <div>
              <span className="text-gray-500">Tier</span>
              <p className="font-medium text-gray-900 capitalize">{product.tier}</p>
            </div>
          </div>
        </div>
      )}

      {/* Page tabs + preview */}
      <div className="bg-white rounded-lg border p-4 space-y-4">
        <h2 className="font-semibold text-gray-900">Redaction Preview</h2>
        <div className="flex gap-2 flex-wrap">
          {pages.map((p) => (
            <button
              key={p}
              onClick={() => setActivePage(p)}
              className={`px-3 py-1 text-sm rounded transition ${
                activePage === p
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Page {p + 1}
            </button>
          ))}
        </div>
        <div className="max-w-2xl">
          <RedactionPreview
            regions={regions}
            page={activePage}
            imageUrl={getPageImageUrl(jobId, activePage)}
            onToggle={handleToggle}
            onUpdate={handleUpdate}
          />
        </div>
      </div>

      {/* Redaction list */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="font-semibold text-gray-900 mb-3">
          Redactions ({regions.length})
        </h2>
        {regions.length === 0 ? (
          <p className="text-gray-500 text-sm">No redaction regions found.</p>
        ) : (
          <div className="space-y-2">
            {regions.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between border rounded p-3 text-sm"
              >
                <div className="flex-1">
                  <span className="font-medium text-gray-900">Page {r.page + 1}</span>
                  <span className="mx-2 text-gray-300">|</span>
                  <span className="text-gray-700">{r.reason}</span>
                  <span className="mx-2 text-gray-300">|</span>
                  <span
                    className={`text-xs font-medium ${
                      r.confidence === "high"
                        ? "text-green-600"
                        : r.confidence === "medium"
                          ? "text-yellow-600"
                          : "text-red-600"
                    }`}
                  >
                    {r.confidence}
                  </span>
                  <span className="ml-2 text-xs text-gray-400">
                    ({r.x_pct.toFixed(1)}, {r.y_pct.toFixed(1)}) {r.w_pct.toFixed(1)}x{r.h_pct.toFixed(1)}%
                  </span>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-xs text-gray-500">
                    {r.approved ? "On" : "Off"}
                  </span>
                  <button
                    onClick={() => handleToggle(r.id, !r.approved)}
                    className={`relative w-9 h-5 rounded-full transition ${
                      r.approved ? "bg-red-500" : "bg-gray-300"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                        r.approved ? "translate-x-4" : ""
                      }`}
                    />
                  </button>
                </label>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
