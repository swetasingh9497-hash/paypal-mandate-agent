import { useId } from "react";
import { useReducedMotion } from "framer-motion";
import { Area, AreaChart, Bar, BarChart, Cell, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SpendingData } from "@/lib/spending";
import { usd } from "./shared";

function SpendingTooltip({ active, payload, label }: { active?: boolean; payload?: readonly { value?: number | string }[]; label?: string | number }) {
  if (!active || !payload?.length) return null;
  return <div className="rounded-lg border border-glass-border bg-popover px-3 py-2 text-sm shadow-md"><p className="text-muted-foreground">{label}</p><p className="font-semibold tnum">{usd(Number(payload[0]?.value) || 0)}</p></div>;
}
export function SpendingCharts({ data }: { data: SpendingData }) {
  const id = useId().replace(/:/g, ""); const reduce = useReducedMotion();
  return <div className="grid min-w-0 gap-5 md:grid-cols-2">
    <section className="glass min-w-0 p-5" aria-label="Weekly spending chart">
      <h2 className="mb-6 font-display text-base font-semibold">Weekly spending</h2>
      <div className="spending-chart h-56" role="img" aria-label={data.weekly.length ? data.weekly.map(p => `${p.label}: ${usd(p.total)}`).join(", ") : "No weekly spending"}>
        {data.weekly.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={data.weekly} margin={{ top: 8, right: 0, bottom: 0, left: -16 }}>
          <defs><linearGradient id={`${id}-bars`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--blue)" /><stop offset="100%" stopColor="var(--violet)" stopOpacity={0.45} /></linearGradient><linearGradient id={`${id}-current`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--ok)" /><stop offset="100%" stopColor="var(--blue)" stopOpacity={0.6} /></linearGradient></defs>
          <XAxis dataKey="label" axisLine={false} tickLine={false} interval={0} /><YAxis axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} width={50} />
          <Tooltip content={<SpendingTooltip />} />
          <Bar dataKey="total" radius={[5, 5, 0, 0]} maxBarSize={34} isAnimationActive={!reduce} animationDuration={900}>{data.weekly.map((p, i) => <Cell key={`${p.label}-${i}`} fill={`url(#${id}-${i === data.weekly.length - 1 ? "current" : "bars"})`} />)}</Bar>
        </BarChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No weekly spending</div>}
      </div>
    </section>
    <section className="glass min-w-0 p-5" aria-label="Monthly spending chart">
      <h2 className="mb-6 font-display text-base font-semibold">Monthly spending</h2>
      <div className="spending-chart h-56" role="img" aria-label={data.monthly.length ? data.monthly.map(p => `${p.label}: ${usd(p.total)}`).join(", ") : "No monthly spending"}>
        {data.monthly.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={data.monthly} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <defs><linearGradient id={`${id}-area`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--blue)" stopOpacity={0.4} /><stop offset="100%" stopColor="var(--blue)" stopOpacity={0.02} /></linearGradient></defs>
          <CartesianGrid vertical={false} stroke="var(--glass-border)" strokeDasharray="3 6" />
          <XAxis dataKey="label" axisLine={false} tickLine={false} /><YAxis axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} width={50} domain={[0, (max: number) => Math.max(max, data.monthly_cap ?? 0)]} />
          <Tooltip content={<SpendingTooltip />} />
          {data.monthly_cap !== null && <ReferenceLine y={data.monthly_cap} stroke="var(--warn)" strokeDasharray="5 5" />}
          <Area type="monotone" dataKey="total" stroke="var(--blue)" strokeWidth={2} fill={`url(#${id}-area)`} dot={{ r: 3, fill: "var(--blue)", stroke: "var(--background)", strokeWidth: 2 }} isAnimationActive={!reduce} animationDuration={1000} />
        </AreaChart></ResponsiveContainer> : <div className="grid h-full place-items-center text-sm text-muted-foreground">No monthly spending</div>}
      </div>
    </section>
  </div>;
}