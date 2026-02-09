"use client";

import { useState } from "react";
import type { AccessToken } from "@/lib/types";
import { updateAccessToken, deleteAccessToken } from "@/lib/api";

interface Props {
  tokens: AccessToken[];
  onRefresh: () => void;
}

export default function TokenTable({ tokens, onRefresh }: Props) {
  const [copied, setCopied] = useState<string | null>(null);

  async function copyToken(token: string, id: string) {
    await navigator.clipboard.writeText(token);
    setCopied(id);
    setTimeout(() => setCopied(null), 1500);
  }

  async function handleToggle(t: AccessToken) {
    await updateAccessToken(t.id, { active: !t.active });
    onRefresh();
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this access token?")) return;
    await deleteAccessToken(id);
    onRefresh();
  }

  if (tokens.length === 0) {
    return <p className="text-gray-500 text-sm py-4">No access tokens yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2 pr-4 font-medium">Label</th>
            <th className="py-2 pr-4 font-medium">Token</th>
            <th className="py-2 pr-4 font-medium">Tiers</th>
            <th className="py-2 pr-4 font-medium">Status</th>
            <th className="py-2 pr-4 font-medium">Uses</th>
            <th className="py-2 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((t) => (
            <tr key={t.id} className="border-b last:border-0">
              <td className="py-2 pr-4 font-medium">{t.label}</td>
              <td className="py-2 pr-4">
                <span className="font-mono text-xs">
                  {t.token.slice(0, 12)}...
                </span>
                <button
                  onClick={() => copyToken(t.token, t.id)}
                  className="ml-2 text-xs text-blue-600 hover:text-blue-800"
                >
                  {copied === t.id ? "Copied!" : "Copy"}
                </button>
              </td>
              <td className="py-2 pr-4">
                <div className="flex gap-1 flex-wrap">
                  {t.tiers.map((tier) => (
                    <span
                      key={tier}
                      className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-xs"
                    >
                      {tier}
                    </span>
                  ))}
                </div>
              </td>
              <td className="py-2 pr-4">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    t.active
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {t.active ? "Active" : "Inactive"}
                </span>
              </td>
              <td className="py-2 pr-4 tabular-nums">{t.use_count}</td>
              <td className="py-2">
                <div className="flex gap-2">
                  <button
                    onClick={() => handleToggle(t)}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    {t.active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
