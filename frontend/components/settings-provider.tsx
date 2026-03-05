"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useReducedMotion } from "framer-motion";
import React from "react";

export type ThemePreference = "system" | "dark" | "light";

type SettingsContextValue = {
  theme: ThemePreference;
  resolvedTheme: "dark" | "light";
  setTheme: (value: ThemePreference) => void;
  enhancedMode: boolean;
  effectiveEnhancedMode: boolean;
  setEnhancedMode: (value: boolean) => void;
};

const ENHANCED_MODE_STORAGE_KEY = "datasoko_enhanced_mode";
export const THEME_STORAGE_KEY = "datasoko_theme";
const SettingsContext = createContext<SettingsContextValue | undefined>(undefined);

function resolveTheme(theme: ThemePreference): "dark" | "light" {
  if (theme === "dark" || theme === "light") {
    return theme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemePreference>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"dark" | "light">("dark");
  const [enhancedMode, setEnhancedModeState] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "light" || storedTheme === "dark" || storedTheme === "system") {
      setThemeState(storedTheme);
      const resolved = resolveTheme(storedTheme);
      setResolvedTheme(resolved);
      document.documentElement.setAttribute("data-theme", resolved);
      document.documentElement.style.colorScheme = resolved;
    } else {
      const resolved = resolveTheme("system");
      setResolvedTheme(resolved);
      document.documentElement.setAttribute("data-theme", resolved);
      document.documentElement.style.colorScheme = resolved;
    }

    const stored = window.localStorage.getItem(ENHANCED_MODE_STORAGE_KEY);
    if (stored === "true") {
      setEnhancedModeState(true);
    }
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const nextResolved = resolveTheme(theme);
      setResolvedTheme(nextResolved);
      document.documentElement.setAttribute("data-theme", nextResolved);
      document.documentElement.style.colorScheme = nextResolved;
    };

    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);

  const setTheme = (value: ThemePreference) => {
    setThemeState(value);
    window.localStorage.setItem(THEME_STORAGE_KEY, value);
    const nextResolved = resolveTheme(value);
    setResolvedTheme(nextResolved);
    document.documentElement.setAttribute("data-theme", nextResolved);
    document.documentElement.style.colorScheme = nextResolved;
  };

  const setEnhancedMode = (value: boolean) => {
    setEnhancedModeState(value);
    window.localStorage.setItem(ENHANCED_MODE_STORAGE_KEY, String(value));
  };

  const effectiveEnhancedMode = enhancedMode && !prefersReducedMotion;

  useEffect(() => {
    document.body.classList.toggle("enhanced-mode", effectiveEnhancedMode);
  }, [effectiveEnhancedMode]);

  const value = useMemo<SettingsContextValue>(
    () => ({ theme, resolvedTheme, setTheme, enhancedMode, effectiveEnhancedMode, setEnhancedMode }),
    [theme, resolvedTheme, enhancedMode, effectiveEnhancedMode],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error("useSettings must be used within SettingsProvider");
  }
  return context;
}
