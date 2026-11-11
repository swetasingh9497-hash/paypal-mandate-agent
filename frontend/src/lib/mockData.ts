import type { RunResponse } from "./types";

export const mockRun: RunResponse = {
  run_id: "mock_run_id",
  mandate: {
    item: "wireless headphones",
    max_total: 200,
    currency: "USD",
    min_rating: 4.5,
    max_delivery_days: 5,
    auto_approve_under: 150,
  },
  candidates: [
    {
      product: { id: "p1", title: "Sony WH-CH720N Noise Cancelling", price: 129.99, currency: "USD", rating: 4.6, merchant: "Best Buy", delivery_days: 2, url: "https://example.com/p1" },
      decision: { action: "auto_pay", reasons: ["Within $200 budget", "Rating 4.6 meets 4.5", "Delivers in 2 days", "Under $150 auto-approve"] },
    },
    {
      product: { id: "p2", title: "Bose QuietComfort SE", price: 179.0, currency: "USD", rating: 4.7, merchant: "Target", delivery_days: 3, url: "https://example.com/p2" },
      decision: { action: "needs_approval", reasons: ["Within $200 budget", "Above $150 auto-approve"] },
    },
    {
      product: { id: "p3", title: "Sennheiser Accentum Plus", price: 189.95, currency: "USD", rating: 4.5, merchant: "Amazon", delivery_days: 4, url: "https://example.com/p3" },
      decision: { action: "needs_approval", reasons: ["Within $200 budget", "Above $150 auto-approve"] },
    },
    {
      product: { id: "p4", title: "Sony WH-1000XM5", price: 279.99, currency: "USD", rating: 4.8, merchant: "Amazon", delivery_days: 2, url: "https://example.com/p4" },
      decision: { action: "reject", reasons: ["Exceeds $200 budget"] },
    },
    {
      product: { id: "p5", title: "Soundcore Life Q30", price: 59.99, currency: "USD", rating: 4.3, merchant: "Walmart", delivery_days: 3, url: "https://example.com/p5" },
      decision: { action: "reject", reasons: ["Rating 4.3 below 4.5"] },
    },
    {
      product: { id: "p6", title: "JBL Tour One M2", price: 169.0, currency: "USD", rating: 4.6, merchant: "eBay", delivery_days: 9, url: "https://example.com/p6" },
      decision: { action: "reject", reasons: ["Delivery 9 days exceeds 5"] },
    },
  ],
  chosen_id: "p1",
  order: { id: "5O190127TN364715T", approve_url: "https://www.sandbox.paypal.com/checkoutnow?token=5O190127TN364715T", product_id: "p1" },
  explanation: {
    summary: "Cheapest option passing every rule, and it ships fastest.",
    notes: {
      p2: "Best rated, but needs your approval.",
      p3: "Solid sound, slower delivery.",
      p4: "Top pick, over budget.",
      p5: "Great price, rating too low.",
      p6: "Ships too slowly.",
    },
  },
  audit: [
    { step: "parse", detail: "Budgie: headphones, max $200, rating 4.5+, 5 days" },
    { step: "search", detail: "Queried 4 merchants, 6 results" },
    { step: "normalize", detail: "Prices normalized to USD" },
    { step: "rules", detail: "3 rejected, 3 passed hard limits" },
    { step: "decide", detail: "Chose p1 at $129.99, auto_pay" },
    { step: "order", detail: "PayPal order 5O190127TN364715T created" },
  ],
  monthly_cap: 500,
  month_spent: 0,
};
