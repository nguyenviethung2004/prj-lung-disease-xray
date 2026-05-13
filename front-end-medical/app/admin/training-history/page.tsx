"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

// Mock Data
const MOCK_TRAINING_DATA = [
  { id: "TRN-001", model: "ResNet-50", dataset: "Chest X-Ray v2", start: "2026-03-15 08:00", end: "2026-03-15 14:30", status: "Success", accuracy: "94.5%", loss: "0.12" },
  { id: "TRN-002", model: "YOLOv8-Med", dataset: "MRI Scans", start: "2026-03-16 09:15", end: "2026-03-16 11:20", status: "Success", accuracy: "89.2%", loss: "0.24" },
  { id: "TRN-003", model: "EfficientNet", dataset: "Skin Lesions", start: "2026-03-16 13:00", end: "-", status: "Running", accuracy: "-", loss: "-" },
  { id: "TRN-004", model: "DenseNet-121", dataset: "CT Scans Lung", start: "2026-03-14 20:00", end: "2026-03-14 21:05", status: "Failed", accuracy: "-", loss: "-" },
  { id: "TRN-005", model: "U-Net", dataset: "Cell Segmentation", start: "2026-03-12 10:00", end: "2026-03-13 02:45", status: "Success", accuracy: "96.1%", loss: "0.08" },
  { id: "TRN-006", model: "MobileNetV3", dataset: "Chest X-Ray v1", start: "2026-03-10 15:30", end: "2026-03-10 18:20", status: "Success", accuracy: "91.0%", loss: "0.19" },
  { id: "TRN-007", model: "ResNet-101", dataset: "Brain Tumor MRI", start: "2026-03-17 01:00", end: "2026-03-17 08:30", status: "Success", accuracy: "93.8%", loss: "0.15" },
];

export default function TrainingHistoryPage() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Filter logic
  const filteredData = MOCK_TRAINING_DATA.filter(
    (item) =>
      item.model.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.dataset.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Pagination logic
  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // UI helpers
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Success":
        return <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">Success</span>;
      case "Failed":
        return <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">Failed</span>;
      case "Running":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 inline-flex items-center gap-1.5 whitespace-nowrap">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
            Running
          </span>
        );
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Training History</h1>
        
        {/* Search */}
        <div className="relative w-full sm:w-72">
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <svg className="w-4 h-4 text-gray-500" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 20">
                <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m19 19-4-4m0-7A7 7 0 1 1 1 8a7 7 0 0 1 14 0Z"/>
            </svg>
          </div>
          <input 
            type="text" 
            className="block w-full p-2 pl-10 text-sm text-gray-900 border border-gray-300 rounded-lg bg-white focus:ring-blue-500 focus:border-blue-500 outline-none transition-all" 
            placeholder="Search model or dataset..." 
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1); // Reset page on search
            }}
          />
        </div>
      </div>

      {/* Table Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-gray-600">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 border-b border-gray-200">
              <tr>
                <th scope="col" className="px-6 py-4 font-semibold">Training ID</th>
                <th scope="col" className="px-6 py-4 font-semibold">Model Name</th>
                <th scope="col" className="px-6 py-4 font-semibold">Dataset</th>
                <th scope="col" className="px-6 py-4 font-semibold">Start Time</th>
                <th scope="col" className="px-6 py-4 font-semibold">End Time</th>
                <th scope="col" className="px-6 py-4 font-semibold">Status</th>
                <th scope="col" className="px-6 py-4 font-semibold">Accuracy / Loss</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {paginatedData.length > 0 ? (
                paginatedData.map((row) => (
                  <tr 
                    key={row.id} 
                    onClick={() => router.push(`/admin/training-history/${row.id}`)}
                    className="bg-white hover:bg-gray-50/80 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4 font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap">
                        {row.id}
                    </td>
                    <td className="px-6 py-4 font-semibold text-blue-600">{row.model}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                        {row.dataset}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{row.start}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{row.end}</td>
                    <td className="px-6 py-4">{getStatusBadge(row.status)}</td>
                    <td className="px-6 py-4">
                      {row.status !== "Running" && row.status !== "Failed" ? (
                        <div className="flex flex-col text-xs space-y-1">
                          <span className="text-emerald-600 font-medium">Acc: {row.accuracy}</span>
                          <span className="text-amber-600 font-medium">Loss: {row.loss}</span>
                        </div>
                      ) : (
                        <span className="text-gray-400 font-medium text-xs">-</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    <div className="flex flex-col items-center justify-center">
                      <svg className="w-8 h-8 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                      <p>No training history found matching <span className="font-semibold text-gray-900">"{searchTerm}"</span></p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {totalPages > 0 && (
          <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50/50">
            <span className="text-sm text-gray-600">
              Showing <span className="font-semibold text-gray-900">{(currentPage - 1) * itemsPerPage + 1}</span> to <span className="font-semibold text-gray-900">{Math.min(currentPage * itemsPerPage, filteredData.length)}</span> of <span className="font-semibold text-gray-900">{filteredData.length}</span> Entries
            </span>
            <div className="inline-flex space-x-2">
              <button 
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="flex items-center justify-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Previous
              </button>
              <button 
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="flex items-center justify-center px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
