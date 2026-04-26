import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { JsonPanel } from "@/components/ui/json-panel";

describe("JsonPanel", () => {
  it("is collapsed by default and expands on click", async () => {
    window.scrollTo = (() => undefined) as typeof window.scrollTo;
    render(<JsonPanel title="Metrics JSON" value={{ k: "v" }} defaultCollapsed={true} />);

    expect(screen.queryByText('"k"')).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Expand" }));
    expect(
      await screen.findByText((content) => {
        return content.includes('"k": "v"');
      }),
    ).not.toBeNull();
  });
});
