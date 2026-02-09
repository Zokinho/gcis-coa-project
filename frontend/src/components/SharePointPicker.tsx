"use client";

import { useEffect, useState } from "react";
import {
  listSharePointSites,
  listSharePointDrives,
  listSharePointFolders,
  createSharePointFolder,
  uploadToSharePoint,
} from "@/lib/api";
import type {
  SharePointSite,
  SharePointDrive,
  SharePointFolder,
} from "@/lib/types";

interface Props {
  jobId: string;
  onClose: () => void;
  onSuccess: (webUrl: string) => void;
}

type Step = "sites" | "drives" | "folders";

interface Breadcrumb {
  id: string;
  name: string;
}

export default function SharePointPicker({ jobId, onClose, onSuccess }: Props) {
  const [step, setStep] = useState<Step>("sites");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const [sites, setSites] = useState<SharePointSite[]>([]);
  const [drives, setDrives] = useState<SharePointDrive[]>([]);
  const [folders, setFolders] = useState<SharePointFolder[]>([]);

  const [selectedSite, setSelectedSite] = useState<SharePointSite | null>(null);
  const [selectedDrive, setSelectedDrive] = useState<SharePointDrive | null>(null);
  const [currentFolderId, setCurrentFolderId] = useState("root");
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([]);

  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [creatingFolder, setCreatingFolder] = useState(false);

  // Load sites on mount
  useEffect(() => {
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await listSharePointSites();
        setSites(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load sites");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function pickSite(site: SharePointSite) {
    setSelectedSite(site);
    setStep("drives");
    setLoading(true);
    setError("");
    try {
      const data = await listSharePointDrives(site.id);
      setDrives(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load document libraries");
    } finally {
      setLoading(false);
    }
  }

  async function pickDrive(drive: SharePointDrive) {
    setSelectedDrive(drive);
    setStep("folders");
    setCurrentFolderId("root");
    setBreadcrumbs([{ id: "root", name: drive.name }]);
    setLoading(true);
    setError("");
    try {
      const data = await listSharePointFolders(selectedSite!.id, drive.id, "root");
      setFolders(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load folders");
    } finally {
      setLoading(false);
    }
  }

  async function openFolder(folder: SharePointFolder) {
    setCurrentFolderId(folder.id);
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
    setLoading(true);
    setError("");
    try {
      const data = await listSharePointFolders(selectedSite!.id, selectedDrive!.id, folder.id);
      setFolders(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load folders");
    } finally {
      setLoading(false);
    }
  }

  async function jumpToBreadcrumb(index: number) {
    const crumb = breadcrumbs[index];
    setCurrentFolderId(crumb.id);
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
    setLoading(true);
    setError("");
    try {
      const data = await listSharePointFolders(selectedSite!.id, selectedDrive!.id, crumb.id);
      setFolders(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load folders");
    } finally {
      setLoading(false);
    }
  }

  function goBack() {
    setError("");
    setShowNewFolder(false);
    if (step === "folders") {
      setStep("drives");
      setSelectedDrive(null);
      setFolders([]);
      setBreadcrumbs([]);
    } else if (step === "drives") {
      setStep("sites");
      setSelectedSite(null);
      setDrives([]);
    }
  }

  async function handleCreateFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    setCreatingFolder(true);
    setError("");
    try {
      const created = await createSharePointFolder(selectedDrive!.id, currentFolderId, name);
      setFolders((prev) => [...prev, created]);
      setNewFolderName("");
      setShowNewFolder(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create folder");
    } finally {
      setCreatingFolder(false);
    }
  }

  async function handleUpload() {
    setUploading(true);
    setError("");
    try {
      const result = await uploadToSharePoint(
        jobId,
        selectedSite!.id,
        selectedDrive!.id,
        currentFolderId,
      );
      onSuccess(result.web_url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const title =
    step === "sites"
      ? "Select a SharePoint Site"
      : step === "drives"
        ? "Select a Document Library"
        : "Select a Folder";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* Breadcrumbs */}
        {step === "folders" && breadcrumbs.length > 0 && (
          <div className="flex items-center gap-1 px-5 pt-3 text-sm text-gray-500 flex-wrap">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.id} className="flex items-center gap-1">
                {i > 0 && <span>/</span>}
                {i < breadcrumbs.length - 1 ? (
                  <button
                    onClick={() => jumpToBreadcrumb(i)}
                    className="text-blue-600 hover:underline"
                  >
                    {crumb.name}
                  </button>
                ) : (
                  <span className="font-medium text-gray-700">{crumb.name}</span>
                )}
              </span>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="px-5 py-4">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mb-3">
              {error}
            </p>
          )}

          {loading ? (
            <p className="text-gray-500 text-sm py-8 text-center">Loading...</p>
          ) : (
            <div className="max-h-72 overflow-y-auto space-y-1">
              {step === "sites" &&
                (sites.length === 0 ? (
                  <p className="text-gray-500 text-sm py-4 text-center">No sites found.</p>
                ) : (
                  sites.map((site) => (
                    <button
                      key={site.id}
                      onClick={() => pickSite(site)}
                      className="w-full text-left px-3 py-2.5 rounded hover:bg-gray-100 transition flex items-center gap-3"
                    >
                      <span className="text-blue-600 text-lg">&#x1F310;</span>
                      <div>
                        <p className="font-medium text-gray-900 text-sm">{site.name}</p>
                        <p className="text-xs text-gray-500 truncate">{site.web_url}</p>
                      </div>
                    </button>
                  ))
                ))}

              {step === "drives" &&
                (drives.length === 0 ? (
                  <p className="text-gray-500 text-sm py-4 text-center">No document libraries found.</p>
                ) : (
                  drives.map((drive) => (
                    <button
                      key={drive.id}
                      onClick={() => pickDrive(drive)}
                      className="w-full text-left px-3 py-2.5 rounded hover:bg-gray-100 transition flex items-center gap-3"
                    >
                      <span className="text-yellow-600 text-lg">&#x1F4C1;</span>
                      <p className="font-medium text-gray-900 text-sm">{drive.name}</p>
                    </button>
                  ))
                ))}

              {step === "folders" &&
                (folders.length === 0 ? (
                  <p className="text-gray-400 text-sm py-4 text-center">No subfolders — you can upload here.</p>
                ) : (
                  folders.map((folder) => (
                    <button
                      key={folder.id}
                      onClick={() => openFolder(folder)}
                      className="w-full text-left px-3 py-2.5 rounded hover:bg-gray-100 transition flex items-center gap-3"
                    >
                      <span className="text-yellow-600 text-lg">&#x1F4C2;</span>
                      <p className="font-medium text-gray-900 text-sm">{folder.name}</p>
                    </button>
                  ))
                ))}
            </div>
          )}

          {/* New Folder inline form */}
          {step === "folders" && !loading && showNewFolder && (
            <div className="flex items-center gap-2 mt-3">
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                placeholder="Folder name"
                autoFocus
                className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleCreateFolder}
                disabled={creatingFolder || !newFolderName.trim()}
                className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded-md hover:bg-gray-800 disabled:opacity-50 transition"
              >
                {creatingFolder ? "Creating..." : "Create"}
              </button>
              <button
                onClick={() => { setShowNewFolder(false); setNewFolderName(""); }}
                className="px-2 py-1.5 text-sm text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-5 py-4">
          <button
            onClick={step === "sites" ? onClose : goBack}
            className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition"
          >
            {step === "sites" ? "Cancel" : "Back"}
          </button>

          {step === "folders" && (
            <div className="flex gap-2">
              {!showNewFolder && (
                <button
                  onClick={() => setShowNewFolder(true)}
                  className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition"
                >
                  New Folder
                </button>
              )}
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {uploading ? "Uploading..." : "Upload Here"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
