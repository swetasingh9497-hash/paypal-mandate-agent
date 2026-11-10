export type Action = "auto_pay" | "needs_approval" | "reject";

export interface Mandate {
  item: string;
  max_total: number;
  currency: string;
  min_rating: number | null;
  max_delivery_days: number | null;
  auto_approve_under: number;
}

export interface Product {
  id: string;
  title: string;
  price: number;
  currency: string;
  rating: number | null;
  merchant: string;
  delivery_days: number | null;
  url: string;
}

export interface Candidate {
  product: Product;
  decision: { action: Action; reasons: string[] };
}

export interface RunResponse {
  run_id: string;
  mandate: Mandate;
  candidates: Candidate[];
  chosen_id: string | null;
  order: { id: string; approve_url: string; product_id?: string } | null;
  order_error?: string;
  explanation?: { summary: string; notes: Record<string, string> };
  audit?: { step: string; detail: string }[];
  monthly_cap?: number;
  month_spent?: number;
}

export interface SelectResponse {
  order: { id: string; approve_url: string };
  product: Product;
  decision: { action: Action; reasons: string[] };
}

export interface CaptureResponse {
  status?: string;
  capture_id?: string;
  amount?: number | string;
  currency?: string;
  payer_email?: string;
  title?: string;
  merchant?: string;
}
