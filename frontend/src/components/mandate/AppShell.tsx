import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import { BarChart3, LogOut, ShoppingBag, ShieldCheck, Loader2, Eye, EyeOff, Mail, Lock, User } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuItem } from "@/components/ui/dropdown-menu";

function Logo() {
  return (
    <span className="flex items-center gap-1.5 font-display text-xl font-bold">
      <img src="/logo.svg" alt="Budgie" className="size-6" />
      Budgie
    </span>
  );
}

function Wordmark() {
  return <span className="flex items-center gap-1.5 font-display text-xl font-bold">Budgie<span className="size-2 rounded-full bg-gradient-accent" /></span>;
}

function LoginScreen({ onLogin, onRegister, onDemo, onError, loginError, registerError }: {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, name?: string) => Promise<void>;
  onDemo: () => Promise<void>;
  onError: () => void;
  loginError?: string | undefined;
  registerError?: string | undefined;
}) {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const setActiveTabWrapper = (value: "login" | "register") => setActiveTab(value);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError();
    setSubmitting(true);
    try {
      if (activeTab === "login") {
        await onLogin(email, password);
      } else {
        await onRegister(email, password, name || undefined);
      }
    } catch (err) {
      // Error handled by parent
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="dot-grid grid min-h-screen place-items-center px-4 py-8">
      <section className="glass w-full max-w-sm space-y-8 p-6 text-center sm:p-8">
        <div className="flex justify-center"><Wordmark /></div>
        <ShieldCheck className="mx-auto size-10 text-blue" aria-hidden />
        <h1 className="font-display text-2xl font-semibold">Welcome to Budgie</h1>

        <Tabs value={activeTab} onValueChange={setActiveTabWrapper} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">Sign in</TabsTrigger>
            <TabsTrigger value="register">Create account</TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <form onSubmit={handleSubmit} className="space-y-4 mt-4 text-left">
              {(loginError) && (
                <div className="rounded-lg bg-bad/10 border border-bad/20 p-3 text-sm text-bad" role="alert">
                  {loginError}
                </div>
              )}
              <div className="space-y-2">
                <label className="flex flex-col gap-1.5 text-sm font-medium">
                  Email
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" aria-hidden />
                    <Input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      autoComplete="email"
                      className="pl-10"
                      required
                      disabled={submitting}
                    />
                  </div>
                </label>
                <label className="flex flex-col gap-1.5 text-sm font-medium">
                  Password
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" aria-hidden />
                    <Input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="current-password"
                      className="pl-10 pr-10"
                      required
                      disabled={submitting}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </button>
                  </div>
                </label>
              </div>
              <Button type="submit" className="w-full h-12" disabled={submitting}>
                {submitting ? <Loader2 className="size-4 animate-spin mx-auto" /> : "Sign in"}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="register">
            <form onSubmit={handleSubmit} className="space-y-4 mt-4 text-left">
              {(registerError) && (
                <div className="rounded-lg bg-bad/10 border border-bad/20 p-3 text-sm text-bad" role="alert">
                  {registerError}
                </div>
              )}
              <div className="space-y-2">
                <label className="flex flex-col gap-1.5 text-sm font-medium">
                  Name (optional)
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" aria-hidden />
                    <Input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Your name"
                      autoComplete="name"
                      className="pl-10"
                      disabled={submitting}
                    />
                  </div>
                </label>
                <label className="flex flex-col gap-1.5 text-sm font-medium">
                  Email
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" aria-hidden />
                    <Input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      autoComplete="email"
                      className="pl-10"
                      required
                      disabled={submitting}
                    />
                  </div>
                </label>
                <label className="flex flex-col gap-1.5 text-sm font-medium">
                  Password
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" aria-hidden />
                    <Input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className="pl-10 pr-10"
                      required
                      disabled={submitting}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </button>
                  </div>
                </label>
              </div>
              <Button type="submit" className="w-full h-12" disabled={submitting}>
                {submitting ? <Loader2 className="size-4 animate-spin mx-auto" /> : "Create account"}
              </Button>
            </form>
          </TabsContent>
        </Tabs>

        <Button variant="ghost" className="w-full h-12" onClick={onDemo} disabled={submitting}>
          Explore with demo account
        </Button>
      </section>
    </main>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { session, ready, login, register, demoLogin, signOut, demo, setDemo } = useAuth();
  const location = useLocation(); const navigate = useNavigate(); const queryClient = useQueryClient();
  const [loginError, setLoginError] = useState<string | undefined>(undefined);
  const [registerError, setRegisterError] = useState<string | undefined>(undefined);

  if (!ready) return <div className="grid min-h-screen place-items-center"><Loader2 aria-label="Loading account" className="size-6 animate-spin text-blue" /></div>;

  if (!session) return (
    <LoginScreen
      onLogin={async (email, password) => {
        try {
          await login(email, password);
        } catch (err) {
          setLoginError(err instanceof Error ? err.message : "Sign in failed");
        }
      }}
      onRegister={async (email, password, name) => {
        try {
          await register(email, password, name);
        } catch (err) {
          setRegisterError(err instanceof Error ? err.message : "Registration failed");
        }
      }}
      onDemo={async () => {
        try {
          await demoLogin();
        } catch (err) {
          setLoginError(err instanceof Error ? err.message : "Demo login failed");
        }
      }}
      onError={() => { setLoginError(undefined); setRegisterError(undefined); }}
      loginError={loginError}
      registerError={registerError}
    />
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
              <DropdownMenuTrigger asChild><Button variant="secondary" size="icon" aria-label="Account menu" className="rounded-full font-semibold">{session.user.name?.split(" ").map(n => n[0]).slice(0, 2).join("") || session.user.email?.[0]?.toUpperCase()}</Button></DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="max-w-[calc(100vw-2rem)]">
                <DropdownMenuLabel><div>{session.user.name}</div><div className="break-all text-xs font-normal text-muted-foreground">{session.user.email}</div></DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={async () => { await queryClient.cancelQueries(); queryClient.clear(); signOut(); try { sessionStorage.removeItem("budgie:chosen"); } catch { /* unavailable */ } await navigate({ to: "/", replace: true }); }}><LogOut />Sign out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>
      {children}
    </>
  );
}