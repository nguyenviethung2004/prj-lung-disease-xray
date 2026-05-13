import { NextResponse } from "next/server";
import { store } from "./store";

export async function GET() {
  // Simulate progress every time we fetch the list to make it dynamic
  store.simulateProgress();
  return NextResponse.json(store.data);
}
