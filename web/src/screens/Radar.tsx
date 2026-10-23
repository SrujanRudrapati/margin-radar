import { api } from "../api";
import type { Focus, Screen } from "../App";
import { RangeBar } from "../components/RangeBar";
import { Empty, ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import { bps, KIND_LABEL, METRIC_LABEL, metricValue, pct, pts, score, usd } from "../format";
import type { Action, Meta, Radar, Run } from "../types";

export function RadarScreen({ run, week, meta, open }: { run: Run; week: number; meta: Meta; open: (s: Screen, f?: Focus) => void }) {
  const state = useAsync<Radar>(() => api.radar(run, week), [run, week]);
  if (state.status === "loading") return <Loading what="this week's radar" />;
  if (state.status === "error") return <ErrorNote what="this week's radar" error={state.error} />;
  const r = state.data;
  const scaleMax = Math.max(1, ...r.actions.map((a) => a.impact.usd_high ?? a.impact.usd_mid ?? 0));
  return (
    <section aria-labelledby="radar-title">
      <h1 id="radar-title" className="text-2xl font-bold">
        {r.actions.length ? `${r.actions.length === 1 ? "One action" : `${r.actions.length} actions`} ranked by margin at risk` : "No margin alerts this week"}
      </h1>
      <p className="mt-1 max-w-[70ch] text-muted">
        Week {r.week}, starting {r.week_start}. {run === "injected" ? "Run with three injected problems." : "Control run: same seed, no problems injected."}
      </p>

      <dl className="mt-6 grid grid-cols-2 border-y border-grid sm:grid-cols-4">
        <Kpi label={`Contribution margin, sold homes (${r.kpis.cm_window_weeks} wks)`} value={pct(r.kpis.cm_pct)} />
        <Kpi label="Margin at risk, sample-scale (midpoints)" value={usd(r.kpis.usd_at_risk_mid)} risk={r.kpis.usd_at_risk_mid > 0} />
        <Kpi label="Of portfolio contribution margin" value={bps(r.kpis.portfolio_cm_bps_mid)} />
        <Kpi label="Active alerts" value={String(r.kpis.active_alerts)} risk={r.kpis.active_alerts > 0} />
      </dl>

      {r.global_abstention ? (
        <div className="mt-8"><Empty>Not enough history yet to separate drift from seasonality, so the radar abstains this week.</Empty></div>
      ) : r.actions.length === 0 ? (
        <div className="mt-8"><Empty>Every leading indicator is within its normal range against peer segments in the same week. Seasonal swings, like the spring peak and the summer margin dip, are not flagged.</Empty></div>
      ) : (
        <ol className="mt-8 divide-y divide-grid rounded-panel border border-grid bg-panel">
          {r.actions.map((a) => <ActionRow key={a.alert_id} a={a} scaleMax={scaleMax} open={open} />)}
        </ol>
      )}
      {r.kpis.more_actions > 0 && <p className="mt-3 text-sm text-muted">{r.kpis.more_actions} more alert(s) below the top three.</p>}
      <p className="mt-6 max-w-[80ch] text-sm text-muted">Dollar figures are {meta.sample_scale_label}. Scores are uncalibrated: they rank how unusual a move is, not the probability that an alert is real.</p>
    </section>
  );
}

function Kpi({ label, value, risk = false }: { label: string; value: string; risk?: boolean }) {
  return (
    <div className="border-grid px-4 py-4 odd:border-r sm:border-r sm:last:border-r-0">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className={`mt-1 text-2xl font-semibold num ${risk ? "text-risk" : ""}`}>{value}</dd>
    </div>
  );
}

function ActionRow({ a, scaleMax, open }: { a: Action; scaleMax: number; open: (s: Screen, f?: Focus) => void }) {
  const dimension = a.dimension === "band" ? "band" : "market";
  const metric = a.signal.metric;
  return (
    <li className="grid gap-4 px-5 py-5 md:grid-cols-[2.5rem_1fr_18rem]">
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
        <RangeBar impact={a.impact} scaleMax={scaleMax} />
        <p className="mt-1 text-sm text-muted num">{bps(a.impact.portfolio_cm_bps_mid)} of portfolio margin</p>
      </div>
    </li>
  );
}
