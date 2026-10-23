export type Run = "injected" | "control";

export interface Meta {
  banner: string; sample_scale_label: string; runs: Run[]; max_week: number; default_week: number;
  trigger_metrics: string[]; markets: string[]; bands: string[]; week_starts: string[]; brief_weeks: number[];
  static?: boolean; export_weeks?: number[];
}

export interface Impact {
  basis: "measured" | "scenario_estimate" | "sensitivity";
  usd_low: number | null; usd_mid: number | null; usd_high: number | null;
  scope_bps_mid: number | null; portfolio_cm_bps_low: number | null; portfolio_cm_bps_mid: number | null;
  portfolio_cm_bps_high: number | null; usd_per_100bps: number | null; exposure_usd: number | null;
  label: string; status: string;
}

export interface Action {
  rank: number; alert_id: string; kind: string; scope: string; dimension: string; onset_week: number;
  action: string; owner: string; impact: Impact;
  signal: { metric: string; direction: "+" | "-"; score: number; gap: number | null };
}

export interface Radar {
  run: Run; week: number; week_start: string; global_abstention: boolean;
  kpis: { cm_pct: number | null; cm_window_weeks: number; usd_at_risk_mid: number; portfolio_cm_bps_mid: number;
          active_alerts: number; more_actions: number };
  actions: Action[];
  watch: { scope: string; metric: string; note: string }[];
}

export interface HeatCell {
  segment: string; market: string; band: string; product: string; score: number | null;
  direction: "+" | "-" | null; fired: boolean; risk_direction: "+" | "-";
}

export interface Episode { alert_id: string; kind: string; scope: string; onset_week: number; first_week: number; last_week: number }
export interface Truth { scenario: string; kind: string; scope: string; start_week: number; first_alert_week: number | null;
  cm_first_visible_week: number | null; lead_weeks: number | null; before_cm: boolean }

export interface Drill {
  run: Run; metric: string; dimension: string; scope: string; weeks: number[]; value: (number | null)[];
  peer: (number | null)[]; gap: (number | null)[]; score: (number | null)[]; alerts: Episode[]; truth: Truth | null;
  query_ids: string[];
}

export interface Cohort { scope: string; close_weeks: number[]; cohort_homes: number; query_id: string;
  points: { sold_share: number; cm_pct: number | null }[] }

export interface Citation { ref: string; label: string; value: number; display: string; kind: string;
  queries?: string[]; sql?: Record<string, { metric: string; level: string; sql: string }> }
export interface Brief { week: number; week_start: string; status: string; model: string | null; body: string;
  citations: Citation[]; grounding: { numbers_checked: number; errors: string[] } }
export interface BriefItem { week: number; status: string; model: string | null; source: string }

export interface Decision { alert_id: string; decision: string; reason: string; decided_week: number; scope: string;
  kind: string; ts: string; is_example?: boolean }
export interface DecisionView {
  decisions: Decision[];
  score: { label: string; decisions: number; alerts_with_decisions: number; decisions_influenced: number;
           estimated_saved_usd: number };
  scored_rows: (Decision & { estimated_saved_usd: number; realized_erosion_bps: number | null;
                              margin_visible_week: number | null; counted: boolean })[];
}
