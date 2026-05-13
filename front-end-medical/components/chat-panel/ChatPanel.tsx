"use client";

import React, { useState, useEffect } from "react";
import ChatHistory, { ChatSession } from "./ChatHistory";
import MessageList, { Message } from "./MessageList";
import PromptInput from "./PromptInput";
import { chatApi } from "../../lib/api/chat";

interface ChatPanelProps {
  currentAnnotations: any[];
  currentImage?: { name: string; id: string };
  onClose: () => void;
}



export default function ChatPanel({
  currentAnnotations,
  currentImage,
  onClose,
}: ChatPanelProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [useAnnotations, setUseAnnotations] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [activeDocumentIds, setActiveDocumentIds] = useState<number[]>([]);

  // Load sessions from API on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await chatApi.getConversations();
      if (res && res.conversations) {
        const fetchedSessions = res.conversations.map((c: any) => ({
          id: c.conversation_id.toString(),
          title: c.title || "New Chat",
          messages: [], // messages loaded on demand
          createdAt: new Date().toISOString(),
        }));
        setSessions(fetchedSessions);
      }
    } catch (error) {
      console.error("Error loading sessions", error);
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleSelectSession = async (id: string) => {
    setCurrentSessionId(id);
    setMessages([]);
    setIsLoading(true);
    try {
      const res = await chatApi.getHistory(id);
      if (res && res.messages) {
        const loadedMessages = res.messages.map((m: any, i: number) => ({
          id: m.message_id?.toString() || `msg-${i}-${Date.now()}`,
          role: m.role === "assistant" ? "bot" : "user",
          text: m.text,
          timestamp: m.timestamp || new Date().toISOString(),
        }));
        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error("Error loading history", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (text: string) => {
    const newUserMessage: Message = {
      id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role: "user",
      text,
      timestamp: new Date().toISOString(),
    };

    const newMessages = [...messages, newUserMessage];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      // Collect context
      const annotationContext = useAnnotations && currentAnnotations.length > 0
        ? ` Image contains ${currentAnnotations.length} annotations: ${currentAnnotations.map(a => a.label).join(", ")}.`
        : "";

      const promptContext = `${annotationContext} ${text}`;
      const title = !currentSessionId ? text.substring(0, 30) : undefined;

      const res = await chatApi.sendMessage(promptContext, currentSessionId, title, activeDocumentIds);

      if (res && res.response) {
        const botReply: Message = {
          id: `bot-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          role: "bot",
          text: res.response,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, botReply]);

        if (!currentSessionId && res.conversation_id) {
          setCurrentSessionId(res.conversation_id.toString());
          loadSessions(); // Reload the list to show new chat
        }
      }
    } catch (error: any) {
      console.error("Chat error:", error);
      const errorReply: Message = {
        id: (Date.now() + 1).toString(),
        role: "bot",
        text: `Error: ${error.message || "Failed to communicate with the server."}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorReply]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearContext = () => {
    setUseAnnotations(false);
  };

  const handleFileUpload = async (file: File) => {
    if (!currentSessionId) {
      // Nếu chưa có session, tạo session mới trước khi upload
      try {
        const res = await chatApi.createConversation(file.name);
        if (res && res.conversation_id) {
          const newId = res.conversation_id.toString();
          setCurrentSessionId(newId);
          await performUpload(newId, file);
          loadSessions();
        }
      } catch (err) {
        console.error("Lỗi tạo conversation cho upload:", err);
      }
    } else {
      await performUpload(currentSessionId, file);
    }
  };

  const performUpload = async (convId: string, file: File) => {
    setSelectedFiles(prev => [...prev, file]);
    setIsLoading(true);
    try {
      const res = await chatApi.uploadChatFile(convId, file);
      if (res && res.document_id) {
        setActiveDocumentIds(prev => [...prev, res.document_id]);
        // Thông báo cho người dùng
        const systemMsg: Message = {
          id: `sys-${Date.now()}`,
          role: "bot",
          text: `Đã thêm tài liệu: **${file.name}** vào ngữ cảnh chat. Bạn có thể đặt câu hỏi về tài liệu này và các tài liệu khác đã chọn.`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, systemMsg]);
      }
    } catch (err) {
      console.error("Lỗi upload file:", err);
      setSelectedFiles(prev => prev.filter(f => f !== file));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    setActiveDocumentIds(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex h-full w-full bg-[#fcfdfe] relative overflow-hidden font-sans">
      {/* Side History Drawer (Overlay) */}
      {showHistory && (
        <div className="absolute inset-0 z-30 flex animate-in fade-in duration-300">
          <div className="w-80 h-full shadow-2xl relative z-40 animate-in slide-in-from-left duration-500 ease-out">
            <ChatHistory
              sessions={sessions}
              currentSessionId={currentSessionId}
              onSelectSession={(id) => {
                handleSelectSession(id);
                setShowHistory(false);
              }}
              onNewChat={() => {
                handleNewChat();
                setShowHistory(false);
              }}
            />
            {/* Close History button */}
            <button
              onClick={() => setShowHistory(false)}
              className="absolute top-5 -right-4 w-9 h-9 bg-white border border-gray-100 rounded-full flex items-center justify-center shadow-xl text-gray-400 hover:text-blue-600 hover:scale-110 active:scale-95 transition-all z-50 group"
              title="Đóng lịch sử"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="group-hover:-translate-x-0.5 transition-transform"><path d="m15 18-6-6 6-6" /></svg>
            </button>
          </div>
          <div
            className="flex-1 bg-blue-900/10 backdrop-blur-[3px] transition-opacity"
            onClick={() => setShowHistory(false)}
          ></div>
        </div>
      )}

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* Background Decorative Element */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-50 rounded-full blur-3xl opacity-30 -mr-32 -mt-32 pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-indigo-50 rounded-full blur-3xl opacity-30 -ml-32 -mb-32 pointer-events-none"></div>

        {/* Header */}
        <header className="px-6 py-4 border-b border-gray-100 flex flex-col gap-4 bg-white/70 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-200 ring-2 ring-white">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /><path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" /></svg>
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full"></span>
              </div>
              <div>
                <h2 className="text-[16px] font-extrabold text-gray-900 tracking-tight leading-none">Medical AI</h2>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest opacity-80">System is ready</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className={`p-2.5 rounded-2xl transition-all active:scale-90 border ${showHistory ? 'text-blue-600 bg-blue-50 border-blue-100 shadow-sm' : 'text-gray-500 hover:text-blue-600 hover:bg-gray-50 border-transparent'}`}
                title="Lịch sử trò chuyện"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
              </button>

              <button
                onClick={handleNewChat}
                className="p-2.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all active:scale-90"
                title="Chat mới"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"></path><path d="M12 5v14"></path></svg>
              </button>

              <button
                onClick={onClose}
                className="p-2.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-2xl transition-all active:scale-90"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>
              </button>
            </div>
          </div>
        </header>

        {/* Messages Space */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <MessageList messages={messages} isLoading={isLoading} />
        </div>

        {/* Footer Context & Input */}
        <footer className="bg-white/90 backdrop-blur-md border-t border-gray-50 pb-2">
          <div className="max-w-4xl mx-auto">
            <PromptInput
              onSendMessage={handleSendMessage}
              onFileUpload={handleFileUpload}
              selectedFiles={selectedFiles}
              onRemoveFile={handleRemoveFile}
              disabled={isLoading}
            />
            {/* <div className="px-6 py-2 text-center">
              <p className="text-[10px] text-gray-400 font-medium">AI có thể đưa ra câu trả lời không chính xác. Hãy kiểm tra lại thông tin y tế.</p>
            </div> */}
          </div>
        </footer>
      </div>
    </div>
  );
}
