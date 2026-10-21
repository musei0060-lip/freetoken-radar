#!/usr/bin/env python3
"""FreeToken Radar — track OpenRouter's free models against a verified pool.

What it does:
  1. Fetches the public OpenRouter model catalog (no API key needed).
  2. Filters models whose prompt AND completion pricing are both zero.
  3. Compares them with data/verified_pool.json — a hand-verified pool of
     free models whose total parameter count (>= 100B) was confirmed from
     vendor-official sources (vendor docs / official Hugging Face cards).
  4. Reports: pool members that vanished or got repriced, and new free
     models that are not verified yet.

Fail-closed rule: a model is NEVER treated as eligible on its name alone.
Names lie (e.g. a "120b" model can be served by a smaller variant); only
official parameter sources count. Models without one stay "unverified".

Optional: set OPENROUTER_API_KEY and pass --probe <model_id> to send a
minimal chat request and confirm the model answers at zero cost.

Stdlib only. Python 3.9+.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

MODELS_URL = "https://openrouter.ai/api/v1/models"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
POOL_PATH = Path(__file__).with_name("data") / "verified_pool.json"


def fetch_catalog() -> list[dict]:
    req = urllib.request.Request(MODELS_URL, headers={"User-Agent": "freetoken-radar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["data"]


def is_free(model: dict) -> bool:
    pricing = model.get("pricing") or {}
    try:
        return float(pricing.get("prompt", "1")) == 0.0 and float(pricing.get("completion", "1")) == 0.0
    except (TypeError, ValueError):
        return False


def load_pool() -> dict:
    with open(POOL_PATH, encoding="utf-8") as f:
        return json.load(f)


def probe(model_id: str, api_key: str) -> tuple[int, str]:
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
        "max_tokens": 64,
        "usage": {"include": True},
    }).encode()
    req = urllib.request.Request(CHAT_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "freetoken-radar/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
            cost = (data.get("usage") or {}).get("cost")
            content = ((data["choices"][0].get("message") or {}).get("content") or "").strip()
            return resp.status, f"cost={cost} reply={content[:40]!r}"
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", metavar="MODEL_ID", help="probe one free model (needs OPENROUTER_API_KEY)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    catalog = fetch_catalog()
    free = {m["id"]: m for m in catalog if is_free(m)}
    pool = load_pool()
    eligible_ids = [e["id"] for e in pool["eligible"]]
    known_ids = (
        set(eligible_ids)
        | {e["id"] for e in pool.get("verified_size_unavailable", [])}
        | {e["id"] for e in pool.get("verified_below_100b", [])}
        | {e["id"] for e in pool.get("unverified", [])}
        | {e["id"] for e in pool.get("not_single_model", [])}
        | {e["id"] for e in pool.get("excluded_non_llm", [])}
    )

    vanished = [mid for mid in eligible_ids if mid not in free]
    still_free = [mid for mid in eligible_ids if mid in free]
    new_unverified = sorted(mid for mid in free if mid not in known_ids)

    if args.json:
        print(json.dumps({
            "free_count": len(free),
            "free_ids": sorted(free),
            "eligible_still_free": still_free,
            "eligible_vanished_or_repriced": vanished,
            "new_unverified": new_unverified,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Free models on OpenRouter: {len(free)}")
        print(f"Verified eligible pool: {len(eligible_ids)} "
              f"({len(still_free)} still free, {len(vanished)} vanished/repriced)")
        for mid in still_free:
            print(f"  OK        {mid}")
        for mid in vanished:
            print(f"  MISSING   {mid}")
        if new_unverified:
            print("New free models not yet verified (names are NOT evidence):")
            for mid in new_unverified:
                print(f"  UNVERIFIED {mid}")
        else:
            print("No new unverified free models.")

    if args.probe:
        if args.probe not in free:
            print(f"REFUSED: {args.probe} is not verified free in the catalog. "
                  "Dropping the ':free' suffix can silently route to a paid variant.",
                  file=sys.stderr)
            return 2
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            print("OPENROUTER_API_KEY is not set; probe skipped.", file=sys.stderr)
            return 2
        status, detail = probe(args.probe, key)
        print(f"probe {args.probe}: HTTP {status} {detail}")
        return 0 if status == 200 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
