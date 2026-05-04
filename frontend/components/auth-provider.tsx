"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { AuthUser } from "@/lib/api";
import { clearStoredToken, readStoredToken, readStoredUser, writeStoredToken, writeStoredUser, clearStoredUser } from "@/lib/auth";

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  isReady: boolean;
  login: (token: string, user: AuthUser, rememberInSession: boolean) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const storedToken = readStoredToken();
    const storedUser = readStoredUser();
    if (storedToken) {
      setToken(storedToken);
    }
    if (storedUser) {
      setUser(storedUser);
    }
    setIsReady(true);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isReady,
      login: (nextToken: string, nextUser: AuthUser, rememberInSession: boolean) => {
        const trimmed = nextToken.trim();
        setToken(trimmed);
        setUser(nextUser);
        if (rememberInSession) {
          writeStoredToken(trimmed);
          writeStoredUser(nextUser);
        } else {
          clearStoredToken();
          clearStoredUser();
        }
      },
      logout: () => {
        setToken(null);
        setUser(null);
        clearStoredToken();
        clearStoredUser();
      },
    }),
    [isReady, token, user],
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
