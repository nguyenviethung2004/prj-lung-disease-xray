"use client";

import React, { useState } from "react";

interface PromptInputProps {
  onSendMessage: (text: string) => void;
  onFileUpload: (file: File) => void;
  selectedFiles?: File[];
  onRemoveFile?: (index: number) => void;
  disabled?: boolean;
  suggestions?: string[];
}

export default function PromptInput({
  onSendMessage,
  onFileUpload,
  selectedFiles = [],
  onRemoveFile,
  disabled,
  suggestions = [],
}: PromptInputProps) {
  const [inputValue, setInputValue] = useState("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== "application/pdf") {
        alert("Chỉ chấp nhận file PDF.");
        return;
      }
      // Kiểm tra trùng file
      if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
        alert("File này đã được chọn.");
        return;
      }
      onFileUpload(file);
      // Reset giá trị để có thể chọn lại cùng một file sau khi xóa
      e.target.value = "";
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || disabled) return;
    onSendMessage(inputValue);
    setInputValue("");
  };

  const handleSuggestionClick = (suggestion: string) => {
    onSendMessage(suggestion);
  };

  return (
    <div className="px-4 pb-6 bg-white flex flex-col gap-3">
      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-1">
          {suggestions.map((suggestion, idx) => (
            <button
              key={idx}
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={disabled}
              className="text-[11px] font-medium text-blue-600 bg-blue-50/50 hover:bg-blue-100/70 border border-blue-100 px-3 py-1.5 rounded-full transition-all disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="flex flex-col w-full bg-white border border-gray-200 rounded-[24px] shadow-[0_2px_12px_rgba(0,0,0,0.04)] focus-within:border-blue-400 focus-within:shadow-[0_2px_20px_rgba(59,130,246,0.08)] transition-all duration-200 overflow-hidden">

        {/* Selected Files Badges */}
        {selectedFiles.length > 0 && (
          <div className="px-4 pt-3 flex flex-wrap items-center gap-2">
            {selectedFiles.map((file, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-blue-50 border border-blue-100 text-blue-700 px-3 py-1.5 rounded-xl text-xs font-semibold animate-in zoom-in-95 duration-200">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                <span className="truncate max-w-[120px]">{file.name}</span>
                <button 
                  onClick={() => onRemoveFile?.(idx)}
                  className="ml-1 p-0.5 hover:bg-blue-200 rounded-full transition-colors"
                  title="Gỡ file"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                </button>
              </div>
            ))}
            <div className="text-[10px] text-emerald-600 font-bold uppercase tracking-wider opacity-80 flex items-center gap-1 ml-1">
               <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
               {selectedFiles.length} File sẵn sàng
            </div>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="relative flex items-center"
        >
          {/* Upload Button */}
          <div className="pl-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="w-10 h-10 rounded-full flex items-center justify-center text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-all active:scale-90"
              title="Upload PDF để phân tích"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.51a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>
            </button>
          </div>

          <textarea
            rows={1}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={selectedFiles.length > 0 ? "Ask about the selected documents..." : "Ask about diseases, medications ..."}
            className="w-full text-[14px] bg-transparent border-none focus:ring-0 resize-none py-4 pl-1 pr-14 min-h-[56px] max-h-[200px] text-gray-800 placeholder-gray-400 leading-relaxed outline-none"
            disabled={disabled}
          />
          <div className="absolute right-2 bottom-2">
            <button
              type="submit"
              disabled={!inputValue.trim() || disabled}
              className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${!inputValue.trim() || disabled
                  ? "bg-gray-100 text-gray-300 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700 shadow-md active:scale-95"
                }`}
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
              >
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </div>
        </form>
      </div>
      <div className="text-[11px] text-center text-gray-400 mt-1">
        AI can make mistakes. Please double-check important medical information.
      </div>
    </div>
  );
}
