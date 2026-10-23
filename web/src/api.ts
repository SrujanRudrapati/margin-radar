import type { BriefItem, Brief, Cohort, DecisionView, Drill, HeatCell, Meta, Radar, Run } from "./types";

// Live mode reads the FastAPI app (/api, always replay-only); static mode reads pre-rendered JSON (make export).
export const STATIC = import.meta.env.VITE_STATIC === "1";
const BASE = import.meta.env.BASE_URL;

async function get<T>(live: string, file: string): Promise<T> {
  const url = STATIC ? `${BASE}data/${file}` : live;
  const res = await fetch(url);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(res.status === 404 ? "Not found" : `Request failed (${res.status}): ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

const q = (params: Record<string, string | number>) => new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();

export const api = {
  meta: () => get<Meta>("/api/meta", "meta.json"),
  radar: (run: Run, week: number) => get<Radar>(`/api/radar?${q({ run, week })}`, `radar/${run}/${week}.json`),
  heatmap: (run: Run, week: number, metric: string) =>
    get<{ cells: HeatCell[]; note: string }>(`/api/heatmap?${q({ run, week, metric })}`, `heatmap/${run}/${week}/${metric}.json`),
  drilldown: (run: Run, metric: string, dimension: string, scope: string) =>
    get<Drill>(`/api/drilldown?${q({ run, metric, dimension, scope })}`, `drilldown/${run}/${metric}/${dimension}/${scope}.json`),
  cohort: (run: Run, week: number, level: string, scope: string) =>
    get<Cohort>(`/api/cohort?${q({ run, week, level, scope, start: 30, end: 33 })}`, `cohort/${run}/${level}/${scope}.json`),
  briefs: () => get<{ briefs: BriefItem[] }>("/api/briefs", "briefs.json"),
  brief: (week: number) => get<Brief>(`/api/brief?${q({ week })}`, `brief/${week}.json`),
  evaluation: () => get<Record<string, any>>("/api/eval", "eval.json"),
  decisions: () => get<DecisionView>("/api/decisions", "decisions.json"),
  addDecision: async (body: { alert_id: string; decision: string; reason: string; decided_week: number }) => {
    const res = await fetch("/api/decisions", { method: "POST", headers: { "Content-Type": "application/json" },
                                                 body: JSON.stringify(body) });
    if (!res.ok) throw new Error((await res.json()).detail ?? `Could not log the decision (${res.status})`);
    return res.json();
  },
};
