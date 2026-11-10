import { animate, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";
import { Star } from "lucide-react";
import type { Action } from "@/lib/types";
import { cn } from "@/lib/utils";

export const usd = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

export function CountUp({ value, className }: { value: number; className?: string }) {
  const reduce = useReducedMotion();
  const [v, setV] = useState(reduce ? value : 0);
  useEffect(() => {
    if (reduce) return setV(value);
    const c = animate(0, value, { duration: 1.1, ease: "easeOut", onUpdate: setV });
    return () => c.stop();
  }, [value, reduce]);
  return <span className={cn("tnum", className)}>{usd(v)}</span>;
}

export const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5 } }),
};

export function Section({ title, icon, children, i = 0 }: { title: string; icon: ReactNode; children: ReactNode; i?: number }) {
  return (
    <motion.section variants={fadeUp} initial="hidden" animate="show" custom={i} className="space-y-3">
      <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        {icon}
        {title}
      </h2>
      {children}
    </motion.section>
  );
}

export const actionStyles: Record<Action, { label: string; text: string; bg: string; border: string }> = {
  auto_pay: { label: "Auto pay", text: "text-ok", bg: "bg-ok/15", border: "border-l-ok" },
  needs_approval: { label: "Needs approval", text: "text-warn", bg: "bg-warn/15", border: "border-l-warn" },
  reject: { label: "Rejected", text: "text-bad", bg: "bg-bad/15", border: "border-l-bad" },
};

export function DecisionBadge({ action }: { action: Action }) {
  const s = actionStyles[action];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold", s.bg, s.text)}>
      <span className="size-1.5 rounded-full bg-current" />
      {s.label}
    </span>
  );
}

export function Rating({ value }: { value: number | null }) {
  if (value == null) return null;
  return (
    <span className="inline-flex items-center gap-1 text-sm text-muted-foreground tnum">
      <Star className="size-3.5 fill-warn text-warn" aria-hidden />
      {value.toFixed(1)}
    </span>
  );
}
