import { apiFetch } from "./auth";

export const chatApi = {
  getConversations: async () => {
    return apiFetch("/chat/conversations", { method: "GET" });
  },

  createConversation: async (title: string) => {
    return apiFetch("/chat/conversations/new", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },

  getHistory: async (convId: number | string, limit = 20, offset = 0) => {
    return apiFetch(`/chat/conversations/${convId}/history?limit=${limit}&offset=${offset}`, {
      method: "GET",
    });
  },

  sendMessage: async (query_text: string, conversation_id?: number | string | null, title?: string, document_ids?: number[] | null) => {
    const payload: any = { query_text };
    if (conversation_id) payload.conversation_id = Number(conversation_id);
    if (title) payload.title = title;
    if (document_ids && document_ids.length > 0) payload.document_ids = document_ids;

    return apiFetch("/chat/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  uploadChatFile: async (convId: number | string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    return apiFetch(`/chat/conversations/${convId}/upload`, {
      method: "POST",
      body: formData, // apiFetch might need adjustment for FormData
      headers: {}, // Do not set Content-Type, browser will do it for FormData
    });
  },

  deleteDocumentChunks: async (docId: number) => {
    return apiFetch(`/chat/documents/${docId}/chunks`, {
      method: "DELETE",
    });
  },

  deleteConversation: async (convId: number | string) => {
    return apiFetch(`/chat/conversations/${convId}`, { method: "DELETE" });
  },
};
