"use client";

import React, { useEffect, useRef } from "react";

export type Message = {
  id: string;
  role: "user" | "bot";
  text: string;
  timestamp: string;
};

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-4 py-8 flex flex-col gap-8 scroll-smooth scrollbar-thin scrollbar-thumb-gray-200"
      style={{
        background: "linear-gradient(to bottom, #ffffff 0%, #f8faff 100%)",
      }}
    >
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-12 animate-in fade-in zoom-in duration-700">
          <div className="relative mb-6">
            <div className="absolute inset-0 bg-blue-400 blur-2xl opacity-20 animate-pulse"></div>
            <div className="relative w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl flex items-center justify-center shadow-xl shadow-blue-200">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="36"
                height="36"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
          </div>
          <h3 className="text-xl font-bold text-gray-900 tracking-tight">AI Assistant Sẵn Sàng</h3>
          <p className="text-sm text-gray-500 max-w-[240px] mt-3 leading-relaxed">
            Ask me about image analysis, medical conditions, or prescriptions.
          </p>
        </div>
      ) : (
        messages.map((msg, index) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in slide-in-from-bottom-4 duration-500`}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className={`flex gap-4 max-w-[88%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              {/* Avatar */}
              <div
                className={`w-9 h-9 rounded-2xl flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-md transition-transform hover:scale-110 ${
                  msg.role === "user"
                    ? "bg-gradient-to-br from-blue-600 to-indigo-700 text-white"
                    : "bg-white border border-gray-100 text-blue-600"
                }`}
              >
                {msg.role === "user" ? "U" : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                )}
              </div>
              
              {/* Message Content */}
              <div className="flex flex-col gap-1.5">
                <div
                  className={`relative px-5 py-3.5 text-[14px] leading-relaxed shadow-sm transition-all ${
                    msg.role === "user"
                      ? "bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-none shadow-blue-100"
                      : "bg-white/80 backdrop-blur-md text-gray-800 border border-white rounded-2xl rounded-tl-none shadow-gray-100"
                  }`}
                >
                  {msg.text}
                </div>
                <div className={`text-[10px] font-medium opacity-40 px-1 ${msg.role === "user" ? "text-right" : "text-left"}`}>
                   {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          </div>
        ))
      )}

      {isLoading && (
        <div className="flex justify-start animate-in fade-in duration-300">
          <div className="flex gap-4 items-center">
            <div className="w-9 h-9 rounded-2xl bg-white border border-gray-50 flex items-center justify-center shadow-sm">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0.2s] mx-1"></div>
                <div className="w-2 h-2 bg-blue-200 rounded-full animate-bounce [animation-delay:0.4s]"></div>
            </div>
            <div className="bg-white/50 backdrop-blur-sm rounded-2xl rounded-tl-none px-5 py-3 text-[13px] text-gray-400 font-medium border border-white/50 italic">
                AI đang suy nghĩ...
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
