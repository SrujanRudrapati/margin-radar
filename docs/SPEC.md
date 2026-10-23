# SPEC.md

> Saved verbatim from the user's instructions on 2026-10-22. Authoritative for Phases 4–8 wherever PLAN.md is less detailed. Where it conflicts with decisions already made (separate DBs, peer-relative detection, excess_share, sample-scale $), those decisions win. Synthetic data — not Opendoor data.

## Phase 4 — Claude agent + grounded briefs
- Read .claude/skills/claude-api/SKILL.md first; use current SDK tool-use and prompt-caching patterns. Cached client, key from .env as MARGIN_RADAR_API_KEY, CLAUDE_MODEL_DEV during development.
- Tools: query_metric, compare_segments, cohort_curve, get_alerts — each returns data + query_id. The agent reads only the injected-run database.
- Brief /briefs/week_XX.md: synthetic-data banner; top 3 actions ranked by $ at risk (sample-scale $ + bps), each with what changed, why it's not seasonality (peer comparison), adverse-selection verdict, recommended action, owner, inline citations [q:xxxx]; a "What we're not sure about" section; explicit abstention when evidence is thin. Adverse selection shown as a labeled scenario range, "unconfirmed until resales".
- Grounding checker: every number in a brief must match the cited query's logged output after normalization (%, bps, $K/$M). Fail loudly on mismatch.
- Save the system prompt to /agent/prompts/brief_system.md. Generate ONE sample brief with CLAUDE_MODEL_FINAL at the end.

## Phase 5 — Evaluation (`make eval` → eval/results.json + eval/results.md)
- Deterministic, tuned on seeds 1–5, reported on seeds 6–10: lead time per scenario vs when margin shows the problem, precision/recall, false alerts per week on the control run, plus the agreed gates.
- LLM, one seed, CLAUDE_MODEL_FINAL: number grounding % (target 100%); brief accuracy (≥90% sections, zero direction errors); semantic-layer accuracy on 20 NL questions with gold answers, via query_metric vs raw SQL against DuckDB; abstention rate on 5 unanswerable questions.
- Use the Message Batches API if the claude-api skill confirms a discount. Report total tokens and estimated cost. Never loosen a gate; report honest numbers.

## Phase 6 — Feedback loop
- DuckDB table decision_log: alert_id, decision (acted/dismissed/deferred), reason, timestamp. A scorer that compares decisions to realized cohort margin → "decisions influenced" and "estimated $ saved (sample-scale)". Seed a few example decisions.

## Phase 7 — Dashboard (always REPLAY=1, no live API calls)
- Use the frontend-design skill. Grounded in the subject: a margin early-warning tool for pricing, ops and finance leaders; calm, precise, executive, not template-like. Tabular numerals, light and dark mode, responsive. Persistent banner: "Synthetic data — not Opendoor data."
- FastAPI in /api; Vite + React + TS + Tailwind + Recharts in /web.
- Screens: (1) Radar — KPI strip (CM%, $ at risk sample-scale, bps, active alerts) + top 3 action cards; (2) Heatmap — market × price band × product by score, click to drill in; (3) Drilldown — indicator vs peer baseline, first-alert and ground-truth markers so lead time is visible; (4) Cohort bleed curve 10%→80% sold; (5) Brief viewer — hover a cited number → metric, query_id, compiled SQL; (6) Evaluation scorecards with seed ranges and eval cost; (7) Decisions log with filters.
- Loading/empty/error states; injected vs control run toggle.
- `make export`: pre-render all API responses to JSON so the frontend runs with no backend (static hosting).
- Verify with the webapp-testing skill (.claude/skills/webapp-testing): screenshot each screen in desktop light + dark and one mobile pass, inspect, fix, repeat.

## Phase 8 — Polish + README
- requesting-code-review on the whole repo; fix important issues.
- Security: .env gitignored; `git log -p | grep -i "sk-ant"` returns nothing; key in no file, log or cache.
- Fresh clone in a temp dir, no .env: `make demo` works end to end in REPLAY mode with zero API calls.
- One-page README: problem (business math + lag), Mermaid architecture diagram, how to run, eval results table from eval/results.json, limitations (including simultaneous all-segment shifts, sample-scale $, uncalibrated scores), synthetic-data disclaimer, Claude skills used and why.
- Add a GitHub Actions workflow for GitHub Pages deployment of the static export, but do not push.
