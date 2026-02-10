"use client";

import { useEffect, useState, useCallback } from "react";
import { listClients, listClientProducts, getProductPdfUrl } from "@/lib/api";
import type { ClientSummary, ClientProduct } from "@/lib/types";
import CollapsiblePdf from "@/components/CollapsiblePdf";
import SyncBadges from "@/components/SyncBadges";
import PhotoThumbnails from "@/components/PhotoThumbnails";
import EvernoteImportModal from "@/components/EvernoteImportModal";

const tierColors: Record<string, string> = {
  gold: "bg-yellow-100 text-yellow-800",
  silver: "bg-gray-100 text-gray-700",
  bronze: "bg-orange-100 text-orange-800",
};

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

interface ProductGrouping {
  groupId: string | null;
  groupName: string;
  products: ClientProduct[];
}

function groupProductsByProductGroup(products: ClientProduct[]): ProductGrouping[] {
  const groups = new Map<string, ProductGrouping>();
  const ungrouped: ClientProduct[] = [];

  for (const p of products) {
    if (p.product_group_id) {
      const existing = groups.get(p.product_group_id);
      if (existing) {
        existing.products.push(p);
      } else {
        groups.set(p.product_group_id, {
          groupId: p.product_group_id,
          groupName: p.product_group_name || p.name,
          products: [p],
        });
      }
    } else {
      ungrouped.push(p);
    }
  }

  const result: ProductGrouping[] = [...groups.values()];

  // Add ungrouped as individual entries
  for (const p of ungrouped) {
    result.push({
      groupId: null,
      groupName: p.name,
      products: [p],
    });
  }

  return result;
}

function ProductCard({ product }: { product: ClientProduct }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      {/* Product summary row */}
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 text-sm">
            {product.name}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Lot: {product.lot_number} · Lab: {product.lab}
            {product.test_date && ` · ${product.test_date}`}
          </p>
        </div>
        <SyncBadges syncs={product.syncs} />
        <span
          className={`text-xs px-2 py-0.5 rounded shrink-0 ${
            tierColors[product.tier] ?? "bg-blue-50 text-blue-700"
          }`}
        >
          {product.tier}
        </span>
        <span
          className={`text-xs px-2 py-0.5 rounded shrink-0 ${
            product.status === "published"
              ? "bg-green-50 text-green-700"
              : "bg-gray-100 text-gray-600"
          }`}
        >
          {product.status}
        </span>
      </div>

      {/* Collapsible PDF */}
      {product.pdf_filename && (
        <CollapsiblePdf
          pdfUrl={getProductPdfUrl(product.id)}
          filename={product.pdf_filename}
          fileSize={product.pdf_file_size}
          pageCount={product.pdf_page_count}
        />
      )}

      {/* Product photos */}
      {product.photos && product.photos.length > 0 && (
        <PhotoThumbnails
          productId={product.id}
          photos={product.photos}
        />
      )}
    </div>
  );
}

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expandedClient, setExpandedClient] = useState<string | null>(null);
  const [products, setProducts] = useState<ClientProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);

  const fetchClients = useCallback(async (q?: string) => {
    try {
      const data = await listClients(q || undefined);
      setClients(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      fetchClients(search);
    }, 300);
    return () => clearTimeout(timeout);
  }, [search, fetchClients]);

  async function toggleClient(clientName: string) {
    if (expandedClient === clientName) {
      setExpandedClient(null);
      setProducts([]);
      return;
    }
    setExpandedClient(clientName);
    setProductsLoading(true);
    try {
      const data = await listClientProducts(clientName);
      setProducts(data);
    } catch {
      setProducts([]);
    } finally {
      setProductsLoading(false);
    }
  }

  const productGroupings = groupProductsByProductGroup(products);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Client Records</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setImportModalOpen(true)}
            className="px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition"
          >
            Import from Evernote
          </button>
          <p className="text-sm text-gray-500">
            {clients.length} client{clients.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Search bar */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading clients...</p>
        </div>
      ) : clients.length === 0 ? (
        <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
          <p className="text-gray-500">
            {search ? "No clients match your search." : "No client records yet."}
          </p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
          {clients.map((client) => {
            const isExpanded = expandedClient === client.client_name;
            return (
              <div key={client.client_name}>
                {/* Client row */}
                <button
                  type="button"
                  onClick={() => toggleClient(client.client_name)}
                  className="w-full flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors text-left"
                >
                  <svg
                    className={`h-5 w-5 text-gray-400 shrink-0 transition-transform duration-200 ${
                      isExpanded ? "rotate-90" : ""
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>

                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900">
                      {client.client_name}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {client.product_count} product{client.product_count !== 1 ? "s" : ""}
                      {client.latest_test_date && ` · Latest: ${client.latest_test_date}`}
                    </p>
                  </div>

                  <div className="flex gap-1.5 shrink-0">
                    {client.tiers.map((tier) => (
                      <span
                        key={tier}
                        className={`text-xs px-2 py-0.5 rounded ${
                          tierColors[tier] ?? "bg-blue-50 text-blue-700"
                        }`}
                      >
                        {tier}
                      </span>
                    ))}
                  </div>
                </button>

                {/* Expanded products — grouped by ProductGroup */}
                {isExpanded && (
                  <div className="bg-gray-50 border-t border-gray-200 px-5 py-4">
                    {productsLoading ? (
                      <p className="text-sm text-gray-500 py-2">Loading products...</p>
                    ) : products.length === 0 ? (
                      <p className="text-sm text-gray-500 py-2">No products found.</p>
                    ) : (
                      <div className="space-y-5">
                        {productGroupings.map((grouping) => (
                          <div key={grouping.groupId || grouping.products[0]?.id}>
                            {/* Group sub-header (only show if there are multiple groups or multiple CoAs) */}
                            {(productGroupings.length > 1 || grouping.products.length > 1) && (
                              <div className="flex items-center gap-2 mb-2">
                                <h4 className="text-sm font-semibold text-gray-700">
                                  {grouping.groupName}
                                </h4>
                                {grouping.products.length > 1 && (
                                  <span className="text-xs text-gray-400">
                                    ({grouping.products.length} CoAs)
                                  </span>
                                )}
                              </div>
                            )}
                            <div className="space-y-3">
                              {grouping.products.map((product) => (
                                <ProductCard key={product.id} product={product} />
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Evernote Import Modal */}
      <EvernoteImportModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onImported={() => fetchClients(search || undefined)}
      />
    </div>
  );
}
