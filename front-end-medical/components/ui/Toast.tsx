"use client";

import React from "react";
import { ToastType, useToast, TOAST_DURATION } from "@/context/ToastContext";

const typeStyles: Record<ToastType, { bg: string; text: string; icon: React.ReactNode; border: string; accent: string }> = {
  success: {
    bg: "bg-emerald-50/95",
    text: "text-emerald-900",
    border: "border-emerald-200",
    accent: "bg-emerald-500",
    icon: (
      <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
        <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    ),
  },
  error: {
    bg: "bg-rose-50/95",
    text: "text-rose-900",
    border: "border-rose-200",
    accent: "bg-rose-500",
    icon: (
      <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center">
        <svg className="w-5 h-5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    ),
  },
  warning: {
    bg: "bg-amber-50/95",
    text: "text-amber-900",
    border: "border-amber-200",
    accent: "bg-amber-500",
    icon: (
      <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
        <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
    ),
  },
  info: {
    bg: "bg-blue-50/95",
    text: "text-blue-900",
    border: "border-blue-200",
    accent: "bg-blue-500",
    icon: (
      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
        <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    ),
  },
};

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useToast();

  return (
    <>
      <style jsx global>{`
        @keyframes toast-progress {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
      <div className="fixed top-6 right-6 z-[9999] flex flex-col gap-4 pointer-events-none min-w-[360px] max-w-md">
        {toasts.map((toast) => {
          const style = typeStyles[toast.type];
          return (
            <div
              key={toast.id}
              className={`
                pointer-events-auto
                relative overflow-hidden
                flex items-center gap-4 px-5 py-4
                rounded-2xl border shadow-[0_10px_40px_-10px_rgba(0,0,0,0.1)] 
                backdrop-blur-xl
                animate-in fade-in slide-in-from-right-8 duration-500
                ${style.bg} ${style.border} ${style.text}
              `}
            >
              {/* Progress Bar */}
              <div 
                className={`absolute bottom-0 left-0 h-[3px] ${style.accent} opacity-40`}
                style={{ 
                  animation: `toast-progress ${TOAST_DURATION}ms linear forwards` 
                }}
              />

              <div className="flex-shrink-0">{style.icon}</div>
              <p className="text-sm font-bold flex-1 leading-relaxed">{toast.message}</p>
              <button
                onClick={() => removeToast(toast.id)}
                className="p-1.5 rounded-full hover:bg-black/5 text-gray-400 hover:text-gray-600 transition-all"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          );
        })}
      </div>
    </>
  );
};
