#!/usr/bin/env python3
"""Collect harness artifacts as evidence for the AHOE self-diagnostic.

Read-only. Walks the repo for the files that describe the agent's harness and
emits a JSON summary the agent reads before scoring (step 1 of the skill). It
does NOT score anything and never reads product source beyond config/context.

Usage:
  python scan_harness.py [--root .] [--out evidence.json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

CONTEXT_NAMES = {"CLAUDE.md", "AGENTS.md", ".cursorrules"}
SKILL_GLOB = os.path.join(".claude", "skills")
MCP_NAMES = {".mcp.json", os.path.join(".cursor", "mcp.json")}
SETTINGS_NAMES = {os.path.join(".claude", "settings.json"),
                  os.path.join(".claude", "settings.local.json")}
SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "dist", "build"}


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _h2_count(text):
    return sum(1 for line in (text or "").splitlines() if line.startswith("## "))


def _git(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def scan(root):
    root = os.path.abspath(root)
    context_files, skills, mcp_configs, settings = [], [], [], []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            if name in CONTEXT_NAMES:
                text = _read(full)
                context_files.append({
                    "path": rel,
                    "lines": len((text or "").splitlines()),
                    "h2_sections": _h2_count(text),
                    "approx_tokens": len(text or "") // 4,
                })
            elif name == "SKILL.md" and SKILL_GLOB in rel:
                text = _read(full)
                skills.append({"path": rel, "lines": len((text or "").splitlines())})
            elif rel in MCP_NAMES or name == ".mcp.json":
                raw = _read(full)
                servers = []
                try:
                    data = json.loads(raw) if raw else {}
                    servers = list((data.get("mcpServers") or data.get("servers") or {}).keys())
                except Exception:
                    pass
                mcp_configs.append({"path": rel, "servers": servers})
            elif rel in SETTINGS_NAMES:
                settings.append({"path": rel, "present": True})

    return {
        "root": root,
        "context_files": context_files,
        "skills": skills,
        "mcp_configs": mcp_configs,
        "settings": settings,
        "git": {
            "is_repo": _git(root, "rev-parse", "--is-inside-work-tree") == "true",
            "last_commit": _git(root, "log", "-1", "--format=%h %cs %s"),
            "tracked_context": [
                c["path"] for c in context_files
                if _git(root, "ls-files", "--error-unmatch", c["path"]) is not None
            ],
        },
        "summary": {
            "context_files": len(context_files),
            "skills": len(skills),
            "mcp_servers": sum(len(m["servers"]) for m in mcp_configs),
            "has_settings": bool(settings),
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan harness artifacts (read-only).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None, help="write JSON here (default: stdout)")
    args = ap.parse_args(argv)

    evidence = scan(args.root)
    text = json.dumps(evidence, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"OK — evidence at {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
