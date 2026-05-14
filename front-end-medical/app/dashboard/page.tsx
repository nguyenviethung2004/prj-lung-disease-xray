"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ChatPanel from "@/components/chat-panel/ChatPanel";
import { getAuthUser, logout, apiFetch } from "@/lib/api/auth";
import { useToast } from "@/context/ToastContext";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

type Annotation = {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  label: string;
};

type ImageInfo = {
  id: string;
  name: string;
  width: number;
  height: number;
};

export default function DashboardPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [user, setUser] = useState<any>(null);


  useEffect(() => {
    const authUser = getAuthUser();
    if (!authUser) {
      router.push("/login");
      return;
    }

    // Role check: Only Doctors can access dashboard (per user request)
    if (authUser.role !== "Doctors") {
      if (authUser.role === "Superadmin") {
        router.push("/admin");
      } else {
        router.push("/login");
      }
      return;
    }

    if (authUser.must_change_password) {
      router.push("/change-password");
      return;
    }

    setUser(authUser);
  }, [router]);

  const [images, setImages] = useState<File[]>([]);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [analyzedUrl, setAnalyzedUrl] = useState<string | null>(null);

  const [imageInfo, setImageInfo] = useState<ImageInfo | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [currentBox, setCurrentBox] = useState<Partial<Annotation> | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState("");
  const [confidenceScore, setConfidenceScore] = useState<number | null>(null);
  const [predictionId, setPredictionId] = useState<number | null>(null);
  const [aiInitialLabel, setAiInitialLabel] = useState<string>("");
  const [zoom, setZoom] = useState(1);

  // Chatbot State
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatTopic, setChatTopic] = useState<"disease" | "medicine">("disease");
  const [chatInput, setChatInput] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isReviewed, setIsReviewed] = useState(false);
  const [chatMessages, setChatMessages] = useState<{ role: "user" | "bot"; text: string }[]>([
    { role: "bot", text: "Hello! How can I help you with your annotations today?" }
  ]);

  // Document Management State
  const [isDocModalOpen, setIsDocModalOpen] = useState(false);
  const [myDocs, setMyDocs] = useState<any[]>([]);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [submittingDocId, setSubmittingDocId] = useState<number | null>(null);
  const [docDescription, setDocDescription] = useState("");
  const [selectedPDF, setSelectedPDF] = useState<File | null>(null);
  const docInputRef = useRef<HTMLInputElement>(null);

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<number | null>(null);
  
  // Pending Images State
  const [pendingImages, setPendingImages] = useState<any[]>([]);
  const [isPendingModalOpen, setIsPendingModalOpen] = useState(false);
  const [isRefreshingPending, setIsRefreshingPending] = useState(false);

  const fetchPendingImages = async () => {
    setIsRefreshingPending(true);
    try {
      const data = await apiFetch("/inference/doctor/pending-images");
      setPendingImages(data || []);
    } catch (error) {
      console.error("Lỗi khi tải danh sách ca chờ:", error);
    } finally {
      setIsRefreshingPending(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchPendingImages();
      fetchMyDocs(); // Fetch documents to show badge
    }
  }, [user]);

  const handleSelectPendingImage = (item: any) => {
    // Load the selected pending image into the dashboard
    const baseUrl = "http://localhost:8000";
    
    const cleanPath = (p: string) => {
      if (!p) return "";
      if (p.startsWith('http')) return p;
      let path = p;
      if (path.startsWith('backend/')) path = path.substring(8);
      if (path.startsWith('/backend/')) path = path.substring(9);
      if (path.startsWith('/')) path = path.substring(1);
      return `${baseUrl}/${path}`;
    };
    
    setSourceUrl(cleanPath(item.image_path));
    setAnalyzedUrl(cleanPath(item.heatmap_path));
    setPredictionId(item.prediction_id);
    setConfidenceScore(item.confidence);
    setAiInitialLabel(item.ai_label);
    setSelectedLabel(item.ai_label);
    
    // Load AI boxes if present in the pending item
    if (item.ai_boxes) {
      try {
        const parsedBoxes = JSON.parse(item.ai_boxes);
        if (Array.isArray(parsedBoxes) && parsedBoxes.length > 0) {
          const aiAnnotations = parsedBoxes.map((b: any, index: number) => ({
            id: `ai-${Date.now()}-${index}-${Math.floor(Math.random() * 1000)}`,
            x1: Math.round(b.bbox[0]),
            y1: Math.round(b.bbox[1]),
            x2: Math.round(b.bbox[2]),
            y2: Math.round(b.bbox[3]),
            label: "Pneumonia"
          }));
          setAnnotations(aiAnnotations);
        } else {
          setAnnotations([]);
        }
      } catch (e) {
        console.error("Error parsing AI boxes:", e);
        setAnnotations([]);
      }
    } else {
      setAnnotations([]);
    }

    setIsReviewed(false);
    setIsPendingModalOpen(false);
    showToast(`Pending case loaded: ${item.filename}. Please verify the labels and click "Save results" to complete the process.`);
  };

  // Dynamic Label Mapping from DB
  const [dbClasses, setDbClasses] = useState<{id: number, name: string}[]>([]);

  useEffect(() => {
    const fetchClasses = async () => {
      try {
        const data = await apiFetch("/inference/classes");
        setDbClasses(data);
      } catch (error) {
        console.error("Lỗi khi tải danh sách nhãn:", error);
      }
    };
    fetchClasses();
  }, []);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      setImages(selectedFiles);
      const newUrl = URL.createObjectURL(selectedFiles[0]);
      setSourceUrl(newUrl);
      setAnalyzedUrl(null); // Clear the right side
      // Reset for new image
      setAnnotations([]);
      setImageInfo(null);
      setIsAnalyzing(false);
      setConfidenceScore(null);
      setPredictionId(null);
      setAiInitialLabel("");
      setZoom(1);
      setSelectedLabel("");
      setIsReviewed(false);
      fetchPendingImages();
    }
  };

  const handleSourceImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    if (images.length > 0) {
      setImageInfo({
        id: Date.now().toString(),
        name: images[0].name,
        width: naturalWidth,
        height: naturalHeight,
      });
    }
  };

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    if (images.length > 0) {
      setImageInfo({
        id: Date.now().toString(),
        name: images[0].name,
        width: naturalWidth,
        height: naturalHeight,
      });
    }
    resizeCanvas();
  };

  const handleAnalyzeImage = async () => {
    if (images.length === 0 || !imageInfo) return;
    const file = images[0];

    setIsAnalyzing(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const data = await apiFetch("/inference/predict", {
        method: "POST",
        body: formData,
        isFormData: true,
      });

      if (data.success) {
        // Sử dụng lại result_image vì backend đã trả về ảnh full-size 
        // có chứa heatmap (nếu là COVID) và tọa độ bbox đã được map về ảnh gốc.
        const resultUrl = `data:image/jpeg;base64,${data.result_image}`;
        setAnalyzedUrl(resultUrl);

        // Auto-select the label returned by the model
        if (data.label) {
          setSelectedLabel(data.label);
          setAiInitialLabel(data.label);
        }

        if (data.confidence !== undefined) {
          setConfidenceScore(data.confidence);
        }

        if (data.prediction_id) {
          setPredictionId(data.prediction_id);
        }

        // Auto-load AI boxes into annotations state with more robust mapping
        if (data.boxes && Array.isArray(data.boxes) && data.boxes.length > 0) {
          const aiAnnotations = data.boxes.map((b: any, index: number) => ({
            id: `ai-${Date.now()}-${index}-${Math.floor(Math.random() * 1000)}`,
            x1: Math.round(b.bbox[0]),
            y1: Math.round(b.bbox[1]),
            x2: Math.round(b.bbox[2]),
            y2: Math.round(b.bbox[3]),
            label: "Pneumonia"
          }));
          setAnnotations(aiAnnotations);
          console.log("Loaded AI Annotations:", aiAnnotations);
          showToast(`The AI has detected ${aiAnnotations.length} lesion regions.`, "info");
        } else {
          setAnnotations([]);
          if (data.label === "Pneumonia") {
            showToast("AI không tìm thấy vùng tổn thương cụ thể mặc dù dự đoán là Pneumonia.", "warning");
          }
        }
        
        // Refresh pending reviews count/list
        fetchPendingImages();
      } else {
        showToast(data.message || "Lỗi khi xử lý ảnh", "error");
      }
    } catch (error: any) {
      console.error("Lỗi khi tải dự đoán từ Model:", error);
      showToast(error.message || "Đã xảy ra lỗi khi kết nối đến server AI.", "error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resizeCanvas = () => {
    if (canvasRef.current && imageRef.current) {
      canvasRef.current.width = imageRef.current.clientWidth;
      canvasRef.current.height = imageRef.current.clientHeight;
      drawAnnotations();
    }
  };

  useEffect(() => {
    window.addEventListener("resize", resizeCanvas);
    return () => window.removeEventListener("resize", resizeCanvas);
  }, [annotations, currentBox]);

  useEffect(() => {
    drawAnnotations();
  }, [annotations, currentBox, imageInfo]);

  const toNatural = (displayX: number, displayY: number) => {
    if (!imageRef.current || !imageInfo) return { x: 0, y: 0 };
    const ratioX = imageInfo.width / imageRef.current.width;
    const ratioY = imageInfo.height / imageRef.current.height;
    return {
      x: Math.round(displayX * ratioX),
      y: Math.round(displayY * ratioY),
    };
  };

  const toDisplay = (naturalX: number, naturalY: number) => {
    if (!imageRef.current || !imageInfo) return { x: 0, y: 0 };
    const ratioX = imageRef.current.width / imageInfo.width;
    const ratioY = imageRef.current.height / imageInfo.height;
    return {
      x: naturalX * ratioX,
      y: naturalY * ratioY,
    };
  };

  const getMousePos = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / zoom,
      y: (e.clientY - rect.top) / zoom,
    };
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isReviewed) return;
    if (selectedLabel !== "Pneumonia") {
      showToast("Bounding boxes can only be drawn for pneumonia diagnosis (Pneumonia).", "info");
      return;
    }
    const pos = getMousePos(e);
    const naturalPos = toNatural(pos.x, pos.y);
    setIsDrawing(true);
    setCurrentBox({
      id: Date.now().toString(),
      x1: naturalPos.x,
      y1: naturalPos.y,
      x2: naturalPos.x,
      y2: naturalPos.y,
      label: selectedLabel,
    });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !currentBox) return;
    const pos = getMousePos(e);
    const naturalPos = toNatural(pos.x, pos.y);
    setCurrentBox((prev) =>
      prev
        ? {
          ...prev,
          x2: naturalPos.x,
          y2: naturalPos.y,
        }
        : null
    );
  };

  const handleMouseUp = () => {
    if (isDrawing && currentBox) {
      const newBox = {
        ...currentBox,
        x1: Math.min(currentBox.x1!, currentBox.x2!),
        y1: Math.min(currentBox.y1!, currentBox.y2!),
        x2: Math.max(currentBox.x1!, currentBox.x2!),
        y2: Math.max(currentBox.y1!, currentBox.y2!),
      } as Annotation;

      // Save if area is big enough (prevent accidental clicks)
      if (newBox.x2 - newBox.x1 > 5 && newBox.y2 - newBox.y1 > 5) {
        setAnnotations((prev) => [...prev, newBox]);
      }
    }
    setIsDrawing(false);
    setCurrentBox(null);
  };

  const drawAnnotations = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw saved annotations
    annotations.forEach((box) => {
      const p1 = toDisplay(box.x1, box.y1);
      const p2 = toDisplay(box.x2, box.y2);

      ctx.strokeStyle = "#3b82f6"; // blue
      ctx.lineWidth = 2;
      ctx.strokeRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);

      // Label background (optional)
      const text = box.label;
      ctx.font = "12px sans-serif";
      const textWidth = ctx.measureText(text).width;
      ctx.fillStyle = "#3b82f6";
      ctx.fillRect(p1.x, p1.y > 20 ? p1.y - 18 : p1.y + 2, textWidth + 8, 18);

      // Label text
      ctx.fillStyle = "white";
      ctx.fillText(text, p1.x + 4, p1.y > 20 ? p1.y - 5 : p1.y + 15);
    });

    // Draw drawing box
    if (isDrawing && currentBox) {
      const p1 = toDisplay(currentBox.x1!, currentBox.y1!);
      const p2 = toDisplay(currentBox.x2!, currentBox.y2!);

      ctx.strokeStyle = "#10b981"; // green
      ctx.setLineDash([5, 5]);
      ctx.lineWidth = 2;
      ctx.strokeRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);
      ctx.setLineDash([]);
    }
  };

  const removeAnnotation = (id: string) => {
    setAnnotations((prev) => prev.filter((a) => a.id !== id));
  };

  const handleSaveReview = async () => {
    if (!predictionId || !user || !selectedLabel) {
      showToast("Vui lòng phân tích ảnh trước khi lưu kết quả.", "warning");
      return;
    }

    // Find label ID from dynamically fetched DB classes
    const classObj = dbClasses.find(c => c.name.trim() === selectedLabel.trim());
    const finalClassId = classObj?.id;

    if (!finalClassId) {
      showToast("Nhãn không hợp lệ hoặc chưa tải được danh sách nhãn từ server", "error");
      return;
    }

    // MANDATORY: If Pneumonia, must have at least one bounding box
    if (selectedLabel.trim() === "Pneumonia" && annotations.length === 0) {
      showToast("Vui lòng khoanh vùng tổn thương (vẽ box) trên ảnh cho chẩn đoán Viêm phổi (Pneumonia).", "warning");
      return;
    }

    const isCorrected = selectedLabel.trim() !== aiInitialLabel.trim();

    setIsExporting(true);

    try {
      const payload = {
        PredictionID: predictionId,
        DoctorID: user.id || user.UserID,
        FinalClassID: finalClassId,
        DoctorNote: "Doctor reviewed and confirmed/corrected label.",
        IsCorrected: isCorrected,
        BoundingBoxes: annotations.length > 0 ? JSON.stringify(annotations) : null
      };

      await apiFetch("/reviews/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      showToast("Evaluation results saved successfully!");
      setIsReviewed(true);
      fetchPendingImages(); // Refresh the pending list
    } catch (error: any) {
      console.error("Error saving review results:", error);
  showToast(error.message || "An error occurred while saving the results.", "error");
    } finally {
      setIsExporting(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMessage = chatInput;
    setChatMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setChatInput("");

    try {
      // --- CÁCH GỌI API THẬT CHO HÔM SAU ---
      // const response = await fetch("http://localhost:8000/api/chat", {
      //   method: "POST",
      //   headers: {
      //     "Content-Type": "application/json",
      //   },
      //   body: JSON.stringify({
      //     message: userMessage,
      //     topic: chatTopic 
      //   }),
      // });
      // const data = await response.json();
      // const botReply = data.reply;
      // -------------------------------------

      // --- MOCK DATA GIẢ CHO HÔM NAY ---
      const MOCK_DELAY = 1000;
      const mockResponse: any = await new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            reply: chatTopic === "disease"
              ? `Bác sĩ AI (Bệnh học): Đây là câu trả lời mô phỏng cho câu hỏi "${userMessage}"`
              : `Dược sĩ AI (Thuốc): Đây là câu trả lời mô phỏng cho câu hỏi "${userMessage}"`
          });
        }, MOCK_DELAY);
      });
      const botReply = mockResponse.reply;

      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: botReply },
      ]);
    } catch (error) {
      console.error("Error calling Chatbot API:", error);
      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: "Xin lỗi, đã có lỗi kết nối đến server AI." },
      ]);
    }
  };

  // Document Management Functions
  const fetchMyDocs = async () => {
    try {
      const data = await apiFetch("/documents/doctor/me");
      setMyDocs(data);
    } catch (error) {
      console.error("Lỗi khi tải danh sách tài liệu:", error);
    }
  };

  useEffect(() => {
    if (isDocModalOpen) {
      fetchMyDocs();
    }
  }, [isDocModalOpen]);

  const handleDocUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Chỉ hỗ trợ định dạng PDF");
      return;
    }
    setSelectedPDF(file);
  };

  const performUpload = async () => {
    if (!selectedPDF) {
      alert("Vui lòng chọn file trước");
      return;
    }

    setIsUploadingDoc(true);
    const formData = new FormData();
    formData.append("file", selectedPDF);
    formData.append("description", docDescription || "Tài liệu y khoa");

    try {
      await apiFetch("/documents/doctor/upload", {
        method: "POST",
        body: formData,
      });
      setDocDescription("");
      setSelectedPDF(null);
      if (docInputRef.current) docInputRef.current.value = "";
      showToast("Upload successful! The document is now in Pending status.");
      fetchMyDocs();
    } catch (error: any) {
      showToast(error.message || "Error occurred while uploading the document.", "error");
    } finally {
      setIsUploadingDoc(false);
    }
  };

  const handleSubmitToAdmin = async (docId: number) => {
    setSubmittingDocId(docId);
    try {
      await apiFetch(`/documents/doctor/${docId}/submit`, { method: "PATCH" });
      
      // Cập nhật trạng thái ngay lập tức trên UI (Optimistic Update)
      setMyDocs(prev => prev.map(doc => 
        doc.DocumentID === docId ? { ...doc, IsSubmitted: true, Status: 'Pending' } : doc
      ));

      showToast("Document has been submitted to the admin for review!");
      // Vẫn gọi fetch để đồng bộ dữ liệu chính xác từ server nhưng UI đã đổi rồi
      fetchMyDocs();
    } catch (error: any) {
      showToast(error.message || "Error occurred while submitting the document.", "error");
    } finally {
      setSubmittingDocId(null);
    }
  };

  const handleDeleteMyDoc = async (docId: number) => {
    setDocToDelete(docId);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;
    try {
      await apiFetch(`/documents/${docToDelete}`, { method: "DELETE" });
      showToast("Document deleted successfully!");
      fetchMyDocs();
    } catch (error: any) {
      showToast(error.message || "Error occurred while deleting the document.", "error");
    } finally {
      setIsDeleteDialogOpen(false);
      setDocToDelete(null);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-gray-50/50">
      {/* Top Navbar */}
      <header className="sticky top-0 z-10 w-full border-b border-gray-200 bg-white/75 backdrop-blur-md">
        <div className="flex h-16 items-center px-6">
          <div className="flex items-center gap-2 font-semibold tracking-tight text-gray-900 text-lg">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-black text-white">
              <span className="text-sm font-bold">M</span>
            </div>
            Medical Annotation Tool
          </div>

          <div className="ml-auto flex items-center space-x-5">
            {/* User Profile Info */}
            <div className="flex items-center gap-3 pl-4 border-l border-gray-100">
              <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center text-xs font-bold text-indigo-700 border border-indigo-200">
                {user ? user.username?.substring(0, 2).toUpperCase() || user.UserName?.substring(0, 2).toUpperCase() || "DR" : "..."}
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-gray-900 hidden sm:block leading-none">
                  {user ? user.username || user.UserName || "Doctor" : "Loading..."}
                </span>
                <span className="text-[10px] text-gray-500 font-medium hidden sm:block mt-1 uppercase tracking-tight">
                  {user?.role || "Medical Professional"}
                </span>
              </div>
            </div>

            <button
              onClick={() => setIsChatOpen(!isChatOpen)}
              className="inline-flex h-9 items-center justify-center rounded-md border border-gray-100 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-all hover:bg-gray-50 hover:border-indigo-100 hover:scale-105 active:scale-95 focus:outline-none shadow-sm group"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mr-2 text-indigo-600 transition-transform duration-500 group-hover:rotate-180"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              Chatbot AI
            </button>
            
            <button
              onClick={() => {
                setIsPendingModalOpen(true);
                fetchPendingImages();
              }}
              className="relative inline-flex h-9 items-center justify-center rounded-md border border-emerald-100 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition-all hover:bg-emerald-100 hover:border-emerald-200 hover:scale-105 active:scale-95 focus:outline-none shadow-sm group"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`mr-2 transition-transform duration-500 ${isRefreshingPending ? 'animate-spin' : 'group-hover:rotate-180'}`}
              >
                <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path>
                <polyline points="21 3 21 8 16 8"></polyline>
              </svg>
              Pending Review
              {pendingImages.length > 0 && (
                <span className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-white animate-bounce">
                  {pendingImages.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setIsDocModalOpen(true)}
              className="relative inline-flex h-9 items-center justify-center rounded-md border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 transition-all hover:bg-indigo-100 hover:border-indigo-200 hover:scale-105 active:scale-95 focus:outline-none shadow-sm group"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mr-2 transition-transform duration-500 group-hover:rotate-180"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              Upload Documents
              {myDocs.filter(d => !d.IsSubmitted).length > 0 && (
                <span className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white shadow-sm ring-2 ring-white animate-bounce">
                  {myDocs.filter(d => !d.IsSubmitted).length}
                </span>
              )}
            </button>
            <button
              onClick={handleLogout}
              className="inline-flex h-9 items-center justify-center rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-red-700 focus:outline-none shadow-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="flex-1 flex overflow-hidden">
        {/* Workspace - Left Side */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-[1400px] mx-auto">
            {/* Left column */}
            <div className="flex flex-col gap-6">
              {/* Image Upload box */}
              <div className={`rounded-xl border border-gray-200 bg-white shadow-sm flex flex-col items-center justify-center border-dashed border-2 ${sourceUrl ? "p-4" : "p-6"} h-[500px]`}>
                {!sourceUrl && (
                  <div className="flex flex-col items-center gap-3 text-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="32"
                      height="32"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="text-gray-400"
                    >
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                      <polyline points="17 8 12 3 7 8"></polyline>
                      <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                    <div className="space-y-1">
                      <label
                        htmlFor="image-upload"
                        className="relative cursor-pointer rounded-md bg-white font-medium text-blue-600 focus-within:outline-none focus-within:ring-2 focus-within:ring-blue-600 focus-within:ring-offset-2 hover:text-blue-500"
                      >
                        <span>Upload medical images</span>
                        <input
                          id="image-upload"
                          name="image-upload"
                          type="file"
                          className="sr-only"
                          onChange={handleImageUpload}
                          multiple
                          accept="image/*"
                        />
                      </label>
                      <p className="text-sm text-gray-500">
                        PNG, JPG, DICOM up to 10MB
                      </p>
                    </div>
                  </div>
                )}
                {sourceUrl && (
                  <div className="flex flex-col items-center gap-4 w-full flex-1 min-h-0">
                    <img
                      src={sourceUrl}
                      alt="Source Thumbnail"
                      onLoad={handleSourceImageLoad}
                      className="w-full h-full object-contain rounded-md bg-gray-50 flex-1 min-h-0"
                    />
                    <div className="flex items-center justify-between w-full px-2">
                      <div className="text-sm text-gray-600 truncate max-w-[60%]">
                        {images[0]?.name}
                      </div>
                      <label
                        htmlFor="image-upload-change"
                        className="cursor-pointer text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-full transition-colors shadow-sm"
                      >
                        Change Image
                        <input
                          id="image-upload-change"
                          type="file"
                          className="sr-only"
                          onChange={handleImageUpload}
                          accept="image/*"
                        />
                      </label>
                    </div>
                    <button
                      onClick={handleAnalyzeImage}
                      disabled={isAnalyzing || !imageInfo || !!analyzedUrl}
                      className="w-full bg-blue-600 text-white rounded-md py-2 px-4 shadow-sm hover:bg-blue-700 transition-colors font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-300 group-hover:rotate-12"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /><path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" /></svg>
                      {isAnalyzing ? "Analyzing..." : analyzedUrl ? "Đã phân tích" : "Phân tích bằng AI"}
                    </button>
                  </div>
                )}
              </div>

              {/* Annotation tools box */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm flex-1">

                <div className="grid grid-cols-2 gap-3 mb-6 flex-wrap">

                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-semibold text-sm text-gray-900 uppercase tracking-wider">HealthScan Result</h4>
                    {confidenceScore !== null && (
                      <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-full border border-blue-100 shadow-sm animate-pulse">
                        ĐÃ CÓ KẾT QUẢ AI
                      </span>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer group ${selectedLabel === "Normal" ? 'bg-green-50/50 border-green-200 shadow-sm' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'}`}>
                      <input
                        type="radio"
                        name="label"
                        value="Normal"
                        className="accent-green-600 w-4 h-4 cursor-pointer"
                        checked={selectedLabel === "Normal"}
                        onChange={(e) => {
                          const val = e.target.value;
                          setSelectedLabel(val);
                          setConfidenceScore(null);
                          if (val !== "Pneumonia") setAnnotations([]);
                        }}
                      />{" "}
                      <div className="flex-1 flex flex-col">
                        <span className={`text-[13px] font-medium transition-colors ${selectedLabel === "Normal" ? 'text-green-700' : 'text-gray-700'}`}>Normal</span>
                        {selectedLabel === "Normal" && confidenceScore !== null && (
                          <div className="mt-1 flex items-center gap-1.5 animate-in fade-in slide-in-from-left-1 duration-300">
                            <span className="text-[10px] font-semibold text-green-500 uppercase tracking-tight">Dự đoán AI</span>
                            <div className="flex-1 h-1.5 bg-green-100 rounded-full overflow-hidden">
                              <div className="h-full bg-green-600 rounded-full" style={{ width: `${Math.round(confidenceScore)}%` }}></div>
                            </div>
                            <span className="text-[11px] font-bold text-green-700">{Math.round(confidenceScore)}%</span>
                          </div>
                        )}
                      </div>
                    </label>
                    <label className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer group ${selectedLabel === "COVID-19" ? 'bg-blue-50/50 border-blue-200 shadow-sm' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'}`}>
                      <input
                        type="radio"
                        name="label"
                        value="COVID-19"
                        className="accent-blue-600 w-4 h-4 cursor-pointer"
                        checked={selectedLabel === "COVID-19"}
                        onChange={(e) => {
                          const val = e.target.value;
                          setSelectedLabel(val);
                          setConfidenceScore(null);
                          if (val !== "Pneumonia") setAnnotations([]);
                        }}
                      />{" "}
                      <div className="flex-1 flex flex-col">
                        <span className={`text-[13px] font-medium transition-colors ${selectedLabel === "COVID-19" ? 'text-blue-700' : 'text-gray-700'}`}>COVID-19</span>
                        {selectedLabel === "COVID-19" && confidenceScore !== null && (
                          <div className="mt-1 flex items-center gap-1.5 animate-in fade-in slide-in-from-left-1 duration-300">
                            <span className="text-[10px] font-semibold text-blue-500 uppercase tracking-tight">Dự đoán AI</span>
                            <div className="flex-1 h-1.5 bg-blue-100 rounded-full overflow-hidden">
                              <div className="h-full bg-blue-600 rounded-full" style={{ width: `${Math.round(confidenceScore)}%` }}></div>
                            </div>
                            <span className="text-[11px] font-bold text-blue-700">{Math.round(confidenceScore)}%</span>
                          </div>
                        )}
                      </div>
                    </label>
                    <label className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer group ${selectedLabel === "Pneumonia" ? 'bg-red-50/50 border-red-200 shadow-sm' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'}`}>
                      <input
                        type="radio"
                        name="label"
                        value="Pneumonia"
                        className="accent-red-600 w-4 h-4 cursor-pointer"
                        checked={selectedLabel === "Pneumonia"}
                        onChange={(e) => {
                          const val = e.target.value;
                          setSelectedLabel(val);
                          setConfidenceScore(null);
                          if (val !== "Pneumonia") setAnnotations([]);
                        }}
                      />{" "}
                      <div className="flex-1 flex flex-col">
                        <span className={`text-[13px] font-medium transition-colors ${selectedLabel === "Pneumonia" ? 'text-red-700' : 'text-gray-700'}`}>Pneumonia</span>
                        {selectedLabel === "Pneumonia" && confidenceScore !== null && (
                          <div className="mt-1 flex items-center gap-1.5 animate-in fade-in slide-in-from-left-1 duration-300">
                            <span className="text-[10px] font-semibold text-red-500 uppercase tracking-tight">Dự đoán AI</span>
                            <div className="flex-1 h-1.5 bg-red-100 rounded-full overflow-hidden">
                              <div className="h-full bg-red-600 rounded-full" style={{ width: `${Math.round(confidenceScore)}%` }}></div>
                            </div>
                            <span className="text-[11px] font-bold text-red-700">{Math.round(confidenceScore)}%</span>
                          </div>
                        )}
                      </div>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Right column */}
            <div className="flex flex-col gap-6 h-full">
              {/* Preview Image Component */}
              <div className="rounded-xl border border-gray-200 bg-white p-1 shadow-sm flex flex-col h-[500px] bg-gray-900 relative overflow-hidden">
                {analyzedUrl ? (
                  <div className="flex-1 overflow-auto flex items-center justify-center p-4 min-h-0 w-full relative">
                    <div
                      className="relative transition-transform duration-200 origin-center"
                      style={{ display: "inline-flex", transform: `scale(${zoom})` }}
                    >
                      <img
                        ref={imageRef}
                        src={analyzedUrl}
                        alt="Analyzed Preview"
                        onLoad={handleImageLoad}
                        className="max-w-full max-h-[440px] object-contain pointer-events-none block"
                        draggable={false}
                      />
                      <canvas
                        ref={canvasRef}
                        onMouseDown={handleMouseDown}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                        className="absolute top-0 left-0 cursor-crosshair touch-none"
                        style={{ width: "100%", height: "100%" }}
                      />
                    </div>

                    {/* Analyzing Overlay */}
                    {isAnalyzing && (
                      <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                        <div className="flex flex-col items-center text-white">
                          <svg className="animate-spin h-10 w-10 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="text-sm font-medium animate-pulse">Model is analyzing...</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-gray-500 flex flex-col items-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="48"
                      height="48"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="opacity-50"
                    >
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <circle cx="8.5" cy="8.5" r="1.5"></circle>
                      <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                    <p className="mt-2 text-sm">No image loaded</p>
                  </div>
                )}

                {/* Zoom Controls Bottom Bar */}
                {analyzedUrl && (
                  <div className="shrink-0 flex items-center justify-center bg-black/40 border-t border-white/10 p-2 gap-1 z-20">
                    <button onClick={() => setZoom(z => Math.max(0.5, z - 0.25))} className="p-1.5 text-white/90 hover:text-white hover:bg-white/20 rounded transition-colors" title="Zoom Out">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                    </button>
                    <div className="flex items-center px-2 text-xs font-medium text-white min-w-[3rem] justify-center select-none">
                      {Math.round(zoom * 100)}%
                    </div>
                    <button onClick={() => setZoom(z => Math.min(3, z + 0.25))} className="p-1.5 text-white/90 hover:text-white hover:bg-white/20 rounded transition-colors" title="Zoom In">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                    </button>
                    <div className="w-px bg-white/20 mx-2 h-4 my-auto"></div>
                    <button onClick={() => setZoom(1)} className="px-3 py-1 text-white/90 hover:text-white hover:bg-white/20 rounded text-xs font-medium transition-colors" title="Reset Zoom">
                      Reset
                    </button>
                  </div>
                )}
              </div>

              {/* Bounding box data list */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm min-h-[250px] flex flex-col">
                <h3 className="font-semibold text-lg flex items-center justify-between mb-4">
                  Saved Annotations
                  <span className="text-xs font-normal bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                    {annotations.length} boxes
                  </span>
                </h3>

                <div className="flex-1 border rounded-md border-gray-100 overflow-y-auto p-4 bg-gray-50/50 flex flex-col gap-2 max-h-[200px]">
                  {annotations.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-center">
                      <p className="text-sm text-gray-500">
                        No bounding box data yet.
                        <br />
                        Draw on the image to create annotations.
                      </p>
                    </div>
                  ) : (
                    <ul className="w-full space-y-2">
                      {annotations.map((box) => (
                        <li
                          key={box.id}
                          className="flex items-center justify-between p-2 bg-white border rounded text-sm hover:border-gray-300 transition-colors"
                        >
                          <span className="flex items-center gap-2 w-1/3 truncate">
                            <span className="w-3 h-3 rounded-full bg-blue-500 flex-shrink-0"></span>
                            <span className="font-medium truncate" title={box.label}>{box.label}</span>
                          </span>
                          <span className="text-gray-400 font-mono text-xs w-1/2 min-w-1/2">
                            [x:{box.x1}, y:{box.y1}, w:{box.x2 - box.x1}, h:{box.y2 - box.y1}]
                          </span>
                          <button
                            onClick={() => removeAnnotation(box.id)}
                            className="text-red-500 hover:text-red-700 p-1 flex-shrink-0"
                            title="Delete Annotation"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => setAnnotations([])}
                    className="flex-1 bg-red-600 text-white rounded-md py-2 text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                    disabled={annotations.length === 0 || isAnalyzing}
                  >
                    Delete All Boxes
                  </button>
                    <button
                      onClick={handleSaveReview}
                      disabled={!predictionId || isExporting || isReviewed || (selectedLabel === "Pneumonia" && annotations.length === 0)}
                      className={`flex-1 bg-indigo-600 text-white rounded-md py-2 text-sm font-bold hover:bg-indigo-700 transition-all disabled:opacity-50 disabled:bg-gray-400 disabled:cursor-not-allowed flex justify-center items-center gap-2 shadow-lg ${predictionId && !isReviewed && !(selectedLabel === "Pneumonia" && annotations.length === 0) ? 'shadow-indigo-200 ring-2 ring-indigo-500 ring-offset-2' : ''}`}
                    >
                      {isExporting ? (
                        <>
                          <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Saving results...
                        </>
                      ) : isReviewed ? (
                        "Results saved"
                      ) : (
                        "Save results"
                      )}
                    </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* AI Assistant Panel - Right Side */}
        {isChatOpen && (
          <aside className="w-[380px] h-[calc(100vh-64px)] border-l border-gray-200 bg-white sticky top-16 flex-shrink-0 animate-in slide-in-from-right duration-300">
            <ChatPanel
              currentAnnotations={annotations}
              currentImage={imageInfo ? { name: imageInfo.name, id: imageInfo.id } : undefined}
              onClose={() => setIsChatOpen(false)}
            />
          </aside>
        )}
      </main>

      {/* Document Management Modal */}
      {isDocModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden border border-gray-100">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
              <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-600"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                Medical Document Management
              </h3>
              <button onClick={() => setIsDocModalOpen(false)} className="text-gray-400 hover:text-gray-600 p-2 hover:bg-gray-100 rounded-full transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {/* Upload Section */}
              <div className="mb-8 p-5 bg-indigo-50/30 border border-indigo-100 rounded-xl">
                <h4 className="text-sm font-bold text-indigo-900 uppercase tracking-wider mb-4">Upload New Document</h4>
                <div className="space-y-4">
                  <input
                    type="text"
                    placeholder="Enter document name (required)"
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all outline-none text-sm font-medium"
                    value={docDescription}
                    onChange={(e) => setDocDescription(e.target.value)}
                  />
                  <div className="relative">
                    <input
                      type="file"
                      ref={docInputRef}
                      onChange={handleDocUpload}
                      accept=".pdf"
                      className="hidden"
                      id="doc-upload-input"
                      disabled={isUploadingDoc}
                    />
                    <label
                      htmlFor="doc-upload-input"
                      className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all ${selectedPDF ? 'bg-indigo-50 border-indigo-300' : 'bg-white border-indigo-200 hover:bg-indigo-50/50 hover:border-indigo-400'}`}
                    >
                      {selectedPDF ? (
                        <div className="flex flex-col items-center gap-2">
                          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-600"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15l2 2 4-4"></path></svg>
                          <p className="text-sm font-bold text-indigo-900">{selectedPDF.name}</p>
                          <button 
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              setSelectedPDF(null);
                              if (docInputRef.current) docInputRef.current.value = "";
                            }}
                            className="text-[10px] text-red-500 font-bold uppercase hover:underline"
                          >
                            Hủy chọn
                          </button>
                        </div>
                      ) : (
                        <>
                          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-500 mb-2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                          <p className="text-sm font-semibold text-indigo-900">Select PDF file</p>
                          <p className="text-xs text-gray-500 mt-1">Maximum file size: 16MB</p>
                        </>
                      )}
                    </label>
                  </div>
                  
                  <button
                    onClick={performUpload}
                    disabled={!selectedPDF || !docDescription.trim() || isUploadingDoc}
                    className="w-full bg-indigo-600 text-white rounded-xl py-3 font-bold shadow-md hover:bg-indigo-700 transition-all disabled:opacity-50 disabled:bg-gray-400 flex items-center justify-center gap-2"
                  >
                    {isUploadingDoc ? (
                      <>
                        <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Uploading...
                      </>
                    ) : (
                      "Confirm Upload"
                    )}
                  </button>
                </div>
              </div>

              {/* List Section */}
              <h4 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">Document uploaded</h4>
              <div className="space-y-3">
                {myDocs.length === 0 ? (
                  <div key="empty-docs" className="text-center py-10 text-gray-500 italic text-sm">
                    No documents uploaded yet.
                  </div>
                ) : (
                  myDocs.map((doc) => (
                    <div key={doc.DocumentID} className="flex items-center justify-between p-4 bg-white border border-gray-100 rounded-xl hover:shadow-sm transition-shadow group">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center text-red-600 flex-shrink-0">
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-gray-900 truncate">{doc.Description || "No title available"}</p>
                          <p className="text-[11px] text-gray-500 truncate italic">{doc.FileName}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-tighter ${doc.Status === 'Done' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                              {doc.Status}
                            </span>
                            <span className="text-[11px] text-gray-400 font-medium">
                              {new Date(doc.UploadedAt).toLocaleDateString('vi-VN')}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {!doc.IsSubmitted && (
                          <button
                            onClick={() => handleSubmitToAdmin(doc.DocumentID)}
                            disabled={submittingDocId === doc.DocumentID}
                            className="bg-indigo-600 text-white text-xs font-bold px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-70 flex items-center gap-2"
                          >
                            {submittingDocId === doc.DocumentID ? (
                              <>
                                <svg className="animate-spin h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span>Uploading...</span>
                              </>
                            ) : (
                              "Submit"
                            )}
                          </button>
                        )}
                        {doc.IsSubmitted && doc.Status === 'Pending' && (
                          <span className="text-[11px] font-bold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100">
                            Submitted
                          </span>
                        )}
                        {doc.Status === 'Done' && (
                          <span className="text-[11px] font-bold text-green-600 bg-green-50 px-3 py-1.5 rounded-lg border border-green-100">
                            Approved
                          </span>
                        )}
                        
                        <button
                          onClick={() => handleDeleteMyDoc(doc.DocumentID)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                          title="Delete Document"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 text-center">
              <p className="text-[11px] text-gray-500 font-medium">
                Documents will be added to the diagnostic support knowledge system after approval.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Xóa tài liệu"
        message="Bạn có chắc chắn muốn xóa tài liệu này? Hành động này không thể hoàn tác."
        confirmLabel="Xóa ngay"
        cancelLabel="Hủy bỏ"
        onConfirm={confirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
        isDanger={true}
      />
      {/* Review Pending Images Modal */}
      {isPendingModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-5 border-b border-gray-50 flex justify-between items-center bg-gray-50/50">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 text-emerald-600 rounded-xl">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                </div>
                <div>
                  <h3 className="font-bold text-lg text-gray-900">Review Queue</h3>
                  <p className="text-xs text-gray-500 font-medium">You have {pendingImages.length} cases pending review</p>
                </div>
              </div>
              <button onClick={() => setIsPendingModalOpen(false)} className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-all">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {pendingImages.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {pendingImages.map((item) => (
                    <div 
                      key={item.prediction_id}
                      onClick={() => handleSelectPendingImage(item)}
                      className="group flex gap-4 p-4 rounded-2xl border border-gray-100 bg-gray-50/30 hover:bg-white hover:border-emerald-200 hover:shadow-lg hover:shadow-emerald-500/5 transition-all cursor-pointer relative overflow-hidden"
                    >
                      <div className="w-24 h-24 rounded-xl overflow-hidden bg-gray-200 flex-shrink-0 border border-gray-100">
                        <img 
                          src={`http://127.0.0.1:8000/${item.image_path}`} 
                          alt="X-ray" 
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                        />
                      </div>
                      <div className="flex-1 flex flex-col justify-between py-1">
                        <div>
                          <h4 className="font-bold text-gray-900 text-sm truncate max-w-[200px]">{item.filename}</h4>
                          <p className="text-[10px] text-gray-400 mt-0.5 font-medium">{new Date(item.created_at).toLocaleString('vi-VN')}</p>
                        </div>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="px-2 py-0.5 rounded-md bg-white border border-gray-100 text-[10px] font-bold text-gray-600 shadow-sm">
                            AI: {item.ai_label}
                          </span>
                          <span className="text-[11px] font-black text-emerald-600">
                            {item.confidence.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-all translate-x-2 group-hover:translate-x-0">
                        <div className="p-2 bg-emerald-500 text-white rounded-full shadow-lg">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-gray-400 gap-4">
                  <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                  </div>
                  <p className="font-medium italic">Tuyệt vời! Bạn đã hoàn thành tất cả các ca cần review.</p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-50 bg-gray-50/30 flex justify-end">
              <button 
                onClick={() => setIsPendingModalOpen(false)}
                className="px-6 py-2.5 text-sm font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition-all"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
