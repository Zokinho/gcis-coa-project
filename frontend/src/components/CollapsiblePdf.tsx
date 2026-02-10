"use client";

import { useState } from "react";

interface CollapsiblePdfProps {
  pdfUrl: string;
  filename: string;
  fileSize: number;
  pageCount: number;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function CollapsiblePdf({
  pdfUrl,
  filename,
  fileSize,
  pageCount,
}: CollapsiblePdfProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header — click to toggle */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        {/* PDF icon */}
        <svg
          className="h-8 w-6 text-red-500 shrink-0"
          viewBox="0 0 24 32"
          fill="currentColor"
        >
          <path d="M14 0H3a3 3 0 00-3 3v26a3 3 0 003 3h18a3 3 0 003-3V10L14 0zm-1 2l9 9h-6a3 3 0 01-3-3V2zM7 20h2c1.1 0 2-.45 2-1.5S10.1 17 9 17H8v-2H6v7h1v-2zm7 2h-2v-7h2c1.66 0 3 1.34 3 3.5S15.66 22 14 22zm5-5h3v1h-2v1.5h1.5v1H20V22h-1v-5z" />
        </svg>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {filename}
          </p>
          <p className="text-xs text-gray-500">
            {formatFileSize(fileSize)}
            {pageCount > 0 && ` · ${pageCount} page${pageCount !== 1 ? "s" : ""}`}
          </p>
        </div>

        {/* Download button */}
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 p-2 text-gray-400 hover:text-blue-600 transition-colors"
          title="Download PDF"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v3a2 2 0 002 2h14a2 2 0 002-2v-3"
            />
          </svg>
        </a>

        {/* Chevron */}
        <svg
          className={`h-5 w-5 text-gray-400 shrink-0 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Expanded: inline PDF preview */}
      <div
        className={`transition-[max-height] duration-300 ease-in-out overflow-hidden ${
          expanded ? "max-h-[800px]" : "max-h-0"
        }`}
      >
        {expanded && (
          <iframe
            src={pdfUrl}
            className="w-full h-[700px] border-t border-gray-200"
            title={filename}
          />
        )}
      </div>
    </div>
  );
}
