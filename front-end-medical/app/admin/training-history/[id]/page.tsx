"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

// Mock Data
const MOCK_DETAIL = {
  id: "TRN-001",
  model: "ResNet-50",
  dataset: "Chest X-Ray v2",
  start: "2026-03-15 08:00",
  end: "2026-03-15 14:30",
  status: "Success",
  accuracy: "94.5%",
  loss: "0.12",
  map: "89.4%", // for object detection if applicable
  config: {
    learning_rate: 0.001,
    batch_size: 32,
    epochs: 100,
    optimizer: "Adam",
    image_size: 256,
  },
  logs: `Epoch 1/100
- loss: 0.854 - accuracy: 0.652
Epoch 2/100
- loss: 0.742 - accuracy: 0.710
Epoch 3/100
- loss: 0.621 - accuracy: 0.785
...
Epoch 99/100
- loss: 0.125 - accuracy: 0.941
Epoch 100/100
- loss: 0.120 - accuracy: 0.945
Training completed successfully.
Model saved to /models/resnet50_v2.pt`,
};

export default function TrainingDetailPage() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [isRetrainOpen, setIsRetrainOpen] = useState(false);
  const [retrainConfig, setRetrainConfig] = useState({
    learning_rate: 0.001,
    batch_size: 32,
    epochs: 100,
    optimizer: "Adam",
    image_size: 256,
  });

  useEffect(() => {
    // Mock fetching data based on ID
    if (id) {
      setData({ ...MOCK_DETAIL, id: id as string });
      setRetrainConfig(MOCK_DETAIL.config);
    }
  }, [id]);

  const handleRetrainSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Submitting retrain with config:", retrainConfig);
    // Call API here...
    alert(`Đã bắt đầu Retrain model ${data?.model} với config mới!`);
    setIsRetrainOpen(false);
  };

  if (!data) return <div className="p-6">Loading...</div>;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/admin/training-history" className="p-2 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors text-gray-600">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Training Detail: {data.id}</h1>
        </div>
        <button 
          onClick={() => setIsRetrainOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium text-sm transition-colors shadow-sm flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.5 2v6h-6M2.13 15.57a10 10 0 1 0 3.12-11.83l-3.32 3.32M4 21v-6h6"/></svg>
          Retrain
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Info & Config */}
        <div className="lg:col-span-1 space-y-6">
          {/* General Info */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-semibold border-b border-gray-100 pb-2">General Info</h2>
            <div className="grid grid-cols-2 gap-y-4 text-sm">
              <div className="text-gray-500">Model Name</div>
              <div className="font-medium text-gray-900">{data.model}</div>
              
              <div className="text-gray-500">Dataset</div>
              <div className="font-medium text-gray-900">{data.dataset}</div>
              
              <div className="text-gray-500">Time</div>
              <div className="font-medium text-gray-900">
                {data.start}
                <br />
                <span className="text-gray-400 text-xs">to {data.end}</span>
              </div>
              
              <div className="text-gray-500">Status</div>
              <div>
                <span className={`px-2 py-1 flex w-max rounded-full text-xs font-medium ${data.status === 'Success' ? 'bg-green-100 text-green-800' : data.status === 'Failed' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
                  {data.status === 'Running' && <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse mr-1.5 self-center"></span>}
                  {data.status}
                </span>
              </div>
            </div>
          </div>

          {/* Config */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
            <h2 className="text-lg font-semibold border-b border-gray-100 pb-2">Configuration</h2>
            <div className="bg-gray-50 p-4 rounded-md overflow-x-auto text-sm border border-gray-200">
              <pre className="text-gray-700 font-mono">
                {JSON.stringify(data.config, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* Right Column: Results & Logs */}
        <div className="lg:col-span-2 space-y-6">
          {/* Results Grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-center">
              <div className="text-sm text-gray-500 font-medium">Accuracy</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">{data.accuracy}</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-center">
              <div className="text-sm text-gray-500 font-medium">Loss</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">{data.loss}</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-center">
              <div className="text-sm text-gray-500 font-medium">mAP</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">{data.map}</div>
            </div>
          </div>

          {/* Chart Placeholder */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 h-72 flex flex-col justify-center items-center relative overflow-hidden">
            <div className="absolute top-4 left-6 font-semibold text-gray-900">Training Metrics Chart</div>
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-20 text-blue-600 mb-2"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            <p className="text-sm font-medium text-gray-400">Chart rendering placeholder (Loss / Accuracy vs Epochs)</p>
          </div>

          {/* Logs */}
          <div className="bg-[#1e1e1e] rounded-xl shadow-sm overflow-hidden border border-gray-700">
            <div className="bg-[#2d2d2d] px-4 py-2 border-b border-gray-700 flex justify-between items-center text-xs text-gray-300 font-medium font-mono">
              <span>training.log</span>
            </div>
            <div className="p-4 h-64 overflow-y-auto font-mono text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
              {data.logs}
            </div>
          </div>
        </div>
      </div>

      {/* Retrain Modal */}
      {isRetrainOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="border-b border-gray-100 px-6 py-4 flex justify-between items-center">
              <h3 className="font-semibold text-lg text-gray-900">Retrain Model Config</h3>
              <button onClick={() => setIsRetrainOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>
            
            <form onSubmit={handleRetrainSubmit} className="p-6 space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Learning Rate</label>
                <input 
                  type="number" step="0.0001" 
                  value={retrainConfig.learning_rate} 
                  onChange={e => setRetrainConfig({...retrainConfig, learning_rate: parseFloat(e.target.value)})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  required 
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Batch Size</label>
                <input 
                  type="number" 
                  value={retrainConfig.batch_size} 
                  onChange={e => setRetrainConfig({...retrainConfig, batch_size: parseInt(e.target.value)})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  required 
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Epochs</label>
                <input 
                  type="number" 
                  value={retrainConfig.epochs} 
                  onChange={e => setRetrainConfig({...retrainConfig, epochs: parseInt(e.target.value)})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  required 
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Optimizer</label>
                <select 
                  value={retrainConfig.optimizer}
                  onChange={e => setRetrainConfig({...retrainConfig, optimizer: e.target.value})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none"
                >
                  <option value="Adam">Adam</option>
                  <option value="SGD">SGD</option>
                  <option value="RMSprop">RMSprop</option>
                  <option value="AdamW">AdamW</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-gray-700">Image Size</label>
                <select 
                  value={retrainConfig.image_size}
                  onChange={e => setRetrainConfig({...retrainConfig, image_size: parseInt(e.target.value)})}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none"
                >
                  <option value="128">128</option>
                  <option value="224">224</option>
                  <option value="256">256</option>
                  <option value="512">512</option>
                  <option value="1024">1024</option>
                </select>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 mt-4">
                <button type="button" onClick={() => setIsRetrainOpen(false)} className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 border border-transparent">
                  Cancel
                </button>
                <button type="submit" className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors">
                  Submit Retrain
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
