import { createContext, createElement, useContext, useEffect, useState, type ReactNode } from "react";

export interface User {
  email: string;
  name: string;
}

export interface AuthSession {
  token: string;
  user: User;
}

export const SESSION_KEY = "budgie:session";
export const DEMO_KEY = "budgie:demo";

export function readSession(): AuthSession | null {
  try {
    const value = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
    return value && typeof value.token === "string" && value.user && typeof value.user.email === "string" && typeof value.user.name === "string"
      ? value
      : null;
  } catch { return null; }
}

export function persistSession(session: AuthSession | null) {
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
  session: AuthSession | null;
  ready: boolean;
  demo: boolean;
  setDemo: (value: boolean) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  demoLogin: () => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const API_URL = (import.meta.env["VITE_API_URL"] as string | undefined) || "http://127.0.0.1:8000";

async function fetchWithAuth(path: string, options: RequestInit = {}): Promise<Response> {
  const session = readSession();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const sessionData = readSession();
  if (sessionData) {
    headers.set("Authorization", `Bearer ${sessionData.token}`);
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  return res;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [ready, setReady] = useState(false);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    const storedSession = readSession();
    const storedDemo = readDemo();
    setSession(storedSession);
    setDemo(storedDemo);

    // If we have a session, verify it with the backend
    if (storedSession) {
      fetchWithAuth("/api/auth/me")
        .then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            setSession({ token: storedSession.token, user: data.user });
          } else {
            persistSession(null);
            setSession(null);
          }
        })
        .catch(() => {
          persistSession(null);
          setSession(null);
        })
        .finally(() => setReady(true));
    } else {
      setReady(true);
    }
  }, []);

  async function login(email: string, password: string) {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = data && typeof data === "object" && "detail" in data ? data.detail : data ?? `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const authSession = { token: data.token, user: data.user };
    persistSession(authSession);
    setSession(authSession);
  }

  async function register(email: string, password: string, name?: string) {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = data && typeof data === "object" && "detail" in data ? data.detail : data ?? `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const authSession = { token: data.token, user: data.user };
    persistSession(authSession);
    setSession(authSession);
  }

  async function demoLogin() {
    const res = await fetch(`${API_URL}/api/auth/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = data && typeof data === "object" && "detail" in data ? data.detail : data ?? `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const authSession = { token: data.token, user: data.user };
    persistSession(authSession);
    setSession(authSession);
    setDemoValue(true);
  }

  function setDemoValue(value: boolean) {
    setDemo(value);
    persistDemo(value);
  }

  function signOut() {
    persistSession(null);
    setSession(null);
    setDemoValue(true);
  }

  return createElement(AuthContext.Provider, { value: { session, ready, demo, setDemo: setDemoValue, login, register, demoLogin, signOut } }, children);
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("AuthProvider is required");
  return auth;
}