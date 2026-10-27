import type { Focus, Screen } from "../App";
import { KIND_LABEL, METRIC_LABEL } from "../format";
import type { Radar } from "../types";

const WINDOW_WEEKS = 13;  // one quarter, the same window as the sold-home margin KPI

interface Episode { id: string; scope: string; kind: string; metric: string; dimension: string; onset: number; weeks: Set<number> }

/** Alert episodes in the trailing quarter, rebuilt from each week's ranked actions (top three per week). */
function episodes(series: Radar[]): Episode[] {
  const byId = new Map<string, Episode>();
  for (const r of series) {
    for (const a of r.actions) {
      const prev = byId.get(a.alert_id);
      const weeks = new Set(prev?.weeks ?? []).add(r.week);
      byId.set(a.alert_id, { id: a.alert_id, scope: a.scope, kind: a.kind, metric: a.signal.metric, dimension: a.dimension, onset: a.onset_week, weeks });
    }
  }
  return [...byId.values()].sort((a, b) => Math.min(...a.weeks) - Math.min(...b.weeks));
}

export function SignalsTimeline({ series, week, open }: { series: Radar[]; week: number; open: (s: Screen, f?: Focus) => void }) {
  const window = series.filter((r) => r.week <= week && r.week > week - WINDOW_WEEKS);
  if (!window.length) return null;
  const weeks = window.map((r) => r.week);
  const eps = episodes(window);
  const cols = { gridTemplateColumns: `minmax(9rem, 14rem) repeat(${weeks.length}, minmax(0, 1fr))` };
  return (
    <section aria-labelledby="signals-title" className="card px-5 py-5 sm:px-6">
      <h2 id="signals-title" className="text-lg font-semibold">Signals this quarter</h2>
      <p className="text-sm text-muted">Weeks {weeks[0]} to {week}. A filled week means the alert was ranked that week; the ring marks its onset.</p>
      <div className="mt-3 overflow-x-auto">
        <div className="min-w-[560px]">
          <div className="grid items-end gap-x-1 border-b border-grid pb-1 text-xs text-muted num" style={cols}>
            <span>Alert</span>
            {weeks.map((w) => <span key={w} className={`text-center ${w === week ? "font-semibold text-ink" : ""}`}>{w}</span>)}
          </div>
          {eps.length === 0 ? (
            <p className="py-3 text-sm text-muted">No alerts in these weeks. Seasonal swings are not flagged.</p>
          ) : eps.map((e) => (
            <div key={e.id} className="grid items-center gap-x-1 border-b border-grid/60 py-2 last:border-b-0" style={cols}>
              <button className="truncate text-left text-sm font-semibold text-accent underline-offset-2 hover:underline"
                      title={`${METRIC_LABEL[e.metric] ?? e.metric}, onset week ${e.onset}`}
                      onClick={() => open("drilldown", { metric: e.metric, dimension: e.dimension === "band" ? "band" : "market", scope: e.scope })}>
                {e.scope}: {KIND_LABEL[e.kind] ?? e.kind}
              </button>
              {weeks.map((w) => {
                const on = e.weeks.has(w);
                return (
                  <span key={w} className="flex h-5 items-center justify-center" aria-hidden={!on}>
                    <span className={`h-3.5 w-full rounded-sm ${on ? (e.weeks.has(week) ? "bg-risk" : "bg-risk/45") : "bg-grid/40"} ${w === e.onset ? "ring-2 ring-ink ring-offset-1 ring-offset-panel" : ""}`} />
                  </span>
                );
              })}
            </div>
          ))}
          <div className="grid items-center gap-x-1 pt-2 text-xs text-muted num" style={cols}>
            <span>Active alerts</span>
            {window.map((r) => <span key={r.week} className={`text-center ${r.kpis.active_alerts ? "font-semibold text-ink" : ""}`}>{r.kpis.active_alerts}</span>)}
          </div>
        </div>
      </div>
    </section>
  );
}
