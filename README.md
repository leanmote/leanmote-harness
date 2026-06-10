# leanmote-harness (AHOE skill)

Self-diagnostic skill for AI agents. The agent scores its **own** harness
maturity (5 dimensions, L1→L4, lowest-wins) and per-agent bottleneck profile
(6 axes), produces an Impact×Effort punch list gated to L+1, and posts a signed
diagnostic to **Leanmote → AI Governance → AHOE**.

Part of Leanmote (épica RD-1743). Methodology: HE-GEO. License: MIT.

- **Read-only** on the harness, runs in *your* context with *your* tokens.
- Posts only the diagnostic (an `ahoe.diagnostic.v0` payload), never source code.
- HMAC-signed; you control the cadence and the secret.

## Install
Copy this folder to your agent's skills dir:
```
cp -r leanmote-harness <repo>/.claude/skills/
```
Then set (values from the Leanmote dashboard → AI Governance → AHOE → "Connect"):
```
export AHOE_ENDPOINT=...      # tenant upload base URL
export AHOE_TOKEN=...         # bearer credential
export AHOE_HMAC_SECRET=...   # signing secret (rotated quarterly)
```

## Run
The agent runs the skill (weekly via `/agents` schedule, or on demand). Under the
hood:
```
python scripts/scan_harness.py --out evidence.json          # 1. gather artifacts (read-only)
# 2. agent applies references/scoring-rubric.md → writes draft.json
python scripts/build_payload.py --draft draft.json \
       --skill-version 0.1.0 --out payload.json             # 3. compute lowest-wins + validate
python scripts/sign_and_post.py --payload payload.json      # 4. sign (HMAC) + POST
```
`scripts/sign_and_post.py --payload payload.json --dry-run` prints the signed
request without sending — useful for a security review.

## Files
- `SKILL.md` — what the agent reads/does.
- `references/scoring-rubric.md` — the L1→L4 + 6-axis field guide.
- `references/contract.md` + `references/ahoe-diagnostic.v0.schema.json` — the wire contract (RD-2065).
- `references/draft.example.json` — a filled draft (Leanmote's own 3-agent fleet).
- `scripts/` — scan / build+validate / sign+post (stdlib only, no deps).

## Contract
Payload conforms to `ahoe.diagnostic.v0`. The signing scheme and validation
rules match the Leanmote receiver exactly (see `references/contract.md`).
