import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { getSpending } from "@/lib/api";
import { SpendingOverview } from "@/components/mandate/SpendingOverview";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/spending")({
  head: () => ({ meta: [
    { title: "Spending — Mandate" },
    { name: "description", content: "Your Mandate spending, monthly cap, and recent shopping orders." },
    { property: "og:title", content: "Spending — Mandate" },
    { property: "og:description", content: "Track weekly and monthly spending and your agent's purchases." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }), component: SpendingPage,
});
function SpendingPage() {
  const { session, demo } = useAuth();
  const queryClient = useQueryClient();
  // Local sandbox identity exists only after hydration; do not fetch private history during SSR.
  const query = useQuery({ 
    queryKey: ["spending", session?.email, demo], 
    queryFn: () => getSpending(session?.email ?? "", demo), 
    enabled: !!session, 
    staleTime: 0, 
    retry: false 
  });
  
  // Refetch when returning from receipt
  const refetch = () => queryClient.invalidateQueries({ queryKey: ["spending"] });
  
  return <main className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
    {query.isPending ? <div role="status" className="flex items-center justify-center gap-2 py-24 text-muted-foreground"><Loader2 className="size-5 animate-spin" />Loading spending</div>
      : query.isError ? <div role="alert" className="space-y-4 rounded-lg border border-bad/40 bg-bad/10 p-5"><p className="break-words text-sm">{query.error.message}</p><Button variant="outline" onClick={() => query.refetch()}><RefreshCw />Try again</Button></div>
      : <SpendingOverview data={query.data} onRefetch={refetch} />}
  </main>;
}
