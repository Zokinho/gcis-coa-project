"use client";

import { useEffect, useState } from "react";
import { getEvernotePreview, pushToEvernote } from "@/lib/api";
import type { EvernotePreview } from "@/lib/types";

interface Props {
  jobId: string;
  onClose: () => void;
  onSuccess: (noteUrl: string) => void;
}

export default function EvernotePushModal({ jobId, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(true);
  const [pushing, setPushing] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<EvernotePreview | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getEvernotePreview(jobId);
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
      const result = await pushToEvernote(jobId);
      onSuccess(result.note_url);
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
            Send to Evernote
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
              Loading preview...
            </p>
          ) : preview ? (
            <>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Note:</span>
                  <span className="font-medium text-gray-900">
                    {preview.note_title}
                  </span>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                      preview.is_new_note
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {preview.is_new_note ? "New" : "Existing"}
                  </span>
                </div>

                {/* Preview content - server-generated HTML from our own build_product_enml (html-escaped) */}
                <div className="max-h-64 overflow-y-auto border rounded p-3 bg-gray-50">
                  <div
                    className="text-sm text-gray-700 prose prose-sm max-w-none"
                    // Safe: content_html is generated server-side by build_product_enml()
                    // with html.escape() on all values. Only shown to authenticated admins.
                    dangerouslySetInnerHTML={{ __html: preview.content_html }}
                  />
                </div>
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
            className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition"
          >
            {pushing ? "Pushing..." : "Push to Evernote"}
          </button>
        </div>
      </div>
    </div>
  );
}
