"use client";

interface TerpeneResult {
  analyte: string;
  value: number | string;
  unit?: string;
}

const barColors = [
  "bg-emerald-500",
  "bg-teal-500",
  "bg-cyan-500",
  "bg-sky-500",
  "bg-indigo-500",
];

export default function TerpeneBar({
  data,
}: {
  data: Record<string, unknown>;
}) {
  const results = (data.results ?? []) as TerpeneResult[];

  const sorted = [...results]
    .map((r) => ({ ...r, numVal: typeof r.value === "number" ? r.value : parseFloat(String(r.value)) || 0 }))
    .filter((r) => r.numVal > 0)
    .sort((a, b) => b.numVal - a.numVal)
    .slice(0, 5);

  if (sorted.length === 0) {
    return <p className="text-sm text-gray-400">No terpene data available.</p>;
  }

  const max = sorted[0].numVal;

  return (
    <div className="space-y-2">
      {sorted.map((t, i) => (
        <div key={t.analyte} className="flex items-center gap-3">
          <span className="text-sm text-gray-700 w-40 shrink-0 truncate">
            {t.analyte}
          </span>
          <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
            <div
              className={`${barColors[i % barColors.length]} h-full rounded-full transition-all`}
              style={{ width: `${(t.numVal / max) * 100}%` }}
            />
          </div>
          <span className="text-sm text-gray-600 w-20 text-right shrink-0">
            {t.numVal.toFixed(3)}
            {t.unit ? ` ${t.unit}` : "%"}
          </span>
        </div>
      ))}
    </div>
  );
}
