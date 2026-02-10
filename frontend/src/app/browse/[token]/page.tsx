"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { validateToken, listProductGroups } from "@/lib/api";
import type { ProductGroup } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FilterChips from "@/components/FilterChips";

const tierColors: Record<string, string> = {
  gold: "bg-yellow-100 text-yellow-800 border-yellow-300",
  silver: "bg-gray-100 text-gray-700 border-gray-300",
  bronze: "bg-orange-100 text-orange-800 border-orange-300",
};

function ProductGroupCard({ group, token }: { group: ProductGroup; token: string }) {
  const latest = group.latest_product;
  return (
    <Link href={`/browse/${token}/products/${group.id}`}>
      <div className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-white cursor-pointer">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-lg text-gray-900 leading-tight">
            {group.name}
          </h3>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded border shrink-0 ${
              tierColors[group.tier] ?? "bg-blue-50 text-blue-700 border-blue-200"
            }`}
          >
            {group.tier}
          </span>
        </div>

        {group.strain_type && (
          <p className="text-sm text-gray-500 mb-1">{group.strain_type}</p>
        )}

        {latest && (
          <div className="text-sm text-gray-600 space-y-0.5 mb-3">
            <p>
              <span className="text-gray-400">Lot:</span> {latest.lot_number}
            </p>
            <p>
              <span className="text-gray-400">Lab:</span> {latest.lab}
            </p>
            {latest.test_date && (
              <p>
                <span className="text-gray-400">Tested:</span> {latest.test_date}
              </p>
            )}
          </div>
        )}

        {group.coa_count > 1 && (
          <p className="text-xs text-blue-600 mb-2">
            {group.coa_count} CoAs available
          </p>
        )}

        {group.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {group.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}

export default function BrowsePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);

  const [valid, setValid] = useState<boolean | null>(null);
  const [label, setLabel] = useState("");
  const [tiers, setTiers] = useState<string[]>([]);
  const [groups, setGroups] = useState<ProductGroup[]>([]);
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

  // Fetch product groups whenever filters change (once token is valid)
  const fetchGroups = useCallback(async () => {
    if (valid !== true) return;
    setLoading(true);
    try {
      const data = await listProductGroups({
        token,
        q: query || undefined,
        tier: selectedTier || undefined,
      });
      setGroups(data);
    } catch {
      setError("Failed to load products.");
    } finally {
      setLoading(false);
    }
  }, [token, valid, query, selectedTier]);

  useEffect(() => {
    fetchGroups();
  }, [fetchGroups]);

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

        {/* Product Group Grid */}
        {loading ? (
          <p className="text-gray-500 text-center py-12">
            Loading products...
          </p>
        ) : groups.length === 0 ? (
          <p className="text-gray-500 text-center py-12">
            No products found.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {groups.map((g) => (
              <ProductGroupCard key={g.id} group={g} token={token} />
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
