import { cadShort, dueLabel, parseDay } from "./format";

function isoOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

describe("dueLabel", () => {
  it("flags overdue, today and tomorrow in local time", () => {
    expect(dueLabel(isoOffset(-3))).toEqual({ text: "3d overdue", tone: "overdue" });
    expect(dueLabel(isoOffset(0))?.tone).toBe("today");
    expect(dueLabel(isoOffset(1))?.text).toBe("Due tomorrow");
    expect(dueLabel(isoOffset(10))?.tone).toBe("later");
    expect(dueLabel(null)).toBeNull();
  });

  it("parses ISO days as local midnight", () => {
    const d = parseDay("2026-01-12");
    expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()]).toEqual([2026, 0, 12, 0]);
  });

  it("formats compact currency", () => {
    expect(cadShort(145700)).toBe("$145.7K");
  });
});
