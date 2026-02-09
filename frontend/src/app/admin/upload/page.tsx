"use client";

import { useEffect, useState, useCallback, useRef, DragEvent } from "react";
import { uploadCoA, listJobs } from "@/lib/api";
import type { Job } from "@/lib/types";
import JobStatusBadge from "@/components/JobStatusBadge";

export default function UploadPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => {
    listJobs().then(setJobs).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }
    setError("");
    setUploading(true);
    try {
      await uploadCoA(file);
      refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onFileSelect() {
    const file = fileRef.current?.files?.[0];
    if (file) handleFile(file);
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Upload CoA</h1>

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition mb-6 ${
          dragOver
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400"
        }`}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          onChange={onFileSelect}
          className="hidden"
        />
        {uploading ? (
          <p className="text-gray-600">Uploading...</p>
        ) : (
          <div>
            <p className="text-gray-600 font-medium">
              Drop a PDF here or click to browse
            </p>
            <p className="text-gray-400 text-sm mt-1">
              Accepts .pdf files only
            </p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mb-4">
          {error}
        </p>
      )}

      {/* Jobs table */}
      {jobs.length > 0 && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-gray-500">
                <th className="px-4 py-3 font-medium">Filename</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Pages</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b last:border-0">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {job.filename}
                  </td>
                  <td className="px-4 py-3">
                    <JobStatusBadge status={job.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {job.page_count ?? "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {formatDate(job.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
