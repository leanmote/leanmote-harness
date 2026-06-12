# AHOE scoring rubric (condensed)

Full methodology: HE-GEO `SKILL.md` §4 (maturity) + §5 (bottleneck) +
`references/interview-protocol.md`. This is the field guide for scoring; cite
evidence from `scan_harness.py` for every level/state.

## The 5 dimensions (team level, ladder L1→L4)

Score each dimension; `build_payload.py` derives the team level as the **minimum**
(lowest-wins) and flags the gating dimensions. Never set team_level yourself.

| Dimension | L1 Artisanal | L2 Collaborative | L3 Structured | L4 Industrial |
|---|---|---|---|---|
| **Context** | ad-hoc prompts, no persistent files | a CLAUDE.md exists, patchy | comprehensive, sectioned, examples, scoped | composable, curated, regenerable, retrieval deliberate |
| **Versioning** | personal files, no history | shared location, no review | in git, PR-reviewed, revertable | checks/eval on context PRs, semver, changelog |
| **Governance** | anyone changes anything, no owner | informal ownership, chat-approved | named owners, required review, documented policy | role-based, tiered approval, automated policy checks |
| **Drift Detection** | noticed only by surprise | users flag ad-hoc | review cadence, failures trace to context | automated drift signals + anomaly detection feed versioning |
| **Distribution** | copy-paste each session | shared, pull manually | auto-pull latest at session start | real-time propagation, fleet-coordinated, staged rollout |

**L+1 gating:** a finding may move a dimension exactly one rung. If a dimension
is L1, recommend L1→L2 — never L1→L3.

## The 6 operational axes (per agent: healthy / degraded / broken / insufficient_evidence)

- **Context Retrieval** — gets the right info when needed (tools, grep, MCP, RAG).
- **Instruction Engineering** — receives clear, prioritized, example-rich instructions.
- **Context Packing** — window used efficiently; key info well-positioned.
- **Grounding / Verification** — output checked against source before delivery.
- **Output Feedback Loop** — quality observed over time, feedback flows back to the harness.
- **Collaboration** — well-integrated in the team interaction fabric (reviews, comments).

Use `insufficient_evidence` honestly when `scan_harness.py` + your own knowledge
can't ground a state. Don't guess.

## Findings (the Impact × Effort punch list)
Each finding: `title`, `impact` (high/medium/low), `effort` (high/medium/low),
plus a `dimension` + `level_move` (a maturity move) and/or an `axis` +
`agent_external_id` (an operational move). The two are **not exclusive** — a
finding may carry both when one move closes both gaps.

**Tag the dimension whenever a move closes a gating dimension's gap.** If a move
would raise a *gating* dimension one rung, it MUST carry that `dimension` +
`level_move` — even when it is also an agent/axis finding. Example: "add a domain
glossary + examples to agent X" raises **Context** (L1→L2) *and* improves the
**Retrieval** axis → tag it with BOTH `dimension: context` + `level_move:
"L1→L2"` AND `axis: context_retrieval` + `agent_external_id`. One finding, both
tags: it then surfaces under the Context dimension *and* the Retrieval axis,
without being duplicated in the punch-list.

Never bury a gating-dimension move under an axis-only finding — the dimension is
what raises the team level, so the move has to be discoverable from the very
dimension whose evidence flagged the gap. Favor high-impact / low-effort moves on
the **gating** dimensions first; those are what raise the team level.
