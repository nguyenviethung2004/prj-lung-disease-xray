"use client";

import React, { useState, useEffect } from "react";

export type ChatSession = {
  id: string;
  title: string;
  messages: any[];
  createdAt: string;
};

interface ChatHistoryProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
}

export default function ChatHistory({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
}: ChatHistoryProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-100 w-full shadow-inner">
      <div className="p-5 border-b border-gray-50 flex flex-col gap-4">
        <h3 className="text-[13px] font-bold text-gray-400 uppercase tracking-[0.1em]">Lịch sử Chat</h3>
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2.5 px-4 rounded-xl text-[13px] font-bold transition-all shadow-lg shadow-blue-100 active:scale-95"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          Hội thoại mới
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1.5 scrollbar-thin scrollbar-thumb-gray-200 hover:scrollbar-thumb-gray-300 transition-colors">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 px-4 text-center opacity-40">
             <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
             </div>
             <p className="text-[12px] font-medium text-gray-500">Chưa có lịch sử trò chuyện</p>
          </div>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={`w-full text-left px-4 py-3.5 rounded-2xl transition-all group relative overflow-hidden ${
                currentSessionId === session.id
                  ? "bg-blue-50 text-blue-700 shadow-sm"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {currentSessionId === session.id && (
                 <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-blue-600 rounded-full"></div>
              )}
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 p-1 rounded-md ${currentSessionId === session.id ? 'bg-blue-100' : 'bg-gray-100 group-hover:bg-white'}`}>
                   <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-[13px] truncate font-semibold ${currentSessionId === session.id ? 'text-blue-700' : 'text-gray-700'}`}>
                    {session.title}
                  </div>
                  <div className="text-[10px] text-gray-400 mt-0.5 font-medium">
                    {mounted ? new Date(session.createdAt).toLocaleDateString('vi-VN', { 
                      day: '2-digit', 
                      month: '2-digit',
                      year: 'numeric' 
                    }) : ""}
                  </div>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
