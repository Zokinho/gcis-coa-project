"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  validateCuratedShare,
  getCuratedShareProducts,
} from "@/lib/api";
import type { ProductDetail } from "@/lib/types";

const tierColors: Record<string, string> = {
  gold: "bg-yellow-100 text-yellow-800",
  silver: "bg-gray-100 text-gray-700",
  bronze: "bg-orange-100 text-orange-800",
};

export default function ShareCatalogPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);

  const [label, setLabel] = useState("");
  const [products, setProducts] = useState<ProductDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    validateCuratedShare(token)
      .then((info) => {
        setLabel(info.label);
        return getCuratedShareProducts(token);
      })
      .then(setProducts)
      .catch((err) => setError(err.message || "Invalid or expired link"))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-xl font-bold text-red-600 mb-2">
            Link Unavailable
          </h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  // Group products by product_group_id for display
  const grouped = new Map<string, ProductDetail[]>();
  const ungrouped: ProductDetail[] = [];
  for (const p of products) {
    if (p.product_group_id) {
      const arr = grouped.get(p.product_group_id) || [];
      arr.push(p);
      grouped.set(p.product_group_id, arr);
    } else {
      ungrouped.push(p);
    }
  }

  // Combine: one card per group (using latest), plus ungrouped
  const displayItems = [
    ...Array.from(grouped.values()).map((items) => {
      const latest = items.find((p) => p.is_latest) || items[0];
      return { product: latest, coaCount: items.length };
    }),
    ...ungrouped.map((p) => ({ product: p, coaCount: 1 })),
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{label}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {displayItems.length} product{displayItems.length !== 1 ? "s" : ""}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {displayItems.map(({ product, coaCount }) => {
            // Extract THC/CBD from test_data
            let thc: string | null = null;
            let cbd: string | null = null;
            for (const td of product.test_data) {
              if (td.test_type === "potency" && td.data) {
                const d = td.data as Record<string, unknown>;
                const thcVal = d.total_thc_pct ?? d.thc_total ?? d.THC_total ?? d.thc;
                const cbdVal = d.total_cbd_pct ?? d.cbd_total ?? d.CBD_total ?? d.cbd;
                if (thcVal != null && thcVal !== "") thc = String(thcVal);
                if (cbdVal != null && cbdVal !== "") cbd = String(cbdVal);
              }
            }

            return (
              <Link
                key={product.id}
                href={`/share/${token}/products/${product.id}`}
                className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h2 className="font-semibold text-gray-900 text-sm">
                    {product.name}
                  </h2>
                  <span
                    className={`text-xs px-2 py-0.5 rounded shrink-0 ${
                      tierColors[product.tier] ?? "bg-blue-50 text-blue-700"
                    }`}
                  >
                    {product.tier}
                  </span>
                </div>

                {product.strain_type && (
                  <p className="text-xs text-gray-500 mb-2">
                    {product.strain_type}
                  </p>
                )}

                <div className="space-y-1 text-xs text-gray-600">
                  <p>Lot: {product.lot_number}</p>
                  <p>Lab: {product.lab}</p>
                  {product.test_date && <p>Tested: {product.test_date}</p>}
                  {thc && <p className="font-medium">THC: {thc}%</p>}
                  {cbd && <p className="font-medium">CBD: {cbd}%</p>}
                </div>

                {coaCount > 1 && (
                  <p className="text-xs text-blue-600 mt-2">
                    {coaCount} CoAs available
                  </p>
                )}
              </Link>
            );
          })}
        </div>

        <p className="text-xs text-gray-400 text-center pt-4">
          Powered by GCIS CoA Automation
        </p>
      </div>
    </div>
  );
}
