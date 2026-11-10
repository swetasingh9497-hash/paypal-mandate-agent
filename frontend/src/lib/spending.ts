import type { Action } from "./types";
export interface SpendingPoint { label: string; total: number }
export interface SpendingOrder {
  id: string; title: string; merchant: string; amount: number; currency: string;
  action: Action; captured_at: string; demo?: boolean;
}
export interface SpendingData {
  user: string;
  kpis: { month_total: number; order_count: number; avg_order: number; auto_pay_share: number };
  monthly_cap: number | null; weekly: SpendingPoint[]; monthly: SpendingPoint[]; orders: SpendingOrder[];
}
type Raw = { [K in 'label'|'total'|'kpis'|'user'|'month_total'|'order_count'|'avg_order'|'auto_pay_share'|'monthly_cap'|'weekly'|'monthly'|'orders'|'id'|'title'|'merchant'|'amount'|'currency'|'action'|'captured_at'|'demo']?: unknown };
const record = (v: unknown): Raw => v && typeof v === "object" ? v as Raw : {};
const number = (v: unknown) => typeof v === "number" && Number.isFinite(v) ? Math.max(0, v) : 0;
const text = (v: unknown, fallback = "") => typeof v === "string" && v.trim() ? v : fallback;
function points(v: unknown, limit: number): SpendingPoint[] {
  return Array.isArray(v) ? v.map(record).filter(p => typeof p.label === "string").slice(-limit)
    .map(p => ({ label: text(p.label), total: number(p.total) })) : [];
}
export function normalizeSpending(value: unknown, user: string): SpendingData {
  const v = record(value); const k = record(v.kpis);
  return {
    user: text(v.user, user),
    kpis: { month_total: number(k.month_total), order_count: Math.floor(number(k.order_count)),
      avg_order: number(k.avg_order), auto_pay_share: Math.min(1, number(k.auto_pay_share)) },
    monthly_cap: typeof v.monthly_cap === "number" && Number.isFinite(v.monthly_cap) && v.monthly_cap >= 0 ? v.monthly_cap : null,
    weekly: points(v.weekly, 8), monthly: points(v.monthly, 6),
    orders: Array.isArray(v.orders) ? v.orders.map(record).map((o, i) => ({
      id: text(o.id, `order-${i}`), title: text(o.title, "Your purchase"), merchant: text(o.merchant, "Merchant"),
      amount: number(o.amount), currency: text(o.currency, "USD"),
      action: o.action === "auto_pay" || o.action === "reject" ? o.action : "needs_approval",
      captured_at: text(o.captured_at), demo: o.demo === true,
    })) : [],
  };
}
export function capTone(total: number, cap: number): "ok" | "warn" | "bad" {
  const ratio = cap > 0 ? total / cap : total > 0 ? Infinity : 0;
  return ratio < 0.7 ? "ok" : ratio <= 0.9 ? "warn" : "bad";
}