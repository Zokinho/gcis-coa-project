"use client";

import Link from "next/link";
import type { Product } from "@/lib/types";

const tierColors: Record<string, string> = {
  gold: "bg-yellow-100 text-yellow-800 border-yellow-300",
  silver: "bg-gray-100 text-gray-700 border-gray-300",
  bronze: "bg-orange-100 text-orange-800 border-orange-300",
};

export default function ProductCard({
  product,
  token,
}: {
  product: Product;
  token: string;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const potency = (product as any).potency as
    | Record<string, unknown>
    | undefined;
  const totalThc = potency?.total_thc;

  return (
    <Link href={`/browse/${token}/products/${product.id}`}>
      <div className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-white cursor-pointer">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-lg text-gray-900 leading-tight">
            {product.name}
          </h3>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded border shrink-0 ${
              tierColors[product.tier] ?? "bg-blue-50 text-blue-700 border-blue-200"
            }`}
          >
            {product.tier}
          </span>
        </div>

        {product.strain_type && (
          <p className="text-sm text-gray-500 mb-1">{product.strain_type}</p>
        )}

        <div className="text-sm text-gray-600 space-y-0.5 mb-3">
          <p>
            <span className="text-gray-400">Lot:</span> {product.lot_number}
          </p>
          <p>
            <span className="text-gray-400">Lab:</span> {product.lab}
          </p>
        </div>

        {totalThc != null && (
          <p className="text-sm font-medium text-green-700">
            THC: {String(totalThc)}%
          </p>
        )}

        {product.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {product.tags.map((tag) => (
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
