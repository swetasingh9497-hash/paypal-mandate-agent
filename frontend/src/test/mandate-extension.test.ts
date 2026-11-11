import { afterEach, describe, expect, it, vi } from "vitest";
import { persistSession, readSession, readDemo, persistDemo } from "@/lib/auth";
import { capTone, normalizeSpending } from "@/lib/spending";
import { getSpending, runMandate, runMockMandate, captureOrder } from "@/lib/api";
import { mockSpending } from "@/lib/mockSpending";

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); localStorage.clear(); });
describe("Session persistence", () => {
  it("restores a valid session", () => {
    const session = { token: "test-token", user: { name: "Test", email: "test@budgie.app" } };
    persistSession(session);
    expect(readSession()).toEqual(session);
  });
  it("clears the persisted session on sign out", () => {
    const session = { token: "test-token", user: { name: "Test", email: "test@budgie.app" } };
    persistSession(session);
    persistSession(null);
    expect(readSession()).toBeNull();
  });
  it("handles invalid saved sessions", () => { localStorage.setItem("budgie:session", "bad json"); expect(readSession()).toBeNull(); });
  it("persists demo flag in localStorage", () => { persistDemo(true); expect(readDemo()).toBe(true); persistDemo(false); expect(readDemo()).toBe(false); });
});
describe("Spending rules", () => {
  it("is green below 70 percent", () => { expect(capTone(349, 500)).toBe("ok"); });
  it("is amber from 70 to 90 percent", () => { expect(capTone(350, 500)).toBe("warn"); expect(capTone(450, 500)).toBe("warn"); });
  it("is rose above 90 percent", () => { expect(capTone(451, 500)).toBe("bad"); });
  it("normalizes malformed responses and empty arrays", () => { const data = normalizeSpending({ kpis: { auto_pay_share: 2, month_total: "bad" }, orders: [null], weekly: null }, "buyer"); expect(data.kpis.auto_pay_share).toBe(1); expect(data.kpis.month_total).toBe(0); expect(data.weekly).toEqual([]); expect(data.monthly_cap).toBeNull(); expect(data.orders[0]?.title).toBe("Your purchase"); });
  it("provides 8 weeks, 6 months and 8 sample orders", () => { const data = mockSpending("buyer"); expect(data.weekly).toHaveLength(8); expect(data.monthly).toHaveLength(6); expect(data.orders).toHaveLength(8); expect(data.kpis.month_total).toBe(240); expect(data.monthly_cap).toBe(500); expect(data.orders.every(o => o.demo)).toBe(true); });
});
describe("External API contract", () => {
  it("sends text only on live runs", async () => { const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}")); await runMandate("lamp", false); expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toEqual({ text: "lamp" }); });
  it("encodes the spending user in the GET request", async () => { const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}")); await getSpending(false); expect(fetcher.mock.calls[0]?.[0]).toContain("/api/spending"); });
  it("makes no network calls in demo mode", async () => { vi.useFakeTimers(); const fetcher = vi.spyOn(globalThis, "fetch"); const run = runMandate("lamp", true); const history = getSpending(true); await vi.advanceTimersByTimeAsync(2000); await Promise.all([run, history, runMockMandate("lamp", true), captureOrder("sample", true)]); expect(fetcher).not.toHaveBeenCalled(); });
});