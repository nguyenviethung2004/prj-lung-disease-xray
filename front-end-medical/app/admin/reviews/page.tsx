"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { getAuthUser, apiFetch } from "@/lib/api/auth";

export default function AdminReviewList() {
  const router = useRouter();
  const [reviews, setReviews] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedReview, setSelectedReview] = useState<any>(null);
  const pageSize = 5;

  // Filter States
  const [classes, setClasses] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [filters, setFilters] = useState({
    class_id: "",
    min_confidence: "",
    doctor_id: "",
    is_corrected: "",
    start_date: "",
    end_date: ""
  });

  const fetchMetadata = async () => {
    try {
      const [classesData, doctorsData] = await Promise.all([
        apiFetch("/inference/classes"),
        apiFetch("/auth/admin/users?role=Doctors")
      ]);
      setClasses(classesData);
      setDoctors(doctorsData);
    } catch (error) {
      console.error("Error loading metadata:", error);
    }
  };

  const fetchReviews = async (page: number) => {
    setIsLoading(true);
    try {
      let url = `/reviews/list?page=${page}&page_size=${pageSize}`;
      if (filters.class_id) url += `&class_id=${filters.class_id}`;
      if (filters.min_confidence) url += `&min_confidence=${filters.min_confidence}`;
      if (filters.doctor_id) url += `&doctor_id=${filters.doctor_id}`;
      if (filters.is_corrected !== "") url += `&is_corrected=${filters.is_corrected}`;
      if (filters.start_date) url += `&start_date=${filters.start_date}`;
      if (filters.end_date) url += `&end_date=${filters.end_date}`;

      const data = await apiFetch(url);
      setReviews(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error("Error loading review list:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Check auth once and load metadata on mount
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

    fetchMetadata();
  }, [router]);

  // Fetch reviews whenever page or filters change
  useEffect(() => {
    const user = getAuthUser();
    if (!user || user.role !== "Superadmin") return;

    fetchReviews(currentPage);
  }, [currentPage, filters]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
    setCurrentPage(1); // Reset to page 1 on filter change
  };

  const resetFilters = () => {
    setFilters({
      class_id: "",
      min_confidence: "",
      doctor_id: "",
      is_corrected: "",
      start_date: "",
      end_date: ""
    });
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Quality Monitoring</h1>
          <p className="text-sm text-gray-500 mt-1">Analyze prediction results and expert evaluations</p>
        </div>
        <button
          onClick={() => fetchReviews(currentPage)}
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
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Doctor's Final Diagnosis</label>
            <select
              name="class_id"
              value={filters.class_id}
              onChange={handleFilterChange}
              className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="">All Diseases</option>
              {classes.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">AI Confidence</label>
            <select
              name="min_confidence"
              value={filters.min_confidence}
              onChange={handleFilterChange}
              className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="">All Levels</option>
              <option value="50">&gt; 50%</option>
              <option value="70">&gt; 70%</option>
              <option value="90">&gt; 90%</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Doctor Review</label>
            <select
              name="doctor_id"
              value={filters.doctor_id}
              onChange={handleFilterChange}
              className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="">All Doctors</option>
              {doctors.map(d => (
                <option key={d.UserID} value={d.UserID}>{d.UserName}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Status</label>
            <select
              name="is_corrected"
              value={filters.is_corrected}
              onChange={handleFilterChange}
              className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="">All</option>
              <option value="false">Correct</option>
              <option value="true">Corrected</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">From Date</label>
            <input
              type="date"
              name="start_date"
              value={filters.start_date}
              onChange={handleFilterChange}
              className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">To Date</label>
            <div className="flex gap-2">
              <input
                type="date"
                name="end_date"
                value={filters.end_date}
                onChange={handleFilterChange}
                className="w-full h-10 px-3 rounded-lg border border-gray-200 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all flex-1"
              />
              <button
                onClick={resetFilters}
                className="h-10 w-10 flex items-center justify-center rounded-lg border border-red-100 bg-red-50 text-red-600 hover:bg-red-500 hover:text-white hover:scale-110 active:scale-95 transition-all shadow-sm"
                title="Clear Filters"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Image</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Patient Code</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">AI Prediction</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Confidence</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Doctor Final</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Approver</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                [1, 2, 3, 4, 5].map((i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="w-12 h-12 bg-gray-200 rounded"></div></td>
                    <td className="px-6 py-4"><div className="h-4 w-16 bg-gray-100 rounded"></div></td>
                    <td className="px-6 py-4"><div className="h-4 w-20 bg-gray-100 rounded"></div></td>
                    <td className="px-6 py-4"><div className="h-4 w-12 bg-gray-100 rounded"></div></td>
                    <td className="px-6 py-4"><div className="h-4 w-20 bg-gray-100 rounded"></div></td>
                    <td className="px-6 py-4"><div className="h-6 w-16 bg-gray-100 rounded-full"></div></td>
                    <td className="px-6 py-4"><div className="h-4 w-24 bg-gray-100 rounded"></div></td>
                    <td className="px-6 py-4"><div className="h-4 w-24 bg-gray-100 rounded"></div></td>
                  </tr>
                ))
              ) : reviews.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-20 text-center">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="text-gray-300"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                      <p className="text-gray-500 font-medium">No matching data found with the current filters.</p>
                      <button onClick={resetFilters} className="text-indigo-600 text-sm font-bold hover:underline">Clear All Filters</button>
                    </div>
                  </td>
                </tr>
              ) : (
                reviews.map((review) => (
                  <tr
                    key={review.id}
                    className="hover:bg-indigo-50/30 transition-colors cursor-pointer group"
                    onClick={() => setSelectedReview(review)}
                  >
                    <td className="px-6 py-4">
                      <div className="w-12 h-12 rounded overflow-hidden border border-gray-100 bg-gray-100 shadow-sm group relative">
                        <img
                          src={(() => {
                            let p = review.image_path || "";
                            if (p.startsWith('http')) return p;
                            if (p.startsWith('backend/')) p = p.substring(8);
                            if (p.startsWith('/backend/')) p = p.substring(9);
                            if (p.startsWith('/')) p = p.substring(1);
                            return `http://localhost:8000/${p}`;
                          })()}
                          alt="X-ray"
                          className="w-full h-full object-cover opacity-85 group-hover:opacity-100 transition-opacity"
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-bold text-gray-950 text-sm">
                        {review.patient_code}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-gray-100 text-gray-700 border border-gray-200">
                        {review.ai_predicted}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 w-16 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${review.confidence > 80 ? 'bg-green-500' : review.confidence > 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${review.confidence}%` }}
                          ></div>
                        </div>
                        <span className="text-[11px] font-bold text-gray-500">{review.confidence.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold ${review.is_corrected ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-600 border border-green-100'
                        }`}>
                        {review.doctor_final}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {review.is_corrected ? (
                        <span className="flex items-center gap-1.5 text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded-md border border-orange-100 w-fit">
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"></path></svg>
                          Corrected
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-md border border-green-100 w-fit">
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          Accurate
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-[10px] font-bold text-indigo-700 border border-indigo-200">
                          {review.doctor_name?.substring(0, 2).toUpperCase()}
                        </div>
                        <span className="text-sm text-gray-700 font-semibold">{review.doctor_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                      <div className="font-medium text-gray-900">{new Date(review.reviewed_at).toLocaleDateString('vi-VN')}</div>
                      <div className="text-[10px] text-gray-400 font-bold">{new Date(review.reviewed_at).toLocaleTimeString('vi-VN')}</div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {!isLoading && total > 0 && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <div className="text-xs text-gray-500 font-medium">
              Showing <span className="font-bold">{(currentPage - 1) * pageSize + 1}</span> - <span className="font-bold">{Math.min(currentPage * pageSize, total)}</span> / <span className="font-bold">{total}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:border-indigo-400 hover:text-indigo-600 disabled:opacity-50 transition-all hover:scale-110 active:scale-90 shadow-sm"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
              </button>

              <div className="flex items-center gap-1.5">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum = i + 1;
                  if (totalPages > 5 && currentPage > 3) {
                    pageNum = currentPage - 2 + i;
                    if (pageNum + (4 - i) > totalPages) pageNum = totalPages - 4 + i;
                  }
                  if (pageNum <= 0) pageNum = i + 1;
                  if (pageNum > totalPages) return null;

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`w-8 h-8 rounded-lg text-xs font-black transition-all hover:scale-110 active:scale-90 ${currentPage === pageNum
                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200 ring-2 ring-indigo-600 ring-offset-2'
                        : 'bg-white border border-gray-200 text-gray-500 hover:border-indigo-400 hover:text-indigo-600 shadow-sm'
                        }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:border-indigo-400 hover:text-indigo-600 disabled:opacity-50 transition-all hover:scale-110 active:scale-90 shadow-sm"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400 font-medium px-2">
        <p className="flex items-center gap-1.5">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          Only Superadmins have access to this admin panel.
        </p>
        <p>Total Records: <span className="text-gray-600 font-bold">{total}</span></p>
      </div>

      {/* Review Detail Modal */}
      {selectedReview && (
        <div className="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
          <div
            className="bg-white w-full max-w-5xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 slide-in-from-bottom-4 duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-8 py-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-2xl ${selectedReview.is_corrected ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}>
                  {selectedReview.is_corrected ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"></path></svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  )}
                </div>
                <div>
                  <h2 className="text-xl font-black text-gray-900">Review Details #{selectedReview.id}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 rounded bg-indigo-50 border border-indigo-100 text-[10px] font-bold text-indigo-700">
                      Mã BN: {selectedReview.patient_code}
                    </span>
                    <span className="text-xs font-medium text-gray-300">|</span>
                    <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">{selectedReview.filename}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedReview(null)}
                className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-all"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Left Side: Images */}
                <div className="lg:col-span-8 space-y-6">
                  <div className={`grid gap-4 ${selectedReview.doctor_final === 'Pneumonia' ? 'grid-cols-2' : 'grid-cols-1'}`}>
                    {/* Original Image */}
                    <div className="space-y-2">
                      <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest text-center">Original Image (Input)</p>
                      <div className="aspect-square bg-black rounded-2xl overflow-hidden border border-gray-200 shadow-inner group relative">
                        <img
                          src={(() => {
                            let p = selectedReview.image_path || "";
                            if (p.startsWith('http')) return p;
                            if (p.startsWith('backend/')) p = p.substring(8);
                            if (p.startsWith('/backend/')) p = p.substring(9);
                            if (p.startsWith('/')) p = p.substring(1);
                            return `http://localhost:8000/${p}`;
                          })()}
                          className="w-full h-full object-cover relative z-20"
                          alt="Original X-ray"
                          onError={(e) => {
                            console.error("Lỗi tải ảnh gốc:", e.currentTarget.src);
                          }}
                        />
                      </div>
                    </div>

                    {/* Annotation Image (Only for Pneumonia) */}
                    {selectedReview.doctor_final === 'Pneumonia' && (
                      <div className="space-y-2">
                        <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest text-center">Doctor Review (Bounding Boxes)</p>
                        <div className="aspect-square bg-black rounded-2xl overflow-hidden border border-blue-100 shadow-inner relative group">
                          <AnnotationCanvas
                            imagePath={selectedReview.image_path}
                            boxesJson={selectedReview.bounding_boxes}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Note Section */}
                  {selectedReview.note && (
                    <div className="p-6 bg-indigo-50/50 rounded-2xl border border-indigo-100/50">
                      <h4 className="text-xs font-black text-indigo-600 uppercase tracking-widest mb-2 flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                        Doctor's Notes
                      </h4>
                      <p className="text-sm text-gray-700 italic leading-relaxed">"{selectedReview.note}"</p>
                    </div>
                  )}
                </div>

                {/* Right Side: Stats & Info */}
                <div className="lg:col-span-4 space-y-6">
                  {/* Status Badge */}
                  <div className={`p-4 rounded-2xl border-2 flex flex-col items-center gap-2 text-center ${selectedReview.is_corrected ? 'border-rose-100 bg-rose-50/30' : 'border-emerald-100 bg-emerald-50/30'}`}>
                    <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${selectedReview.is_corrected ? 'text-rose-500' : 'text-emerald-500'}`}>Status</span>
                    <span className={`text-xl font-black ${selectedReview.is_corrected ? 'text-rose-700' : 'text-emerald-700'}`}>
                      {selectedReview.is_corrected ? 'Corrected' : 'Accurate'}
                    </span>
                  </div>

                  {/* Comparisons */}
                  <div className="space-y-3">
                    <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                      <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">AI Prediction</p>
                      <div className="flex items-center justify-between">
                        <span className="font-black text-gray-700">{selectedReview.ai_predicted}</span>
                        <span className="text-sm font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-lg border border-blue-100">{selectedReview.confidence.toFixed(1)}%</span>
                      </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-gray-900 border border-gray-800 shadow-xl">
                      <p className="text-[10px] font-bold text-gray-500 uppercase mb-1">Doctor's Conclusion</p>
                      <div className="flex items-center justify-between">
                        <span className="font-black text-white text-lg">{selectedReview.doctor_final}</span>
                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="pt-6 border-t border-gray-100 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-sm font-black text-indigo-700 border border-indigo-200">
                        {selectedReview.doctor_name?.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase">Doctor</p>
                        <p className="text-sm font-black text-gray-900">{selectedReview.doctor_name}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 border border-gray-200">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase">Review Date and Time</p>
                        <p className="text-sm font-black text-gray-900">
                          {new Date(selectedReview.reviewed_at).toLocaleDateString('vi-VN')} {new Date(selectedReview.reviewed_at).toLocaleTimeString('vi-VN')}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component for rendering the image with bounding boxes
function AnnotationCanvas({ imagePath, boxesJson }: { imagePath: string, boxesJson: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    const baseUrl = "http://localhost:8000";

    let p = imagePath || "";
    if (!p.startsWith('http')) {
      if (p.startsWith('backend/')) p = p.substring(8);
      if (p.startsWith('/backend/')) p = p.substring(9);
      if (p.startsWith('/')) p = p.substring(1);
      p = `${baseUrl}/${p}`;
    }

    console.log("Đang tải ảnh lên Canvas từ:", p);

    img.src = p;
    img.onload = () => {
      console.log("Ảnh đã tải xong, bắt đầu vẽ lên Canvas...");
      // Set canvas size to match its container's displayed size
      const container = canvas.parentElement;
      if (!container) return;

      const displayWidth = container.clientWidth;
      const displayHeight = container.clientHeight;

      canvas.width = displayWidth;
      canvas.height = displayHeight;

      // 1. Draw the image to fill the canvas
      ctx.drawImage(img, 0, 0, displayWidth, displayHeight);

      // 2. Draw boxes only if data is available
      if (boxesJson) {
        try {
          const boxes = JSON.parse(boxesJson);
          if (Array.isArray(boxes) && boxes.length > 0) {
            const ratioX = displayWidth / img.naturalWidth;
            const ratioY = displayHeight / img.naturalHeight;

            boxes.forEach((box) => {
              // Convert natural coordinates to display coordinates
              const x1 = box.x1 * ratioX;
              const y1 = box.y1 * ratioY;
              const x2 = box.x2 * ratioX;
              const y2 = box.y2 * ratioY;
              const w = x2 - x1;
              const h = y2 - y1;

              // Draw Bounding Box (Blue)
              ctx.strokeStyle = "#3b82f6";
              ctx.lineWidth = 3;
              ctx.strokeRect(x1, y1, w, h);

              // Draw Label Background
              ctx.fillStyle = "#3b82f6";
              const labelY = y1 > 25 ? y1 - 25 : y1;
              ctx.fillRect(x1, labelY, 90, 25);

              // Draw Label Text
              ctx.fillStyle = "white";
              ctx.font = "bold 12px sans-serif";
              ctx.fillText("Pneumonia", x1 + 8, labelY + 17);

              // Optional: Add a subtle glow/shadow to the box
              ctx.shadowBlur = 10;
              ctx.shadowColor = "rgba(59, 130, 246, 0.5)";
              ctx.strokeRect(x1, y1, w, h);
              ctx.shadowBlur = 0;
            });
          }
        } catch (e) {
          console.error("Lỗi khi vẽ Bounding Boxes:", e);
        }
      }
    };

    img.onerror = () => {
      console.error("KHÔNG THỂ TẢI ẢNH TỪ PATH:", img.src);
    };
  }, [imagePath, boxesJson]);

  return <canvas ref={canvasRef} className="w-full h-full object-contain" />;
}
