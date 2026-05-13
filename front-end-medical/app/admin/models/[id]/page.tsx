"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

// Mock Data
const MOCK_MODEL_DETAIL = {
  id: "MDL-001",
  name: "YOLOv8-Medical",
  type: "Detection",
  version: "v1.2",
  created: "2026-03-12",
  acc: "89.5%",
  loss: "0.24",
  map: "85.2%",
  status: "Ready",
  dataset: "DS-002: MRI Brain Scans",
  config: {
    epochs: 50,
    batch_size: 16,
    learning_rate: 0.01,
    optimizer: "SGD",
    image_size: 512
  },
  history: [
    { version: "v1.2", dataset: "MRI Brain Scans", acc: "89.5%", map: "85.2%", date: "2026-03-12", note: "Fine-tuned with extra data" },
    { version: "v1.1", dataset: "MRI Scans v1", acc: "87.0%", map: "82.1%", date: "2026-02-20", note: "Changed optimizer to SGD" },
    { version: "v1.0", dataset: "Toy Medical", acc: "70.5%", map: "65.0%", date: "2026-01-05", note: "Initial prototype" },
  ],
  sampleImage: "https://placehold.co/600x400/1e293b/ffffff?text=Inference+Sample+Output"
};

export default function ModelDetailPage() {
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState<"overview" | "history">("overview");

  // Mock fetch
  const data = MOCK_MODEL_DETAIL;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4">
        <div className="flex items-center gap-4">
          <Link href="/admin/models" className="p-2 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors text-gray-600 bg-white shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              {data.name}
              <span className="text-sm font-medium bg-green-100 text-green-800 px-2.5 py-0.5 rounded-full">{data.status}</span>
            </h1>
            <p className="text-sm text-gray-500 mt-1 font-mono">Model ID: {id} | Ver {data.version}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link href={`/admin/new-training`} className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium px-4 py-2 rounded-md transition-colors shadow-sm flex items-center gap-2 text-sm">
            <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Retrain Base
          </Link>
          <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-md transition-colors shadow-sm flex items-center gap-2 text-sm">
            <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            Deploy
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Metrics & Info */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 grid grid-cols-2 gap-4 text-center">
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Accuracy</div>
              <div className="text-xl font-bold text-gray-900 mt-1">{data.acc}</div>
            </div>
            {data.type === "Detection" && (
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">mAP</div>
                <div className="text-xl font-bold text-gray-900 mt-1">{data.map}</div>
              </div>
            )}
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-100 col-span-2">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Loss</div>
              <div className="text-xl font-bold text-gray-900 mt-1">{data.loss}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold border-b border-gray-100 pb-2 mb-4">Training Config</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Dataset</span>
                <Link href="/admin/dataset/DS-002" className="font-medium text-blue-600 hover:underline">{data.dataset}</Link>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Epochs</span>
                <span className="font-medium text-gray-900">{data.config.epochs}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Batch Size</span>
                <span className="font-medium text-gray-900">{data.config.batch_size}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Learning Rate</span>
                <span className="font-medium text-gray-900">{data.config.learning_rate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Optimizer</span>
                <span className="font-medium text-gray-900">{data.config.optimizer}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Image Size</span>
                <span className="font-medium text-gray-900">{data.config.image_size}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Previews & History */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
            <button 
              onClick={() => setActiveTab("overview")} 
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${activeTab === "overview" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
            >
              Inference Sample
            </button>
            <button 
              onClick={() => setActiveTab("history")} 
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${activeTab === "history" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
            >
              Model Version History
            </button>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 min-h-[400px]">
            {activeTab === "overview" ? (
              <div className="space-y-4 animate-in fade-in duration-200 flex flex-col items-center">
                <h3 className="font-semibold text-gray-900 w-full text-left">Inference Output Sample</h3>
                <div className="w-full max-w-lg mt-4 border border-gray-300 rounded-lg overflow-hidden shadow-sm relative">
                   <img src={data.sampleImage} alt="Inference Sample" className="w-full h-auto object-cover" />
                   {data.type === 'Detection' && (
                     <div className="absolute top-1/4 left-1/4 w-1/3 h-1/3 border-2 border-green-500 bg-green-500/10 rounded pointer-events-none">
                       <span className="absolute -top-6 left-0 bg-green-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-t">Lesion: 98%</span>
                     </div>
                   )}
                </div>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in duration-200">
                <h3 className="font-semibold text-gray-900">Training Iterations</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-600">
                      <thead className="text-xs text-gray-700 uppercase bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="px-4 py-3 font-semibold">Ver</th>
                          <th className="px-4 py-3 font-semibold">Date</th>
                          <th className="px-4 py-3 font-semibold">Metrics (Acc/mAP)</th>
                          <th className="px-4 py-3 font-semibold w-1/3">Notes</th>
                          <th className="px-4 py-3 font-semibold text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                         {data.history.map((hist, idx) => (
                           <tr key={idx} className={`${idx === 0 ? "bg-blue-50/30" : "bg-white"} transition-colors`}>
                             <td className="px-4 py-3 font-semibold text-gray-900">{hist.version}</td>
                             <td className="px-4 py-3 text-gray-500">{hist.date}</td>
                             <td className="px-4 py-3">
                               <div className="flex flex-col text-xs space-y-0.5 font-medium">
                                 <span className="text-emerald-600">Acc: {hist.acc}</span>
                                 <span className="text-amber-600">mAP: {hist.map}</span>
                               </div>
                             </td>
                             <td className="px-4 py-3 text-xs text-gray-600">{hist.note}</td>
                             <td className="px-4 py-3 text-right">
                               <button className="text-xs font-medium text-blue-600 hover:underline">Select as Active</button>
                             </td>
                           </tr>
                         ))}
                      </tbody>
                    </table>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
