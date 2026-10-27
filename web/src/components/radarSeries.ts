import { useEffect, useState } from "react";
import { api, STATIC } from "../api";
import type { Meta, Radar, Run } from "../types";
import type { AsyncState } from "./useAsync";

/** Weeks the dashboard can show: every week live, only the exported weeks in the static build. */
export function weekList(meta: Meta): number[] {
  return STATIC && meta.export_weeks ? meta.export_weeks : Array.from({ length: meta.max_week + 1 }, (_, i) => i);
}

// One fetch per (run, week) for the page's lifetime, so replaying weeks (Play) never refetches.
const cache = new Map<string, Promise<Radar>>();
function radarWeek(run: Run, week: number): Promise<Radar> {
  const key = `${run}:${week}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const p = api.radar(run, week);
  p.catch(() => cache.delete(key));
  cache.set(key, p);
  return p;
}

/** This week's radar. Keeps showing the previous week while the next one loads, so stepping weeks doesn't flash. */
export function useRadarWeek(run: Run, week: number): AsyncState<Radar> {
  const [state, setState] = useState<AsyncState<Radar>>({ status: "loading" });
  useEffect(() => {
    let live = true;
    radarWeek(run, week).then((data) => live && setState({ status: "ready", data }))
                        .catch((e: Error) => live && setState({ status: "error", error: e.message }));
    return () => { live = false; };
  }, [run, week]);
  return state;
}

/** Every week's radar for a run, in week order: the source for the margin trend, sparkline and signal timeline. */
export function useRadarSeries(run: Run, meta: Meta): AsyncState<Radar[]> {
  const [state, setState] = useState<AsyncState<Radar[]>>({ status: "loading" });
  useEffect(() => {
    let live = true;
    setState({ status: "loading" });
    Promise.all(weekList(meta).map((w) => radarWeek(run, w)))
      .then((data) => live && setState({ status: "ready", data }))
      .catch((e: Error) => live && setState({ status: "error", error: e.message }));
    return () => { live = false; };
  }, [run, meta]);
  return state;
}
