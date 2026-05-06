"use client";

import React from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { AuthUser } from "@/lib/api";
import { authMe } from "@/lib/api";
import { clearStoredToken, clearStoredUser, readStoredToken, readStoredUser, writeStoredToken, writeStoredUser } from "@/lib/auth";

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  isReady: boolean;
  isAuthenticated: boolean;
  login: (token: string, user: AuthUser) => void;
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
    if (!storedToken || !storedUser) {
      clearStoredToken();
      clearStoredUser();
      setIsReady(true);
      return;
    }

    let mounted = true;
    void authMe(storedToken)
      .then((freshUser) => {
        if (!mounted) return;
        setToken(storedToken);
        setUser(freshUser);
        writeStoredUser(freshUser);
      })
      .catch(() => {
        if (!mounted) return;
        setToken(null);
        setUser(null);
        clearStoredToken();
        clearStoredUser();
      })
      .finally(() => {
        if (mounted) setIsReady(true);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback((nextToken: string, nextUser: AuthUser) => {
    const trimmed = nextToken.trim();
    setToken(trimmed);
    setUser(nextUser);
    writeStoredToken(trimmed);
    writeStoredUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    clearStoredToken();
    clearStoredUser();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isReady,
      isAuthenticated: !!token,
      login,
      logout,
    }),
    [isReady, token, user, login, logout],
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
