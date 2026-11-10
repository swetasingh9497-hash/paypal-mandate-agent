import { mockRun } from "./mockData";
import type { CaptureResponse, RunResponse, SelectResponse } from "./types";
import { mockSpending } from "./mockSpending";
import { normalizeSpending, type SpendingData } from "./spending";

export const API_URL: string =
  (import.meta.env["VITE_API_URL"] as string | undefined) || "http://127.0.0.1:8000";

export class ApiError extends Error {}

export function formatError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : JSON.stringify(d)))
      .join("; ");
  try {
    return JSON.stringify(detail);
  } catch {
    return "Unknown error";
  }
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? null : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(`Cannot reach API at ${API_URL}`);
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data ?? `HTTP ${res.status}`;
    throw new ApiError(formatError(detail));
  }
  return data as T;
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function runMandate(text: string, demo: boolean, userEmail: string): Promise<RunResponse> {
  if (demo) {
    await delay(2000);
    return structuredClone(mockRun);
  }
  return post<RunResponse>("/api/run", { text, user_email: userEmail });
}

export async function runMockMandate(text: string, demo = true): Promise<RunResponse> {
  if (demo) return structuredClone(mockRun);
  return post<RunResponse>("/api/mock/run", { text });
}

export async function selectProduct(runId: string, productId: string, userEmail: string): Promise<SelectResponse> {
  return post<SelectResponse>(`/api/runs/${encodeURIComponent(runId)}/select`, { product_id: productId, user_email: userEmail });
}

export async function captureOrder(orderId: string, demo = false): Promise<CaptureResponse> {
  if (demo) return { status: "COMPLETED", amount: 129.99, currency: "USD", title: "Sony WH-CH720N Noise Cancelling", merchant: "Best Buy" };
  try {
    return await post<CaptureResponse>(`/api/orders/${encodeURIComponent(orderId)}/capture`);
  } catch (e) {
    if (e instanceof Error && e.message.includes("ORDER_ALREADY_CAPTURED")) return { status: "COMPLETED" };
    throw e;
  }
}

export async function getSpending(userEmail: string, demo: boolean): Promise<SpendingData> {
  if (demo) { await delay(600); return mockSpending(userEmail); }
  let res: Response;
  try { res = await fetch(`${API_URL}/api/spending?user=${encodeURIComponent(userEmail)}`); }
  catch { throw new ApiError(`Cannot reach API at ${API_URL}`); }
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : `HTTP ${res.status}`;
    throw new ApiError(formatError(detail));
  }
  return normalizeSpending(data, userEmail);
}

export const CHOSEN_KEY = "mandate:chosen";
