import { usd } from "../format";
import type { Impact } from "../types";

/** $ at risk on a shared scale: a range with a midpoint tick for scenario estimates, a single mark when measured. */
export function RangeBar({ impact, scaleMax }: { impact: Impact; scaleMax: number }) {
  if (impact.basis === "sensitivity" || impact.usd_mid === null) {
    return <p className="text-sm text-muted">Unquantified. Each 100 bps of erosion would cost {usd(impact.usd_per_100bps)}.</p>;
  }
  const at = (v: number | null) => `${Math.min(100, Math.max(0, ((v ?? 0) / scaleMax) * 100))}%`;
  const scenario = impact.basis === "scenario_estimate";
  return (
    <div className="w-full">
      <div className="relative h-3 rounded-full bg-grid/50" aria-hidden="true">
        {scenario ? (
          <div className="absolute top-0 h-3 rounded-full bg-risk/30"
               style={{ left: at(impact.usd_low), width: `calc(${at(impact.usd_high)} - ${at(impact.usd_low)})` }} />
        ) : null}
        <div className="absolute -top-1 h-5 w-[3px] rounded bg-risk" style={{ left: `calc(${at(impact.usd_mid)} - 1px)` }} />
      </div>
      <p className="mt-1.5 text-sm">
        {scenario ? (
          <>
            <span className="font-semibold">{usd(impact.usd_mid)}</span>{" "}
            <span className="text-muted">midpoint, range {usd(impact.usd_low)} to {usd(impact.usd_high)}. Scenario estimate, unconfirmed until resales.</span>
          </>
        ) : (
          <>
            <span className="font-semibold">{usd(impact.usd_mid)}</span>{" "}
            <span className="text-muted">{impact.status}</span>
          </>
        )}
      </p>
    </div>
  );
}
