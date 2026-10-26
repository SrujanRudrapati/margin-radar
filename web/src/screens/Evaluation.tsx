import { Fragment } from "react";
import { api } from "../api";
import { Empty, ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";

type Gate = { pass: boolean; value: unknown; rule: string };
type Scenario = { seeds: number; detected_before_cm: number; median_lead_weeks: number | null; min_lead_weeks: number | null; max_lead_weeks: number | null; median_delay_weeks: number | null };
type Split = { seeds: number[]; control_false_alerts_per_week: number; control_alert_weeks: number; control_evaluable_weeks: number;
  wrong_episodes: number; precision: number | null; recall_before_cm: number | null; scenarios: Record<string, Scenario> };

const NAMES: Record<string, string> = { A: "A: buyers slow down (one market)", B: "B: adverse selection (one price band)", C: "C: renovation overrun (one market)" };
const SPLIT_LABEL: Record<string, string> = { holdout: "true holdout", tuning: "tuning", seen: "seen earlier", confirm: "confirmation (leakage check)" };

export function EvaluationScreen() {
  const state = useAsync(() => api.evaluation(), []);
  if (state.status === "loading") return <Loading what="the evaluation" />;
  if (state.status === "error") return <ErrorNote what="the evaluation" error={state.error} />;
  const e = state.data;
  if (!e.available) return <Empty>No evaluation results yet. Run make eval to produce them.</Empty>;
  const gates: [string, Gate][] = [...Object.entries(e.detector?.gates ?? {}), ...Object.entries(e.llm?.gates ?? {})] as [string, Gate][];
  const splits = e.detector?.by_split as Record<string, Split> | undefined;
  const bHold = splits?.holdout?.scenarios.B, bConf = splits?.confirm?.scenarios.B;
  return (
    <section aria-labelledby="eval-title">
      <h1 id="eval-title" className="text-2xl font-bold">How well it works, measured honestly</h1>
      <p className="mt-1 max-w-[72ch] text-muted">Gates are scored on the true holdout, seeds 11 to 20: each seed draws its own scopes and onset weeks, they were held out from tuning; keep/revert was decided on them (D32), and one control run, seed 18, was inspected to diagnose false alerts. Seeds 21 to 30 were never looked at before this run and check for leakage. Seeds 1 to 5 tuned the detector; seeds 6 to 10 were seen in an earlier run. Gates are never loosened to pass.</p>
      {bHold && bConf && (
        <p className="mt-2 max-w-[72ch] text-muted">Adverse-selection recall before margin: <span className="num">{bHold.detected_before_cm}/{bHold.seeds}</span> held-out, <span className="num">{bConf.detected_before_cm}/{bConf.seeds}</span> on a second untouched set; with n=10 each the difference isn't significant (pooled <span className="num">{bHold.detected_before_cm + bConf.detected_before_cm}/{bHold.seeds + bConf.seeds}</span>). A known limit, not investigated.</p>
      )}
      <table className="mt-6 w-full max-w-4xl text-left text-[15px]">
        <caption className="sr-only">Evaluation gates</caption>
        <thead className="border-b border-grid text-sm text-muted"><tr><th className="py-2 pr-3">Gate</th><th className="pr-3">Result</th><th className="pr-3">Measured</th><th>Rule</th></tr></thead>
        <tbody className="divide-y divide-grid">
          {gates.map(([name, g]) => (
            <tr key={name}>
              <td className="py-2 pr-3">{name.replace(/_/g, " ")}</td>
              <td className="pr-3"><span className={`rounded px-2 py-0.5 text-sm font-semibold ${g.pass ? "bg-calm/15 text-calm" : "bg-riskwash text-risk"}`}>{g.pass ? "Pass" : "Fail"}</span></td>
              <td className="pr-3 num">{typeof g.value === "object" ? JSON.stringify(g.value) : String(g.value)}</td>
              <td className="text-sm text-muted">{g.rule}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {splits && (["holdout", "confirm", "tuning", "seen"] as const).filter((k) => splits[k]).map((k) => <SplitView key={k} name={k} s={splits[k]} />)}
      {e.llm?.summary && (
        <div className="mt-10">
          <h2 className="text-xl font-bold">Briefs and questions (seed 42, final model)</h2>
          <dl className="mt-3 grid max-w-3xl grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-[15px]">
            {Object.entries(e.llm.summary).map(([k, v]) => (
              <Fragment key={k}><dt className="text-muted">{k.replace(/_/g, " ")}</dt><dd className="num">{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd></Fragment>
            ))}
          </dl>
        </div>
      )}
      {e.cost && (
        <div className="mt-10">
          <h2 className="text-xl font-bold">Tokens and estimated cost</h2>
          <table className="mt-3 text-left text-[15px]">
            <thead className="border-b border-grid text-sm text-muted"><tr><th className="py-2 pr-4">Scope</th><th className="pr-4">Live calls</th><th className="pr-4">Input tokens</th><th className="pr-4">Output tokens</th><th>Est. cost (USD)</th></tr></thead>
            <tbody className="divide-y divide-grid">
              {Object.entries(e.cost as Record<string, Record<string, unknown>>).map(([k, t]) => (
                <tr key={k}><td className="py-2 pr-4">{k}</td><td className="pr-4 num">{String(t.live_calls ?? "")}</td><td className="pr-4 num">{String(t.input_tokens ?? "")}</td><td className="pr-4 num">{String(t.output_tokens ?? "")}</td><td className="num">{String(t.est_cost_usd ?? "")}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SplitView({ name, s }: { name: string; s: Split }) {
  const max = 16;
  return (
    <div className="mt-10">
      <h2 className="text-xl font-bold">Detector, {SPLIT_LABEL[name] ?? name} seeds {s.seeds[0]} to {s.seeds[s.seeds.length - 1]}</h2>
      <p className="mt-1 text-[15px]">
        Control run: {(Math.trunc(s.control_false_alerts_per_week * 1000) / 1000).toFixed(3)} false alerts per week ({s.control_alert_weeks} alert-weeks over {s.control_evaluable_weeks} weeks).
        Wrong-scope alerts in injected runs: {s.wrong_episodes}.
      </p>
      <ul className="mt-4 space-y-4">
        {Object.entries(s.scenarios).map(([key, sc]) => (
          <li key={key} className="grid gap-2 md:grid-cols-[16rem_1fr]">
            <div>
              <p className="font-semibold">{NAMES[key] ?? key}</p>
              <p className="text-sm text-muted">Caught before margin showed it in {sc.detected_before_cm} of {sc.seeds} seeds. The range covers those seeds only.</p>
            </div>
            <div className="self-center">
              {sc.median_lead_weeks === null ? <p className="text-sm text-muted">No early detection in these seeds.</p> : (
                <svg viewBox={`0 0 ${max * 20 + 40} 34`} className="h-9 w-full max-w-md" role="img"
                     aria-label={`Lead time ${sc.min_lead_weeks} to ${sc.max_lead_weeks} weeks, median ${sc.median_lead_weeks}`}>
                  <line x1="20" x2={max * 20 + 20} y1="14" y2="14" stroke="rgb(var(--grid))" />
                  <line x1={20 + (sc.min_lead_weeks ?? 0) * 20} x2={20 + (sc.max_lead_weeks ?? 0) * 20} y1="14" y2="14" stroke="rgb(var(--risk))" strokeWidth="4" strokeLinecap="round" />
                  <circle cx={20 + sc.median_lead_weeks * 20} cy="14" r="6" fill="rgb(var(--risk))" />
                  <text x={20 + sc.median_lead_weeks * 20} y="32" textAnchor="middle" fontSize="11" fill="rgb(var(--ink))">{sc.median_lead_weeks} wks earlier</text>
                </svg>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
