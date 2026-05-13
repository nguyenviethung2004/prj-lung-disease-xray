"use client";

import React, { useState } from "react";

interface ContextPreviewProps {
  imageName?: string;
  annotationsCount: number;
  onClear: () => void;
  useAnnotations: boolean;
  setUseAnnotations: (val: boolean) => void;
}

export default function ContextPreview({
  imageName,
  annotationsCount,
  onClear,
  useAnnotations,
  setUseAnnotations,
}: ContextPreviewProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!imageName && annotationsCount === 0) return null;

  return (
    <div className="mx-4 mb-2 bg-gray-50 border border-gray-200 rounded-xl overflow-hidden shadow-sm transition-all duration-200">
      <div 
        className="flex items-center justify-between px-3 py-2 bg-gray-100/50 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <div className="p-1 bg-blue-100 rounded text-blue-600">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
          </div>
          <span className="text-xs font-semibold text-gray-700">RAG Context</span>
          {annotationsCount > 0 && (
             <span className="px-1.5 py-0.5 bg-blue-600 text-white text-[10px] font-bold rounded-full">
               {annotationsCount}
             </span>
          )}
        </div>
        <div className="flex items-center gap-2">
           <button 
             onClick={(e) => { e.stopPropagation(); onClear(); }}
             className="text-gray-400 hover:text-red-500 transition-colors p-1"
             title="Clear context"
           >
             <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>
           </button>
           <button className="text-gray-400 transition-transform">
             <svg 
               className={`transform transition-transform ${isCollapsed ? "-rotate-90" : "rotate-0"}`}
               xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
             >
               <polyline points="6 9 12 15 18 9"></polyline>
             </svg>
           </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="p-3 bg-white border-t border-gray-100 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-[11px] text-gray-600">
                <span className="font-medium text-gray-400">Current Image:</span>
                <span className="truncate max-w-[150px]" title={imageName}>{imageName || "None"}</span>
            </div>
            <label className="flex items-center gap-1.5 cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={useAnnotations} 
                  onChange={(e) => setUseAnnotations(e.target.checked)}
                  className="w-3.5 h-3.5 accent-blue-600 rounded cursor-pointer"
                />
                <span className="text-[11px] text-gray-500 select-none">Include Boxes</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
