import { NextResponse } from "next/server";
import { store } from "../store";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { model, dataset, config } = body;

    const newId = `TRN-${String(store.data.length + 1).padStart(3, '0')}`;
    
    const newRecord: any = {
      id: newId,
      model: model || "Retrained Model",
      dataset: dataset || "Previous Dataset",
      start: new Date().toISOString().replace('T', ' ').substring(0, 16),
      end: "-",
      status: "Running",
      accuracy: "-",
      loss: "-",
      progress: 0,
      config: config,
      logs: "Initializing training environment...\nLoading dataset...\nStarting training loop...",
    };

    // Thêm lên đầu danh sách
    store.data.unshift(newRecord);

    return NextResponse.json({ success: true, data: newRecord }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Invalid data" }, { status: 400 });
  }
}
