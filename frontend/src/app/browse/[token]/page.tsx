"use client";

import { use, useCallback, useEffect, useState } from "react";
import { validateToken, listProducts } from "@/lib/api";
import type { Product } from "@/lib/types";
import ProductCard from "@/components/ProductCard";
import SearchBar from "@/components/SearchBar";
import FilterChips from "@/components/FilterChips";

export default function BrowsePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);

  const [valid, setValid] = useState<boolean | null>(null);
  const [label, setLabel] = useState("");
  const [tiers, setTiers] = useState<string[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [query, setQuery] = useState("");
  const [selectedTier, setSelectedTier] = useState<string | null>(null);

  // Validate the token on mount
  useEffect(() => {
    validateToken(token)
      .then((res) => {
        setValid(res.valid);
        setLabel(res.label);
        setTiers(res.tiers);
      })
      .catch(() => {
        setValid(false);
        setError("Unable to validate access token.");
      });
  }, [token]);

  // Fetch products whenever filters change (once token is valid)
  const fetchProducts = useCallback(async () => {
    if (valid !== true) return;
    setLoading(true);
    try {
      const data = await listProducts({
        token,
        q: query || undefined,
        tier: selectedTier || undefined,
      });
      setProducts(data);
    } catch {
      setError("Failed to load products.");
    } finally {
      setLoading(false);
    }
  }, [token, valid, query, selectedTier]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Token validation in progress
  if (valid === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Validating access...</p>
      </div>
    );
  }

  // Invalid token
  if (!valid) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-2">
            Access Denied
          </h1>
          <p className="text-gray-600">
            {error || "This access link is invalid or has expired."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <h1 className="text-2xl font-bold text-gray-900">
            GCIS Product Catalog
          </h1>
          {label && (
            <p className="text-sm text-gray-500 mt-1">Viewing as: {label}</p>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Search + Filters */}
        <div className="space-y-4">
          <SearchBar value={query} onChange={setQuery} />
          {tiers.length > 0 && (
            <FilterChips
              options={tiers}
              selected={selectedTier}
              onSelect={setSelectedTier}
              label="Tier:"
            />
          )}
        </div>

        {/* Product Grid */}
        {loading ? (
          <p className="text-gray-500 text-center py-12">
            Loading products...
          </p>
        ) : products.length === 0 ? (
          <p className="text-gray-500 text-center py-12">
            No products found.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} token={token} />
            ))}
          </div>
        )}

        {error && !loading && (
          <p className="text-red-500 text-sm text-center">{error}</p>
        )}
      </main>
    </div>
  );
}
