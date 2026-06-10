#!/usr/bin/env python3
"""Assemble + validate an ahoe.diagnostic.v0 payload from the agent's draft.

The agent produces a *draft* (dimensions, agents, findings, ...). This script
adds the deterministic envelope: schema_version, run metadata, and — crucially —
computes `team_level` (lowest-wins) and `gating_dimensions` so the contract's
consistency rules can never be violated by the agent. It then runs the SAME
validation the Leanmote receiver runs (RD-2068), refusing to emit on failure.

Usage:
  python build_payload.py --draft draft.json --skill-version 0.1.0 --out payload.json
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = "ahoe.diagnostic.v0"
LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
TRANSCRIPT_SOFT_CAP_BYTES = 256 * 1024  # soft guidance: keep the interview concise


def _transcript_bytes(payload):
    """Total UTF-8 size of every agent's interview_transcript (0 if none)."""
    total = 0
    for a in payload.get("agents") or []:
        t = a.get("interview_transcript") if isinstance(a, dict) else None
        if t:
            total += len(json.dumps(t, ensure_ascii=False).encode("utf-8"))
    return total


def _parse_level_move(move):
    text = str(move).replace("->", "→")
    if "→" not in text:
        return None
    a, b = [p.strip() for p in text.split("→", 1)]
    if a not in LEVEL_ORDER or b not in LEVEL_ORDER:
        return None
    return a, b


def validate(payload):
    """Return a list of error strings (empty = valid). Mirrors the receiver."""
    errors = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    mv = payload.get("maturity_vector")
    agents = payload.get("agents")
    findings = payload.get("findings")
    if not isinstance(mv, dict):
        return errors + ["maturity_vector must be an object"]
    if not isinstance(agents, list) or not agents:
        errors.append("agents[] must be a non-empty array")
    if not isinstance(findings, list):
        errors.append("findings[] must be an array")
    dims = mv.get("dimensions")
    if not isinstance(dims, dict) or not dims:
        return errors + ["maturity_vector.dimensions is required"]

    levels = []
    for name, dim in dims.items():
        level = dim.get("level") if isinstance(dim, dict) else None
        if level not in LEVEL_ORDER:
            errors.append(f"dimension {name} has invalid level {level!r}")
        else:
            levels.append(level)
    team_level = mv.get("team_level")
    if team_level not in LEVEL_ORDER:
        errors.append(f"team_level {team_level!r} is invalid")
    elif levels:
        min_level = min(levels, key=lambda lv: LEVEL_ORDER[lv])
        if team_level != min_level:
            errors.append(f"lowest-wins: team_level {team_level} != min(dimensions) {min_level}")

    agent_ids = {a.get("external_id") for a in (agents or []) if isinstance(a, dict)}
    for f in findings or []:
        if not isinstance(f, dict):
            errors.append("each finding must be an object"); continue
        if not f.get("title") or not f.get("impact") or not f.get("effort"):
            errors.append(f"finding {f.get('id')} needs title, impact and effort")
        if f.get("finding_scope") == "agent" and f.get("agent_external_id") not in agent_ids:
            errors.append(f"finding {f.get('id')} references unknown agent {f.get('agent_external_id')!r}")
        move = f.get("level_move")
        if move:
            parsed = _parse_level_move(move)
            if parsed is None:
                errors.append(f"finding {f.get('id')} has malformed level_move {move!r}")
            elif LEVEL_ORDER[parsed[1]] - LEVEL_ORDER[parsed[0]] != 1:
                errors.append(f"finding {f.get('id')} skips rungs ({move}); only L+1 allowed")
    return errors


def build(draft, skill_version):
    mv = dict(draft.get("maturity_vector") or {})
    dims = mv.get("dimensions") or {}

    # Compute lowest-wins so the agent can never get it wrong.
    valid_levels = {n: d.get("level") for n, d in dims.items()
                    if isinstance(d, dict) and d.get("level") in LEVEL_ORDER}
    if valid_levels:
        team_level = min(valid_levels.values(), key=lambda lv: LEVEL_ORDER[lv])
        mv["team_level"] = team_level
        mv["gating_dimensions"] = sorted(
            [n for n, lv in valid_levels.items() if lv == team_level],
            key=lambda n: list(dims).index(n),
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run = dict(draft.get("run") or {})
    run.setdefault("id", "run-" + uuid.uuid4().hex)  # idempotency key (required by the receiver)
    run.setdefault("started_at", now)
    run["completed_at"] = now
    run["skill_version"] = skill_version

    return {
        "schema_version": SCHEMA_VERSION,
        "scope": draft.get("scope") or ("single_agent" if len(draft.get("agents") or []) == 1 else "fleet"),
        "tenant_label": draft.get("tenant_label"),
        "run": run,
        "maturity_vector": mv,
        "agents": draft.get("agents") or [],
        "findings": draft.get("findings") or [],
        "confidence_ledger": draft.get("confidence_ledger") or {},
        "conflicts": draft.get("conflicts") or [],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build + validate an ahoe.diagnostic.v0 payload.")
    ap.add_argument("--draft", required=True, help="path to the agent's draft JSON")
    ap.add_argument("--skill-version", required=True)
    ap.add_argument("--out", required=True, help="path to write the validated payload")
    args = ap.parse_args(argv)

    with open(args.draft) as fh:
        draft = json.load(fh)

    payload = build(draft, args.skill_version)
    errors = validate(payload)
    if errors:
        print("INVALID — fix the draft and re-run:", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1

    transcript_bytes = _transcript_bytes(payload)
    if transcript_bytes > TRANSCRIPT_SOFT_CAP_BYTES:
        print(f"WARNING — interview_transcript is {transcript_bytes // 1024} KB "
              f"(> {TRANSCRIPT_SOFT_CAP_BYTES // 1024} KB soft cap). Consider trimming "
              f"answers; oversized payloads slow the POST and the drill-down.", file=sys.stderr)

    with open(args.out, "w") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"OK — {args.out} (team_level={payload['maturity_vector'].get('team_level')}, "
          f"gating={payload['maturity_vector'].get('gating_dimensions')}, "
          f"findings={len(payload['findings'])}, transcript={transcript_bytes // 1024}KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
