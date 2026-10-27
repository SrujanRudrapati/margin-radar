import { useState } from "react";
import { api } from "../api";
import type { Focus, Screen } from "../App";
import { ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import { METRIC_LABEL, score } from "../format";
import type { HeatCell, Meta, Run } from "../types";

interface HeatmapProps { run: Run; week: number; meta: Meta; open: (s: Screen, f?: Focus) => void }

export function HeatmapScreen({ run, week, meta, open }: HeatmapProps) {
  const [metric, setMetric] = useState(meta.trigger_metrics[0]);
  const state = useAsync(() => api.heatmap(run, week, metric), [run, week, metric]);
  const columns = meta.bands.flatMap((b) => ["cash", "CNML"].map((p) => ({ band: b, product: p })));
  return (
    <section aria-labelledby="heat-title">
      <h1 id="heat-title" className="text-2xl font-bold">Where each segment sits against its peers</h1>
      <p className="mt-1 max-w-[72ch] text-muted">
        Each cell compares one segment with the same band and product in the other markets, in week {week}. Darker plum means a
        larger move in the direction that costs margin. An outline means the segment's own drift test tripped; alerts themselves are raised on whole markets and price bands. Pick a market to see it against its peers.
      </p>
      <div role="radiogroup" aria-label="Metric" className="mt-5 flex flex-wrap gap-2">
        {meta.trigger_metrics.map((m) => (
          <button key={m} role="radio" aria-checked={metric === m} onClick={() => setMetric(m)}
                  className={`rounded-panel border px-3 py-1.5 text-sm ${metric === m ? "border-ink bg-ink text-paper" : "border-grid"}`}>
            {METRIC_LABEL[m] ?? m}
          </button>
        ))}
      </div>
      {state.status === "loading" && <Loading what="the heatmap" />}
      {state.status === "error" && <div className="mt-6"><ErrorNote what="the heatmap" error={state.error} /></div>}
      {state.status === "ready" && (
        <div className="mt-6 overflow-x-auto">
          <HeatLegend />
          <table className="mt-3 w-full max-w-4xl border-separate border-spacing-1">
            <caption className="sr-only">{METRIC_LABEL[metric]} uncalibrated scores by market, band and product</caption>
            <thead>
              <tr>
                <th scope="col" className="px-2 text-left text-sm font-semibold">Market</th>
                {columns.map((c) => <th key={c.band + c.product} scope="col" className="px-2 text-sm font-semibold">{c.band} {c.product}</th>)}
              </tr>
            </thead>
            <tbody>
              {meta.markets.map((market) => (
                <tr key={market}>
                  <th scope="row" className="px-2 text-left">
                    <button className="font-semibold text-focus underline-offset-2 hover:underline"
                            onClick={() => open("drilldown", { metric, dimension: "market", scope: market })}>{market}</button>
                  </th>
                  {columns.map((c) => {
                    const cell = state.data.cells.find((x) => x.market === market && x.band === c.band && x.product === c.product);
                    return <td key={c.band + c.product}><Cell cell={cell} /></td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-sm text-muted">Scores are uncalibrated: they rank how unusual a move is, not the probability that it matters. Blank cells had too little volume to score.</p>
        </div>
      )}
    </section>
  );
}

function HeatLegend() {
  const swatch = (bg: string) => <span aria-hidden="true" className="inline-block h-3.5 w-6 rounded-sm" style={{ background: bg }} />;
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted">
      <li className="flex items-center gap-1.5">{swatch("rgb(var(--peer) / 0.45)")} Moves away from margin risk</li>
      <li className="flex items-center gap-1.5">{swatch("rgb(var(--risk) / 0.15)")}{swatch("rgb(var(--risk) / 0.5)")}{swatch("rgb(var(--risk) / 0.85)")} Toward margin risk, stronger as it darkens</li>
      <li className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-block h-3.5 w-6 rounded-sm ring-2 ring-ink" /> Segment drift test tripped</li>
    </ul>
  );
}

function Cell({ cell }: { cell?: HeatCell }) {
  if (!cell || cell.score === null) return <div className="h-12 min-w-[4.5rem] rounded border border-dashed border-grid" aria-label="Too little volume to score" />;
  const towardRisk = cell.risk_direction === "+" ? cell.score : -cell.score;
  const strength = Math.min(1, Math.abs(towardRisk) / 4);
  const background = towardRisk > 0 ? `rgb(var(--risk) / ${0.08 + 0.8 * strength})` : `rgb(var(--peer) / ${0.06 + 0.5 * strength})`;
  const light = towardRisk > 0 && strength > 0.55;
  return (
    <div className={`flex h-12 min-w-[4.5rem] items-center justify-center rounded text-sm num ${cell.fired ? "ring-2 ring-ink" : ""} ${light ? "text-white" : ""}`}
         style={{ background }} title={`${cell.segment}: score ${score(cell.score)}${cell.fired ? ", segment drift test tripped" : ""}`}>
      {score(cell.score)}
    </div>
  );
}
