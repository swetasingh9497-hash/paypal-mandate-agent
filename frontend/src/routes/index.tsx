import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Gauge, ListTree, Loader2, Package, Shield, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { CHOSEN_KEY, captureOrder, runMandate, selectProduct } from "@/lib/api";
import type { Candidate, RunResponse } from "@/lib/types";
import { Pipeline, type PipelineStatus } from "@/components/mandate/Pipeline";
import { Guardrails, PriceZone } from "@/components/mandate/Guardrails";
import { OtherCandidates, Recommendation } from "@/components/mandate/Recommendation";
import { Cancelled, Receipt, type ReceiptData } from "@/components/mandate/Receipt";
import { Section, fadeUp } from "@/components/mandate/shared";
import { formatAudit } from "@/lib/formatAudit";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Budgie — AI shopping agent with limits" },
      { name: "description", content: "An AI agent that buys within your limits and pays with PayPal." },
      { property: "og:title", content: "Budgie — AI shopping agent with limits" },
      { property: "og:description", content: "An AI agent that buys within your limits and pays with PayPal." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: MandateApp,
});

const EXAMPLES = ["Desk lamp under $60", "Headphones under $200, 4.5+", "Mouse under $50, auto-buy under $30"];

function Background() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="blob-1 absolute -left-40 -top-40 size-[36rem] rounded-full opacity-25 blur-[120px]" />
      <div className="blob-2 absolute -bottom-40 -right-40 size-[36rem] rounded-full opacity-25 blur-[120px]" />
      <div className="dot-grid absolute inset-0" />
    </div>
  );
}

function Skeletons() {
  return (
    <div className="space-y-4">
      {[28, 20, 48].map((h) => (
        <div key={h} className="shimmer rounded-[20px]" style={{ height: `${h * 4}px` }} />
      ))}
    </div>
  );
}

function MandateApp() {
  const { demo, session } = useAuth();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [status, setStatus] = useState<PipelineStatus>("idle");
  const [data, setData] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<ReceiptData | null>(null);
  const [capturing, setCapturing] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const captured = useRef(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order");
    if (params.get("cancelled") === "1") {
      setCancelled(true);
      window.history.replaceState(null, "", window.location.pathname);
    }
    if (!orderId || captured.current) return;
    captured.current = true;
    window.history.replaceState(null, "", window.location.pathname);
    let stored: ReceiptData["stored"] = null;
    try {
      const raw = sessionStorage.getItem(CHOSEN_KEY);
      const c = raw ? (JSON.parse(raw) as Partial<Candidate>) : null;
      stored = c?.product ? { title: c.product.title, merchant: c.product.merchant, price: c.product.price } : null;
    } catch {
      stored = null;
    }
    setCapturing(true);
    captureOrder(orderId)
      .then((capture) => setReceipt({ orderId, capture: capture ?? {}, stored, demo }))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setCapturing(false));
  }, [demo]);

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    const q = text.trim() || "Headphones under $200, 4.5+";
    setError(null);
    setData(null);
    setSelectedId(null);
    setStatus("running");
    try {
      if (!session) return;
      const res = await runMandate(q, demo);
      setData(res);
      setSelectedId(res.chosen_id);
      setStatus("done");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Session expired")) {
        setError("Session expired. Sign in again.");
        // Sign out will be handled by the auth context
      } else {
        setError(msg);
      }
      setStatus("error");
    }
  }

  function handleSelect(candidate: Candidate) {
    setSelectedId(candidate.product.id);
  }

  async function handlePay(candidate: Candidate) {
    if (!data?.run_id) {
      // Fallback for old backend or demo mode
      if (data?.order) {
        if (demo) {
          setReceipt({ orderId: data.order.id, capture: { status: "COMPLETED", amount: candidate.product.price, currency: candidate.product.currency }, stored: { title: candidate.product.title, merchant: candidate.product.merchant, price: candidate.product.price }, demo: true });
        } else {
          sessionStorage.setItem(CHOSEN_KEY, JSON.stringify(candidate));
          window.location.href = data.order.approve_url;
        }
      }
      return;
    }

    // For needs_approval products, send approved=true only after user confirms in dialog
    const approved = candidate.decision.action === "needs_approval";

    try {
      const result = await selectProduct(data.run_id, candidate.product.id, approved);

      // Save selected candidate for receipt
      sessionStorage.setItem(CHOSEN_KEY, JSON.stringify(candidate));

      // Redirect to PayPal
      window.location.href = result.order.approve_url;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Payment failed";
      if (msg.includes("Session expired")) {
        setError("Session expired. Sign in again.");
      } else {
        setError(msg);
      }
    }
  }

  function reset() {
    setReceipt(null);
    setCancelled(false);
    setData(null);
    setSelectedId(null);
    setStatus("idle");
    setText("");
    sessionStorage.removeItem(CHOSEN_KEY);
  }

  const auditLines = data?.audit?.length
    ? data.audit.map((a) => formatAudit(a))
    : ["parse", "search", "rules", "decide"];

  const hasRun = status !== "idle";

  return (
    <div className="relative min-h-screen">
      <Background />

      <main className="mx-auto max-w-5xl space-y-12 px-4 py-12 sm:py-16">
        {error && (
          <div role="alert" className="flex items-start gap-3 rounded-xl border border-bad/40 bg-bad/10 p-4 text-sm">
            <span className="flex-1 break-words">{error}</span>
            <button onClick={() => setError(null)} aria-label="Dismiss error" className="rounded p-0.5 text-muted-foreground hover:text-foreground">
              <X className="size-4" />
            </button>
          </div>
        )}

        {capturing ? (
          <div className="flex items-center justify-center gap-2 py-24 text-muted-foreground">
            <Loader2 className="size-5 animate-spin" /> Capturing payment
          </div>
        ) : receipt ? (
          <Receipt data={receipt} onReset={reset} onViewSpending={() => navigate({ to: "/spending" })} />
        ) : cancelled ? (
          <Cancelled onRetry={reset} />
        ) : (
          <>
            <motion.section variants={fadeUp} initial="hidden" animate="show" className="space-y-6 text-center">
              <h1 className="font-display text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
                Tell Budgie what to buy.
                <br />
                <span className="text-gradient">It stays inside your limits.</span>
              </h1>
              <form onSubmit={run} className="group mx-auto max-w-2xl rounded-full bg-glass-border p-px transition focus-within:bg-gradient-accent focus-within:shadow-[0_0_40px_-8px_var(--blue)]">
                <div className="flex items-center gap-2 rounded-full bg-background p-1.5 pl-5">
                  <Sparkles className="size-5 shrink-0 text-blue" aria-hidden />
                  <input
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Headphones under $200, 4.5+"
                    aria-label="Shopping budgie"
                    className="min-w-0 flex-1 bg-transparent py-2.5 text-base outline-none placeholder:text-muted-foreground"
                  />
                  <button type="submit" disabled={status === "running"} className="flex items-center gap-2 rounded-full bg-gradient-accent px-4 py-2.5 font-semibold disabled:opacity-70 sm:px-5">
                    {status === "running" ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4" />}
                    <span className="hidden sm:inline">Run</span>
                  </button>
                </div>
              </form>
              <div className="flex flex-wrap justify-center gap-2">
                {EXAMPLES.map((ex) => (
                  <button key={ex} onClick={() => setText(ex)} className="glass glass-hover rounded-full px-4 py-1.5 text-sm">
                    {ex}
                  </button>
                ))}
              </div>
            </motion.section>

            {hasRun && (
              <>
                <Section title="Agent pipeline" icon={<ListTree className="size-4" />} i={1}>
                  <Pipeline status={status} lines={auditLines} />
                </Section>

                {status === "running" && <Skeletons />}

                <AnimatePresence>
                  {data && status === "done" && (
                    <div className="space-y-12">
                      <Section title="Your guardrails" icon={<Shield className="size-4" />}>
                        <Guardrails mandate={data.mandate} />
                      </Section>
                      <Section title="Price zones" icon={<Gauge className="size-4" />} i={1}>
                        <PriceZone mandate={data.mandate} candidates={data.candidates} chosenId={data.chosen_id} />
                      </Section>
                      <Section title="Recommended purchase" icon={<Sparkles className="size-4" />} i={2}>
                        <Recommendation
                          data={data}
                          onPay={handlePay}
                          selectedId={selectedId}
                          onSelect={handleSelect}
                        />
                      </Section>
                      <Section title="Other candidates" icon={<Package className="size-4" />} i={3}>
                        <OtherCandidates 
                          data={data} 
                          selectedId={selectedId}
                          onSelect={handleSelect}
                        />
                      </Section>
                                          </div>
                  )}
                </AnimatePresence>
              </>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-glass-border py-6 text-center text-sm text-muted-foreground">
        AI proposes. Code decides.
      </footer>
    </div>
  );
}
