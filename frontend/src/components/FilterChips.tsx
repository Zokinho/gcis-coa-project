"use client";

export default function FilterChips({
  options,
  selected,
  onSelect,
  label,
}: {
  options: string[];
  selected: string | null;
  onSelect: (v: string | null) => void;
  label?: string;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {label && (
        <span className="text-sm text-gray-500 mr-1">{label}</span>
      )}
      {options.map((opt) => {
        const active = selected === opt;
        return (
          <button
            key={opt}
            onClick={() => onSelect(active ? null : opt)}
            className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
              active
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}
