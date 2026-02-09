"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { createAccessToken, listAccessTokens } from "@/lib/api";
import type { AccessToken } from "@/lib/types";
import TokenTable from "@/components/TokenTable";

export default function TokensPage() {
  const [tokens, setTokens] = useState<AccessToken[]>([]);
  const [label, setLabel] = useState("");
  const [tiersInput, setTiersInput] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    listAccessTokens().then(setTokens).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    const tiers = tiersInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (!label.trim()) {
      setError("Label is required.");
      return;
    }
    if (tiers.length === 0) {
      setError("At least one tier is required.");
      return;
    }
    setCreating(true);
    try {
      await createAccessToken(label.trim(), tiers);
      setLabel("");
      setTiersInput("");
      refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create token");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          Access Tokens
        </h1>

        {/* Create form */}
        <form
          onSubmit={handleCreate}
          className="bg-white rounded-lg border p-4 space-y-4"
        >
          <h2 className="font-semibold text-gray-900">Create Token</h2>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
              {error}
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Label
              </label>
              <input
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. Buyer ABC"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tiers (comma-separated)
              </label>
              <input
                type="text"
                value={tiersInput}
                onChange={(e) => setTiersInput(e.target.value)}
                placeholder="e.g. basic, premium"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={creating}
            className="px-4 py-2 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800 disabled:opacity-50 transition"
          >
            {creating ? "Creating..." : "Create Token"}
          </button>
        </form>
      </div>

      {/* Token list */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="font-semibold text-gray-900 mb-3">All Tokens</h2>
        <TokenTable tokens={tokens} onRefresh={refresh} />
      </div>
    </div>
  );
}
