import { afterEach, describe, expect, it, vi } from "vitest";
import { DEMO_SESSION, persistSession, readSession, startPayPalLogin, readDemo, persistDemo } from "@/lib/auth";
import { capTone, normalizeSpending } from "@/lib/spending";
import { getSpending, runMandate, runMockMandate, captureOrder } from "@/lib/api";
import { mockSpending } from "@/lib/mockSpending";

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); localStorage.clear(); });
describe("Session persistence", () => {
  it("restores the exact demo buyer", () => { persistSession(DEMO_SESSION); expect(readSession()).toEqual({ name: "Demo Buyer", email: "demo@mandate.app", mode: "demo" }); });
  it("uses the PayPal buyer without credentials", () => { expect(startPayPalLogin()).toEqual({ name: "PayPal Buyer", email: "buyer@mandate.app", mode: "paypal" }); });
  it("clears the persisted session on sign out", () => { persistSession(DEMO_SESSION); persistSession(null); expect(readSession()).toBeNull(); });
  it("handles invalid saved sessions", () => { localStorage.setItem("mandate:session", "bad json"); expect(readSession()).toBeNull(); });
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
  it("sends user_email beside text on live runs", async () => { const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}")); await runMandate("lamp", false, "demo@mandate.app"); expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toEqual({ text: "lamp", user_email: "demo@mandate.app" }); });
  it("encodes the spending user in the GET request", async () => { const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}")); await getSpending("buyer+test@mandate.app", false); expect(fetcher.mock.calls[0]?.[0]).toContain("/api/spending?user=buyer%2Btest%40mandate.app"); });
  it("makes no network calls in demo mode", async () => { vi.useFakeTimers(); const fetcher = vi.spyOn(globalThis, "fetch"); const run = runMandate("lamp", true, "demo@mandate.app"); const history = getSpending("demo@mandate.app", true); await vi.advanceTimersByTimeAsync(2000); await Promise.all([run, history, runMockMandate("lamp", true), captureOrder("sample", true)]); expect(fetcher).not.toHaveBeenCalled(); });
});
