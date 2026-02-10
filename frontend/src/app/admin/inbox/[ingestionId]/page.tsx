"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getEmailIngestion,
  confirmEmailClient,
  reclassifyAttachment,
  getAttachmentFileUrl,
} from "@/lib/api";
import type { EmailIngestion, AttachmentType } from "@/lib/types";

const TYPE_COLORS: Record<AttachmentType, string> = {
  coa_pdf: "bg-blue-100 text-blue-700",
  coa_photo: "bg-teal-100 text-teal-700",
  product_photo: "bg-purple-100 text-purple-700",
};

const TYPE_OPTIONS: { value: AttachmentType; label: string }[] = [
  { value: "coa_pdf", label: "CoA PDF" },
  { value: "coa_photo", label: "CoA Photo" },
  { value: "product_photo", label: "Product Photo" },
];

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function EmailDetailPage() {
  const params = useParams<{ ingestionId: string }>();
  const ingestionId = params.ingestionId;

  const [email, setEmail] = useState<EmailIngestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [clientInput, setClientInput] = useState("");
  const [editingClient, setEditingClient] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showBody, setShowBody] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await getEmailIngestion(ingestionId);
      setEmail(data);
      setClientInput(data.confirmed_client || data.suggested_client || "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [ingestionId]);

  async function handleConfirmClient() {
    if (!clientInput.trim()) return;
    setSaving(true);
    try {
      const updated = await confirmEmailClient(ingestionId, clientInput.trim());
      setEmail(updated);
      setEditingClient(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleReclassify(attachmentId: string, newType: AttachmentType) {
    try {
      await reclassifyAttachment(attachmentId, newType);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reclassify failed");
    }
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error && !email) return <p className="text-red-600">{error}</p>;
  if (!email) return <p className="text-gray-500">Not found</p>;

  const productPhotos = email.attachments.filter(
    (a) => a.attachment_type === "product_photo"
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/admin/inbox"
          className="text-gray-400 hover:text-gray-600 transition"
        >
          &larr; Inbox
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 flex-1 truncate">
          {email.subject || "(no subject)"}
        </h1>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
          {error}
        </p>
      )}

      {/* Email metadata */}
      <div className="bg-white rounded-lg border p-4 space-y-3">
        <h2 className="font-semibold text-gray-900">Email Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">From</span>
            <p className="font-medium text-gray-900">{email.sender}</p>
          </div>
          <div>
            <span className="text-gray-500">Received</span>
            <p className="font-medium text-gray-900">
              {email.received_at
                ? new Date(email.received_at).toLocaleString()
                : "—"}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Status</span>
            <p className="font-medium text-gray-900 capitalize">{email.status}</p>
          </div>
          <div>
            <span className="text-gray-500">Attachments</span>
            <p className="font-medium text-gray-900">{email.attachments.length}</p>
          </div>
        </div>

        {email.body_text && (
          <div>
            <button
              onClick={() => setShowBody(!showBody)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              {showBody ? "Hide body" : "Show body"}
            </button>
            {showBody && (
              <pre className="mt-2 text-sm text-gray-700 bg-gray-50 p-3 rounded max-h-48 overflow-y-auto whitespace-pre-wrap">
                {email.body_text}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* Client name */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="font-semibold text-gray-900 mb-3">Client Name</h2>

        {email.confirmed_client && !editingClient ? (
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-green-700 bg-green-50 px-3 py-1.5 rounded">
              {email.confirmed_client}
            </span>
            <button
              onClick={() => setEditingClient(true)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Edit
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {email.suggested_client && !email.confirmed_client && (
              <p className="text-sm text-gray-500">
                AI suggestion:{" "}
                <span className="font-medium text-gray-900">
                  {email.suggested_client}
                </span>
              </p>
            )}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={clientInput}
                onChange={(e) => setClientInput(e.target.value)}
                placeholder="Enter client name"
                className="flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleConfirmClient}
                disabled={saving || !clientInput.trim()}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition"
              >
                {saving ? "Saving..." : "Confirm"}
              </button>
              {editingClient && (
                <button
                  onClick={() => setEditingClient(false)}
                  className="px-3 py-2 text-sm text-gray-600 border rounded-md hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Attachments table */}
      <div className="bg-white rounded-lg border p-4">
        <h2 className="font-semibold text-gray-900 mb-3">
          Attachments ({email.attachments.length})
        </h2>
        {email.attachments.length === 0 ? (
          <p className="text-gray-500 text-sm">No attachments</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-2 pr-4 text-gray-500 font-medium">Filename</th>
                  <th className="py-2 pr-4 text-gray-500 font-medium">Type</th>
                  <th className="py-2 pr-4 text-gray-500 font-medium">Size</th>
                  <th className="py-2 pr-4 text-gray-500 font-medium">Job</th>
                  <th className="py-2 text-gray-500 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {email.attachments.map((att) => (
                  <tr key={att.id} className="border-b border-gray-100">
                    <td className="py-2 pr-4">
                      <a
                        href={getAttachmentFileUrl(att.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {att.original_filename}
                      </a>
                    </td>
                    <td className="py-2 pr-4">
                      <span
                        className={`px-2 py-0.5 text-xs font-medium rounded ${
                          TYPE_COLORS[att.attachment_type]
                        }`}
                      >
                        {att.attachment_type.replace("_", " ")}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {formatBytes(att.file_size)}
                    </td>
                    <td className="py-2 pr-4">
                      {att.job_id ? (
                        <Link
                          href={`/admin/review/${att.job_id}`}
                          className="text-blue-600 hover:underline text-xs"
                        >
                          View Job
                        </Link>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="py-2">
                      <select
                        value={att.attachment_type}
                        onChange={(e) =>
                          handleReclassify(att.id, e.target.value as AttachmentType)
                        }
                        className="text-xs border rounded px-2 py-1 text-gray-700"
                      >
                        {TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Product photos gallery */}
      {productPhotos.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-900 mb-3">
            Product Photos ({productPhotos.length})
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {productPhotos.map((photo) => (
              <a
                key={photo.id}
                href={getAttachmentFileUrl(photo.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="block aspect-square bg-gray-100 rounded-lg overflow-hidden hover:ring-2 ring-blue-400 transition"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getAttachmentFileUrl(photo.id)}
                  alt={photo.original_filename}
                  className="w-full h-full object-cover"
                />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
