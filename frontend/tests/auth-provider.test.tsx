import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "@/components/auth-provider";

const authMeMock = vi.fn();

vi.mock("@/lib/api", () => ({
  authMe: (...args: unknown[]) => authMeMock(...args),
}));

function Consumer() {
  const { isReady, isAuthenticated, user } = useAuth();
  return (
    <div>
      <span data-testid="ready">{String(isReady)}</span>
      <span data-testid="authed">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? "none"}</span>
    </div>
  );
}

describe("AuthProvider session bootstrap", () => {
  beforeEach(() => {
    window.localStorage.clear();
    authMeMock.mockReset();
  });

  it("clears stored session when token validation fails", async () => {
    window.localStorage.setItem("datasoko_token", "expired-token");
    window.localStorage.setItem(
      "datasoko_user",
      JSON.stringify({
        id: "u1",
        email: "old@example.com",
        role: "admin",
        organization_id: "org1",
        business_id: null,
      }),
    );
    authMeMock.mockRejectedValue({ status: 401, message: "Invalid or expired token." });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("ready").textContent).toBe("true"));

    expect(screen.getByTestId("authed").textContent).toBe("false");
    expect(screen.getByTestId("email").textContent).toBe("none");
    expect(window.localStorage.getItem("datasoko_token")).toBeNull();
    expect(window.localStorage.getItem("datasoko_user")).toBeNull();
  });
});
