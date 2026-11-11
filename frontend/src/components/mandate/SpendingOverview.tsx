import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { ArrowUpRight, BarChart3, CreditCard, DollarSign, ShieldCheck, ShoppingBag, RotateCw } from "lucide-react";
import { formatDistanceToNow, isValid, parseISO } from "date-fns";
import { capTone, type SpendingData } from "@/lib/spending";
import { cn } from "@/lib/utils";
import { DecisionBadge } from "./shared";
import { formatMoney } from "@/lib/formatMoney";
import { SpendingCharts } from "./SpendingCharts";
import { Button } from "@/components/ui/button";

function AnimatedValue({ value, format }: { value: number; format: (v: number) => string }) {
  const reduce = useReducedMotion(); const [current, setCurrent] = useState(value);
  useEffect(() => { if (reduce) { setCurrent(value); return; } const controls = animate(0, value, { duration: 0.9, onUpdate: setCurrent }); return () => controls.stop(); }, [value, reduce]);
  return <span className="tnum">{format(current)}</span>;
}
const integer = (v: number) => Math.round(v).toLocaleString("en-US");
const percent = (v: number) => `${Math.round(v * 100)}%`;
function relativeDate(value: string) {
  const date = parseISO(value); return isValid(date) ? formatDistanceToNow(date, { addSuffix: true }) : "Date unavailable";
}
export function SpendingOverview({ data, onRefetch }: { data: SpendingData; onRefetch?: () => void }) {
  const samples = data.orders.some(o => o.demo); const cap = data.monthly_cap;
  const tone = cap === null ? "ok" : capTone(data.kpis.month_total, cap);
  const meter = { ok: "bg-ok", warn: "bg-warn", bad: "bg-bad" };
  const kpis = [
    { label: "This month", value: data.kpis.month_total, format: formatMoney, icon: DollarSign },
    { label: "Orders", value: data.kpis.order_count, format: integer, icon: ShoppingBag },
    { label: "Avg order", value: data.kpis.avg_order, format: formatMoney, icon: CreditCard },
    { label: "Auto-approved", value: data.kpis.auto_pay_share, format: percent, icon: ShieldCheck },
  ];
  return <div className="space-y-7">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="font-display text-3xl font-semibold">Spending</h1>
      {samples && <span className="inline-flex items-center gap-1.5 rounded-full border border-glass-border bg-muted px-3 py-1.5 text-xs text-muted-foreground"><BarChart3 className="size-3.5" />Includes sample history</span>}
      {onRefetch && <Button variant="outline" size="sm" onClick={onRefetch} className="gap-1"><RotateCw className="size-3.5" />Refresh</Button>}
    </div>
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{kpis.map(({ label, value, format, icon: Icon }) => <section key={label} className="glass min-w-0 p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-1 text-muted-foreground"><span className="text-xs sm:text-sm">{label}</span><Icon className="size-4 shrink-0" /></div>
      <div className="flex items-center justify-between gap-1"><p className="font-display text-2xl font-semibold"><AnimatedValue value={value} format={format} /></p><ArrowUpRight className="size-4 shrink-0 text-blue" aria-hidden /></div>
    </section>)}</div>
    {cap !== null && <section className="space-y-3 py-2" aria-label="Monthly cap">
      <div className="flex flex-wrap justify-between gap-2 text-sm"><h2 className="font-semibold">Monthly cap</h2><span className="tnum text-muted-foreground">{formatMoney(data.kpis.month_total)} <span className="text-foreground">of {formatMoney(cap)}</span></span></div>
      <div role="progressbar" aria-label="Monthly cap usage" aria-valuemin={0} aria-valuemax={cap || 1} aria-valuenow={Math.min(data.kpis.month_total, cap || 1)} aria-valuetext={`${formatMoney(data.kpis.month_total)} of ${formatMoney(cap)}`} className="h-2.5 overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full transition-all duration-700", meter[tone])} style={{ width: `${cap > 0 ? Math.min(100, data.kpis.month_total / cap * 100) : data.kpis.month_total > 0 ? 100 : 0}%` }} /></div>
    </section>}
    <SpendingCharts data={data} />
    <section>
      <h2 className="mb-3 font-display text-lg font-semibold">Recent orders</h2>
      {data.orders.length ? <ul className="divide-y divide-glass-border">{data.orders.map((order, i) => <li key={`${order.id}-${i}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-3 gap-y-2 py-4">
        <div className="min-w-0"><p className="break-words font-medium">{order.title}</p><p className="mt-1 text-xs text-muted-foreground">{order.merchant} · {relativeDate(order.captured_at)}</p></div>
        <span className="tnum font-semibold">{formatMoney(order.amount)}{order.currency !== "USD" && <span className="ml-1 text-xs text-muted-foreground">{order.currency}</span>}</span>
        <div className="col-span-2 flex items-center gap-2"><DecisionBadge action={order.action} />{order.demo && <span className="rounded border border-glass-border px-1.5 py-0.5 text-xs text-muted-foreground">Sample</span>}</div>
      </li>)}</ul> : <div className="py-12 text-center text-sm text-muted-foreground">No orders yet</div>}
    </section>
  </div>;
}
