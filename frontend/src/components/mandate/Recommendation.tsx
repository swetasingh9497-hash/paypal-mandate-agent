import { motion } from "framer-motion";
import { useState } from "react";
import {
  CircleCheck,
  Lightbulb,
  Store,
  XCircle,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

import type { Candidate, RunResponse } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  CountUp,
  DecisionBadge,
  Rating,
  actionStyles,
} from "./shared";
import { formatAudit } from "@/lib/formatAudit";
import { formatMoney } from "@/lib/formatMoney";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

import { Button } from "@/components/ui/button";

import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";


function ProductRating({ value }: { value?: number | null }) {
  if (value == null) {
    return (
      <span className="text-sm text-muted-foreground">
        No rating available
      </span>
    );
  }

  return <Rating value={value} />;
}


// ==================================================
// AUDIT DISPLAY
// ==================================================

function SafeAudit({ data }: { data: RunResponse }) {
  try {
    if (!data.audit || data.audit.length === 0) return null;

    return (
      <div className="space-y-2 font-mono text-sm">
        {data.audit.map((a, i) => (
          <div key={i} className="flex gap-3">
            <span className="w-20 shrink-0 text-blue">
              {a.step}
            </span>
            <span className="break-words">
              {formatAudit(a)}
            </span>
          </div>
        ))}
      </div>
    );
  } catch {
    return (
      <div className="space-y-2 font-mono text-sm text-bad">
        <div className="flex gap-3">
          <span className="w-20 shrink-0 text-blue">error</span>
          <span className="break-words">
            Could not display this entry
          </span>
        </div>
      </div>
    );
  }
}


// ==================================================
// OTHER CANDIDATE CARD
// ==================================================

interface SelectableCardProps {
  candidate: Candidate;
  isSelected: boolean;
  onSelect: () => void;
  disabled?: boolean;
  rejectReason?: string;
  children?: React.ReactNode;
}

function SelectableCard({
  candidate,
  isSelected,
  onSelect,
  disabled,
  rejectReason,
  children,
}: SelectableCardProps) {
  const p = candidate.product;
  const styles = actionStyles[candidate.decision.action];

  return (
    <TooltipProvider>
      <button
        type="button"
        onClick={onSelect}
        disabled={disabled}
        className={cn(
          "relative w-full text-left glass glass-hover border-l-4 p-4 transition-all",
          styles.border,
          disabled && "opacity-50 cursor-not-allowed",
          !disabled && "cursor-pointer",
          isSelected &&
            "ring-2 ring-blue/50 shadow-[0_0_0_2px_rgba(0,156,222,0.3)]"
        )}
        aria-pressed={isSelected}
        aria-disabled={disabled}
      >
        <div className="flex items-start justify-between gap-3">
          <p className="font-medium leading-snug">
            {p.title}
          </p>

          <span className="font-display font-semibold tnum">
            {formatMoney(p.price, p.currency)}
          </span>
        </div>

        <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
          <span>{p.merchant}</span>
          <ProductRating value={p.rating} />
        </div>

        {children}

        {isSelected && (
          <div
            className="absolute inset-0 border-2 border-blue/30 rounded-r-lg pointer-events-none"
            aria-hidden
          />
        )}

        {disabled && rejectReason && (
          <Tooltip>
            <TooltipTrigger asChild>
              <AlertTriangle
                className="absolute top-2 right-2 size-4 text-bad/70"
                aria-hidden
              />
            </TooltipTrigger>

            <TooltipContent
              side="top"
              align="start"
              className="max-w-xs"
            >
              <p className="text-sm text-bad">
                {rejectReason}
              </p>
            </TooltipContent>
          </Tooltip>
        )}
      </button>
    </TooltipProvider>
  );
}


// ==================================================
// MAIN RECOMMENDATION COMPONENT
// ==================================================

export function Recommendation({
  data,
  onPay,
  selectedId,
  onSelect,
}: {
  data: RunResponse;
  onPay: (c: Candidate) => void;
  selectedId: string | null;
  onSelect: (c: Candidate) => void;
}) {

  // Original recommendation
  const chosen = data.candidates.find(
    (c) => c.product.id === data.chosen_id
  );

  // Currently selected product
  const selectedCandidate =
    data.candidates.find(
      (c) => c.product.id === selectedId
    ) ?? chosen;

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingCandidate, setPendingCandidate] =
    useState<Candidate | null>(null);

  const [paying, setPaying] = useState(false);

  const [payError, setPayError] =
    useState<string | null>(null);


  // ==================================================
  // COMPARISON STATE
  // ==================================================

  const showComparison = Boolean(
    chosen &&
    selectedCandidate &&
    selectedCandidate.product.id !== chosen.product.id
  );

  const priceDifference =
    showComparison && chosen && selectedCandidate
      ? selectedCandidate.product.price -
        chosen.product.price
      : 0;


  // ==================================================
  // PAYMENT HANDLING
  // ==================================================

  function handleContinue(candidate: Candidate) {

    if (candidate.decision.action === "reject") {
      return;
    }

    // Update the active selection
    onSelect(candidate);

    setPayError(null);

    // Manual approval required
    if (candidate.decision.action === "needs_approval") {
      setPendingCandidate(candidate);
      setConfirmOpen(true);
      return;
    }

    // Auto-pay candidate
    setPaying(true);

    try {
      onPay(candidate);
    } catch (error) {
      setPayError(
        error instanceof Error
          ? error.message
          : "Payment failed"
      );
      setPaying(false);
    }
  }


  function confirmPayment() {
    if (!pendingCandidate) return;

    const candidate = pendingCandidate;

    setConfirmOpen(false);
    setPendingCandidate(null);

    setPaying(true);

    try {
      onPay(candidate);
    } catch (error) {
      setPayError(
        error instanceof Error
          ? error.message
          : "Payment failed"
      );
      setPaying(false);
    }
  }


  // ==================================================
  // PAYMENT BUTTON
  // ==================================================

  function ContinueButton({
    candidate,
    labelMode = "comparison",
  }: {
    candidate: Candidate;
    labelMode?: "normal" | "comparison";
  }) {

    const rejected =
      candidate.decision.action === "reject";

    return (
      <Button
        type="button"
        disabled={rejected || paying}
        onClick={() => handleContinue(candidate)}
        className="w-full rounded-full bg-gold px-4 py-3 font-display font-bold text-navy hover:brightness-105 disabled:opacity-50"
      >
        {paying
          ? "Processing..."
          : rejected
            ? "Not eligible"
            : labelMode === "normal"
              ? `Review and Pay ${formatMoney(candidate.product.price, candidate.product.currency)}`
              : `Continue with this product · Pay ${formatMoney(candidate.product.price, candidate.product.currency)}`
        }
      </Button>
    );
  }


  // ==================================================
  // EMPTY STATE
  // ==================================================

  if (!chosen || !data.order) {

    const rejectReasons = Array.from(
      new Set(
        data.candidates
          .filter(
            (c) => c.decision.action === "reject"
          )
          .flatMap(
            (c) => c.decision.reasons
          )
      )
    );

    const nonRejected = data.candidates.some(
      (c) => c.decision.action !== "reject"
    );

    return (
      <div className="glass p-6">

        <div className="mb-4 flex items-center gap-2">
          <XCircle className="size-5 text-bad" />

          <h3 className="font-display text-lg font-semibold">
            No recommendation yet
          </h3>
        </div>

        {rejectReasons.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {rejectReasons.map((r) => (
              <span
                key={r}
                className="rounded-full bg-bad/15 px-3 py-1 text-xs text-bad"
              >
                {r}
              </span>
            ))}
          </div>
        )}

        {nonRejected && (
          <p className="text-sm text-muted-foreground">
            Pick a product below
          </p>
        )}

        {data.order_error && (
          <div className="mt-4 p-3 rounded-lg bg-bad/10 border border-bad/20 text-sm text-bad">
            {data.order_error}
          </div>
        )}

      </div>
    );
  }


  // ==================================================
  // ORIGINAL RECOMMENDATION
  // ==================================================

  const p = chosen.product;

  return (

    <div className="gradient-border overflow-hidden rounded-[20px]">

      {/* ==========================================
          COMPARISON MODE
          Original recommendation + User selection
      ========================================== */}

      {showComparison && selectedCandidate ? (

        <div className="p-5 sm:p-7">

          <div className="mb-5">

            <h3 className="font-display text-xl font-semibold">
              Compare your choices
            </h3>

            <p className="mt-1 text-sm text-muted-foreground">
              Compare both products and continue with the one you prefer.
            </p>

          </div>


          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">

            {/* RECOMMENDED PRODUCT */}

            <div
              className={cn(
                "flex flex-col rounded-xl border p-4 transition-all",
                selectedId === chosen.product.id
                  ? "border-ok ring-2 ring-ok/30 bg-ok/5"
                  : "border-ok/30 bg-ok/5"
              )}
            >

              <div className="mb-3 flex items-center gap-2">
                <CheckCircle className="size-4 text-ok" />

                <span className="text-xs font-semibold uppercase tracking-wider text-ok">
                  Recommended
                </span>
              </div>

              <h4 className="font-semibold leading-snug">
                {chosen.product.title}
              </h4>

              <p className="mt-2 text-sm text-muted-foreground">
                {chosen.product.merchant}
              </p>

              <p className="mt-4 font-display text-3xl font-bold tnum">
                {formatMoney(chosen.product.price, chosen.product.currency)}
              </p>

              <div className="mt-2">
                <ProductRating value={chosen.product.rating} />
              </div>

              <div className="mt-3">
                <DecisionBadge
                  action={chosen.decision.action}
                />
              </div>

              <div className="mt-auto pt-5">
                <ContinueButton candidate={chosen} labelMode="comparison" />
              </div>

            </div>


            {/* USER SELECTED PRODUCT */}

            <div
              className={cn(
                "flex flex-col rounded-xl border p-4 transition-all",
                selectedId === selectedCandidate.product.id
                  ? "border-blue ring-2 ring-blue/30 bg-blue/5"
                  : "border-blue/40 bg-blue/5"
              )}
            >

              <div className="mb-3 flex items-center gap-2">
                <CheckCircle className="size-4 text-blue" />

                <span className="text-xs font-semibold uppercase tracking-wider text-blue">
                  Your pick
                </span>
              </div>

              <h4 className="font-semibold leading-snug">
                {selectedCandidate.product.title}
              </h4>

              <p className="mt-2 text-sm text-muted-foreground">
                {selectedCandidate.product.merchant}
              </p>

              <p className="mt-4 font-display text-3xl font-bold tnum">
                {formatMoney(selectedCandidate.product.price, selectedCandidate.product.currency)}
              </p>

              <div className="mt-2">
                <ProductRating value={selectedCandidate.product.rating} />
              </div>

              <div className="mt-3">
                <DecisionBadge
                  action={selectedCandidate.decision.action}
                />
              </div>

              <div className="mt-auto pt-5">
                <ContinueButton candidate={selectedCandidate} labelMode="comparison" />
              </div>

            </div>

          </div>


          {/* PRICE DIFFERENCE */}

          <div className="mt-5 rounded-xl bg-muted/60 p-5 text-center">

            <p
              className={cn(
                "font-display text-2xl font-bold tnum",
                priceDifference > 0 && "text-warn",
                priceDifference < 0 && "text-ok"
              )}
            >
              {priceDifference > 0
                ? `+${formatMoney(priceDifference, chosen.product.currency)}`
                : priceDifference < 0
                  ? `-${formatMoney(Math.abs(priceDifference), chosen.product.currency)}`
                  : formatMoney(0, chosen.product.currency)}
            </p>

            <p className="mt-1 text-xs uppercase tracking-wider text-muted-foreground">
              {priceDifference > 0
                ? "More expensive than recommended"
                : priceDifference < 0
                  ? "Cheaper than recommended"
                  : "Same price as recommended"}
            </p>

            <p className="mt-1 text-xs text-muted-foreground">
              Compared with Budgie's original recommendation
            </p>

          </div>


          {/* CLEAR COMPARISON */}

          <div className="mt-4 flex justify-center">

            <Button
              variant="outline"
              onClick={() => onSelect(chosen)}
              className="rounded-full"
            >
              <XCircle className="mr-2 size-4" />
              Clear comparison
            </Button>

          </div>

        </div>

      ) : (

        /* ==========================================
           NORMAL RECOMMENDATION MODE
           Only one product card
        ========================================== */

        <>

          <div className="grid gap-6 p-5 sm:p-7 md:grid-cols-2">

            <div className="space-y-3">

              <DecisionBadge
                action={chosen.decision.action}
              />

              <div className="flex items-center gap-2">

                <h3 className="font-display text-xl font-semibold sm:text-2xl">
                  {p.title}
                </h3>

                <span className="inline-flex items-center gap-1 rounded-full bg-ok/10 text-ok px-2 py-0.5 text-xs font-medium">
                  <CheckCircle className="size-3" />
                  Recommended
                </span>

              </div>

              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Store className="size-4" />
                {p.merchant}
              </p>

              <CountUp
                value={p.price}
                className="block font-display text-4xl font-bold sm:text-5xl"
              />

              <ProductRating value={p.rating} />

            </div>


            <div className="space-y-5">

              <div>

                <p className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
                  Rules passed
                </p>

                <ul className="space-y-2">

                  {chosen.decision.reasons.map((r, i) => (

                    <motion.li
                      key={`${r}-${i}`}
                      initial={{ opacity: 0, x: 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{
                        delay: 0.3 + i * 0.12,
                      }}
                      className="flex items-center gap-2 text-sm"
                    >
                      <CircleCheck className="size-4 shrink-0 text-ok" />
                      {r}
                    </motion.li>

                  ))}

                </ul>

              </div>


              {data.explanation?.summary && (

                <div>

                  <p className="mb-1 flex items-center gap-1.5 text-xs uppercase tracking-widest text-muted-foreground">
                    <Lightbulb className="size-3.5" />
                    Why this one
                  </p>

                  <p className="text-sm">
                    {data.explanation.summary}
                  </p>

                </div>

              )}

            </div>

          </div>


          <div className="perforated h-3.5 bg-glass-border/40" aria-hidden />

          <div className="bg-muted p-5 sm:p-6">

            {data.order_error && (
              <div className="mb-3 p-3 rounded-lg bg-bad/10 border border-bad/20 text-sm text-bad">
                {data.order_error}
              </div>
            )}

            <ContinueButton candidate={chosen} labelMode="normal" />

            {chosen.decision.action === "auto_pay" &&
              data.mandate.auto_approve_under != null && (

                <p className="mt-3 text-xs text-muted-foreground text-center">
                  Within your{" "}
                  {formatMoney(data.mandate.auto_approve_under)}{" "}
                  auto-approve limit
                </p>

              )}

          </div>

        </>

      )}


      {/* ==========================================
          PAYMENT CONFIRMATION DIALOG
      ========================================== */}

      <Dialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
      >

        <DialogContent className="max-w-md">

          <DialogHeader>

            <DialogTitle>
              Approve payment
            </DialogTitle>

            <DialogDescription>
              You are approving payment for{" "}
              <strong>
                {pendingCandidate?.product.title}
              </strong>
              .
            </DialogDescription>

          </DialogHeader>


          {pendingCandidate && (

            <div className="mt-3 space-y-3">

              <div className="rounded-xl bg-muted p-4">

                <p className="text-sm text-muted-foreground">
                  Selected product
                </p>

                <p className="mt-1 font-semibold">
                  {pendingCandidate.product.title}
                </p>

                <p className="mt-2 font-display text-2xl font-bold">
                  {formatMoney(
                    pendingCandidate.product.price,
                    pendingCandidate.product.currency
                  )}
                </p>

              </div>

              <ul className="space-y-2 text-sm">

                {pendingCandidate.decision.reasons.map((r, i) => (

                  <li
                    key={`${r}-${i}`}
                    className="flex items-center gap-2 text-muted-foreground"
                  >
                    <AlertTriangle className="size-4 shrink-0 text-warn" />
                    {r}
                  </li>

                ))}

              </ul>

            </div>

          )}


          <DialogFooter className="gap-2">

            <Button
              variant="outline"
              onClick={() => {
                setConfirmOpen(false);
                setPendingCandidate(null);
              }}
            >
              Cancel
            </Button>

            <Button
              onClick={confirmPayment}
              disabled={paying || !pendingCandidate}
            >
              Approve and continue
            </Button>

          </DialogFooter>

        </DialogContent>

      </Dialog>


      {payError && (
        <div
          role="alert"
          className="m-4 rounded-lg border border-bad/20 bg-bad/10 p-3 text-sm text-bad"
        >
          {payError}
        </div>
      )}

    </div>
  );
}


// ==================================================
// OTHER CANDIDATES
// ==================================================

export function OtherCandidates({
  data,
  selectedId,
  onSelect,
}: {
  data: RunResponse;
  selectedId: string | null;
  onSelect: (c: Candidate) => void;
}) {

  const others = data.candidates.filter(
    (c) => c.product.id !== data.chosen_id
  );

  return (

    <div className="grid gap-3 sm:grid-cols-2">

      {others.map((c) => {

        const rejected =
          c.decision.action === "reject";

        const isSelected =
          selectedId === c.product.id;

        const note =
          data.explanation?.notes?.[c.product.id];

        const rejectReason = rejected
          ? c.decision.reasons.join("; ")
          : undefined;

        return (

          <SelectableCard
            key={c.product.id}
            candidate={c}
            isSelected={isSelected}
            onSelect={() => onSelect(c)}
            disabled={rejected}
            rejectReason={rejectReason}
          >

            {note && (
              <p className="mt-2 text-sm">
                {note}
              </p>
            )}

            {rejected && (
              <p className="mt-1 text-sm text-bad">
                {c.decision.reasons.join("; ")}
              </p>
            )}

          </SelectableCard>

        );

      })}

    </div>
  );
}


export { SafeAudit };
