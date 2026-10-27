import { api } from "../api";
import type { Focus, Screen } from "../App";
import { LeadTimeChart } from "../components/LeadTimeChart";
import { useRadarSeries, useRadarWeek } from "../components/radarSeries";
import { RangeBar } from "../components/RangeBar";
import { SignalsTimeline } from "../components/SignalsTimeline";
import { Empty, ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import { bps, KIND_LABEL, METRIC_LABEL, metricValue, pct, pts, score, usd } from "../format";
import type { Action, Meta, Radar, Run } from "../types";

const QUARTER_WEEKS = 13;
const SPARK_WEEKS = 26;

interface RadarProps { run: Run; week: number; meta: Meta; fallback: Focus; open: (s: Screen, f?: Focus) => void }

export function RadarScreen({ run, week, meta, fallback, open }: RadarProps) {
  const state = useRadarWeek(run, week);
  const series = useRadarSeries(run, meta);
  if (state.status === "error") return <ErrorNote what="this week's radar" error={state.error} />;
  if (state.status === "loading" || state.data.run !== run) return <Loading what="this week's radar" />;
  const r = state.data;
  const past = series.status === "ready" ? series.data.filter((x) => x.week <= week) : [];
  const scaleMax = Math.max(1, ...r.actions.map((a) => a.impact.usd_high ?? a.impact.usd_mid ?? 0));
  return (
    <section aria-labelledby="radar-title">
      <h1 id="radar-title" className="text-[28px] font-bold leading-tight tracking-[-0.01em]">{headline(r)}</h1>
      <p className="mt-1 max-w-[70ch] text-muted">
        Week {r.week}, starting {r.week_start}. {run === "injected" ? "Run with three injected problems." : "Control run: same seed, no problems injected."}
      </p>

      <div className={r.global_abstention ? "" : "mt-5"}>
        {r.global_abstention ? null : series.status === "error" ? <ErrorNote what="the margin history" error={series.error} />
          : series.status === "loading" ? <Loading what="the margin history" />
          : <Hero series={series.data} week={week} focus={heroFocus(r, past, fallback)} />}
      </div>

      <dl className="mt-5 grid grid-cols-3 rounded-panel border border-grid bg-panel sm:grid-cols-[1.9fr_1fr_1fr_1fr]">
        <MarginKpi r={r} past={past} />
        <Kpi label="Margin at risk" value={usd(r.kpis.usd_at_risk_mid)} risk={r.kpis.usd_at_risk_mid > 0} note="Sample-scale midpoint" />
        <Kpi label="Share of portfolio margin" value={bps(r.kpis.portfolio_cm_bps_mid)} note="Midpoint" />
        <Kpi label="Active alerts" value={String(r.kpis.active_alerts)} risk={r.kpis.active_alerts > 0} />
      </dl>

      {r.global_abstention ? (
        <div className="mt-5"><Empty>Not enough history yet to separate drift from seasonality, so the radar abstains this week.</Empty></div>
      ) : r.actions.length === 0 ? (
        <div className="mt-5"><Empty>Every leading indicator is within its normal range against peer segments in the same week. Seasonal swings, like the spring peak and the summer margin dip, are not flagged.</Empty></div>
      ) : (
        <ol className="mt-5 divide-y divide-grid rounded-panel border border-grid bg-panel">
          {r.actions.map((a) => <ActionRow key={a.alert_id} a={a} scaleMax={scaleMax} open={open} />)}
        </ol>
      )}
      {r.kpis.more_actions > 0 && <p className="mt-3 text-sm text-muted">{r.kpis.more_actions} more alert(s) below the top three.</p>}

      {past.length > 0 && <div className="mt-5"><SignalsTimeline series={past} week={week} open={open} /></div>}
      <p className="mt-5 max-w-[80ch] text-sm text-muted">Dollar figures are {meta.sample_scale_label}. Scores are uncalibrated: they rank how unusual a move is, not the probability that an alert is real.</p>
    </section>
  );
}

function headline(r: Radar): string {
  if (r.global_abstention) return "This week: not enough history to judge";
  const n = r.kpis.active_alerts;
  return n === 0 ? "This week: no segment needs attention" : `This week: ${n} segment${n === 1 ? " needs" : "s need"} attention`;
}

/** The hero follows the top action; with none this week, the latest alert so far; otherwise the app's default focus. */
function heroFocus(r: Radar, past: Radar[], fallback: Focus): Focus {
  const a = r.actions[0] ?? [...past].reverse().find((x) => x.actions.length)?.actions[0];
  return a ? { metric: a.signal.metric, dimension: a.dimension === "band" ? "band" : "market", scope: a.scope } : fallback;
}

function Hero({ series, week, focus }: { series: Radar[]; week: number; focus: Focus }) {
  const drill = useAsync(() => api.drilldown(series[0].run, focus.metric, focus.dimension, focus.scope),
                         [series[0].run, focus.metric, focus.dimension, focus.scope]);
  if (drill.status === "loading") return <Loading what={`${focus.scope} against its peers`} />;
  if (drill.status === "error") return <ErrorNote what={`${focus.scope} against its peers`} error={drill.error} />;
  return <LeadTimeChart d={drill.data} series={series} week={week} />;
}

function MarginKpi({ r, past }: { r: Radar; past: Radar[] }) {
  const prior = past.find((x) => x.week === r.week - QUARTER_WEEKS)?.kpis.cm_pct ?? null;
  const change = r.kpis.cm_pct !== null && prior !== null ? r.kpis.cm_pct - prior : null;
  const spark = past.slice(-SPARK_WEEKS).map((x) => x.kpis.cm_pct);
  return (
    <div className="col-span-3 flex items-end justify-between gap-4 border-b border-grid px-4 py-4 sm:col-span-1 sm:border-b-0 sm:border-r">
      <div>
        <dt className="text-sm text-muted">Sold-home contribution margin, {r.kpis.cm_window_weeks} wks</dt>
        <dd className="mt-1 text-[28px] font-semibold leading-none num">{pct(r.kpis.cm_pct)}</dd>
        {change !== null && <dd className="mt-1.5 text-sm text-muted num">{pts(change)} vs prior quarter (wk {r.week - QUARTER_WEEKS})</dd>}
      </div>
      {spark.length > 1 && <Sparkline values={spark} label={`Sold-home margin, last ${spark.length} weeks`} />}
    </div>
  );
}

function Sparkline({ values, label }: { values: (number | null)[]; label: string }) {
  const known = values.map((v, i) => [i, v] as const).filter((p): p is readonly [number, number] => p[1] !== null);
  if (known.length < 2) return null;
  const [w, h, pad] = [112, 40, 3];
  const ys = known.map(([, v]) => v), lo = Math.min(...ys), hi = Math.max(...ys);
  const px = (i: number) => (i / (values.length - 1)) * (w - 2 * pad) + pad;
  const py = (v: number) => h - pad - ((v - lo) / (hi - lo || 1)) * (h - 2 * pad);
  const d = known.map(([i, v], k) => `${k ? "L" : "M"}${px(i).toFixed(1)},${py(v).toFixed(1)}`).join("");
  const [li, lv] = known[known.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} role="img" aria-label={label} className="shrink-0">
      <path d={d} fill="none" stroke="rgb(var(--muted))" strokeWidth={1.5} strokeLinejoin="round" />
      <circle cx={px(li)} cy={py(lv)} r={2.5} fill="rgb(var(--ink))" />
    </svg>
  );
}

function Kpi({ label, value, risk = false, note }: { label: string; value: string; risk?: boolean; note?: string }) {
  return (
    <div className="border-r border-grid px-4 py-4 last:border-r-0">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className={`mt-1 text-[28px] font-semibold leading-none num ${risk ? "text-risk" : ""}`}>{value}</dd>
      {note && <dd className="mt-1.5 text-xs text-muted">{note}</dd>}
    </div>
  );
}

function ActionRow({ a, scaleMax, open }: { a: Action; scaleMax: number; open: (s: Screen, f?: Focus) => void }) {
  const dimension = a.dimension === "band" ? "band" : "market";
  const metric = a.signal.metric;
  return (
    <li className="grid gap-4 px-5 py-5 md:grid-cols-[2.5rem_1fr_19rem] md:gap-6">
      <p className="text-3xl font-bold leading-none text-risk num" aria-label={`Rank ${a.rank}`}>{a.rank}</p>
      <div className="min-w-0">
        <h2 className="text-lg font-semibold">{a.scope}: {KIND_LABEL[a.kind] ?? a.kind}</h2>
        <p className="mt-1 text-[15px]">
          {METRIC_LABEL[metric] ?? metric} {a.signal.direction === "+" ? "rose" : "fell"} against peers
          {a.signal.gap !== null ? <> ({metric === "reno_overrun_pct" || metric.endsWith("_rate") ? pts(a.signal.gap) : metricValue(metric, a.signal.gap)})</> : null},
          uncalibrated score {score(a.signal.score)}, since week {a.onset_week}.
        </p>
        <p className="mt-2 text-[15px]"><span className="font-semibold">{a.owner}:</span> {a.action}</p>
        <button className="mt-3 text-sm font-semibold text-focus underline-offset-2 hover:underline"
                onClick={() => open("drilldown", { metric, dimension, scope: a.scope })}>
          See {a.scope} against its peers
        </button>
      </div>
      <div className="self-center">
        <p className="mb-2 text-sm font-semibold">Margin at risk</p>
        <RangeBar impact={a.impact} scaleMax={scaleMax} />
        <p className="mt-1 text-sm text-muted num">{bps(a.impact.portfolio_cm_bps_mid)} of portfolio margin at the midpoint</p>
      </div>
    </li>
  );
}
