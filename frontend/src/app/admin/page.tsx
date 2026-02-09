"use client";

import { useEffect, useState } from "react";
import { getStats } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";

interface StatCard {
  label: string;
  key: keyof DashboardStats;
  color: string;
}

const CARDS: StatCard[] = [
  { label: "Total Jobs", key: "total_jobs", color: "bg-gray-900 text-white" },
  { label: "Queued", key: "queued", color: "bg-gray-100 text-gray-700" },
  { label: "Processing", key: "processing", color: "bg-blue-100 text-blue-700" },
  { label: "Review", key: "review", color: "bg-yellow-100 text-yellow-800" },
  { label: "Published", key: "published", color: "bg-green-100 text-green-700" },
  { label: "Flagged", key: "flagged", color: "bg-orange-100 text-orange-700" },
  { label: "Error", key: "error", color: "bg-red-100 text-red-700" },
  { label: "Products Published", key: "products_published", color: "bg-emerald-100 text-emerald-700" },
  { label: "Access Tokens", key: "total_tokens", color: "bg-purple-100 text-purple-700" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) {
    return <p className="text-red-600">{error}</p>;
  }

  if (!stats) {
    return <p className="text-gray-500">Loading stats...</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {CARDS.map((card) => (
          <div
            key={card.key}
            className={`rounded-lg p-4 ${card.color}`}
          >
            <p className="text-sm font-medium opacity-80">{card.label}</p>
            <p className="text-3xl font-bold mt-1">{stats[card.key]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
