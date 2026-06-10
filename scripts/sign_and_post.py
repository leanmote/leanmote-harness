#!/usr/bin/env python3
"""Sign an ahoe.diagnostic.v0 payload (HMAC-SHA256) and POST it to Leanmote.

Signing scheme MUST match the receiver (UPLOAD-DATA slug harness-diagnostic):
  body = json.dumps(payload, ensure_ascii=False, separators=(",",":"))  # exact bytes posted
  signed = f"{ts}." + body
  X-AHOE-Signature: sha256=<hexdigest(HMAC-SHA256(secret, signed))>
  X-AHOE-Timestamp: <unix seconds>
  Authorization: Bearer <token>

We sign over the *exact* serialized string we send, so the receiver verifies the
same bytes it received. Uses only the stdlib (urllib) — no third-party deps.

Usage:
  python sign_and_post.py --payload payload.json --endpoint URL --token T --secret S
  python sign_and_post.py --payload payload.json --dry-run   # print signed request, don't send
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request


def canonical_body(payload) -> str:
    """The exact string that gets both signed and posted."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def sign(body: str, secret: str, ts: int) -> str:
    signed = f"{ts}.".encode("utf-8") + body.encode("utf-8")
    return "sha256=" + hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sign + post an AHOE diagnostic.")
    ap.add_argument("--payload", required=True)
    ap.add_argument("--endpoint", default=os.environ.get("AHOE_ENDPOINT"),
                    help="upload base URL; slug /upload-data/harness-diagnostic is appended")
    ap.add_argument("--token", default=os.environ.get("AHOE_TOKEN"))
    ap.add_argument("--secret", default=os.environ.get("AHOE_HMAC_SECRET"))
    ap.add_argument("--dry-run", action="store_true", help="print the signed request, do not send")
    args = ap.parse_args(argv)

    with open(args.payload) as fh:
        payload = json.load(fh)

    if not args.secret:
        print("error: HMAC secret required (--secret or AHOE_HMAC_SECRET)", file=sys.stderr)
        return 2

    body = canonical_body(payload)
    ts = int(time.time())
    signature = sign(body, args.secret, ts)
    headers = {
        "Content-Type": "application/json",
        "X-AHOE-Signature": signature,
        "X-AHOE-Timestamp": str(ts),
        "X-AHOE-Skill-Version": str((payload.get("run") or {}).get("skill_version") or ""),
    }
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    if args.dry_run:
        print(json.dumps({"headers": headers, "body_bytes": len(body)}, indent=2))
        return 0

    if not args.endpoint or not args.token:
        print("error: --endpoint and --token required to post (or use --dry-run)", file=sys.stderr)
        return 2

    url = args.endpoint.rstrip("/") + "/upload-data/harness-diagnostic"
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.status, resp.read().decode("utf-8"))
            return 0
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read().decode("utf-8"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
