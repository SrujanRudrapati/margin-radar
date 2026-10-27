import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { SYNTHETIC_BANNER } from "./banner";
import { ErrorNote, Loading } from "./components/States";
import { weekList } from "./components/radarSeries";
import { useAsync } from "./components/useAsync";
import type { Meta, Run } from "./types";
import { RadarScreen } from "./screens/Radar";
import { HeatmapScreen } from "./screens/Heatmap";
import { DrilldownScreen } from "./screens/Drilldown";
import { CohortScreen } from "./screens/Cohort";
import { BriefScreen } from "./screens/Briefs";
import { EvaluationScreen } from "./screens/Evaluation";
import { DecisionsScreen } from "./screens/Decisions";

const PLAY_STEP_MS = 700;

export type Screen = "radar" | "heatmap" | "drilldown" | "cohort" | "briefs" | "evaluation" | "decisions";
export interface Focus { metric: string; dimension: "market" | "band"; scope: string }

const SCREENS: { id: Screen; label: string }[] = [
  { id: "radar", label: "Radar" }, { id: "heatmap", label: "Heatmap" }, { id: "drilldown", label: "Drilldown" },
  { id: "cohort", label: "Cohort bleed" }, { id: "briefs", label: "Briefs" }, { id: "evaluation", label: "Evaluation" },
  { id: "decisions", label: "Decisions" },
];

function initialScreen(): Screen {
  const hash = window.location.hash.replace("#", "") as Screen;
  return SCREENS.some((s) => s.id === hash) ? hash : "radar";
}

export default function App() {
  const meta = useAsync<Meta>(() => api.meta(), []);
  const [screen, setScreen] = useState<Screen>(initialScreen);
  const [run, setRun] = useState<Run>("injected");
  const [week, setWeek] = useState<number | null>(null);
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem("mr-theme") ? localStorage.getItem("mr-theme") === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; }
    catch { return false; }
  });
  const [focus, setFocus] = useState<Focus>({ metric: "contract_rate", dimension: "band", scope: "B2" });

  useEffect(() => { document.documentElement.classList.toggle("dark", dark); try { localStorage.setItem("mr-theme", dark ? "dark" : "light"); } catch { /* private mode */ } }, [dark]);
  useEffect(() => { window.location.hash = screen; }, [screen]);
  useEffect(() => {  // back/forward and shared links switch screens too
    const onHash = () => setScreen(initialScreen());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => { if (meta.status === "ready" && week === null) setWeek(meta.data.default_week); }, [meta, week]);

  const open = (s: Screen, f?: Focus) => { if (f) setFocus(f); setScreen(s); };

  return (
    <div className="min-h-screen">
      <p className="bg-ink px-4 py-1.5 text-center text-sm font-semibold text-paper" data-testid="banner">{SYNTHETIC_BANNER}</p>
      <div className="mx-auto flex max-w-[1280px] flex-col md:flex-row">
        <nav aria-label="Screens" className="border-b border-grid md:min-h-[calc(100vh-2rem)] md:w-52 md:shrink-0 md:border-b-0 md:border-r">
          <div className="px-4 pb-2 pt-4 md:pt-6">
            <p className="text-lg font-bold leading-tight">Margin Radar</p>
            <p className="text-sm text-muted">Margin early warning, weeks before it shows in sold homes.</p>
          </div>
          <ul className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-6">
            {SCREENS.map((s) => (
              <li key={s.id}>
                <button onClick={() => setScreen(s.id)} aria-current={screen === s.id ? "page" : undefined}
                        className={`w-full whitespace-nowrap rounded-panel px-3 py-2 text-left text-[15px] ${screen === s.id ? "bg-ink text-paper" : "hover:bg-grid/40"}`}>
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <main className="min-w-0 flex-1 px-4 pb-16 md:px-8">
          {meta.status === "loading" && <Loading what="the dashboard" />}
          {meta.status === "error" && <div className="pt-8"><ErrorNote what="the dashboard" error={meta.error} /></div>}
          {meta.status === "ready" && week !== null && (
            <>
              <Controls meta={meta.data} run={run} setRun={setRun} week={week} setWeek={setWeek} dark={dark} setDark={setDark} />
              {screen === "radar" && <RadarScreen run={run} week={week} meta={meta.data} fallback={focus} open={open} />}
              {screen === "heatmap" && <HeatmapScreen run={run} week={week} meta={meta.data} open={open} />}
              {screen === "drilldown" && <DrilldownScreen run={run} week={week} meta={meta.data} focus={focus} setFocus={setFocus} />}
              {screen === "cohort" && <CohortScreen run={run} meta={meta.data} />}
              {screen === "briefs" && <BriefScreen meta={meta.data} />}
              {screen === "evaluation" && <EvaluationScreen />}
              {screen === "decisions" && <DecisionsScreen run={run} week={week} />}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function Controls({ meta, run, setRun, week, setWeek, dark, setDark }: {
  meta: Meta; run: Run; setRun: (r: Run) => void; week: number; setWeek: (w: number) => void; dark: boolean; setDark: (d: boolean) => void;
}) {
  const weeks = useMemo(() => weekList(meta), [meta]);
  const [lo, hi] = [weeks[0], weeks[weeks.length - 1]];
  const [playing, setPlaying] = useState(false);
  useEffect(() => {  // Play steps one week at a time and stops at the last week
    if (!playing) return;
    const i = weeks.indexOf(week);
    if (i < 0 || i >= weeks.length - 1) { setPlaying(false); return; }
    const t = setTimeout(() => setWeek(weeks[i + 1]), PLAY_STEP_MS);
    return () => clearTimeout(t);
  }, [playing, week, weeks, setWeek]);
  const togglePlay = () => {
    if (!playing && week >= hi) setWeek(lo);
    setPlaying(!playing);
  };
  return (
    <div className="sticky top-0 z-10 -mx-4 mb-6 flex flex-wrap items-center gap-x-6 gap-y-3 border-b border-grid bg-paper/95 px-4 py-3 backdrop-blur md:-mx-8 md:px-8">
      <div role="radiogroup" aria-label="Run" className="flex rounded-panel border border-grid p-0.5">
        {(["injected", "control"] as Run[]).map((r) => (
          <button key={r} role="radio" aria-checked={run === r} onClick={() => setRun(r)}
                  className={`rounded px-3 py-1 text-sm ${run === r ? "bg-ink text-paper" : ""}`}>
            {r === "injected" ? "Injected problems" : "Control (no problems)"}
          </button>
        ))}
      </div>
      <div className="flex min-w-[300px] flex-1 items-center gap-3 text-sm">
        <button onClick={togglePlay} aria-pressed={playing} title="Advance one week every 0.7 seconds"
                className="flex w-[4.75rem] items-center justify-center gap-1.5 rounded-panel border border-grid px-2 py-1 text-sm">
          <svg aria-hidden="true" viewBox="0 0 10 10" className="h-2.5 w-2.5 fill-current">
            {playing ? <path d="M1 1h3v8H1zM6 1h3v8H6z" /> : <path d="M1.5 1l7.5 4-7.5 4z" />}
          </svg>
          {playing ? "Pause" : "Play"}
        </button>
        <label className="flex flex-1 items-center gap-3">
          <span className="whitespace-nowrap font-semibold num">Week {week}</span>
          <input type="range" min={lo} max={hi} value={week} onChange={(e) => { setPlaying(false); setWeek(Number(e.target.value)); }}
                 className="flex-1 accent-[rgb(var(--ink))]" aria-label="As-of week" />
          <span className="whitespace-nowrap text-muted">from {meta.week_starts[week]}</span>
        </label>
      </div>
      <button onClick={() => setDark(!dark)} className="rounded-panel border border-grid px-3 py-1 text-sm" aria-pressed={dark}>
        {dark ? "Light mode" : "Dark mode"}
      </button>
    </div>
  );
}
