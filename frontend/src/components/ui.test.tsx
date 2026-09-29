import { render, screen } from "@testing-library/react";
import type { Priority } from "../api";
import { PriorityBreakdown, SignalStrip } from "./ui";

const priority: Priority = {
  score: 72,
  band: "Hot",
  flags: [],
  components: [
    { key: "urgency", label: "Urgency", points: 10, max: 25, reasons: ["follow-up due today"] },
    { key: "fit", label: "Service fit", points: 20, max: 25, reasons: ["strong signal"] },
    { key: "qualification", label: "Qualification (BANT)", points: 22, max: 30, reasons: ["budget confirmed"] },
    { key: "momentum", label: "Momentum", points: 20, max: 20, reasons: ["last touch 1 day ago"] },
  ],
};

it("describes every component to screen readers, in a fixed order", () => {
  render(<SignalStrip priority={priority} />);
  expect(screen.getByRole("img")).toHaveAccessibleName(
    "Priority 72: Service fit 20 of 25, Qualification (BANT) 22 of 30, Momentum 20 of 20, Urgency 10 of 25",
  );
});

it("lists the reason behind each component", () => {
  render(<PriorityBreakdown priority={priority} />);
  expect(screen.getByText("follow-up due today")).toBeInTheDocument();
  expect(screen.getByText("budget confirmed")).toBeInTheDocument();
});
