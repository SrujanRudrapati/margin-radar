# Decisions log

Decisions made on Srujan's behalf during the autonomous run (2026-10-22 →), per the instruction "wherever a skill would ask me, choose the option most consistent with CLAUDE.md and PLAN.md, log it here with reasoning, and continue." Earlier planner's calls are marked *(planner's call)* inside PLAN.md. Synthetic data — not Opendoor data.

| # | Phase | Decision | Reasoning |
|---|---|---|---|
| D1 | 4 | Use SPEC.md's tool design (`query_metric`, `compare_segments`, `cohort_curve`, `get_alerts`, each returning data + `query_id`) instead of PLAN.md's "the model sees fact IDs only" design. The LLM copies numbers with `[q:xxxx]` citations, and a grounding checker verifies every number against the cited query's logged output. | SPEC.md is authoritative for Phase 4 and asks for a "number grounding %" metric, which only means something if the model can make mistakes. Rule 2 ("the LLM never computes numbers") is enforced instead by (a) tools that return every derived number the brief needs (deltas, ranges, peer medians) and (b) the checker, which fails any number not present in a cited output. |
| D2 | 4 | Briefs are written to `briefs/week_XX.md` (SPEC.md) for the injected run only. | SPEC.md: "The agent reads only the injected-run database." Control-run views in the dashboard come from detector output, not briefs. |
