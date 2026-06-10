---
name: leanmote-harness
description: >-
  AHOE — diagnostica el harness de este agente y envía el resultado a Leanmote.
  Use this skill to self-assess the agent's harness maturity (the 5-dimension
  L1→L4 vector with lowest-wins) and per-agent bottleneck profile (6 operational
  axes), produce an Impact×Effort punch list gated to L+1, and post the signed
  diagnostic to Leanmote's AI Governance → AHOE tab. Trigger on "run the harness
  diagnostic", "score our harness", "diagnose this agent's setup", "AHOE run",
  or on the weekly schedule. Reuses the validated HE-GEO methodology.
---

# leanmote-harness (AHOE)

Self-diagnostic skill: the agent scores its **own** harness and posts the result
to Leanmote. Read-only on the harness, runs in the client's context with the
client's tokens, posts an HMAC-signed payload. No live invocation, no source code
leaves the perimeter — only the diagnostic.

Output conforms to the contract **`ahoe.diagnostic.v0`** (see
`references/contract.md`). Leanmote stores it (UPLOAD-DATA slug
`harness-diagnostic`) and renders it in **AI Governance → AHOE**.

## When to run
- Weekly (default), via `/agents` schedule or a CI step.
- On demand when someone asks to diagnose the harness.

## Workflow (follow in order)

### 1. Scan the harness (gather evidence)
Run `scripts/scan_harness.py` to collect the artifacts that ground the scoring:
`CLAUDE.md`/`AGENTS.md` (root + subdirs), `.claude/skills/*/SKILL.md`,
`.claude/settings.json`, MCP configs, and `git` status/log on those paths.
Read its JSON output — it is your evidence, not a score.

### 2. Run the HE-GEO self-interview + score
Apply the rubric in `references/scoring-rubric.md`. For **each of the 5
dimensions** (Context, Versioning, Governance, Drift Detection, Distribution)
pick a level **L1–L4** and cite evidence from step 1. For **each of the 6 axes**
(Context Retrieval, Instruction Engineering, Context Packing,
Grounding/Verification, Output Feedback Loop, Collaboration) pick a state
(`healthy`/`degraded`/`broken`/`insufficient_evidence`).

**Rules you must respect (the script enforces them too):**
- **Lowest-wins:** the team level is the minimum dimension level. *You do not set
  `team_level` — the script computes it.*
- **L+1 gating:** every finding's `level_move` advances exactly one rung
  (e.g. `L1→L2`). Never recommend a skip.
- **Evidence, not vibes:** every level/state carries at least one evidence string
  from step 1. Use `insufficient_evidence` honestly when you can't ground it.

Write your assessment as a JSON object (a "draft" — dimensions, agents,
findings, confidence_ledger). See `references/contract.md` for the shape and
`references/draft.example.json` for a filled example.

### 3. Build + validate the payload
```
python scripts/build_payload.py --draft draft.json --skill-version 0.1.0 --out payload.json
```
This fills `schema_version`/`run`, **computes `team_level` + `gating_dimensions`
(lowest-wins)**, and runs the same validation the Leanmote receiver runs. If it
prints errors, fix the draft and re-run — do not post an invalid payload.

### 4. Sign + post
```
python scripts/sign_and_post.py --payload payload.json \
    --endpoint "$AHOE_ENDPOINT" --token "$AHOE_TOKEN" --secret "$AHOE_HMAC_SECRET"
```
HMAC-SHA256 over `{timestamp}.{body}`, posts to
`{endpoint}/upload-data/harness-diagnostic`. A `201` with `id_harness_diagnostic`
means Leanmote stored it. Report that id back to the user.

## Configuration (one-time, from the Leanmote dashboard)
- `AHOE_ENDPOINT` — your tenant's upload base URL.
- `AHOE_TOKEN` — bearer credential (a `user_apps_credentials` value).
- `AHOE_HMAC_SECRET` — shared signing secret (rotated quarterly).

## What this skill never does
- Never invokes other agents or runs in production on their behalf.
- Never reads product source beyond harness/config files.
- Never writes anything in the client repo. Read-only + post-out only.
