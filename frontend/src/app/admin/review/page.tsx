"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listJobs } from "@/lib/api";
import type { Job } from "@/lib/types";
import JobStatusBadge from "@/components/JobStatusBadge";

export default function ReviewListPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listJobs()
      .then((all) => setJobs(all.filter((j) => j.status === "review")))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-gray-500">Loading...</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Jobs Pending Review
      </h1>

      {jobs.length === 0 ? (
        <p className="text-gray-500">No jobs awaiting review.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="bg-white rounded-lg border p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-gray-900 text-sm truncate">
                  {job.filename}
                </p>
                <JobStatusBadge status={job.status} />
              </div>
              <div className="text-xs text-gray-500 space-y-1">
                <p>{job.page_count} page{job.page_count !== 1 ? "s" : ""}</p>
                <p>{new Date(job.created_at).toLocaleString()}</p>
              </div>
              <Link
                href={`/admin/review/${job.id}`}
                className="inline-block text-sm font-medium text-blue-600 hover:text-blue-800"
              >
                Review &rarr;
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
