import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import { pct } from "../format";
import type { Meta, Run } from "../types";

export function CohortScreen({ run, meta }: { run: Run; meta: Meta }) {
  const [scope, setScope] = useState("B2");
  const level = scope.startsWith("M") ? "market" : "band";
  const other: Run = run === "injected" ? "control" : "injected";
  const state = useAsync(() => Promise.all([api.cohort(run, meta.max_week, level, scope), api.cohort(other, meta.max_week, level, scope)]),
                         [run, scope]);
  return (
    <section aria-labelledby="cohort-title">
      <h1 id="cohort-title" className="text-2xl font-bold">How a purchase cohort's margin bleeds as it sells</h1>
      <p className="mt-1 max-w-[72ch] text-muted">
        Homes bought in weeks 30 to 33, when the injected problems began. Each point is the contribution margin of the first 10% to 80%
        of the cohort to resell, measured with data up to week {meta.max_week}. A mispriced cohort shows its loss late, as its slowest homes sell.
      </p>
      <label className="mt-5 flex items-center gap-2 text-sm">
        Scope
        <select value={scope} onChange={(e) => setScope(e.target.value)} className="rounded-panel border border-grid bg-panel px-2 py-1.5">
          {[...meta.bands, ...meta.markets].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      {state.status === "loading" && <Loading what="the cohort curve" />}
      {state.status === "error" && <div className="mt-6"><ErrorNote what="the cohort curve" error={state.error} /></div>}
      {state.status === "ready" && (() => {
        const [mine, theirs] = state.data;
        const rows = mine.points.map((p, i) => ({ share: `${Math.round(p.sold_share * 100)}%`, [run]: p.cm_pct, [other]: theirs.points[i]?.cm_pct }));
        return (
          <figure className="mt-6 rounded-panel border border-grid bg-panel p-3">
            <figcaption className="px-2 pt-1 text-sm font-semibold">{scope}: margin of the first homes to sell ({mine.cohort_homes} homes in the cohort)</figcaption>
            <div className="h-[320px]">
              <ResponsiveContainer>
                <LineChart data={rows} margin={{ top: 16, right: 16, bottom: 4, left: 4 }}>
                  <CartesianGrid stroke="rgb(var(--grid))" strokeDasharray="2 4" vertical={false} />
                  <XAxis dataKey="share" stroke="rgb(var(--muted))" tick={{ fontSize: 12 }} label={{ value: "share of cohort sold", position: "insideBottom", offset: -2, fontSize: 12 }} height={40} />
                  <YAxis stroke="rgb(var(--muted))" tick={{ fontSize: 12 }} tickFormatter={(v) => pct(v)} width={56} />
                  <Tooltip formatter={(v: number) => pct(v)} contentStyle={{ background: "rgb(var(--panel))", border: "1px solid rgb(var(--grid))" }} />
                  <Legend verticalAlign="top" height={28} />
                  <Line dataKey={run} name={run === "injected" ? "Injected run" : "Control run"} stroke="rgb(var(--risk))" strokeWidth={2.5} isAnimationActive={false} />
                  <Line dataKey={other} name={other === "injected" ? "Injected run" : "Control run"} stroke="rgb(var(--peer))" strokeDasharray="5 4" strokeWidth={2} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="px-2 pb-1 text-sm text-muted">Source query: {mine.query_id}. Points that the cohort has not reached yet are left out.</p>
          </figure>
        );
      })()}
    </section>
  );
}
