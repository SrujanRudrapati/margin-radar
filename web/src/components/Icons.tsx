import type { Screen } from "../App";

// Simple 20px stroke icons for the sidebar; drawn here so the app ships no icon dependency.
const PATHS: Record<Screen, string> = {
  radar: "M10 10l5.5-5.5M10 17a7 7 0 1 1 7-7M10 13.5A3.5 3.5 0 1 1 13.5 10",
  heatmap: "M3 3h6v6H3zM11 3h6v6h-6zM3 11h6v6H3zM11 11h6v6h-6z",
  drilldown: "M3 16l4.5-5 3 3L17 6M3 3v14h14",
  cohort: "M3 5h14M3 5l4 5 3-2 7 7M14 15h3v-3",
  briefs: "M5 2.5h7l3 3v12H5zM8 8h5M8 11h5M8 14h3",
  evaluation: "M10 2.5l2 1.5 2.5-.2.8 2.4 2 1.5-.8 2.3.8 2.3-2 1.5-.8 2.4-2.5-.2-2 1.5-2-1.5-2.5.2-.8-2.4-2-1.5.8-2.3-.8-2.3 2-1.5.8-2.4 2.5.2zM7.5 10l1.8 1.8L13 8",
  decisions: "M4 5.5l1.5 1.5L8 4.5M10.5 6H16M4 10.5l1.5 1.5L8 9.5M10.5 11H16M4.5 15.5h2M10.5 16H16",
};

export function ScreenIcon({ screen }: { screen: Screen }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor"
         strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
      <path d={PATHS[screen]} />
    </svg>
  );
}

/** The Margin Radar mark: a sweep line over two range rings. */
export function RadarMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-7 w-7 shrink-0">
      <rect width="24" height="24" rx="7" fill="rgb(var(--accent))" />
      <circle cx="12" cy="12" r="6.5" fill="none" stroke="white" strokeOpacity="0.55" strokeWidth="1.4" />
      <circle cx="12" cy="12" r="3" fill="none" stroke="white" strokeOpacity="0.8" strokeWidth="1.4" />
      <path d="M12 12l5-5" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
