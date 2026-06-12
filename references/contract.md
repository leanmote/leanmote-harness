# Contract — `ahoe.diagnostic.v0` (skill side)

Canonical spec: Leanmote `specs/ahoe-diagnostic-v0-contract.md` (RD-2065). Schema:
`ahoe-diagnostic.v0.schema.json` (next to this file). Summary for skill authors:

## Transport
```
POST {AHOE_ENDPOINT}/upload-data/harness-diagnostic
Authorization: Bearer {AHOE_TOKEN}
Content-Type: application/json
X-AHOE-Signature: sha256=<hex>
X-AHOE-Timestamp: <unix seconds>
X-AHOE-Skill-Version: <semver>
```
The organization is resolved server-side from the token — it is **not** in the body.

## Signing (must match the receiver byte-for-byte)
```
body = json.dumps(payload, ensure_ascii=False, separators=(",",":"))
signed = f"{ts}." + body
signature = "sha256=" + HMAC_SHA256(secret, signed).hexdigest()
```
Sign over the exact bytes you POST. Timestamp must be within ±600s (anti-replay).
`scripts/sign_and_post.py` implements this; don't re-serialize between sign and send.

## Rules the receiver enforces (so `build_payload.py` enforces them first)
1. `schema_version == "ahoe.diagnostic.v0"`.
2. Valid HMAC + fresh timestamp.
3. Structural: `maturity_vector` object, non-empty `agents[]`, `findings[]`.
4. **Lowest-wins:** `team_level == min(dimension levels)`. *(build_payload computes it.)*
5. **L+1 gating:** every `level_move` advances exactly one rung.
6. Every `agent`-scoped finding references an `external_id` present in `agents[]`;
   every finding has `title` + `impact` + `effort`. A finding MAY carry both a
   `dimension`+`level_move` and an `axis`+`agent_external_id` (not mutually
   exclusive) — use that when one move closes both a maturity gap and an
   operational gap, so it surfaces under the dimension *and* the axis.
7. **Transcript:** optional `agents[].interview_transcript` is preserved inside
   the stored signed payload and served on demand by Leanmote's "View interview"
   drill-down — it is never embedded in the dashboard's hot payload. Not a
   rejection cause; keep it concise (`build_payload.py` warns past ~256 KB).

A payload that violates any rule is rejected (4xx) — `build_payload.py` catches
these locally so the agent never posts something the receiver will refuse.
