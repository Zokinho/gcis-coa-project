"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getProduct, getProductPdfUrl } from "@/lib/api";
import type { ProductDetail, ProductTestData } from "@/lib/types";
import TerpeneBar from "@/components/TerpeneBar";

const tierColors: Record<string, string> = {
  gold: "bg-yellow-100 text-yellow-800 border-yellow-300",
  silver: "bg-gray-100 text-gray-700 border-gray-300",
  bronze: "bg-orange-100 text-orange-800 border-orange-300",
};

interface ResultRow {
  analyte: string;
  value: string | number;
  unit?: string;
  status?: string;
}

function TestDataTable({ testData }: { testData: ProductTestData }) {
  const results = (testData.data.results ?? []) as ResultRow[];

  if (results.length === 0) {
    return <p className="text-sm text-gray-400">No results data.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500">
            <th className="py-2 pr-4 font-medium">Analyte</th>
            <th className="py-2 pr-4 font-medium">Value</th>
            <th className="py-2 pr-4 font-medium">Unit</th>
            <th className="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => (
            <tr key={i} className="border-b border-gray-100">
              <td className="py-1.5 pr-4 text-gray-800">{r.analyte}</td>
              <td className="py-1.5 pr-4 text-gray-700">{String(r.value)}</td>
              <td className="py-1.5 pr-4 text-gray-500">{r.unit ?? "-"}</td>
              <td className="py-1.5">
                {r.status ? (
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded ${
                      r.status === "pass" || r.status === "Pass"
                        ? "bg-green-50 text-green-700"
                        : r.status === "fail" || r.status === "Fail"
                          ? "bg-red-50 text-red-700"
                          : "bg-gray-50 text-gray-600"
                    }`}
                  >
                    {r.status}
                  </span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TestDataSection({ testData }: { testData: ProductTestData }) {
  const isTerpene =
    testData.test_type.toLowerCase().includes("terpene");

  return (
    <section className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900 capitalize">
          {testData.test_type.replace(/_/g, " ")}
        </h3>
        {testData.overall_result && (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded ${
              testData.overall_result.toLowerCase() === "pass"
                ? "bg-green-50 text-green-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {testData.overall_result}
          </span>
        )}
      </div>

      {testData.method && (
        <p className="text-xs text-gray-400 mb-3">
          Method: {testData.method}
        </p>
      )}

      {isTerpene ? (
        <TerpeneBar data={testData.data} />
      ) : (
        <TestDataTable testData={testData} />
      )}
    </section>
  );
}

export default function ProductDetailPage({
  params,
}: {
  params: Promise<{ token: string; id: string }>;
}) {
  const { token, id } = use(params);

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getProduct(id, token)
      .then(setProduct)
      .catch((err) => setError(err.message || "Failed to load product."))
      .finally(() => setLoading(false));
  }, [id, token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading product...</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-bold text-red-600 mb-2">Error</h1>
          <p className="text-gray-600">{error || "Product not found."}</p>
          <Link
            href={`/browse/${token}`}
            className="text-blue-600 hover:underline text-sm mt-4 inline-block"
          >
            Back to catalog
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Back link */}
        <Link
          href={`/browse/${token}`}
          className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to catalog
        </Link>

        {/* Product header */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {product.name}
              </h1>
              {product.strain_type && (
                <p className="text-gray-500 mt-1">{product.strain_type}</p>
              )}
            </div>
            <span
              className={`text-sm font-medium px-3 py-1 rounded border shrink-0 ${
                tierColors[product.tier] ?? "bg-blue-50 text-blue-700 border-blue-200"
              }`}
            >
              {product.tier}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-400">Lot Number</p>
              <p className="text-gray-800 font-medium">{product.lot_number}</p>
            </div>
            <div>
              <p className="text-gray-400">Lab</p>
              <p className="text-gray-800 font-medium">{product.lab}</p>
            </div>
            {product.test_date && (
              <div>
                <p className="text-gray-400">Test Date</p>
                <p className="text-gray-800 font-medium">{product.test_date}</p>
              </div>
            )}
            {product.report_number && (
              <div>
                <p className="text-gray-400">Report Number</p>
                <p className="text-gray-800 font-medium">
                  {product.report_number}
                </p>
              </div>
            )}
            {product.producer && (
              <div>
                <p className="text-gray-400">Producer</p>
                <p className="text-gray-800 font-medium">{product.producer}</p>
              </div>
            )}
          </div>

          {product.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-gray-100">
              {product.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Download PDF */}
        <div>
          <a
            href={getProductPdfUrl(product.id, token)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v3a2 2 0 002 2h14a2 2 0 002-2v-3"
              />
            </svg>
            Download PDF
          </a>
        </div>

        {/* Test data sections */}
        {product.test_data.length > 0 ? (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Test Results</h2>
            {product.test_data.map((td) => (
              <TestDataSection key={td.id} testData={td} />
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">
            No test data available for this product.
          </p>
        )}
      </div>
    </div>
  );
}
