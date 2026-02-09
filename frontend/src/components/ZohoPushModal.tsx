"use client";

import { useEffect, useState } from "react";
import { getZohoPreview, pushToZoho } from "@/lib/api";
import type { ZohoProductPreview } from "@/lib/types";

interface Props {
  jobId: string;
  onClose: () => void;
  onSuccess: (recordUrl: string) => void;
}

const FIELD_LABELS: Record<string, string> = {
  Product_Name: "Product Name",
  Product_Code: "Lot / Product Code",
  Lab: "Lab",
  Manufacturer: "Producer",
  Strain_Type: "Strain Type",
  Description: "Description",
  Test_Date: "Test Date",
  THC_Percentage: "THC %",
  CBD_Percentage: "CBD %",
  Terpene_Profile: "Terpene Profile",
};

export default function ZohoPushModal({ jobId, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(true);
  const [pushing, setPushing] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<ZohoProductPreview | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getZohoPreview(jobId);
        setPreview(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load preview");
      } finally {
        setLoading(false);
      }
    })();
  }, [jobId]);

  async function handlePush() {
    setPushing(true);
    setError("");
    try {
      const result = await pushToZoho(jobId);
      onSuccess(result.record_url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Push failed");
    } finally {
      setPushing(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Send to Zoho CRM
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="px-5 py-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mb-3">
              {error}
            </p>
          )}

          {loading ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              Loading field mapping...
            </p>
          ) : preview ? (
            <>
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 pr-4 text-gray-500 font-medium">
                        CRM Field
                      </th>
                      <th className="text-left py-2 text-gray-500 font-medium">
                        Value
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(preview.fields).map(([key, value]) => (
                      <tr key={key} className="border-b border-gray-100">
                        <td className="py-2 pr-4 text-gray-600">
                          {FIELD_LABELS[key] || key}
                        </td>
                        <td className="py-2 font-medium text-gray-900">
                          {value != null ? String(value) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 text-sm text-gray-500 flex items-center gap-2">
                <span>PDF attachment:</span>
                <span className="font-medium text-gray-700">
                  {preview.pdf_filename}
                </span>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-5 py-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={handlePush}
            disabled={pushing || loading || !preview}
            className="px-4 py-2 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 transition"
          >
            {pushing ? "Pushing..." : "Push to Zoho CRM"}
          </button>
        </div>
      </div>
    </div>
  );
}
