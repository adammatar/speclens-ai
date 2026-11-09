import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { probeApiKey } from "./api";

const STORAGE_KEY = "speclens.apiKey";

type AuthContextValue = {
  apiKey: string | null;
  ready: boolean;
  signIn: (key: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [ready] = useState(true);

  const signIn = useCallback(async (key: string) => {
    const trimmed = key.trim();
    if (!trimmed) {
      throw new Error("API key is required");
    }
    const ok = await probeApiKey(trimmed);
    if (!ok) {
      throw new Error("Invalid API key");
    }
    sessionStorage.setItem(STORAGE_KEY, trimmed);
    setApiKey(trimmed);
  }, []);

  const signOut = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setApiKey(null);
  }, []);

  const value = useMemo(
    () => ({ apiKey, ready, signIn, signOut }),
    [apiKey, ready, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
