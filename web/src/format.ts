export const KIND_LABEL: Record<string, string> = {
  adverse_selection: "Adverse selection", demand_softening: "Demand softening",
  reno_cost_drift: "Renovation cost drift", portfolio_shift: "Portfolio-wide shift",
};
export const METRIC_LABEL: Record<string, string> = {
  contract_rate: "Contract rate", first_offer_rate: "First-offer rate", reno_overrun_pct: "Renovation overrun",
};

export function usd(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const a = Math.abs(v), s = v < 0 ? "−" : "";
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${s}$${(a / 1e3).toFixed(0)}K`;
  return `${s}$${a.toFixed(0)}`;
}
export const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(d)}%`);
export const pts = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1)} pts`);
export const bps = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v).toLocaleString()} bps`);
export const score = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toFixed(1));
export function metricValue(metric: string, v: number | null | undefined): string {
  return metric === "reno_overrun_pct" || metric === "contract_rate" || metric === "first_offer_rate" ? pct(v) : score(v);
}
