"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { clearStoredToken, readStoredToken, writeStoredToken } from "@/lib/auth";

type AuthContextValue = {
  token: string | null;
  isReady: boolean;
  login: (token: string, rememberInSession: boolean) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const storedToken = readStoredToken();
    if (storedToken) {
      setToken(storedToken);
    }
    setIsReady(true);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isReady,
      login: (nextToken: string, rememberInSession: boolean) => {
        const trimmed = nextToken.trim();
        setToken(trimmed);
        if (rememberInSession) {
          writeStoredToken(trimmed);
        } else {
          clearStoredToken();
        }
      },
      logout: () => {
        setToken(null);
        clearStoredToken();
      },
    }),
    [isReady, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
