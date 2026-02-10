"use client";

import { useState } from "react";
import type { ProductPhoto } from "@/lib/types";
import { getProductPhotoUrl } from "@/lib/api";

export default function PhotoThumbnails({
  productId,
  photos,
}: {
  productId: string;
  photos: ProductPhoto[];
}) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  if (!photos || photos.length === 0) return null;

  return (
    <>
      <div className="flex gap-2 overflow-x-auto py-1">
        {photos.map((photo) => {
          const url = getProductPhotoUrl(productId, photo.id);
          return (
            <button
              key={photo.id}
              type="button"
              onClick={() => setLightboxUrl(url)}
              className="shrink-0 w-16 h-16 rounded border border-gray-200 overflow-hidden hover:ring-2 hover:ring-blue-400 transition"
              title={photo.original_filename}
            >
              <img
                src={url}
                alt={photo.original_filename}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </button>
          );
        })}
      </div>

      {/* Lightbox overlay */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setLightboxUrl(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh]">
            <button
              type="button"
              onClick={() => setLightboxUrl(null)}
              className="absolute -top-10 right-0 text-white text-sm hover:text-gray-300"
            >
              Close
            </button>
            <img
              src={lightboxUrl}
              alt="Product photo"
              className="max-w-full max-h-[85vh] object-contain rounded"
            />
          </div>
        </div>
      )}
    </>
  );
}
