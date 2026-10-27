import { usd } from "../format";
import type { Impact } from "../types";

/** $ at risk on a shared scale: low, midpoint and high each marked and labeled for scenario estimates; one mark when measured. */
export function RangeBar({ impact, scaleMax }: { impact: Impact; scaleMax: number }) {
  if (impact.basis === "sensitivity" || impact.usd_mid === null) {
    return <p className="text-sm text-muted">Unquantified. Each 100 bps of erosion would cost {usd(impact.usd_per_100bps)}.</p>;
  }
  const at = (v: number | null) => Math.min(100, Math.max(0, ((v ?? 0) / scaleMax) * 100));
  const scenario = impact.basis === "scenario_estimate";
  const marks = scenario
    ? [{ name: "Low", v: impact.usd_low, main: false }, { name: "Midpoint", v: impact.usd_mid, main: true }, { name: "High", v: impact.usd_high, main: false }]
    : [{ name: "Measured", v: impact.usd_mid, main: true }];
  // Labels sit under their marks; near an edge they align to it instead of overflowing.
  const shift = (p: number) => (p < 12 ? "0%" : p > 88 ? "-100%" : "-50%");
  return (
    <div className="w-full">
      <div className="relative h-2.5 rounded-full bg-grid/50" aria-hidden="true">
        {scenario && <div className="absolute top-0 h-2.5 rounded-full bg-risk/25"
                          style={{ left: `${at(impact.usd_low)}%`, width: `${at(impact.usd_high) - at(impact.usd_low)}%` }} />}
        {marks.map((m) => (
          <div key={m.name} className={`absolute rounded bg-risk ${m.main ? "-top-1.5 h-[22px] w-[3px]" : "-top-0.5 h-3.5 w-[2px]"}`}
               style={{ left: `calc(${at(m.v)}% - 1px)` }} />
        ))}
      </div>
      <dl className="relative mt-2 h-10 text-sm num">
        {marks.map((m) => (
          <div key={m.name} className="absolute top-0 whitespace-nowrap" style={{ left: `${at(m.v)}%`, transform: `translateX(${shift(at(m.v))})`,
                                                                                  textAlign: shift(at(m.v)) === "-50%" ? "center" : shift(at(m.v)) === "0%" ? "left" : "right" }}>
            <dt className="text-xs text-muted">{m.name}</dt>
            <dd className={m.main ? "font-semibold text-risk" : "font-medium"}>{usd(m.v)}</dd>
          </div>
        ))}
      </dl>
      {(scenario || impact.status !== "measured") && <p className="text-xs text-muted">{scenario ? "Scenario estimate, unconfirmed until resales." : impact.status}</p>}
    </div>
  );
}
