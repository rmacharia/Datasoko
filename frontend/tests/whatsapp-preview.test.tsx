import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WhatsAppPreview } from "@/components/whatsapp-preview";

describe("WhatsAppPreview", () => {
  it("calls onCopy when copy button is clicked", async () => {
    const onCopy = vi.fn();
    render(<WhatsAppPreview message="Weekly summary" onCopy={onCopy} />);

    await userEvent.click(screen.getByRole("button", { name: "Copy WhatsApp Message" }));
    expect(onCopy).toHaveBeenCalledTimes(1);
  });
});
