import { CartesianGrid, ComposedChart, Legend, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import type { Focus } from "../App";
import { Empty, ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import { KIND_LABEL, METRIC_LABEL, metricValue, score } from "../format";
import type { Drill, Meta, Run } from "../types";

const Z_ALERT = 3.25;

interface DrilldownProps { run: Run; week: number; meta: Meta; focus: Focus; setFocus: (f: Focus) => void }

export function DrilldownScreen({ run, week, meta, focus, setFocus }: DrilldownProps) {
  const state = useAsync(() => api.drilldown(run, focus.metric, focus.dimension, focus.scope), [run, focus.metric, focus.dimension, focus.scope]);
  const scopes = focus.dimension === "market" ? meta.markets : meta.bands;
  return (
    <section aria-labelledby="drill-title">
      <h1 id="drill-title" className="text-2xl font-bold">{focus.scope} against its peers</h1>
      <p className="mt-1 max-w-[72ch] text-muted">
        Peers move together with the season, so seasonality shows up in both lines. Drift is the gap between them. Showing weeks up to {week}.
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <Select label="Metric" value={focus.metric} options={meta.trigger_metrics.map((m) => [m, METRIC_LABEL[m] ?? m])}
                onChange={(metric) => setFocus({ ...focus, metric })} />
        <Select label="Compare" value={focus.dimension} options={[["market", "Markets"], ["band", "Price bands"]]}
                onChange={(d) => setFocus({ ...focus, dimension: d as Focus["dimension"], scope: d === "market" ? meta.markets[0] : meta.bands[0] })} />
        <Select label={focus.dimension === "market" ? "Market" : "Band"} value={focus.scope} options={scopes.map((s) => [s, s])}
                onChange={(scope) => setFocus({ ...focus, scope })} />
      </div>
      {state.status === "loading" && <Loading what={`${focus.scope}`} />}
      {state.status === "error" && <div className="mt-6"><ErrorNote what={focus.scope} error={state.error} /></div>}
      {state.status === "ready" && <Charts d={state.data} week={week} />}
    </section>
  );
}

function Select({ label, value, options, onChange }: { label: string; value: string; options: string[][]; onChange: (v: string) => void }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} className="rounded-panel border border-grid bg-panel px-2 py-1.5">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}

function Charts({ d, week }: { d: Drill; week: number }) {
  const rows = d.weeks.map((w, i) => ({ week: w, value: d.value[i], peer: d.peer[i], score: d.score[i] })).filter((r) => r.week <= week);
  if (!rows.length) return <div className="mt-6"><Empty>No weeks to show yet.</Empty></div>;
  const episodes = d.alerts.filter((a) => a.first_week <= week);
  const t = d.truth;
  const lead = t && t.first_alert_week !== null && t.cm_first_visible_week !== null && t.first_alert_week <= week ? t : null;
  const fmt = (v: number) => metricValue(d.metric, v);
  return (
    <>
      {lead && (
        <p className="mt-6 text-lg">
          <span className="font-bold text-risk">{lead.lead_weeks} weeks of warning.</span>{" "}
          The detector flagged {d.scope} in week {lead.first_alert_week}; {d.scope} cohort margin showed the problem in week {lead.cm_first_visible_week}.
        </p>
      )}
      <figure className="mt-4 card p-5">
        <figcaption className="text-sm font-semibold">{METRIC_LABEL[d.metric]}: {d.scope} and its peer median (4-week windows)</figcaption>
        <div className="h-[320px]">
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 24, right: 16, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="rgb(var(--grid))" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="week" stroke="rgb(var(--muted))" tick={{ fontSize: 12 }} />
              <YAxis stroke="rgb(var(--muted))" tick={{ fontSize: 12 }} tickFormatter={fmt} width={56} domain={["auto", "auto"]} />
              <Tooltip formatter={(v: number) => fmt(v)} labelFormatter={(w) => `Week ${w}`}
                       contentStyle={{ background: "rgb(var(--panel))", border: "1px solid rgb(var(--grid))" }} />
              <Legend />
              {lead && <ReferenceArea x1={lead.first_alert_week!} x2={Math.min(lead.cm_first_visible_week!, week)} fill="rgb(var(--risk))" fillOpacity={0.1} />}
              {t && t.start_week <= week && <ReferenceLine x={t.start_week} stroke="rgb(var(--muted))" strokeDasharray="4 4" label={{ value: "problem began", position: "top", fontSize: 11, fill: "rgb(var(--muted))" }} />}
              {lead && <ReferenceLine x={lead.first_alert_week!} stroke="rgb(var(--risk))" strokeWidth={2} label={{ value: `Alert raised (wk ${lead.first_alert_week})`, position: "top", fontSize: 11, fill: "rgb(var(--risk))" }} />}
              {t && t.cm_first_visible_week !== null && t.cm_first_visible_week <= week && <ReferenceLine x={t.cm_first_visible_week} stroke="rgb(var(--ink))" strokeDasharray="6 3" label={{ value: `${d.scope} cohort margin shows it (wk ${t.cm_first_visible_week})`, position: "top", fontSize: 11, fill: "rgb(var(--ink))" }} />}
              <Line dataKey="peer" name="Peer median" stroke="rgb(var(--peer))" dot={false} strokeWidth={2} connectNulls isAnimationActive={false} />
              <Line dataKey="value" name={d.scope} stroke="rgb(var(--risk))" dot={false} strokeWidth={2.5} connectNulls isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </figure>
      <figure className="mt-4 card p-5">
        <figcaption className="text-sm font-semibold">Uncalibrated score of the gap (alerts need two weeks past ±{Z_ALERT}, or a sustained run)</figcaption>
        <div className="h-[180px]">
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 12, right: 16, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="rgb(var(--grid))" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="week" stroke="rgb(var(--muted))" tick={{ fontSize: 12 }} />
              <YAxis stroke="rgb(var(--muted))" tick={{ fontSize: 12 }} width={56} />
              <Tooltip formatter={(v: number) => score(v)} labelFormatter={(w) => `Week ${w}`}
                       contentStyle={{ background: "rgb(var(--panel))", border: "1px solid rgb(var(--grid))" }} />
              <ReferenceLine y={Z_ALERT} stroke="rgb(var(--risk))" strokeDasharray="3 3" label={{ value: `alert threshold +${Z_ALERT}`, position: "insideTopLeft", fontSize: 11, fill: "rgb(var(--risk))" }} />
              <ReferenceLine y={-Z_ALERT} stroke="rgb(var(--risk))" strokeDasharray="3 3" label={{ value: `alert threshold −${Z_ALERT}`, position: "insideBottomLeft", fontSize: 11, fill: "rgb(var(--risk))" }} />
              <Line dataKey="score" name="Score" stroke="rgb(var(--ink))" dot={false} connectNulls isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </figure>
      <div className="mt-4 text-[15px]">
        {episodes.length ? (
          <ul className="space-y-1">
            {episodes.map((a) => (
              <li key={a.alert_id}>{KIND_LABEL[a.kind] ?? a.kind} alert: fired week {a.first_week}, onset week {a.onset_week}
                {a.last_week < week ? `, closed after week ${a.last_week}` : ", still active"}.</li>
            ))}
          </ul>
        ) : <p className="text-muted">No alert on {d.scope} for this metric up to week {week}.</p>}
        <p className="mt-2 text-sm text-muted">Source queries: {d.query_ids.join(", ")}</p>
      </div>
    </>
  );
}
