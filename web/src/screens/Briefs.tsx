import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { Empty, ErrorNote, Loading } from "../components/States";
import { useAsync } from "../components/useAsync";
import type { Brief, Citation, Meta } from "../types";

export function BriefScreen({ meta }: { meta: Meta }) {
  const list = useAsync(() => api.briefs(), []);
  const [week, setWeek] = useState<number>(meta.brief_weeks.includes(40) ? 40 : meta.brief_weeks[0]);
  const brief = useAsync<Brief | null>(() => (week === undefined ? Promise.resolve(null) : api.brief(week)), [week]);
  return (
    <section aria-labelledby="brief-title">
      <h1 id="brief-title" className="text-2xl font-bold">Weekly briefs</h1>
      <p className="mt-1 max-w-[72ch] text-muted">Written by Claude from governed facts only. Every number cites a fact; hover, tap or focus a citation to see the metric, value and the SQL behind it.</p>
      {list.status === "error" && <div className="mt-4"><ErrorNote what="the briefs" error={list.error} /></div>}
      {list.status === "ready" && (
        list.data.briefs.length === 0 ? <div className="mt-4"><Empty>No briefs yet. Run make briefs to write them from the recorded responses.</Empty></div> :
        <div role="tablist" aria-label="Brief week" className="mt-4 flex flex-wrap gap-2">
          {list.data.briefs.map((b) => (
            <button key={b.week} role="tab" aria-selected={b.week === week} onClick={() => setWeek(b.week)}
                    className={`rounded-panel border px-3 py-1.5 text-sm ${b.week === week ? "border-accent bg-accent text-paper" : "border-grid bg-panel hover:border-accent/50"}`}>
              Week {b.week}{b.status !== "valid" ? ` (${b.status === "no_alerts" ? "no alerts" : b.status})` : ""}
            </button>
          ))}
        </div>
      )}
      {brief.status === "loading" && <Loading what="the brief" />}
      {brief.status === "error" && <div className="mt-6"><ErrorNote what="the brief" error={brief.error} /></div>}
      {brief.status === "ready" && brief.data && <BriefView b={brief.data} />}
    </section>
  );
}

function BriefView({ b }: { b: Brief }) {
  const cites = new Map(b.citations.map((c) => [c.ref, c]));
  return (
    <article className="mt-6 max-w-[78ch] card px-7 py-6 leading-relaxed">
      <p className="text-sm font-semibold">Synthetic data — not Opendoor data.</p>
      <p className="mt-1 text-sm text-muted">Week {b.week}, from {b.week_start}. Status: {b.status}{b.model ? `, written by ${b.model}` : ""}. {b.grounding.numbers_checked} numbers checked against their facts.</p>
      <div className="mt-4">{renderBody(b.body, cites)}</div>
    </article>
  );
}

function renderBody(body: string, cites: Map<string, Citation>) {
  return body.split("\n").map((line, i) => {
    if (line.startsWith("### ")) return <h3 key={i} className="mt-5 text-lg font-semibold">{inline(line.slice(4), cites)}</h3>;
    if (line.startsWith("## ")) return <h2 key={i} className="mt-6 text-xl font-bold">{inline(line.slice(3), cites)}</h2>;
    if (line.startsWith("- ")) return <p key={i} className="mt-2 pl-4 -indent-4">– {inline(line.slice(2), cites)}</p>;
    if (!line.trim()) return null;
    return <p key={i} className="mt-2">{inline(line, cites)}</p>;
  });
}

function inline(text: string, cites: Map<string, Citation>) {
  // Text only (no HTML injection): **bold** and [q:ID] citations.
  return text.split(/(\*\*[^*]+\*\*|\[q:[A-Za-z0-9]+\])/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    const m = part.match(/^\[q:([A-Za-z0-9]+)\]$/);
    if (m) return <Cite key={i} id={m[1]} c={cites.get(m[1])} />;
    return <span key={i}>{part}</span>;
  });
}

function Cite({ id, c }: { id: string; c?: Citation }) {
  // Opens on mouse hover (the tooltip itself stays hoverable), keyboard focus, or a tap/click, which pins it open. A
  // click or Enter on a pinned or keyboard-opened citation closes it, as do Escape, blur and a tap anywhere else
  // (Safari never focuses a clicked button). Clicks ignore hover state, so a click never races a hover.
  // Hover counts only for a mouse and focus only for keyboard focus, so a tap toggles cleanly on touch screens.
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pinned, setPinned] = useState(false);
  const wrapper = useRef<HTMLSpanElement>(null);
  const tipId = useId();
  const open = hovered || focused || pinned;
  const close = () => { setHovered(false); setFocused(false); setPinned(false); };
  useEffect(() => {
    if (!pinned) return;
    const onOutside = (e: PointerEvent) => { if (!wrapper.current?.contains(e.target as Node)) close(); };
    document.addEventListener("pointerdown", onOutside);
    return () => document.removeEventListener("pointerdown", onOutside);
  }, [pinned]);
  const sql = c?.sql ? Object.entries(c.sql)[0] : undefined;
  return (
    <span ref={wrapper} className="relative inline-block indent-0"
          onPointerEnter={(e) => { if (e.pointerType === "mouse") setHovered(true); }}
          onPointerLeave={(e) => { if (e.pointerType === "mouse") setHovered(false); }}>
      <button type="button" aria-expanded={open} aria-label={`Citation ${id}`} aria-describedby={open ? tipId : undefined}
              onFocus={(e) => { if (e.currentTarget.matches(":focus-visible")) setFocused(true); }}
              onBlur={() => { setFocused(false); setPinned(false); }}
              onClick={() => (pinned || focused ? close() : setPinned(true))}
              onKeyDown={(e) => { if (e.key === "Escape") close(); }}
              className="mx-0.5 rounded bg-grid/60 px-1 align-super text-[10px] font-semibold text-muted hover:bg-accent hover:text-paper">q</button>
      {open && (
        <span id={tipId} role="tooltip" className="absolute left-0 top-6 z-20 block w-[min(30rem,80vw)] rounded-panel border border-grid bg-panel p-3 text-left text-sm shadow-lg">
          {c ? (
            <>
              <span className="block font-semibold">{c.display}: {c.label}</span>
              <span className="mt-1 block text-muted">Fact {id}{c.queries?.length ? `, from queries ${c.queries.join(", ")}` : ""}</span>
              {sql && <>
                <span className="mt-2 block text-muted">Metric {sql[1].metric} at {sql[1].level} level, compiled SQL:</span>
                <code className="mt-1 block max-h-40 overflow-auto whitespace-pre-wrap break-all rounded bg-paper p-2 text-[11px]">{sql[1].sql}</code>
              </>}
            </>
          ) : <span>Fact {id} is not in this brief's citation table.</span>}
        </span>
      )}
    </span>
  );
}
