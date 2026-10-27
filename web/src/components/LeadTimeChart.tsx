import { CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { METRIC_LABEL, metricValue, pct } from "../format";
import type { Drill, Radar } from "../types";

const HINDSIGHT_WEEKS = 8;  // how far past the margin marker the hindsight view reaches
const TICK_EVERY = 4;
const MIN_WEEKS = 4;  // fewer points than this is not a trend
const tooltipStyle = { background: "rgb(var(--panel))", border: "1px solid rgb(var(--grid))", fontSize: 13 };
const axisTick = { fontSize: 12, fill: "rgb(var(--muted))" };

/**
 * The radar's hero: the alerting indicator against its peers, above portfolio sold-home margin (context), on one week axis.
 * The margin marker is when the alerting scope's own cohort margin showed the problem; that series is not plotted.
 * Markers come from the evaluation's lead-time markers (make markers), the same ones the Drilldown shows.
 * Weeks after the selected week are drawn faded as hindsight, so the gap stays visible mid-story.
 */
export function LeadTimeChart({ d, series, week }: { d: Drill; series: Radar[]; week: number }) {
  const cmByWeek = new Map(series.map((r) => [r.week, r.kpis.cm_pct]));
  const t = d.truth;
  const alertWeek = t?.first_alert_week ?? null, marginWeek = t?.cm_first_visible_week ?? null;
  const showLead = t !== null && alertWeek !== null && marginWeek !== null && alertWeek <= week;
  const last = Math.max(...series.map((r) => r.week));
  const end = showLead ? Math.min(last, Math.max(week, marginWeek! + HINDSIGHT_WEEKS)) : week;
  const rows = d.weeks.map((w, i) => ({ week: w, value: d.value[i], peer: d.peer[i], cm: cmByWeek.get(w) ?? null }))
                      .filter((r) => r.week <= end && cmByWeek.has(r.week));
  if (rows.length < MIN_WEEKS) return null;
  const start = rows[0].week;
  const metric = METRIC_LABEL[d.metric] ?? d.metric;
  const fmt = (v: number) => metricValue(d.metric, v);
  const xTicks = Array.from({ length: Math.floor((end - start) / TICK_EVERY) + 1 }, (_, i) => start + i * TICK_EVERY);
  const x = { dataKey: "week", type: "number" as const, domain: [start, end], ticks: xTicks, stroke: "rgb(var(--grid))", tick: axisTick };
  // Margin axis: whole points, with a point and a half of room under the line for the lead label.
  const cms = rows.map((r) => r.cm).filter((v): v is number => v !== null);
  const cmLo = Math.floor((Math.min(...cms) - 0.015) * 100), cmHi = Math.ceil(Math.max(...cms) * 100);
  const cmTicks = Array.from({ length: Math.floor((cmHi - cmLo) / 2) + 1 }, (_, i) => (cmLo + i * 2) / 100);
  const hindsight = (labelled: boolean) => end > week ? (
    <ReferenceArea x1={week} x2={end} fill="rgb(var(--panel))" fillOpacity={0.72} ifOverflow="hidden"
                   label={labelled ? { value: `Hindsight, after week ${week}`, position: "insideTopRight", fontSize: 11, fill: "rgb(var(--muted))" } : undefined} />
  ) : null;
  const gap = showLead ? <ReferenceArea x1={alertWeek!} x2={marginWeek!} fill="rgb(var(--risk))" fillOpacity={0.09} ifOverflow="hidden" /> : null;
  const alertLine = showLead ? <ReferenceLine x={alertWeek!} stroke="rgb(var(--risk))" strokeWidth={2} /> : null;
  const marginLine = showLead ? <ReferenceLine x={marginWeek!} stroke="rgb(var(--ink))" strokeWidth={1.5} strokeDasharray="5 3" /> : null;

  return (
    <figure className="card px-5 pb-4 pt-5 sm:px-6">
      <figcaption>
        <p className="text-lg font-semibold leading-snug sm:text-xl">
          {showLead
            ? <>{d.scope} {metric.toLowerCase()} broke from its peers <span className="text-risk">{t!.lead_weeks} weeks</span> before {d.scope} cohort margin showed it.</>
            : d.alerts.some((a) => a.first_week <= week)
              ? <>{d.scope} {metric.toLowerCase()} has broken from its peers; {d.scope} cohort margin has not shown it yet.</>
              : <>{d.scope} {metric.toLowerCase()} is moving with its peers. Seasonal swings show in both lines and are not flagged.</>}
        </p>
        <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
          <Key color="var(--risk)">{d.scope} {metric.toLowerCase()}</Key>
          <Key color="var(--peer)">Peer median</Key>
          <Key color="var(--ink)">Portfolio sold-home margin, 13-week trailing (context)</Key>
        </ul>
      </figcaption>
      <div className="mt-2 h-[190px]">
        <ResponsiveContainer>
          <ComposedChart data={rows} syncId="lead" margin={{ top: 22, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="rgb(var(--grid))" strokeDasharray="2 4" vertical={false} />
            <XAxis {...x} hide />
            <YAxis stroke="rgb(var(--grid))" tick={axisTick} tickFormatter={fmt} width={52} domain={["auto", "auto"]} />
            <Tooltip formatter={(v: number) => fmt(v)} labelFormatter={(w) => `Week ${w}`} contentStyle={tooltipStyle} />
            <Line dataKey="peer" name="Peer median" stroke="rgb(var(--peer))" dot={false} strokeWidth={2} connectNulls isAnimationActive={false} />
            <Line dataKey="value" name={d.scope} stroke="rgb(var(--risk))" dot={false} strokeWidth={2.5} connectNulls isAnimationActive={false} />
            {hindsight(true)}{gap}{alertLine}{marginLine}
            {showLead && <ReferenceLine x={alertWeek!} stroke="none" label={{ value: `Alert raised (wk ${alertWeek})`, position: "insideTopRight", offset: 6, fontSize: 12, fontWeight: 600, fill: "rgb(var(--risk))" }} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs font-medium text-muted">
        Below: portfolio sold-home margin, shown for context.{showLead ? ` The dashed marker is when ${d.scope} cohort margin showed the problem.` : ""}
      </p>
      <div className="h-[150px]">
        <ResponsiveContainer>
          <ComposedChart data={rows} syncId="lead" margin={{ top: 22, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="rgb(var(--grid))" strokeDasharray="2 4" vertical={false} />
            <XAxis {...x} tickFormatter={(w) => `wk ${w}`} />
            <YAxis stroke="rgb(var(--grid))" tick={axisTick} tickFormatter={(v) => pct(v, 0)} width={52} domain={[cmTicks[0], cmTicks[cmTicks.length - 1]]} ticks={cmTicks} />
            <Tooltip formatter={(v: number) => pct(v)} labelFormatter={(w) => `Week ${w}`} contentStyle={tooltipStyle} />
            <Line dataKey="cm" name="Portfolio sold-home margin" stroke="rgb(var(--ink))" dot={false} strokeWidth={2} connectNulls isAnimationActive={false} />
            {hindsight(false)}{gap}{alertLine}{marginLine}
            {showLead && <ReferenceLine x={marginWeek!} stroke="none" label={{ value: `${d.scope} cohort margin shows it (wk ${marginWeek})`, position: "insideTopLeft", offset: 6, fontSize: 12, fontWeight: 600, fill: "rgb(var(--ink))" }} />}
            {showLead && <ReferenceArea x1={alertWeek!} x2={marginWeek!} fill="none" ifOverflow="hidden"
                                        label={{ value: t!.lead_weeks! >= 5 ? `${t!.lead_weeks}-week lead` : `${t!.lead_weeks} wks`, position: "insideBottom", offset: 4, fontSize: 12, fontWeight: 600, fill: "rgb(var(--risk))" }} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs text-muted">
        Portfolio margin includes the expected Q2 to Q3 seasonal dip. Markers are this synthetic run's lead-time markers, the same ones the Drilldown shows. Source queries: {d.query_ids.join(", ")}.
      </p>
    </figure>
  );
}

function Key({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-1.5">
      <span aria-hidden="true" className="inline-block h-[3px] w-4 rounded" style={{ background: `rgb(${color})` }} />
      {children}
    </li>
  );
}
