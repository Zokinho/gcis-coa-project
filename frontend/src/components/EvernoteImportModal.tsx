"use client";

import { useEffect, useState } from "react";
import {
  listEvernoteNotes,
  getEvernoteNoteDetail,
  triggerEvernoteImport,
} from "@/lib/api";
import type {
  EvernoteNoteListItem,
  EvernoteNoteDetail,
} from "@/lib/types";

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function EvernoteImportModal({
  open,
  onClose,
  onImported,
}: {
  open: boolean;
  onClose: () => void;
  onImported?: () => void;
}) {
  const [step, setStep] = useState<"browse" | "preview">("browse");
  const [notes, setNotes] = useState<EvernoteNoteListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedGuid, setSelectedGuid] = useState<string | null>(null);
  const [detail, setDetail] = useState<EvernoteNoteDetail | null>(null);
  const [clientName, setClientName] = useState("");
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setStep("browse");
    setError("");
    setLoading(true);
    listEvernoteNotes()
      .then(setNotes)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [open]);

  async function selectNote(guid: string) {
    setSelectedGuid(guid);
    setLoading(true);
    setError("");
    try {
      const d = await getEvernoteNoteDetail(guid);
      setDetail(d);
      setClientName(d.client_name);
      setStep("preview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to preview note");
    } finally {
      setLoading(false);
    }
  }

  async function handleImport() {
    if (!selectedGuid) return;
    setImporting(true);
    setError("");
    try {
      await triggerEvernoteImport(selectedGuid, clientName || undefined);
      onImported?.();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {step === "browse" ? "Import from Evernote" : "Preview Import"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading...</p>
            </div>
          ) : step === "browse" ? (
            <div className="space-y-2">
              {notes.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No notes found in the configured notebook.</p>
              ) : (
                notes.map((note) => (
                  <button
                    key={note.guid}
                    type="button"
                    onClick={() => selectNote(note.guid)}
                    className="w-full flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 text-sm truncate">
                        {note.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {note.resource_count} resource{note.resource_count !== 1 ? "s" : ""}
                        {note.updated && ` · Updated: ${new Date(note.updated).toLocaleDateString()}`}
                      </p>
                    </div>
                    {note.already_imported && (
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 shrink-0">
                        Already imported
                      </span>
                    )}
                    <svg className="h-4 w-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ))
              )}
            </div>
          ) : detail ? (
            <div className="space-y-4">
              {/* Back button */}
              <button
                type="button"
                onClick={() => { setStep("browse"); setDetail(null); }}
                className="text-sm text-blue-600 hover:underline"
              >
                Back to notes
              </button>

              {/* Note info */}
              <div>
                <p className="text-sm font-medium text-gray-900">{detail.title}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {detail.pdf_count} PDF{detail.pdf_count !== 1 ? "s" : ""}, {detail.photo_count} photo{detail.photo_count !== 1 ? "s" : ""}
                </p>
              </div>

              {/* Client name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Client Name
                </label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Client name for imported products"
                />
              </div>

              {/* Resources table */}
              {detail.resources.length > 0 && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-gray-500">File</th>
                        <th className="text-left px-3 py-2 font-medium text-gray-500">Type</th>
                        <th className="text-right px-3 py-2 font-medium text-gray-500">Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.resources.map((res) => (
                        <tr key={res.guid} className="border-b border-gray-100">
                          <td className="px-3 py-2 text-gray-800 truncate max-w-[200px]">{res.filename}</td>
                          <td className="px-3 py-2">
                            <span
                              className={`text-xs px-2 py-0.5 rounded ${
                                res.is_pdf
                                  ? "bg-red-50 text-red-700"
                                  : "bg-blue-50 text-blue-700"
                              }`}
                            >
                              {res.is_pdf ? "PDF" : "Image"}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right text-gray-500">{formatSize(res.size)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Cost estimate */}
              {detail.pdf_count > 0 && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
                  <strong>Estimate:</strong> {detail.pdf_count} PDF{detail.pdf_count !== 1 ? "s" : ""} will be processed via Claude API.
                  Each CoA typically costs ~$0.05-0.15 in API tokens (6 pages avg).
                  Total estimated cost: ${(detail.pdf_count * 0.10).toFixed(2)}-${(detail.pdf_count * 0.15).toFixed(2)}
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        {step === "preview" && detail && (
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              onClick={handleImport}
              disabled={importing || detail.pdf_count === 0}
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
            >
              {importing ? "Importing..." : `Import ${detail.pdf_count} PDF${detail.pdf_count !== 1 ? "s" : ""}`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
