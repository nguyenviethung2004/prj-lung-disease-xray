"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/context/ToastContext";
import { getAuthUser, apiFetch } from "@/lib/api/auth";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

// Initial state is empty
const INITIAL_DOCS: any[] = [];

export default function DocumentManagementPage() {
  const router = useRouter();
  const [docs, setDocs] = useState(INITIAL_DOCS);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [currentDoc, setCurrentDoc] = useState<any>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { showToast } = useToast();

  const [isApproveDialogOpen, setIsApproveDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [docToProcess, setDocToProcess] = useState<number | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  useEffect(() => {
    const user = getAuthUser();
    if (!user) {
      router.push("/login");
      return;
    }

    if (user.role !== "Superadmin") {
      router.push("/dashboard");
      return;
    }

    fetchDocuments();
  }, [router]);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch("/documents/");
      setDocs(data || []);
    } catch (error: any) {
      showToast(error.message || "Failed to load document list", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const fileInputRef = useState<any>(null); // We'll use a direct ref or just the event

  const filteredDocs = docs.filter(doc =>
    (doc.Description || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.FileName || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.UploaderName || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalPages = Math.ceil(filteredDocs.length / itemsPerPage);
  const paginatedDocs = filteredDocs.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Reset to page 1 when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const handleDelete = async (id: number) => {
    setDocToProcess(id);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!docToProcess) return;
    try {
      await apiFetch(`/documents/${docToProcess}`, { method: "DELETE" });
      setDocs(docs.filter(d => d.DocumentID !== docToProcess));
      showToast("Document deleted successfully!");
    } catch (error: any) {
      showToast(error.message || "Failed to delete document", "error");
    } finally {
      setIsDeleteDialogOpen(false);
      setDocToProcess(null);
    }
  };

  const handleDownload = async (id: number, filename: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/documents/admin/${id}/download`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`
        }
      });

      if (!response.ok) throw new Error("Failed to download document");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      showToast(error.message || "Failed to download document", "error");
    }
  };

  const handleApprove = (id: number) => {
    setDocToProcess(id);
    setIsApproveDialogOpen(true);
  };

  const startPolling = (docId: number, fileName: string) => {
    console.log(`[Polling] Started for Doc ${docId}: ${fileName}`);
    const interval = setInterval(async () => {
      try {
        // Add timestamp to avoid browser cache
        const data = await apiFetch(`/documents/?_t=${Date.now()}`);
        const updatedDoc = data.find((d: any) => d.DocumentID == docId);
        
        console.log(`[Polling] Doc ${docId} status: ${updatedDoc?.Status}`);
        
        if (updatedDoc) {
          // Luôn cập nhật state để sync UI (ví dụ nếu có doc khác thay đổi)
          setDocs(data || []);

          if (updatedDoc.Status === 'Done') {
            showToast(`Document "${fileName}" processing finished!`, "success");
            clearInterval(interval);
          } else if (updatedDoc.Status === 'Error') {
            showToast(`Document "${fileName}" processing failed!`, "error");
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error("Polling error:", err);
        clearInterval(interval);
      }
    }, 3000); // Check every 3s
    
    // Auto-clear after 5 minutes
    setTimeout(() => {
      clearInterval(interval);
      console.log(`[Polling] Auto-stopped for Doc ${docId}`);
    }, 300000);
  };

  const confirmApprove = async () => {
    if (!docToProcess) return;
    
    // Find filename for the toast
    const doc = docs.find(d => d.DocumentID === docToProcess);
    const fileName = doc?.FileName || "Document";

    setIsSubmitting(true);
    try {
      await apiFetch(`/documents/admin/${docToProcess}/process`, { method: "POST" });

      setIsApproveDialogOpen(false);
      showToast(`Approval successful! "${fileName}" is being processed in background.`, "info");

      // Update local state immediately so button disappears
      setDocs(prev => prev.map(d => 
        d.DocumentID === docToProcess ? { ...d, Status: 'Processing' } : d
      ));

      // Start polling for "Done" status
      startPolling(docToProcess, fileName);
      
      setDocToProcess(null);
    } catch (error: any) {
      showToast(error.message || "Failed to approve document", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditClick = (doc: any) => {
    setCurrentDoc(doc);
    setNewTitle(doc.Description || "");
    setIsEditOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const updated = await apiFetch(`/documents/${currentDoc.DocumentID}`, {
        method: "PATCH",
        body: JSON.stringify({ Description: newTitle })
      });

      setDocs(docs.map(d => d.DocumentID === currentDoc.DocumentID ? {
        ...d,
        Description: updated.Description
      } : d));

      setIsEditOpen(false);
      showToast("Information updated successfully!");
    } catch (error: any) {
      showToast(error.message || "Failed to update document", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      // Automatically set title if empty
      if (!newTitle) {
        setNewTitle(file.name.split('.').slice(0, -1).join('.'));
      }
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      showToast("Vui lòng chọn một tập tin!", "error");
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("description", newTitle || selectedFile.name);

      await apiFetch("/documents/admin/upload", {
        method: "POST",
        body: formData,
      });

      await fetchDocuments(); // Refresh list
      setIsUploadOpen(false);
      setNewTitle("");
      setSelectedFile(null);
      showToast("Document uploaded successfully!");
    } catch (error: any) {
      showToast(error.message || "Failed to upload document", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFileIcon = (type: string) => {
    if (type === "pdf") {
      return (
        <div className="p-2 bg-red-50 text-red-600 rounded-lg">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15h3a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H9v-3z"></path><path d="M17 12V15a1 1 0 0 1-1 1h-2"></path><path d="M3 13h2"></path></svg>
        </div>
      );
    }
    return (
      <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M8 13h2"></path><path d="M8 17h2"></path><path d="M14 13h2"></path><path d="M14 17h2"></path></svg>
      </div>
    );
  };

  return (
    <div className="space-y-6 relative pb-10">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Management</h1>
          <p className="text-sm text-gray-500 mt-1">Upload and manage medical documents (PDF, DOCX) for RAG</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDocuments}
            disabled={isLoading}
            className="p-3 bg-white text-indigo-600 rounded-2xl border border-gray-100 shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.2)] transition-all hover:scale-110 active:scale-95 group flex items-center justify-center"
            title="Refresh"
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2.5" 
              strokeLinecap="round" 
              strokeLinejoin="round"
              className={`transition-transform duration-500 ${isLoading ? 'animate-spin' : 'group-hover:rotate-180'}`}
            >
              <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path>
              <polyline points="21 3 21 8 16 8"></polyline>
            </svg>
          </button>
          <button
            onClick={() => { setIsUploadOpen(true); setNewTitle(""); }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-bold text-sm transition-all shadow-lg shadow-blue-100 flex items-center gap-2 max-w-max active:scale-95"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            Upload Document
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Total Documents</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{docs.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Processed</p>
          <p className="text-2xl font-bold text-emerald-600 mt-1">{docs.filter(d => d.Status === "Done").length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Storage Used</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            {docs.reduce((acc, d) => acc + (d.FileSizeMB || 0), 0).toFixed(1)} MB
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative w-full">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        </div>
        <input
          type="text"
          className="block w-full p-3 pl-10 text-sm text-gray-900 border border-gray-200 rounded-xl bg-white focus:ring-blue-500 focus:border-blue-500 outline-none transition-all shadow-sm"
          placeholder="Search documents by name or file..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-gray-600">
            <thead className="text-[11px] text-gray-400 uppercase bg-gray-50/50 border-b border-gray-100">
              <tr>
                <th scope="col" className="px-6 py-4 font-bold tracking-wider">Document</th>
                <th scope="col" className="px-6 py-4 font-bold tracking-wider">Uploader</th>
                <th scope="col" className="px-6 py-4 font-bold tracking-wider">Size</th>
                <th scope="col" className="px-6 py-4 font-bold tracking-wider">Upload Date</th>
                <th scope="col" className="px-6 py-4 font-bold tracking-wider">Status</th>
                <th scope="col" className="px-6 py-4 font-bold tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    <div className="flex flex-col items-center gap-3">
                      <svg className="animate-spin h-8 w-8 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span className="text-sm font-medium">Loading documents...</span>
                    </div>
                  </td>
                </tr>
              ) : paginatedDocs.length > 0 ? (
                paginatedDocs.map((doc) => (
                  <tr key={doc.DocumentID} className="bg-white hover:bg-gray-50/50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-4">
                        {getFileIcon(doc.FileType?.toLowerCase() || "pdf")}
                        <div className="flex flex-col min-w-0">
                          <span className="font-bold text-gray-900 truncate" title={doc.Description}>{doc.Description}</span>
                          <span className="text-[11px] text-gray-400 truncate">{doc.FileName}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center text-[10px] font-bold text-blue-600 border border-blue-100">
                          {doc.UploaderName?.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium text-gray-700">{doc.UploaderName}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 font-medium">
                      {doc.FileSizeMB?.toFixed(2)} MB
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 font-medium">
                      {new Date(doc.UploadedAt).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`
                        flex items-center gap-1.5 w-fit px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider 
                        ${doc.Status === "Done" ? "bg-emerald-50 text-emerald-600 border border-emerald-100" : 
                          doc.Status === "Processing" ? "bg-amber-50 text-amber-600 border border-amber-100" : 
                          "bg-blue-50 text-blue-600 border border-blue-100"}
                      `}>
                        {doc.Status === "Processing" && (
                          <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        )}
                        {doc.Status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button 
                          onClick={() => handleDownload(doc.DocumentID, doc.FileName)} 
                          className="p-2.5 text-emerald-600 bg-emerald-50 hover:bg-emerald-100 border border-emerald-100 rounded-xl transition-all active:scale-95 shadow-sm" 
                          title="Download Document"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        </button>
                        {doc.Status === "Pending" && (
                          <button 
                            onClick={() => handleApprove(doc.DocumentID)} 
                            className="p-2.5 text-orange-600 bg-orange-50 hover:bg-orange-100 border border-orange-100 rounded-xl transition-all active:scale-95 shadow-sm" 
                            title="Approve & Chunk"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                          </button>
                        )}
                        <button 
                          onClick={() => handleEditClick(doc)} 
                          className="p-2.5 text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-100 rounded-xl transition-all active:scale-95 shadow-sm" 
                          title="Edit Document"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                        </button>
                        <button 
                          onClick={() => handleDelete(doc.DocumentID)} 
                          className="p-2.5 text-red-500 bg-red-50 hover:bg-red-100 border border-red-100 rounded-xl transition-all active:scale-95 shadow-sm" 
                          title="Delete Document"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400 italic">
                    No matching documents found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination UI */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50/30">
            <div className="text-[13px] text-gray-500 font-medium">
              Showing <span className="text-gray-900 font-bold">{((currentPage - 1) * itemsPerPage) + 1}</span> to <span className="text-gray-900 font-bold">{Math.min(currentPage * itemsPerPage, filteredDocs.length)}</span> of <span className="text-gray-900 font-bold">{filteredDocs.length}</span> documents
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
              </button>

              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`min-w-[36px] h-9 rounded-lg text-sm font-bold transition-all active:scale-95 ${currentPage === page
                        ? "bg-blue-600 text-white shadow-md shadow-blue-100"
                        : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                      }`}
                  >
                    {page}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-5 border-b border-gray-50 flex justify-between items-center">
              <h3 className="font-bold text-[17px] text-gray-900">Upload New Document</h3>
              <button onClick={() => setIsUploadOpen(false)} className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-all">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="p-6 space-y-6">
              <div
                onClick={() => document.getElementById('file-upload-input')?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center gap-3 transition-all cursor-pointer group ${selectedFile ? 'border-blue-400 bg-blue-50/30' : 'border-gray-200 bg-gray-50/50 hover:bg-blue-50 hover:border-blue-200'
                  }`}
              >
                <div className={`w-12 h-12 bg-white rounded-2xl shadow-sm flex items-center justify-center transition-transform ${selectedFile ? 'text-blue-500 scale-110' : 'text-blue-600 group-hover:scale-110'}`}>
                  {selectedFile ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                  )}
                </div>
                <div className="text-center">
                  <p className="text-sm font-bold text-gray-900">
                    {selectedFile ? selectedFile.name : "Select PDF or DOCX file to upload"}
                  </p>
                  <p className="text-[11px] text-gray-400 mt-1">
                    {selectedFile ? formatFileSize(selectedFile.size) : "Maximum file size is 10MB"}
                  </p>
                </div>
                <input
                  id="file-upload-input"
                  type="file"
                  className="sr-only"
                  accept=".pdf,.docx,.doc"
                  onChange={handleFileChange}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-bold text-gray-700 ml-1">Document Title</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-3 text-sm focus:bg-white focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition-all placeholder:text-gray-300"
                  placeholder="Enter document title or name..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setIsUploadOpen(false)} className="flex-1 py-3 text-sm font-bold text-gray-500 hover:bg-gray-50 rounded-xl transition-all">Hủy</button>
                <button type="submit" disabled={isSubmitting} className="flex-[2] py-3 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-100 transition-all flex items-center justify-center gap-2">
                  {isSubmitting ? (
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : "Bắt đầu tải lên"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-5 border-b border-gray-50 flex justify-between items-center">
              <h3 className="font-bold text-[17px] text-gray-900">Edit Document Information</h3>
              <button onClick={() => setIsEditOpen(false)} className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-all">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
            <form onSubmit={handleEditSubmit} className="p-6 space-y-6">
              <div className="space-y-1.5">
                <label className="text-[13px] font-bold text-gray-700 ml-1">Document Title</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-3 text-sm focus:bg-white focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition-all"
                  required
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setIsEditOpen(false)} className="flex-1 py-3 text-sm font-bold text-gray-500 hover:bg-gray-50 rounded-xl transition-all">Hủy</button>
                <button type="submit" disabled={isSubmitting} className="flex-[2] py-3 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-100 transition-all flex items-center justify-center">
                  {isSubmitting ? "Saving..." : "Save changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialogs */}
      <ConfirmDialog
        isOpen={isApproveDialogOpen}
        title="Approve Document"
        message="Are you sure you want to approve and start the processing (chunking) for this document?"
        confirmLabel="Approve & Chunk"
        cancelLabel="Cancel"
        onConfirm={confirmApprove}
        onCancel={() => setIsApproveDialogOpen(false)}
        isSubmitting={isSubmitting}
      />

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Delete Document"
        message="This action will permanently delete the document from the system. Are you sure you want to proceed?"
        confirmLabel="Delete Permanently"
        cancelLabel="Cancel"
        onConfirm={confirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
        isDanger={true}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
