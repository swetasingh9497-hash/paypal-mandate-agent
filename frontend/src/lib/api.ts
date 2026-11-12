import { mockRun } from "./mockData";
import type { CaptureResponse, RunResponse, SelectResponse } from "./types";
import { mockSpending } from "./mockSpending";
import { normalizeSpending, type SpendingData } from "./spending";
import { readSession } from "./auth";

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

async function authorizedFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const session = readSession();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (session) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(`Cannot reach API at ${API_URL}`);
  }

  if (res.status === 401) {
    // Session expired - sign out
    readSession(); // This doesn't clear, but we need to trigger sign out
    // We'll need to import signOut from auth, but let's handle it at the call site
    // For now, throw a special error
    const err = new ApiError("Session expired. Sign in again.");
    (err as any).status = 401;
    throw err;
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data ?? `HTTP ${res.status}`;
    throw new ApiError(formatError(detail));
  }
  return data as T;
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function runMandate(text: string, demo: boolean): Promise<RunResponse> {
  if (demo) {
    await delay(2000);
    return structuredClone(mockRun);
  }
  return authorizedFetch<RunResponse>("/api/run", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function runMockMandate(text: string, demo = true): Promise<RunResponse> {
  if (demo) return structuredClone(mockRun);
  return authorizedFetch<RunResponse>("/api/mock/run", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function selectProduct(runId: string, productId: string, approved = false): Promise<SelectResponse> {
  return authorizedFetch<SelectResponse>(`/api/runs/${encodeURIComponent(runId)}/select`, {
    method: "POST",
    body: JSON.stringify({ product_id: productId, approved }),
  });
}

export async function captureOrder(orderId: string, demo = false): Promise<CaptureResponse> {
  if (demo) return { status: "COMPLETED", amount: 129.99, currency: "USD", title: "Sony WH-CH720N Noise Cancelling", merchant: "Best Buy" };
  const capture = await authorizedFetch<CaptureResponse>(`/api/orders/${encodeURIComponent(orderId)}/capture`, {
    method: "POST",
  });
  // Verify the capture was actually completed
  if (capture.status !== "COMPLETED") {
    throw new ApiError(capture.status ? `Payment not completed (status: ${capture.status})` : "Payment not completed");
  }
  return capture;
}

export async function getSpending(demo: boolean): Promise<SpendingData> {
  if (demo) { await delay(600); return mockSpending("demo@budgie.app"); }
  return authorizedFetch<SpendingData>("/api/spending");
}

export const CHOSEN_KEY = "budgie:chosen";