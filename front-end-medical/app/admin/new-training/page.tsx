"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useToast } from "@/context/ToastContext";

// Mock Data for Options
const MOCK_DATASETS = [
  { id: "ds1", name: "Chest X-Ray v2", count: "10,000", type: "Classification" },
  { id: "ds2", name: "MRI Scans", count: "5,500", type: "Detection" },
  { id: "ds3", name: "Skin Lesions", count: "12,000", type: "Segmentation" },
];

const MOCK_MODELS = [
  { id: "m1", name: "YOLOv8-Med" },
  { id: "m2", name: "ResNet-50" },
  { id: "m3", name: "U-Net" },
  { id: "m4", name: "DenseNet-121" },
];

export default function NewTrainingPage() {
  const router = useRouter();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const { showToast } = useToast();
  // Removed local toastMessage and toastType states

  // --- Form States ---
  // Source
  const [sourceType, setSourceType] = useState("predefined");
  const [gitUrl, setGitUrl] = useState("");
  const [customFile, setCustomFile] = useState<File | null>(null);

  // Dataset
  const [datasetId, setDatasetId] = useState(MOCK_DATASETS[0].id);

  // Model
  const [modelId, setModelId] = useState(MOCK_MODELS[0].id);
  const [usePretrained, setUsePretrained] = useState(false);
  const [weightFile, setWeightFile] = useState<File | null>(null);

  // Hyperparameters
  const [learningRate, setLearningRate] = useState(0.001);
  const [batchSize, setBatchSize] = useState(32);
  const [epochs, setEpochs] = useState(100);
  const [optimizer, setOptimizer] = useState("Adam");
  const [imageSize, setImageSize] = useState(256);
  const [device, setDevice] = useState("GPU");

  // Advanced
  const [dataAugmentation, setDataAugmentation] = useState(true);
  const [earlyStopping, setEarlyStopping] = useState(true);
  const [saveCheckpoint, setSaveCheckpoint] = useState(true);
  const [advancedConfigJson, setAdvancedConfigJson] = useState("");

  // showToast is now provided by useToast hook

  const handleReset = () => {
    setSourceType("predefined");
    setGitUrl("");
    setCustomFile(null);
    setDatasetId(MOCK_DATASETS[0].id);
    setModelId(MOCK_MODELS[0].id);
    setUsePretrained(false);
    setWeightFile(null);
    setLearningRate(0.001);
    setBatchSize(32);
    setEpochs(100);
    setOptimizer("Adam");
    setImageSize(256);
    setDevice("GPU");
    setDataAugmentation(true);
    setEarlyStopping(true);
    setSaveCheckpoint(true);
    setAdvancedConfigJson("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Create a customized ID for mock redirect later
      const mockNewId = `TRN-999`; 

      // MOCK API Call Simulation
      await new Promise(resolve => setTimeout(resolve, 1500)); 

      /*
      // In a real app we would send this data to a POST /api/trainings endpoint
      const payload = {
        source: { type: sourceType, url: gitUrl },
        dataset: datasetId,
        model: { id: modelId, pretrained: usePretrained },
        hyperparameters: { learning_rate: learningRate, batch_size: batchSize, epochs: epochs, optimizer: optimizer, image_size: imageSize, device: device },
        advanced: { data_augmentation: dataAugmentation, early_stopping: earlyStopping, save_checkpoint: saveCheckpoint, custom_json: advancedConfigJson }
      };
      await fetch('/api/trainings', { method: 'POST', body: JSON.stringify(payload) });
      */

      showToast("Tạo tiến trình training thành công!", "success");
      
      // Redirect sau 1 giây
      setTimeout(() => {
        router.push(`/admin/training-history`);
      }, 1000);

    } catch (error) {
      showToast("Lỗi khi tạo training!", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto pb-12 relative animate-in fade-in duration-300">

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configure New Training</h1>
          <p className="text-sm text-gray-500 mt-1">Setup and initialize a new AI training session</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* 1. Training Source */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
            1. Source Code
          </h2>
          <div className="space-y-4">
            <div className="flex gap-6 flex-wrap">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" value="predefined" checked={sourceType === "predefined"} onChange={() => setSourceType("predefined")} className="text-blue-600 focus:ring-blue-500" />
                <span className="text-sm font-medium text-gray-700">Pre-defined Models</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" value="git" checked={sourceType === "git"} onChange={() => setSourceType("git")} className="text-blue-600 focus:ring-blue-500" />
                <span className="text-sm font-medium text-gray-700">Git Repository (URL)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" value="upload" checked={sourceType === "upload"} onChange={() => setSourceType("upload")} className="text-blue-600 focus:ring-blue-500" />
                <span className="text-sm font-medium text-gray-700">Upload Zip</span>
              </label>
            </div>

            {sourceType === "git" && (
              <div className="animate-in fade-in slide-in-from-top-1 mt-3">
                <input type="url" placeholder="https://github.com/username/repo.git" value={gitUrl} onChange={e => setGitUrl(e.target.value)} required className="w-full sm:w-2/3 border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" />
              </div>
            )}
            
            {sourceType === "upload" && (
              <div className="animate-in fade-in slide-in-from-top-1 mt-3">
                <input type="file" accept=".zip" onChange={e => { if(e.target.files) setCustomFile(e.target.files[0])} } required className="block w-full sm:w-2/3 text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-md p-1" />
              </div>
            )}
          </div>
        </div>

        {/* 2. Dataset */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2">
            <svg className="w-5 h-5 text-purple-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>
            2. Dataset Selection
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700 block">Available Datasets</label>
              <select value={datasetId} onChange={e => setDatasetId(e.target.value)} className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none">
                {MOCK_DATASETS.map(ds => (
                  <option key={ds.id} value={ds.id}>{ds.name} ({ds.count} images - {ds.type})</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button type="button" className="text-sm text-blue-600 font-medium hover:underline flex items-center gap-1 pb-2">
                <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Upload New Dataset
              </button>
            </div>
          </div>
        </div>

        {/* 3. Model */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
           <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2">
            <svg className="w-5 h-5 text-orange-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
            3. Model Architecture
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
             <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700 block">Base Model</label>
              <select value={modelId} onChange={e => setModelId(e.target.value)} className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none">
                {MOCK_MODELS.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
            
            <div className="flex flex-col justify-end space-y-3">
               <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={usePretrained} onChange={e => setUsePretrained(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500 border-gray-300" />
                  <span className="text-sm font-medium text-gray-700">Use pre-trained weights</span>
               </label>
               {usePretrained && (
                 <div className="animate-in fade-in">
                   <input type="file" accept=".pt,.pth,.h5" onChange={e => { if(e.target.files) setWeightFile(e.target.files[0])} } className="block w-full text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200 border border-gray-200 rounded p-0.5" />
                 </div>
               )}
            </div>
          </div>
        </div>

        {/* 4. Hyperparameters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>
            4. Hyperparameters
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Learning Rate</label>
              <input type="number" step="0.0001" min="0" value={learningRate} onChange={e => setLearningRate(parseFloat(e.target.value))} required className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Batch Size</label>
              <input type="number" min="1" value={batchSize} onChange={e => setBatchSize(parseInt(e.target.value))} required className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Epochs</label>
              <input type="number" min="1" value={epochs} onChange={e => setEpochs(parseInt(e.target.value))} required className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Optimizer</label>
              <select value={optimizer} onChange={e => setOptimizer(e.target.value)} className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none">
                <option value="Adam">Adam</option>
                <option value="SGD">SGD</option>
                <option value="RMSprop">RMSprop</option>
                <option value="AdamW">AdamW</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Image Size</label>
              <select value={imageSize} onChange={e => setImageSize(parseInt(e.target.value))} className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none">
                <option value={128}>128x128</option>
                <option value={224}>224x224</option>
                <option value={256}>256x256</option>
                <option value={512}>512x512</option>
                <option value={1024}>1024x1024</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">Device</label>
              <select value={device} onChange={e => setDevice(e.target.value)} className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none">
                <option value="GPU">GPU (CUDA)</option>
                <option value="CPU">CPU</option>
                <option value="MPS">MPS (Apple Silicon)</option>
              </select>
            </div>
          </div>
        </div>

        {/* 5. Advanced Config */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100 flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            5. Advanced Config (Optional)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <label className="flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                <span className="text-sm font-medium text-gray-800">Data Augmentation</span>
                <input type="checkbox" checked={dataAugmentation} onChange={e => setDataAugmentation(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500 border-gray-300 h-4 w-4" />
              </label>
              <label className="flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                <span className="text-sm font-medium text-gray-800">Early Stopping</span>
                <input type="checkbox" checked={earlyStopping} onChange={e => setEarlyStopping(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500 border-gray-300 h-4 w-4" />
              </label>
              <label className="flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                <span className="text-sm font-medium text-gray-800">Save Checkpoint on best epoch</span>
                <input type="checkbox" checked={saveCheckpoint} onChange={e => setSaveCheckpoint(e.target.checked)} className="rounded text-blue-600 focus:ring-blue-500 border-gray-300 h-4 w-4" />
              </label>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Custom JSON Override</label>
              <textarea 
                rows={5} 
                className="w-full border border-gray-300 rounded-md p-3 text-sm font-mono focus:ring-blue-500 focus:border-blue-500 outline-none resize-none bg-gray-50" 
                placeholder='{&#10;  "optimizer_args": { "weight_decay": 1e-4 },&#10;  "lr_scheduler": "cosine"&#10;}'
                value={advancedConfigJson}
                onChange={e => setAdvancedConfigJson(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          <button type="button" onClick={handleReset} disabled={isSubmitting} className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-200 disabled:opacity-50 transition-colors">
            Reset
          </button>
          <button type="submit" disabled={isSubmitting} className="px-5 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed">
            {isSubmitting ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Initializing Training...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                Start Training
              </>
            )}
          </button>
        </div>

      </form>
    </div>
  );
}
