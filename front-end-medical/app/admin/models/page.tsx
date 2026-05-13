"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useToast } from "@/context/ToastContext";

// Mock Data
const MOCK_MODELS = [
  { id: "MDL-001", name: "YOLOv8-fvfdbbfgbfgbfgMedical", type: "Detection", version: "v1.2", created: "2026-03-12", acc: "89.5%", status: "Ready" },
  { id: "MDL-002", name: "ResNetgfhbfrthrthrthrhrhtrhrt-50-Chest", type: "Classification", version: "v2.0", created: "2026-03-15", acc: "94.2%", status: "Ready" },
  { id: "MDL-003", name: "UNet-Brain", type: "Segmentation", version: "v1.0", created: "2026-03-16", acc: "-", status: "Training" },
  { id: "MDL-004", name: "DenseNet-Lungs", type: "Classification", version: "v1.1", created: "2026-03-10", acc: "-", status: "Failed" },
];

export default function ModelManagementPage() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Upload Modal State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadType, setUploadType] = useState("Classification");
  const [uploadDesc, setUploadDesc] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { showToast } = useToast();

  // Filter logic
  const filteredData = MOCK_MODELS.filter(
    (item) =>
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
      (filterType === "All" || item.type === filterType)
  );

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      alert("Vui lòng chọn file Weight (.pt, .pth, .onnx)!");
      return;
    }

    setIsUploading(true);
    await new Promise(resolve => setTimeout(resolve, 2000));

    showToast("Model weight uploaded successfully!");
    setIsUploading(false);
    setIsUploadOpen(false);

    // Reset
    setUploadName("");
    setUploadType("Classification");
    setUploadDesc("");
    setUploadFile(null);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Ready": return <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">Ready</span>;
      case "Failed": return <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">Failed</span>;
      case "Training": return (
        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 inline-flex items-center gap-1.5 whitespace-nowrap">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
          Training
        </span>
      );
      default: return null;
    }
  };

  return (
    <div className="space-y-6 relative pb-10">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Model Management</h1>
          <p className="text-sm text-gray-500 mt-1">Quản lý các mô hình AI, weights và version</p>
        </div>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium text-sm transition-colors shadow-sm flex items-center gap-2 max-w-max"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          Upload Model
        </button>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setCurrentPage(1); }}
          className="w-full sm:w-auto border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none bg-white min-w-[150px]"
        >
          <option value="All">All Types</option>
          <option value="Classification">Classification</option>
          <option value="Detection">Detection</option>
          <option value="Segmentation">Segmentation</option>
        </select>

        <div className="relative w-full sm:w-80">
          <input
            type="text"
            className="block w-full p-2 pl-3 text-sm text-gray-900 border border-gray-300 rounded-lg bg-white focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
            placeholder="Search model name..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-gray-600">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 border-b border-gray-200">
              <tr>
                <th scope="col" className="px-6 py-4 font-semibold">Model ID</th>
                <th scope="col" className="px-6 py-4 font-semibold">Name</th>
                <th scope="col" className="px-6 py-4 font-semibold">Task Type</th>
                <th scope="col" className="px-6 py-4 font-semibold">Version</th>
                <th scope="col" className="px-6 py-4 font-semibold">Metrics (Acc/mAP)</th>
                <th scope="col" className="px-6 py-4 font-semibold">Status</th>
                <th scope="col" className="px-6 py-4 font-semibold">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {paginatedData.length > 0 ? (
                paginatedData.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => router.push(`/admin/models/${row.id}`)}
                    className="bg-white hover:bg-gray-50/80 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4 font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap">
                      {row.id}
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-800">{row.name}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                        {row.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-xs">{row.version}</td>
                    <td className="px-6 py-4 whitespace-nowrap font-semibold text-emerald-600">{row.acc}</td>
                    <td className="px-6 py-4">{getStatusBadge(row.status)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{row.created}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    <p>No models found.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {totalPages > 0 && (
          <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50/50 text-sm text-gray-600">
            <span>Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, filteredData.length)} of {filteredData.length}</span>
            <div className="inline-flex space-x-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 disabled:opacity-50 transition-all"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 disabled:opacity-50 transition-all"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200 border border-gray-100">
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h3 className="font-bold text-lg text-gray-900">Upload Pre-trained Model</h3>
              <button onClick={() => setIsUploadOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="p-6 space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Model Name <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={uploadName}
                  onChange={e => setUploadName(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none"
                  placeholder="Ex: YOLOv8-v2-Custom"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Arch Type <span className="text-red-500">*</span></label>
                <select
                  value={uploadType}
                  onChange={e => setUploadType(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none"
                >
                  <option value="Classification">Classification</option>
                  <option value="Detection">Detection (YOLO, Faster-RCNN, etc.)</option>
                  <option value="Segmentation">Segmentation (U-Net, Mask-RCNN)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Weight File (.pt, .pth, .onnx) <span className="text-red-500">*</span></label>
                <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer relative">
                  <div className="space-y-1 text-center">
                    <p className="text-sm text-gray-600 font-medium">Click or drag & drop to upload</p>
                    <p className="text-xs text-gray-500">Max size: 500MB</p>
                    {uploadFile && <p className="text-xs font-semibold text-blue-600 pt-2">{uploadFile.name}</p>}
                  </div>
                  <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" accept=".pt,.pth,.onnx" onChange={e => { if (e.target.files) setUploadFile(e.target.files[0]) }} required={!uploadFile} />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 mt-4 border-t border-gray-100 pt-5">
                <button type="button" onClick={() => setIsUploadOpen(false)} disabled={isUploading} className="px-5 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none disabled:opacity-50">
                  Cancel
                </button>
                <button type="submit" disabled={isUploading} className="px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm flex items-center gap-2 justify-center disabled:opacity-70 disabled:cursor-not-allowed">
                  {isUploading ? "Uploading..." : "Upload Model"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
