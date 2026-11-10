import type { SpendingData } from "./spending";
export function mockSpending(user: string): SpendingData {
  const now = new Date();
  const orders = [
    ["Sony WH-CH720N", "Best Buy", 129.99, "auto_pay", 1],
    ["Logitech Pebble Mouse", "Target", 29.99, "auto_pay", 3],
    ["LED desk lamp", "Amazon", 44.99, "auto_pay", 5],
    ["USB-C hub", "Best Buy", 35.03, "needs_approval", 7],
    ["Mechanical keyboard", "Amazon", 89.99, "needs_approval", 16],
    ["Laptop stand", "Target", 39.99, "auto_pay", 22],
    ["Braided charging cable", "Walmart", 18.99, "auto_pay", 30],
    ["Portable SSD", "Best Buy", 74.99, "auto_pay", 38],
  ] as const;
  const week = Math.ceil(((now.getTime() - new Date(now.getFullYear(), 0, 1).getTime()) / 86400000 + new Date(now.getFullYear(), 0, 1).getDay() + 1) / 7);
  return {
    user, kpis: { month_total: 240, order_count: 4, avg_order: 60, auto_pay_share: 0.75 }, monthly_cap: 500,
    weekly: [42, 114.98, 18.99, 129.98, 35.03, 44.99, 29.99, 129.99].map((total, i) => ({ label: `W${week - 7 + i}`, total })),
    monthly: [178, 312.5, 226, 389.99, 294.97, 240].map((total, i) => ({ label: new Date(now.getFullYear(), now.getMonth() - 5 + i, 1).toLocaleDateString("en-US", { month: "short" }), total })),
    orders: orders.map(([title, merchant, amount, action, days], i) => ({ id: `sample-${i + 1}`, title, merchant, amount, currency: "USD", action, demo: true, captured_at: new Date(now.getTime() - days * 86400000).toISOString() })),
  };
}