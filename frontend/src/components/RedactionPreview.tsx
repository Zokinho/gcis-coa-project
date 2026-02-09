"use client";

import { useRef, useCallback } from "react";
import type { RedactionRegion } from "@/lib/types";

interface Props {
  regions: RedactionRegion[];
  page: number;
  imageUrl: string;
  onToggle: (id: string, approved: boolean) => void;
  onUpdate: (id: string, coords: { x_pct: number; y_pct: number; w_pct: number; h_pct: number }) => void;
}

const PADDING_PCT = 0.5;
const DRAG_THRESHOLD = 3; // pixels before a click becomes a drag
const MIN_SIZE_PCT = 1; // minimum box dimension in percent

export default function RedactionPreview({ regions, page, imageUrl, onToggle, onUpdate }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRegions = regions.filter((r) => r.page === page);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, region: RedactionRegion, mode: "move" | "resize") => {
      e.preventDefault();
      e.stopPropagation();

      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const startX = e.clientX;
      const startY = e.clientY;
      let moved = false;

      // Current position including padding offset
      let curX = region.x_pct - PADDING_PCT;
      let curY = region.y_pct - PADDING_PCT;
      let curW = region.w_pct + 2 * PADDING_PCT;
      let curH = region.h_pct + 2 * PADDING_PCT;

      // The overlay element being dragged
      const overlay = (e.target as HTMLElement).closest("[data-redaction-id]") as HTMLElement;
      if (!overlay) return;

      overlay.style.opacity = "0.7";

      function onMouseMove(ev: MouseEvent) {
        const dx = ev.clientX - startX;
        const dy = ev.clientY - startY;

        if (!moved && Math.abs(dx) < DRAG_THRESHOLD && Math.abs(dy) < DRAG_THRESHOLD) {
          return;
        }
        moved = true;

        const dxPct = (dx / rect.width) * 100;
        const dyPct = (dy / rect.height) * 100;

        if (mode === "move") {
          const newX = Math.max(0, Math.min(100 - curW, (region.x_pct - PADDING_PCT) + dxPct));
          const newY = Math.max(0, Math.min(100 - curH, (region.y_pct - PADDING_PCT) + dyPct));
          overlay.style.left = `${newX}%`;
          overlay.style.top = `${newY}%`;
          curX = newX;
          curY = newY;
        } else {
          const baseW = region.w_pct + 2 * PADDING_PCT;
          const baseH = region.h_pct + 2 * PADDING_PCT;
          const newW = Math.max(MIN_SIZE_PCT, Math.min(100 - curX, baseW + dxPct));
          const newH = Math.max(MIN_SIZE_PCT, Math.min(100 - curY, baseH + dyPct));
          overlay.style.width = `${newW}%`;
          overlay.style.height = `${newH}%`;
          curW = newW;
          curH = newH;
        }
      }

      function onMouseUp() {
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        overlay.style.opacity = "";

        if (!moved) {
          // It was a click, not a drag — toggle
          onToggle(region.id, !region.approved);
          return;
        }

        // Convert back: remove padding to get the raw coordinates
        const newX = Math.max(0, curX + PADDING_PCT);
        const newY = Math.max(0, curY + PADDING_PCT);
        const newW = Math.max(MIN_SIZE_PCT, curW - 2 * PADDING_PCT);
        const newH = Math.max(MIN_SIZE_PCT, curH - 2 * PADDING_PCT);

        onUpdate(region.id, {
          x_pct: Math.round(newX * 100) / 100,
          y_pct: Math.round(newY * 100) / 100,
          w_pct: Math.round(newW * 100) / 100,
          h_pct: Math.round(newH * 100) / 100,
        });
      }

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [onToggle, onUpdate]
  );

  return (
    <div ref={containerRef} className="relative bg-white rounded border border-gray-300 overflow-hidden select-none">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={imageUrl}
        alt={`Page ${page + 1}`}
        className="w-full h-auto block pointer-events-none"
        draggable={false}
      />
      {pageRegions.map((r) => {
        const left = Math.max(0, r.x_pct - PADDING_PCT);
        const top = Math.max(0, r.y_pct - PADDING_PCT);
        const width = r.w_pct + 2 * PADDING_PCT;
        const height = r.h_pct + 2 * PADDING_PCT;
        return (
          <div
            key={r.id}
            data-redaction-id={r.id}
            title={`${r.reason} (${r.confidence}) — drag to move, corner to resize, click to toggle`}
            className={`absolute transition-colors ${
              r.approved
                ? "bg-red-500/40 border-2 border-red-500"
                : "bg-gray-400/20 border-2 border-dashed border-gray-400"
            }`}
            style={{
              left: `${left}%`,
              top: `${top}%`,
              width: `${width}%`,
              height: `${height}%`,
              cursor: "move",
            }}
            onMouseDown={(e) => handleMouseDown(e, r, "move")}
          >
            <span className="sr-only">{r.reason}</span>
            {/* Resize handle — bottom-right corner */}
            <div
              className="absolute bottom-0 right-0 w-3 h-3 bg-white/80 border border-gray-500 cursor-nwse-resize"
              onMouseDown={(e) => {
                e.stopPropagation();
                handleMouseDown(e, r, "resize");
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
