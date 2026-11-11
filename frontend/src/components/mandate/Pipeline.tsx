import { motion } from "framer-motion";
import { Check, FileText, Gavel, Scale, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const NODES = [
  { key: "Parse", icon: FileText },
  { key: "Search", icon: Search },
  { key: "Rules", icon: Scale },
  { key: "Decide", icon: Gavel },
];

export type PipelineStatus = "idle" | "running" | "done" | "error";

export function Pipeline({ status, lines }: { status: PipelineStatus; lines: string[] }) {
  const [step, setStep] = useState(0);
  const [typed, setTyped] = useState(0);

  useEffect(() => {
    if (status === "running") {
      setStep(0);
      const t = setInterval(() => setStep((s) => Math.min(s + 1, 3)), 550);
      return () => clearInterval(t);
    }
    if (status === "done") setStep(4);
    return undefined;
  }, [status]);

  useEffect(() => {
    setTyped(0);
    if (status !== "done") return;
    const t = setInterval(() => setTyped((n) => (n >= lines.length ? n : n + 1)), 260);
    return () => clearInterval(t);
  }, [status, lines]);

  const fill = status === "done" ? 100 : status === "idle" ? 0 : (step / 3) * 100;

  return (
    <div className="glass space-y-6 p-5 sm:p-6">
      <div className="relative">
        <div className="absolute left-[12.5%] right-[12.5%] top-6 h-0.5 bg-glass-border">
          <motion.div className="h-full bg-gradient-accent" animate={{ width: `${fill}%` }} transition={{ duration: 0.5 }} />
        </div>
        <ol className="relative grid grid-cols-4">
          {NODES.map((n, i) => {
            const done = status === "done" || (status === "running" && i < step) || (status === "error" && i < step);
            const active = status === "running" && i === step;
            const failed = status === "error" && i === step;
            const Icon = failed ? X : done ? Check : n.icon;
            return (
              <li key={n.key} className="flex flex-col items-center gap-2">
                <span
                  className={cn(
                    "relative grid size-12 place-items-center rounded-full border bg-background transition-colors",
                    done && "border-ok text-ok",
                    failed && "border-bad text-bad",
                    active && "border-blue text-blue",
                    !done && !failed && !active && "border-glass-border text-muted-foreground",
                  )}
                >
                  {active && <span className="absolute inset-0 animate-ping rounded-full border border-blue" />}
                  <Icon className="size-5" aria-hidden />
                </span>
                <span className="text-xs font-medium">{n.key}</span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}