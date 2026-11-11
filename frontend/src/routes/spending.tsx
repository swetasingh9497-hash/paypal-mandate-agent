import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { getSpending } from "@/lib/api";
import { SpendingOverview } from "@/components/mandate/SpendingOverview";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/spending")({
  head: () => ({ meta: [
    { title: "Spending — Budgie" },
    { name: "description", content: "Your Budgie spending, monthly cap, and recent shopping orders." },
    { property: "og:title", content: "Spending — Budgie" },
    { property: "og:description", content: "Track weekly and monthly spending and your agent's purchases." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }), component: SpendingPage,
});
function SpendingPage() {
  const { session, demo } = useAuth();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["spending", demo],
    queryFn: () => getSpending(demo),
    enabled: !!session,
    staleTime: 0,
    retry: false
  });

  // Refetch when returning from receipt
  const refetch = () => queryClient.invalidateQueries({ queryKey: ["spending"] });

  return <main className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
    <div className="mb-6 flex items-center justify-between gap-3">
      <h1 className="font-display text-3xl font-semibold">Spending</h1>
      {session && <span className="text-sm text-muted-foreground">{session.user.email}</span>}
    </div>
    {query.isPending ? <div role="status" className="flex items-center justify-center gap-2 py-24 text-muted-foreground"><Loader2 className="size-5 animate-spin" />Loading spending</div>
      : query.isError ? <div role="alert" className="space-y-4 rounded-lg border border-bad/40 bg-bad/10 p-5"><p className="break-words text-sm">{query.error.message}</p><Button variant="outline" onClick={() => query.refetch()}><RefreshCw />Try again</Button></div>
      : <SpendingOverview data={query.data} onRefetch={refetch} />}
  </main>;
}
