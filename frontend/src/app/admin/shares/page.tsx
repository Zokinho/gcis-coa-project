"use client";

import { useEffect, useState, useCallback } from "react";
import {
  listCuratedShares,
  createCuratedShare,
  deleteCuratedShare,
  listProducts,
} from "@/lib/api";
import type { CuratedShare, Product } from "@/lib/types";

export default function SharesPage() {
  const [shares, setShares] = useState<CuratedShare[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const fetchShares = useCallback(async () => {
    try {
      const data = await listCuratedShares();
      setShares(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShares();
  }, [fetchShares]);

  async function handleDeactivate(id: string) {
    try {
      await deleteCuratedShare(id);
      fetchShares();
    } catch {
      // ignore
    }
  }

  function copyLink(token: string) {
    const url = `${window.location.origin}/share/${token}`;
    navigator.clipboard.writeText(url);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Curated Shares</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
        >
          New Share
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading shares...</p>
        </div>
      ) : shares.length === 0 ? (
        <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
          <p className="text-gray-500">No curated shares yet.</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
          {shares.map((share) => {
            const expired =
              share.expires_at && new Date(share.expires_at) < new Date();

            return (
              <div
                key={share.id}
                className="flex items-center gap-4 px-5 py-4"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 text-sm">
                    {share.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {share.product_ids.length} product{share.product_ids.length !== 1 ? "s" : ""}
                    {" · "}Created {new Date(share.created_at).toLocaleDateString()}
                    {share.expires_at && (
                      <>
                        {" · "}Expires{" "}
                        {new Date(share.expires_at).toLocaleDateString()}
                      </>
                    )}
                    {share.use_count > 0 && (
                      <>
                        {" · "}{share.use_count} view{share.use_count !== 1 ? "s" : ""}
                      </>
                    )}
                  </p>
                </div>

                <span
                  className={`text-xs px-2 py-0.5 rounded shrink-0 ${
                    !share.active
                      ? "bg-red-50 text-red-700"
                      : expired
                        ? "bg-yellow-50 text-yellow-700"
                        : "bg-green-50 text-green-700"
                  }`}
                >
                  {!share.active ? "Inactive" : expired ? "Expired" : "Active"}
                </span>

                <button
                  onClick={() => copyLink(share.token)}
                  className="text-xs px-3 py-1.5 border border-gray-200 rounded hover:bg-gray-50 text-gray-600 transition"
                  title="Copy share link"
                >
                  Copy Link
                </button>

                {share.active && (
                  <button
                    onClick={() => handleDeactivate(share.id)}
                    className="text-xs px-3 py-1.5 border border-red-200 rounded hover:bg-red-50 text-red-600 transition"
                  >
                    Deactivate
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create Share Modal */}
      {showCreate && (
        <CreateShareModal
          onClose={() => setShowCreate(false)}
          onCreated={fetchShares}
        />
      )}
    </div>
  );
}

function CreateShareModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [label, setLabel] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [products, setProducts] = useState<Product[]>([]);
  const [productSearch, setProductSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [expiresAt, setExpiresAt] = useState("");

  useEffect(() => {
    listProducts({ per_page: 200 })
      .then((data) => {
        // Only show published products
        setProducts(data.filter((p) => p.status === "published"));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = products.filter(
    (p) =>
      !productSearch ||
      p.name.toLowerCase().includes(productSearch.toLowerCase()) ||
      (p.client_name && p.client_name.toLowerCase().includes(productSearch.toLowerCase()))
  );

  function toggleProduct(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleCreate() {
    if (!label.trim() || selectedIds.size === 0) return;
    setCreating(true);
    try {
      await createCuratedShare(
        label.trim(),
        Array.from(selectedIds),
        expiresAt || undefined,
      );
      onCreated();
      onClose();
    } catch {
      // ignore
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            New Curated Share
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Label</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g., Sativa selection for Client X"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Expiry (optional)
            </label>
            <input
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Products ({selectedIds.size} selected)
            </label>
            <input
              type="text"
              value={productSearch}
              onChange={(e) => setProductSearch(e.target.value)}
              placeholder="Search products..."
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {loading ? (
              <p className="text-gray-500 text-sm py-4 text-center">Loading products...</p>
            ) : (
              <div className="border border-gray-200 rounded-lg max-h-60 overflow-auto divide-y divide-gray-100">
                {filtered.map((p) => (
                  <label
                    key={p.id}
                    className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(p.id)}
                      onChange={() => toggleProduct(p.id)}
                      className="rounded"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 truncate">{p.name}</p>
                      <p className="text-xs text-gray-500">
                        {p.client_name && `${p.client_name} · `}
                        {p.lot_number} · {p.lab}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating || !label.trim() || selectedIds.size === 0}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {creating ? "Creating..." : "Create Share"}
          </button>
        </div>
      </div>
    </div>
  );
}
