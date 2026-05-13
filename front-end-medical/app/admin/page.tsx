"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";
import { getAuthUser, apiFetch } from "@/lib/api/auth";

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const data = await apiFetch("/reviews/dashboard-stats");
      setStats(data);
    } catch (error) {
      console.error("Lỗi khi tải thông số dashboard:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const user = getAuthUser();
    if (!user) {
      router.push("/login");
      return;
    }

    if (user.role !== "Superadmin") {
      router.push("/dashboard");
      return;
    }

    fetchStats();
  }, [router]);

  const statCards = [
    { title: "Total Images", value: stats?.overview?.total_images || 0 },
    { title: "AI Predictions", value: stats?.overview?.total_predictions || 0 },
    { title: "Doctor Reviews", value: stats?.overview?.total_reviews || 0 },
    { title: "AI Accuracy", value: `${stats?.overview?.ai_accuracy_percentage || 0}%` },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">AI Monitoring System</h1>
        <button
          onClick={fetchStats}
          disabled={isLoading}
          className="p-3 bg-white text-indigo-600 rounded-2xl border border-gray-100 shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.2)] transition-all hover:scale-110 active:scale-95 group flex items-center justify-center"
          title="Làm mới"
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
            className={`transition-transform duration-500 ${isLoading ? 'animate-spin' : 'group-hover:rotate-180'}`}
          >
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path>
            <polyline points="21 3 21 8 16 8"></polyline>
          </svg>
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => (
          <div key={stat.title} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-center transition-all hover:shadow-lg hover:-translate-y-1 group">
            <dt className="text-xs font-bold text-gray-400 uppercase tracking-wider group-hover:text-indigo-500 transition-colors">{stat.title}</dt>
            <dd className="mt-2 text-3xl font-black text-gray-900 flex items-center justify-between">
              {isLoading ? (
                <span className="h-9 w-20 bg-gray-100 animate-pulse rounded-md"></span>
              ) : (
                stat.value
              )}
              <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center group-hover:bg-indigo-50 transition-colors">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-300 group-hover:bg-indigo-400"></div>
              </div>
            </dd>
          </div>
        ))}
      </div>

      {/* Performance Trends Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Accuracy Trend */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span className="w-2 h-6 bg-emerald-500 rounded-full"></span>
              Accuracy Evolution (%)
            </h2>
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest bg-gray-50 px-2 py-1 rounded-md">Last 7 Days</div>
          </div>
          <div className="h-[250px] w-full">
            {isLoading ? (
              <div className="w-full h-full bg-gray-50 animate-pulse rounded-xl"></div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={stats?.performance_trends || []}>
                  <defs>
                    <linearGradient id="colorAcc" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fontSize: 10, fontWeight: 600, fill: '#94a3b8'}}
                    dy={10}
                    tickFormatter={(str) => str.split('-').slice(1).reverse().join('/')}
                  />
                  <YAxis 
                    domain={[0, 100]} 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fontSize: 10, fontWeight: 600, fill: '#94a3b8'}}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontSize: '12px', fontWeight: 'bold' }}
                    cursor={{ stroke: '#10b981', strokeWidth: 2 }}
                  />
                  <Area type="monotone" dataKey="accuracy" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorAcc)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Error Trend */}
        <div className="bg-white p-6 rounded-2xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span className="w-2 h-6 bg-rose-500 rounded-full"></span>
              Daily Errors (Drift Check)
            </h2>
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest bg-gray-50 px-2 py-1 rounded-md">Last 7 Days</div>
          </div>
          <div className="h-[250px] w-full">
            {isLoading ? (
              <div className="w-full h-full bg-gray-50 animate-pulse rounded-xl"></div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats?.performance_trends || []}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fontSize: 10, fontWeight: 600, fill: '#94a3b8'}}
                    dy={10}
                    tickFormatter={(str) => str.split('-').slice(1).reverse().join('/')}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fontSize: 10, fontWeight: 600, fill: '#94a3b8'}}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontSize: '12px', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="errors" fill="#f43f5e" radius={[4, 4, 0, 0]} barSize={30} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Error Analysis Chart */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <span className="w-2 h-6 bg-indigo-500 rounded-full"></span>
            AI Error Analysis (Confusion Matrix)
          </h2>

          <div className="flex flex-col items-center justify-center py-10 bg-gray-50/30 rounded-3xl border border-gray-100/50 backdrop-blur-sm">
            {isLoading ? (
              <div className="h-[350px] w-full max-w-md bg-gray-100/50 animate-pulse rounded-2xl"></div>
            ) : stats?.confusion_matrix ? (
              <div className="relative p-8">
                {/* Header Labels */}
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1">
                  <span className="text-[10px] font-black text-blue-500 uppercase tracking-[0.4em] mb-1">Prediction Output</span>
                  <div className="h-px w-20 bg-gradient-to-r from-transparent via-blue-400 to-transparent"></div>
                </div>

                <div className="flex gap-8">
                  {/* Left Label */}
                  <div className="flex items-center">
                    <div className="[writing-mode:vertical-lr] rotate-180 text-[10px] font-black text-rose-500 uppercase tracking-[0.4em] flex items-center gap-4">
                      <div className="h-20 w-px bg-gradient-to-b from-transparent via-rose-400 to-transparent"></div>
                      Ground Truth
                    </div>
                  </div>

                  {/* Matrix Container */}
                  <div className="relative">
                    <table className="border-separate border-spacing-3">
                      <thead>
                        <tr>
                          <th className="w-20"></th>
                          {stats.confusion_matrix.labels.map((label: string) => (
                            <th key={label} className="pb-4">
                              <div className="text-[10px] font-bold text-gray-400 uppercase vertical-text transform -rotate-45 origin-bottom-left whitespace-nowrap">
                                {label}
                              </div>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {stats.confusion_matrix.labels.map((actual: string) => (
                          <tr key={actual}>
                            <td className="pr-6 py-2 text-right">
                              <span className="text-[11px] font-bold text-gray-500 uppercase tracking-tight">
                                {actual}
                              </span>
                            </td>
                            {stats.confusion_matrix.labels.map((predicted: string) => {
                              // Filter entries for this specific cell (Actual row, Predicted column)
                              const cellEntries = stats.confusion_matrix.entries.filter(
                                (e: any) => e.doctor_label === actual && e.ai_label === predicted
                              );
                              
                              const count = cellEntries.reduce((sum: number, e: any) => sum + e.count, 0);
                              const isDiagonal = actual === predicted;
                              
                              // Dynamic Color Intensity logic
                              const maxCount = 10;
                              const intensity = Math.min(count / maxCount, 1);
                              
                              let cellStyles = "bg-gray-50 text-gray-300 border-gray-100";
                              let glowStyles = "";

                              if (count > 0) {
                                if (isDiagonal) {
                                  // Correct predictions: Green/Emerald scale
                                  cellStyles = `bg-emerald-500 text-white border-emerald-400 shadow-[0_0_20px_rgba(16,185,129,${intensity * 0.3})]`;
                                  glowStyles = "ring-2 ring-emerald-500/20";
                                } else {
                                  // Mispredictions: Rose/Red scale
                                  cellStyles = `bg-rose-500 text-white border-rose-400 shadow-[0_0_20px_rgba(244,63,94,${intensity * 0.3})]`;
                                  glowStyles = "ring-2 ring-rose-500/10";
                                }
                              }

                              return (
                                <td 
                                  key={`${actual}-${predicted}`} 
                                  className="p-0 relative group hover:z-[100]"
                                >
                                  <div 
                                    className={`w-16 h-16 flex items-center justify-center text-lg font-black rounded-2xl border-2 transition-all duration-300 hover:scale-110 hover:-translate-y-1 cursor-pointer relative ${cellStyles} ${glowStyles}`}
                                  >
                                    <span className="relative z-10">{count}</span>
                                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/20 to-transparent pointer-events-none"></div>
                                    
                                    <div className="absolute -top-14 left-1/2 -translate-x-1/2 px-4 py-2 bg-gray-900/95 backdrop-blur-md text-white text-[11px] rounded-xl opacity-0 group-hover:opacity-100 transition-all duration-200 whitespace-nowrap z-[100] pointer-events-none font-bold shadow-2xl border border-white/10 scale-90 group-hover:scale-100">
                                      <div className="flex flex-col items-center gap-0.5">
                                        <span className="text-[9px] text-gray-400 uppercase tracking-tighter">Actual: {actual}</span>
                                        <span>AI Prediction: {predicted} ({count} cases)</span>
                                        {count > 0 ? (
                                          <span className={isDiagonal ? "text-emerald-400" : "text-rose-400"}>
                                            {isDiagonal ? "AI and Doctor Match Labels (Correct)" : "AI and Doctor Mismatch Labels (Incorrect)"}
                                          </span>
                                        ) : (
                                          <span className="text-gray-400 italic">
                                            {isDiagonal ? "AI prediction is correct (No cases available)" : "AI prediction is incorrect (No cases available)"}
                                          </span>
                                        )}
                                      </div>
                                      <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-gray-900 rotate-45 border-r border-b border-white/10"></div>
                                    </div>
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Legend - Premium Style */}
                <div className="mt-12 flex items-center gap-10 justify-center">
                  <div className="flex items-center gap-3 px-4 py-2 bg-emerald-50 rounded-full border border-emerald-100">
                    <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                    <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">Correct Precision</span>
                  </div>
                  <div className="flex items-center gap-3 px-4 py-2 bg-rose-50 rounded-full border border-rose-100">
                    <div className="w-3 h-3 bg-rose-500 rounded-full shadow-[0_0_10px_rgba(244,63,94,0.5)]"></div>
                    <span className="text-[11px] font-bold text-rose-700 uppercase tracking-wider">Misclassification</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-gray-400 italic">
                No matrix data available.
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-4 italic">Statistics based on cases where doctors corrected labels compared to AI predictions.</p>
        </div>

        {/* Model Performance */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <span className="w-2 h-6 bg-blue-500 rounded-full"></span>
            Performance by Model Version
          </h2>
          <div className="space-y-4">
            {isLoading ? (
              [1, 2, 3].map(i => <div key={i} className="h-16 w-full bg-gray-50 animate-pulse rounded-lg"></div>)
            ) : stats?.model_performance?.length > 0 ? (
              stats.model_performance.map((m: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="flex flex-col">
                    <span className="font-bold text-gray-900">{m.name}</span>
                    <span className="text-xs text-gray-500">Version: {m.version}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xl font-bold text-blue-600">{m.predictions}</span>
                    <p className="text-[10px] text-gray-400 uppercase font-bold">AI Predictions</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 italic text-center py-10">No model information available.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
