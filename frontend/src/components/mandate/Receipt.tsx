import { motion } from "framer-motion";
import { BarChart3, Check, Copy, RotateCcw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMemo, useState } from "react";
import type { CaptureResponse } from "@/lib/types";
import { usd } from "./shared";

export interface ReceiptData {
  orderId: string;
  capture: CaptureResponse;
  stored: { title?: string; merchant?: string; price?: number } | null;
  demo?: boolean;
}

function Confetti() {
  const pieces = useMemo(
    () => Array.from({ length: 40 }, (_, i) => ({ left: Math.random() * 100, delay: Math.random() * 0.6, blue: i % 2 === 0 })),
    [],
  );
  return (
    <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden" aria-hidden>
      {pieces.map((p, i) => (
        <span key={i} className={`confetti-piece absolute -top-4 h-3 w-1.5 rounded-sm ${p.blue ? "bg-blue" : "bg-violet"}`} style={{ left: `${p.left}%`, animationDelay: `${p.delay}s` }} />
      ))}
    </div>
  );
}

function Row({ label, value, copy }: { label: string; value: string; copy?: boolean }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-center justify-between gap-3 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex min-w-0 items-center gap-2 font-mono tnum">
        <span className="truncate">{value}</span>
        {copy && (
          <button
            aria-label={`Copy ${label}`}
            onClick={() => {
              navigator.clipboard?.writeText(value);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
            className="rounded p-1 text-muted-foreground hover:text-foreground"
          >
            {copied ? <Check className="size-3.5 text-ok" /> : <Copy className="size-3.5" />}
          </button>
        )}
      </span>
    </div>
  );
}

export function Receipt({ data, onReset, onViewSpending }: { data: ReceiptData; onReset: () => void; onViewSpending: () => void }) {
  const c = data.capture ?? {};
  const title = c.title || data.stored?.title || "Your purchase";
  const merchant = c.merchant || data.stored?.merchant || "Merchant";
  const amountNum = Number(c.amount ?? data.stored?.price);
  const amount = Number.isFinite(amountNum) ? usd(amountNum) : "—";

  return (
    <>
      <Confetti />
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass mx-auto max-w-md overflow-hidden">
        <div className="dashed-edge h-px" />
        <div className="space-y-5 p-6 sm:p-8">
          <div className="flex flex-col items-center gap-3 text-center">
            <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", delay: 0.2 }} className="grid size-16 place-items-center rounded-full bg-ok/20 text-ok">
              <Check className="size-8" strokeWidth={3} aria-hidden />
            </motion.span>
            <h2 className="font-display text-2xl font-semibold">Payment complete</h2>
            {data.demo && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-warn/15 px-3 py-1 text-xs text-warn">
                Demo mode — no real payment
              </span>
            )}
          </div>
          <div className="text-center">
            <p className="font-medium">{title}</p>
            <p className="text-sm text-muted-foreground">{merchant}</p>
            <p className="mt-2 font-display text-4xl font-bold tnum">{amount}</p>
          </div>
          <div className="divide-y divide-glass-border border-y border-glass-border">
            {c.capture_id && <Row label="Capture ID" value={c.capture_id} copy />}
            <Row label="Order ID" value={data.orderId} />
            {c.payer_email && <Row label="Payer" value={c.payer_email} />}
            {c.status && <Row label="Status" value={c.status} />}
          </div>
          <button onClick={onReset} className="flex w-full items-center justify-center gap-2 rounded-full bg-gradient-accent px-6 py-3 font-semibold">
            <RotateCcw className="size-4" aria-hidden /> New mandate
          </button>
          <Button variant="outline" onClick={onViewSpending} className="w-full rounded-full"><BarChart3 />View spending</Button>
        </div>
        <div className="dashed-edge h-px" />
      </motion.div>
    </>
  );
}

export function Cancelled({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="glass mx-auto flex max-w-md flex-col items-center gap-4 p-8 text-center">
      <XCircle className="size-10 text-muted-foreground" aria-hidden />
      <h2 className="font-display text-xl font-semibold">Payment cancelled</h2>
      <button onClick={onRetry} className="rounded-full bg-gradient-accent px-6 py-2.5 font-semibold">Try again</button>
    </div>
  );
}
