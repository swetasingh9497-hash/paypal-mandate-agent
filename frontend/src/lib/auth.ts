import { formatDetail } from "@/lib/formatDetail";
import {
  createContext,
  createElement,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

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

    return value &&
      typeof value.token === "string" &&
      value.user &&
      typeof value.user.email === "string" &&
      typeof value.user.name === "string"
      ? value
      : null;
  } catch {
    return null;
  }
}

export function persistSession(session: AuthSession | null) {
  try {
    if (session) {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
  } catch {
    // Storage may be unavailable; this session still works in memory.
  }
}

// Demo mode always starts disabled on a fresh application load.
export function readDemo(): boolean {
  try {
    localStorage.removeItem(DEMO_KEY);
  } catch {
    // Storage may be unavailable.
  }

  return false;
}

// Demo mode is intentionally not persisted across page reloads.
export function persistDemo(_demo: boolean) {
  try {
    localStorage.removeItem(DEMO_KEY);
  } catch {
    // Storage may be unavailable.
  }
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

const API_URL =
  (import.meta.env["VITE_API_URL"] as string | undefined) ||
  "http://127.0.0.1:8000";

async function fetchWithAuth(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers);

  headers.set("Content-Type", "application/json");

  const session = readSession();

  if (session) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }

  return fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [ready, setReady] = useState(false);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    const storedSession = readSession();

    setSession(storedSession);
    setDemo(false);

    if (storedSession) {
      fetchWithAuth("/api/auth/me")
        .then(async (res) => {
          if (!res.ok) {
            persistSession(null);
            setSession(null);
            return;
          }

          const data: unknown = await res.json();

          if (
            typeof data !== "object" ||
            data === null ||
            !("email" in data) ||
            typeof data.email !== "string" ||
            !("name" in data) ||
            typeof data.name !== "string"
          ) {
            persistSession(null);
            setSession(null);
            return;
          }

          const restoredSession: AuthSession = {
            token: storedSession.token,
            user: {
              email: data.email,
              name: data.name,
            },
          };

          persistSession(restoredSession);
          setSession(restoredSession);
        })
        .catch(() => {
          persistSession(null);
          setSession(null);
        })
        .finally(() => {
          setReady(true);
        });
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
      const detail =
        data && typeof data === "object" && "detail" in data
          ? data.detail
          : data ?? `HTTP ${res.status}`;

      throw new Error(formatDetail(detail) || `HTTP ${res.status}`);
    }

    const authSession: AuthSession = {
      token: data.token,
      user: data.user,
    };

    persistSession(authSession);
    setSession(authSession);
    setDemoValue(false);
  }

  async function register(email: string, password: string, name?: string) {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const detail =
        data && typeof data === "object" && "detail" in data
          ? data.detail
          : data ?? `HTTP ${res.status}`;

      const message = Array.isArray(detail)
  ? detail
      .map((item: unknown) =>
        item && typeof item === "object" && "msg" in item
          ? String(item.msg)
          : formatDetail(item),
      )
      .join("; ")
  : formatDetail(detail);

throw new Error(message || `HTTP ${res.status}`);
    }

    const authSession: AuthSession = {
      token: data.token,
      user: data.user,
    };

    persistSession(authSession);
    setSession(authSession);
    setDemoValue(false);
  }

  async function demoLogin() {
    const res = await fetch(`${API_URL}/api/auth/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const detail =
        data && typeof data === "object" && "detail" in data
          ? data.detail
          : data ?? `HTTP ${res.status}`;

      throw new Error(
        typeof detail === "string" ? detail : JSON.stringify(detail),
      );
    }

    const authSession: AuthSession = {
      token: data.token,
      user: data.user,
    };

    persistSession(authSession);
    setSession(authSession);
    setDemoValue(false);
  }

  function setDemoValue(value: boolean) {
    setDemo(value);
  }

  function signOut() {
    persistSession(null);
    setSession(null);
    setDemoValue(false);
  }

  return createElement(
    AuthContext.Provider,
    {
      value: {
        session,
        ready,
        demo,
        setDemo: setDemoValue,
        login,
        register,
        demoLogin,
        signOut,
      },
    },
    children,
  );
}

export function useAuth() {
  const auth = useContext(AuthContext);

  if (!auth) {
    throw new Error("AuthProvider is required");
  }

  return auth;
}
