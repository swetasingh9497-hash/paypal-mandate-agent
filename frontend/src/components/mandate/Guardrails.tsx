import { BadgeCheck, Clock, ShieldCheck, Star, Wallet, Zap } from "lucide-react";
import * as Tooltip from "@radix-ui/react-tooltip";
import type { Candidate, Mandate } from "@/lib/types";
import { cn } from "@/lib/utils";
import { usd } from "./shared";

export function Guardrails({ mandate }: { mandate: Mandate }) {
  const chips = [
    { icon: Wallet, label: "Budget", value: usd(mandate.max_total) },
    mandate.min_rating != null && { icon: Star, label: "Min rating", value: `${mandate.min_rating}+` },
    mandate.max_delivery_days != null && { icon: Clock, label: "Delivery", value: `${mandate.max_delivery_days} days` },
    { icon: Zap, label: "Auto-approve", value: `< ${usd(mandate.auto_approve_under)}` },
  ].filter(Boolean) as { icon: typeof Wallet; label: string; value: string }[];

  return (
    <div className="glass relative overflow-hidden p-5 sm:p-6">
      <ShieldCheck className="absolute -right-6 -top-6 size-32 text-glass-border" aria-hidden />
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Mandate for</p>
          <p className="font-display text-xl font-semibold capitalize">{mandate.item}</p>
        </div>
        <BadgeCheck className="size-8 text-blue" aria-hidden />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {chips.map((c) => (
          <div key={c.label} className="rounded-xl border border-glass-border bg-muted p-3">
            <c.icon className="mb-2 size-4 text-blue" aria-hidden />
            <p className="text-xs text-muted-foreground">{c.label}</p>
            <p className="font-semibold tnum">{c.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PriceZone({ mandate, candidates, chosenId }: { mandate: Mandate; candidates: Candidate[]; chosenId: string | null }) {
  const maxPrice = Math.max(mandate.max_total, ...candidates.map((c) => c.product.price));
  const scale = maxPrice * 1.1;
  const pct = (n: number) => `${Math.min(100, (n / scale) * 100)}%`;
  const chosen = candidates.find((c) => c.product.id === chosenId);

  return (
    <Tooltip.Provider delayDuration={100}>
      <div className="glass p-5 pb-10 sm:p-6 sm:pb-10">
        <div className="relative mt-10 h-3 rounded-full">
          <div className="absolute inset-y-0 left-0 rounded-l-full bg-ok/40" style={{ width: pct(mandate.auto_approve_under) }} />
          <div className="absolute inset-y-0 bg-warn/40" style={{ left: pct(mandate.auto_approve_under), width: `calc(${pct(mandate.max_total)} - ${pct(mandate.auto_approve_under)})` }} />
          <div className="absolute inset-y-0 right-0 rounded-r-full bg-bad/40" style={{ left: pct(mandate.max_total) }} />
          {candidates.map((c) => {
            const isChosen = c.product.id === chosenId;
            return (
              <Tooltip.Root key={c.product.id}>
                <Tooltip.Trigger asChild>
                  <button
                    aria-label={`${c.product.title}, ${usd(c.product.price)}`}
                    className={cn(
                      "absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background",
                      isChosen ? "z-10 size-5 bg-foreground shadow-[0_0_20px_4px_var(--blue)]" : "size-3 bg-foreground/70",
                    )}
                    style={{ left: pct(c.product.price) }}
                  />
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content sideOffset={8} className="z-50 rounded-lg border border-glass-border bg-popover px-3 py-1.5 text-xs">
                    {c.product.title} · <span className="tnum">{usd(c.product.price)}</span>
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            );
          })}
          {chosen && (
            <span className="absolute -top-9 -translate-x-1/2 rounded-md bg-gradient-accent px-2 py-0.5 text-xs font-semibold tnum" style={{ left: pct(chosen.product.price) }}>
              {usd(chosen.product.price)}
            </span>
          )}
        </div>
        <div className="relative mt-3 text-xs text-muted-foreground tnum">
          <span className="absolute left-0">$0</span>
          <span className="absolute -translate-x-1/2 text-ok" style={{ left: pct(mandate.auto_approve_under) }}>{usd(mandate.auto_approve_under)}</span>
          <span className="absolute -translate-x-1/2 text-warn" style={{ left: pct(mandate.max_total) }}>{usd(mandate.max_total)}</span>
        </div>
      </div>
    </Tooltip.Provider>
  );
}
