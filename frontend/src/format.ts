const money = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-CA", { notation: "compact", maximumFractionDigits: 1 });

export const cad = (value: number) => money.format(value);
export const cadShort = (value: number) => `$${compact.format(value)}`;
export const pct = (value: number) => `${Math.round(value * 100)}%`;

export function parseDay(value: string): Date {
  // API dates are ISO days (YYYY-MM-DD); parse as local midnight so "today" is not shifted by time zone.
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function startOfToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

export function daysFromToday(value: string): number {
  return Math.round((parseDay(value).getTime() - startOfToday().getTime()) / 86_400_000);
}

export function dueLabel(value: string | null): { text: string; tone: "overdue" | "today" | "soon" | "later" } | null {
  if (!value) return null;
  const days = daysFromToday(value);
  if (days < 0) return { text: `${-days}d overdue`, tone: "overdue" };
  if (days === 0) return { text: "Due today", tone: "today" };
  if (days === 1) return { text: "Due tomorrow", tone: "soon" };
  return { text: `Due ${shortDate(value)}`, tone: days <= 3 ? "soon" : "later" };
}

export function shortDate(value: string): string {
  return parseDay(value).toLocaleDateString("en-CA", { month: "short", day: "numeric" });
}

export function relativeTime(value: string): string {
  const then = new Date(value).getTime();
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days}d ago`;
}

export const BANT_LABEL: Record<string, string> = {
  unknown: "Unknown",
  indicated: "Indicated",
  confirmed: "Confirmed",
  influencer: "Influencer",
  decision_maker: "Decision maker",
  low: "Low",
  medium: "Medium",
  high: "High",
  "6_plus_months": "6+ months",
  "3_6_months": "3–6 months",
  under_3_months: "Under 3 months",
};

export const PRACTICE_LABEL: Record<string, string> = {
  security: "Cybersecurity",
  cloud: "Cloud & hybrid IT",
  network: "Networking",
  ai: "AI & data",
  lifecycle: "Lifecycle & deployment",
  training: "Training & enablement",
};

export const KIND_LABEL: Record<string, string> = {
  end_of_support: "End of support",
  renewal: "Renewal",
  purchase: "Purchase pattern",
  attach_gap: "Attach gap",
  vendor_program: "Vendor program",
  marketplace: "Marketplace",
  inbound: "Inbound interest",
};
