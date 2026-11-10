import { createContext, createElement, useContext, useEffect, useState, type ReactNode } from "react";

export interface Session { name: string; email: string; mode: "paypal" | "demo" }
export const SESSION_KEY = "mandate:session";
export const DEMO_KEY = "mandate:demo";
export const DEMO_SESSION: Session = { name: "Demo Buyer", email: "demo@mandate.app", mode: "demo" };
export function startPayPalLogin(): Session {
  // TODO: Replace this sandbox session with a redirect to `${API}/api/auth/paypal/login`.
  // Never collect PayPal credentials; a real session must be verified by the external backend.
  return { name: "PayPal Buyer", email: "buyer@mandate.app", mode: "paypal" };
}
export function readSession(): Session | null {
  try {
    const value = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
    return value && typeof value.name === "string" && typeof value.email === "string" &&
      (value.mode === "demo" || value.mode === "paypal") ? value : null;
  } catch { return null; }
}
export function persistSession(session: Session | null) {
  try {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  } catch { /* Storage may be unavailable; this session still works in memory. */ }
}
export function readDemo(): boolean {
  try {
    const value = localStorage.getItem(DEMO_KEY);
    return value === "true";
  } catch { return false; }
}
export function persistDemo(demo: boolean) {
  try {
    localStorage.setItem(DEMO_KEY, String(demo));
  } catch { /* Storage may be unavailable. */ }
}
interface AuthState {
  session: Session | null; ready: boolean; demo: boolean;
  setDemo: (value: boolean) => void; login: (mode: Session["mode"]) => void; signOut: () => void;
}
const AuthContext = createContext<AuthState | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [demo, setDemo] = useState(false);
  useEffect(() => {
    setSession(readSession());
    setDemo(readDemo());
    setReady(true);
  }, []);
  function login(mode: Session["mode"]) {
    const next = mode === "demo" ? { ...DEMO_SESSION } : startPayPalLogin();
    persistSession(next); setSession(next);
  }
  function setDemoValue(value: boolean) {
    setDemo(value);
    persistDemo(value);
  }
  function signOut() { persistSession(null); setSession(null); setDemoValue(true); }
  return createElement(AuthContext.Provider, { value: { session, ready, demo, setDemo: setDemoValue, login, signOut } }, children);
}
export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("AuthProvider is required");
  return auth;
}
