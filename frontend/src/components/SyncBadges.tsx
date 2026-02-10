"use client";

import type { SyncLog } from "@/lib/types";

const targetConfig: Record<string, { label: string; bg: string; text: string }> = {
  evernote: { label: "EN", bg: "bg-green-100", text: "text-green-700" },
  sharepoint: { label: "SP", bg: "bg-blue-100", text: "text-blue-700" },
  zoho: { label: "ZO", bg: "bg-orange-100", text: "text-orange-700" },
};

export default function SyncBadges({ syncs }: { syncs: SyncLog[] }) {
  if (!syncs || syncs.length === 0) return null;

  return (
    <span className="inline-flex gap-1">
      {syncs.map((sync) => {
        const cfg = targetConfig[sync.target] ?? {
          label: sync.target.slice(0, 2).toUpperCase(),
          bg: "bg-gray-100",
          text: "text-gray-600",
        };
        const date = new Date(sync.synced_at).toLocaleDateString();

        return sync.external_url ? (
          <a
            key={sync.id}
            href={sync.external_url}
            target="_blank"
            rel="noopener noreferrer"
            title={`Synced to ${sync.target} on ${date}`}
            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.text} hover:opacity-80 transition-opacity`}
          >
            {cfg.label}
          </a>
        ) : (
          <span
            key={sync.id}
            title={`Synced to ${sync.target} on ${date}`}
            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.text}`}
          >
            {cfg.label}
          </span>
        );
      })}
    </span>
  );
}
