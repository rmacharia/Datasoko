import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsProvider, THEME_STORAGE_KEY, useSettings } from "@/components/settings-provider";

function Consumer() {
  const { theme, setTheme } = useSettings();
  return (
    <div>
      <span>{theme}</span>
      <button onClick={() => setTheme("light")}>set-light</button>
    </div>
  );
}

describe("SettingsProvider theme persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        media: query,
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("persists theme and updates html data-theme", async () => {
    render(
      <SettingsProvider>
        <Consumer />
      </SettingsProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "set-light" }));

    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});
