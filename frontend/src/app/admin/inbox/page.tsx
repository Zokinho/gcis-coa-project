"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listEmailIngestions, triggerEmailPoll } from "@/lib/api";
import type { EmailIngestion, EmailIngestionStatus } from "@/lib/types";

const STATUS_COLORS: Record<EmailIngestionStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  review: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

const FILTERS: { label: string; value: EmailIngestionStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Processing", value: "processing" },
  { label: "Review", value: "review" },
  { label: "Completed", value: "completed" },
  { label: "Error", value: "error" },
];

export default function InboxPage() {
  const [emails, setEmails] = useState<EmailIngestion[]>([]);
  const [filter, setFilter] = useState<EmailIngestionStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [pollResult, setPollResult] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await listEmailIngestions(filter === "all" ? undefined : filter);
      setEmails(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filter]);

  async function handlePoll() {
    setPolling(true);
    setPollResult(null);
    try {
      const result = await triggerEmailPoll();
      setPollResult(`Found ${result.new_emails} new email(s)`);
      await load();
    } catch (err: unknown) {
      setPollResult(err instanceof Error ? err.message : "Poll failed");
    } finally {
      setPolling(false);
    }
  }

  function formatDate(d: string | null) {
    if (!d) return "—";
    return new Date(d).toLocaleString();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Email Inbox</h1>
        <button
          onClick={handlePoll}
          disabled={polling}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {polling ? "Polling..." : "Poll Now"}
        </button>
      </div>

      {pollResult && (
        <div className="text-sm bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded flex items-center justify-between">
          <span>{pollResult}</span>
          <button
            onClick={() => setPollResult(null)}
            className="text-blue-600 hover:text-blue-800 ml-4"
          >
            &times;
          </button>
        </div>
      )}

      {/* Status filter chips */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-sm rounded-full transition ${
              filter === f.value
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Email list */}
      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : emails.length === 0 ? (
        <p className="text-gray-500 text-sm">No emails found.</p>
      ) : (
        <div className="space-y-3">
          {emails.map((em) => {
            const coaCount = em.attachments.filter(
              (a) => a.attachment_type === "coa_pdf" || a.attachment_type === "coa_photo"
            ).length;
            const photoCount = em.attachments.filter(
              (a) => a.attachment_type === "product_photo"
            ).length;

            return (
              <Link
                key={em.id}
                href={`/admin/inbox/${em.id}`}
                className="block bg-white border rounded-lg p-4 hover:border-gray-400 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 truncate">
                      {em.subject || "(no subject)"}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      From: {em.sender}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <span>{formatDate(em.received_at || em.created_at)}</span>
                      <span>{em.attachments.length} attachment(s)</span>
                      {coaCount > 0 && (
                        <span className="text-blue-600">{coaCount} CoA</span>
                      )}
                      {photoCount > 0 && (
                        <span className="text-purple-600">{photoCount} photo(s)</span>
                      )}
                    </div>
                    {(em.confirmed_client || em.suggested_client) && (
                      <p className="text-sm mt-2">
                        <span className="text-gray-500">Client: </span>
                        <span className="font-medium text-gray-900">
                          {em.confirmed_client || em.suggested_client}
                        </span>
                        {!em.confirmed_client && em.suggested_client && (
                          <span className="text-xs text-yellow-600 ml-1">(suggested)</span>
                        )}
                      </p>
                    )}
                  </div>
                  <span
                    className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                      STATUS_COLORS[em.status]
                    }`}
                  >
                    {em.status}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
