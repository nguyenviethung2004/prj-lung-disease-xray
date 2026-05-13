import { NextResponse } from "next/server";
import { store } from "../store";

export async function GET(request: Request, { params }: { params: { id: string } }) {
  store.simulateProgress(); // Update progress before fetching

  const record = store.data.find((item) => item.id === params.id);
  
  if (!record) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  return NextResponse.json(record);
}
