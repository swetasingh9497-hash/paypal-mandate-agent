import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import { BarChart3, LogOut, ShoppingBag, ShieldCheck, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuItem } from "@/components/ui/dropdown-menu";

function Logo() {
  return (
    <span className="flex items-center gap-1.5 font-display text-xl font-bold">
      <img src="/logo.svg" alt="" className="size-6" />
      Mandate
    </span>
  );
}

function Wordmark() {
  return <span className="flex items-center gap-1.5 font-display text-xl font-bold">Mandate<span className="size-2 rounded-full bg-gradient-accent" /></span>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { session, ready, login, signOut, demo, setDemo } = useAuth();
  const location = useLocation(); const navigate = useNavigate(); const queryClient = useQueryClient();
  if (!ready) return <div className="grid min-h-screen place-items-center"><Loader2 aria-label="Loading account" className="size-6 animate-spin text-blue" /></div>;
  if (!session) return (
    <main className="dot-grid grid min-h-screen place-items-center px-4 py-8">
      <section className="glass w-full max-w-sm space-y-8 p-6 text-center sm:p-8">
        <div className="flex justify-center"><Logo /></div>
        <ShieldCheck className="mx-auto size-10 text-blue" aria-hidden />
        <h1 className="font-display text-2xl font-semibold">Sign in to your agent.</h1>
        <div className="space-y-3">
          <Button variant="paypal" className="h-12 w-full" onClick={() => login("paypal")}><span aria-hidden className="font-display text-lg font-bold italic">P</span>Continue with PayPal</Button>
          <Button variant="ghost" className="h-12 w-full" onClick={() => login("demo")}>Explore with demo account</Button>
        </div>
      </section>
    </main>
  );
  return (
    <>
      <header className="sticky top-0 z-40 border-b border-glass-border bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 py-3">
          <Logo />
          <nav aria-label="Main navigation" className="order-3 flex w-full gap-1 pt-1 sm:order-none sm:w-auto sm:pt-0">
            <Button asChild variant={location.pathname === "/" ? "secondary" : "ghost"}><Link to="/" aria-current={location.pathname === "/" ? "page" : undefined}><ShoppingBag />Shop</Link></Button>
            <Button asChild variant={location.pathname === "/spending" ? "secondary" : "ghost"}><Link to="/spending" aria-current={location.pathname === "/spending" ? "page" : undefined}><BarChart3 />Spending</Link></Button>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <label className="flex items-center gap-2 text-sm"><span className="hidden min-[400px]:inline">Demo data</span><Switch checked={demo} onCheckedChange={setDemo} aria-label="Demo data" /></label>
            <DropdownMenu>
              <DropdownMenuTrigger asChild><Button variant="secondary" size="icon" aria-label="Account menu" className="rounded-full font-semibold">{session.name.split(" ").map(n => n[0]).slice(0, 2).join("")}</Button></DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="max-w-[calc(100vw-2rem)]">
                <DropdownMenuLabel><div>{session.name}</div><div className="break-all text-xs font-normal text-muted-foreground">{session.email}</div></DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={async () => { await queryClient.cancelQueries(); queryClient.clear(); signOut(); try { sessionStorage.removeItem("mandate:chosen"); } catch { /* unavailable */ } await navigate({ to: "/", replace: true }); }}><LogOut />Sign out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>
      {children}
    </>
  );
}
