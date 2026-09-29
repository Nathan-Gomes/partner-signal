// Typed client for the PartnerSignal API. Shapes mirror src/partnersignal/services/workflow.py.

export type PracticeKey = "security" | "cloud" | "network" | "ai" | "lifecycle" | "training";
export type Bant = { budget: string; authority: string; need: string; timeline: string };

export interface Component {
  key: "fit" | "qualification" | "momentum" | "urgency";
  label: string;
  points: number;
  max: number;
  reasons: string[];
}
export interface Priority {
  score: number;
  band: "Hot" | "Warm" | "Cool";
  flags: string[];
  components: Component[];
}

export interface OpportunitySummary {
  id: number;
  title: string;
  partner_id: string;
  partner: string;
  end_customer: string;
  industry: string;
  practice: PracticeKey;
  service_key: string;
  service: string;
  stage: string;
  value: number;
  weighted_value: number;
  next_step: string;
  next_step_due: string | null;
  days_in_stage: number;
  last_touch: string | null;
  specialist: string | null;
  bant: Bant;
  priority: Priority;
}

export interface Activity {
  id: number;
  partner_id: string;
  partner: string;
  opportunity_id: number | null;
  kind: string;
  summary: string;
  outcome: string;
  occurred_at: string;
}

export interface SignalItem {
  id: number;
  partner_id: string;
  partner: string;
  kind: string;
  source: string;
  practice: PracticeKey;
  service_key: string;
  service: string;
  title: string;
  detail: string;
  strength: number;
  detected_on: string;
  deadline: string | null;
  status: string;
  score: number;
  estimated_value: number;
}

export interface Draft {
  id: number;
  partner_id: string;
  opportunity_id: number | null;
  signal_id: number | null;
  goal: string;
  subject: string;
  body: string;
  edited: boolean;
  personalization: { element: string; reason: string }[];
  engine: "claude" | "local";
  status: "draft" | "approved";
  created_at: string;
}

export interface Specialist {
  id: string;
  name: string;
  title: string;
  practice: string;
  load: number;
  capacity: number;
  utilization: number;
  recommended?: boolean;
}

export interface OpportunityDetail extends OpportunitySummary {
  challenge: string;
  close_reason: string;
  created_on: string;
  contact_name: string;
  contact_title: string;
  specialist_id: string | null;
  signal: SignalItem | null;
  activities: Activity[];
  drafts: Draft[];
  specialists: Specialist[];
  handoff: { sections: Record<string, string | string[]>; text: string };
  playbook: { questions: string[]; triggers: string[] };
}

export interface QueueItem {
  kind: "follow_up" | "route" | "reengage" | "prospect";
  verb: string;
  score: number;
  band: string;
  title: string;
  partner: string;
  partner_id: string;
  opportunity_id: number | null;
  signal_id: number | null;
  next_step: string;
  due: string | null;
  stage: string;
  reasons: string[];
  practice: PracticeKey;
}

export interface TodayView {
  date: string;
  kpis: {
    touches_this_week: number;
    weekly_touch_goal: number;
    due_today: number;
    overdue: number;
    open_pipeline: number;
    weighted_pipeline: number;
    open_opportunities: number;
    new_signals: number;
    qualified_or_later: number;
  };
  queue: QueueItem[];
  recent_activity: Activity[];
}

export interface WhitespaceCell {
  share: number;
  product_revenue: number;
  status: "none" | "attached" | "gap";
  potential: number;
}

export interface PartnerSummary {
  id: string;
  name: string;
  partner_type: string;
  tier: string;
  city: string;
  province: string;
  contact_name: string;
  contact_title: string;
  verticals: string[];
  trailing_revenue: number;
  services_revenue: number;
  attach_rate: number;
  open_opportunities: number;
  open_pipeline: number;
  new_signals: number;
  whitespace_potential: number;
  last_touch: string | null;
  days_since_touch: number | null;
}

export interface PartnerDetail extends PartnerSummary {
  contact_email: string;
  vendors: string[];
  about: string;
  whitespace: Record<PracticeKey, WhitespaceCell>;
  signals: SignalItem[];
  opportunities: OpportunitySummary[];
  activities: Activity[];
}

export interface Meta {
  practices: Record<PracticeKey, string>;
  services: { key: string; practice: PracticeKey; name: string; kind: string; typical_value: number; duration: string; summary: string }[];
  stages: { name: string; probability: number; cadence_days: number }[];
  bant_levels: Record<keyof Bant, string[]>;
  playbooks: Record<PracticeKey, { triggers: string[]; questions: string[]; ai_use_cases: string[] }>;
}

export interface Quoted { level: string; quote: string }
export interface Extraction {
  summary: string;
  end_customer: string;
  industry: string;
  challenges: { point: string; quote: string }[];
  practices: { practice: PracticeKey; service_key: string; confidence: string; quote: string }[];
  bant: { budget: Quoted; authority: Quoted; need: Quoted; timeline: Quoted };
  missing_information: string[];
  follow_up_questions: string[];
  risks: string[];
  next_step: string;
}
export interface EngineMeta { engine: "claude" | "local"; model: string; note: string }

export interface Reports {
  funnel: { stage: string; count: number; value: number }[];
  by_practice: { practice: PracticeKey; label: string; open_value: number; weighted_value: number; won_value: number; count: number }[];
  activity_weeks: { week: string; call: number; email: number; meeting: number }[];
  signal_sources: { source: string; total: number; actioned: number }[];
  win_rate: number | null;
  won_value: number;
  closed_count: number;
  won_count: number;
  avg_cycle_days: number | null;
  open_pipeline: number;
  weighted_pipeline: number;
  stalled: number;
}

export interface Health {
  status: string;
  commit: string;
  ai: { live_model_available: boolean; model: string };
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : (detail as { message?: string })?.message ?? `Request failed (${status})`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body: unknown = {}) => request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T,>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
};
