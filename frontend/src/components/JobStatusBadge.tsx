"use client";

import type { JobStatus } from "@/lib/types";

const STATUS_STYLES: Record<JobStatus, string> = {
  queued: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  review: "bg-yellow-100 text-yellow-800",
  published: "bg-green-100 text-green-700",
  flagged: "bg-orange-100 text-orange-700",
  error: "bg-red-100 text-red-700",
};

export default function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700"}`}
    >
      {status}
    </span>
  );
}
