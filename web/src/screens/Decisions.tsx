import { useState } from "react";
import { api, STATIC } from "../api";
import { Empty, ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import { bps, KIND_LABEL, usd } from "../format";
import type { Run } from "../types";

export function DecisionsScreen({ run, week }: { run: Run; week: number }) {
  const [reload, setReload] = useState(0);
  const [filter, setFilter] = useState({ decision: "", kind: "", scope: "" });
  const view = useAsync(() => api.decisions(), [reload]);
  if (view.status === "loading") return <Loading what="the decision log" />;
  if (view.status === "error") return <ErrorNote what="the decision log" error={view.error} />;
  const v = view.data;
  const rows = v.scored_rows.filter((r) => (!filter.decision || r.decision === filter.decision) && (!filter.kind || r.kind === filter.kind)
                                          && (!filter.scope || r.scope === filter.scope));
  const options = (key: "decision" | "kind" | "scope") => Array.from(new Set(v.scored_rows.map((r) => r[key]))).sort();
  return (
    <section aria-labelledby="dec-title">
      <h1 id="dec-title" className="text-2xl font-bold">Decisions and what they were worth</h1>
      <p className="mt-1 max-w-[72ch] text-muted">Each logged decision is compared with the margin that was later realized in its scope.</p>
      <dl className="mt-6 grid max-w-3xl grid-cols-2 border-y border-grid sm:grid-cols-3">
        <div className="border-r border-grid px-4 py-3"><dt className="text-sm text-muted">Decisions logged</dt><dd className="text-2xl font-semibold num">{v.score.decisions}</dd></div>
        <div className="border-grid px-4 py-3 sm:border-r"><dt className="text-sm text-muted">Alerts acted on</dt><dd className="text-2xl font-semibold num">{v.score.decisions_influenced} of {v.score.alerts_with_decisions}</dd></div>
        <div className="px-4 py-3"><dt className="text-sm text-muted">Estimated saved, sample-scale</dt><dd className="text-2xl font-semibold text-calm num">{usd(v.score.estimated_saved_usd)}</dd></div>
      </dl>
      <p className="mt-2 max-w-[80ch] text-sm text-muted">{v.score.label}.</p>
      <div className="mt-6 flex flex-wrap gap-3" aria-label="Filters">
        {(["decision", "kind", "scope"] as const).map((key) => (
          <label key={key} className="flex items-center gap-2 text-sm capitalize">{key}
            <select value={filter[key]} onChange={(e) => setFilter({ ...filter, [key]: e.target.value })} className="rounded-panel border border-grid bg-panel px-2 py-1.5">
              <option value="">All</option>
              {options(key).map((o) => <option key={o} value={o}>{key === "kind" ? KIND_LABEL[o] ?? o : o}</option>)}
            </select>
          </label>
        ))}
      </div>
      {rows.length === 0 ? <div className="mt-4"><Empty>No decisions match these filters.</Empty></div> : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-[15px]">
            <thead className="border-b border-grid text-sm text-muted"><tr><th className="py-2 pr-3">Week</th><th className="pr-3">Alert</th><th className="pr-3">Decision</th><th className="pr-3">Reason</th><th className="pr-3">Realized erosion</th><th className="pr-3">Margin showed it</th><th>Est. saved</th></tr></thead>
            <tbody className="divide-y divide-grid">
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="py-2 pr-3 num">{r.decided_week}</td>
                  <td className="pr-3">{r.scope}: {KIND_LABEL[r.kind] ?? r.kind}</td>
                  <td className="pr-3 capitalize">{r.decision}{r.decision === "acted" && !r.counted ? " (repeat, not counted)" : ""}</td>
                  <td className="pr-3">{r.reason}</td>
                  <td className="pr-3 num">{bps(r.realized_erosion_bps)}</td>
                  <td className="pr-3 num">{r.margin_visible_week === null ? "not yet" : `week ${r.margin_visible_week}`}</td>
                  <td className="num">{r.decision === "acted" ? usd(r.estimated_saved_usd) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <LogForm run={run} week={week} onSaved={() => setReload((n) => n + 1)} />
    </section>
  );
}

function LogForm({ run, week, onSaved }: { run: Run; week: number; onSaved: () => void }) {
  const radar = useAsync(() => api.radar("injected", week), [week]);
  const [form, setForm] = useState({ alert_id: "", decision: "acted", reason: "" });
  const [message, setMessage] = useState<string | null>(null);
  if (STATIC) return <p className="mt-8 max-w-[70ch] text-sm text-muted">This is the static export, so logging decisions is turned off. Run make demo to log decisions against the live API.</p>;
  const alerts = radar.status === "ready" ? radar.data.actions : [];
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.addDecision({ ...form, decided_week: week });
      setMessage("Decision logged."); setForm({ ...form, reason: "" }); onSaved();
    } catch (err) { setMessage((err as Error).message); }
  };
  return (
    <form onSubmit={submit} className="mt-10 max-w-2xl card p-6">
      <h2 className="text-lg font-semibold">Log a decision for week {week}</h2>
      {run !== "injected" && <p className="mt-1 text-sm text-muted">Decisions apply to the injected run.</p>}
      {alerts.length === 0 ? <p className="mt-3 text-sm text-muted">No active alerts in week {week} to decide on. Move the week slider to a week with alerts.</p> : (
        <div className="mt-3 grid gap-3">
          <label className="text-sm">Alert
            <select required value={form.alert_id} onChange={(e) => setForm({ ...form, alert_id: e.target.value })} className="mt-1 block w-full rounded-panel border border-grid bg-paper px-2 py-1.5">
              <option value="">Choose an alert</option>
              {alerts.map((a) => <option key={a.alert_id} value={a.alert_id}>{a.scope}: {KIND_LABEL[a.kind] ?? a.kind}</option>)}
            </select>
          </label>
          <fieldset className="text-sm"><legend>Decision</legend>
            <div className="mt-1 flex gap-4">{["acted", "deferred", "dismissed"].map((d) => (
              <label key={d} className="flex items-center gap-1.5 capitalize"><input type="radio" name="decision" value={d} checked={form.decision === d} onChange={() => setForm({ ...form, decision: d })} />{d}</label>))}
            </div>
          </fieldset>
          <label className="text-sm">Reason
            <textarea required maxLength={500} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="mt-1 block w-full rounded-panel border border-grid bg-paper px-2 py-1.5" rows={2} />
          </label>
          <button type="submit" className="justify-self-start rounded-panel bg-accent px-4 py-2 text-sm font-semibold text-paper">Log decision</button>
          {message && <p role="status" className="text-sm">{message}</p>}
        </div>
      )}
    </form>
  );
}
