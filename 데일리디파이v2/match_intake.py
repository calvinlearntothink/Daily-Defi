#!/usr/bin/env python3
"""Step 2: cluster today's intake into issue candidates. No research prose."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))

TAGS = {
    "btc": [r"\bbitcoin\b", r"\bbtc\b", r"\betf\b"],
    "lending": [r"\baave\b", r"\bmorpho\b", r"\bcurator\b", r"\blending\b", r"\bvault\b"],
    "stables": [r"\bstablecoin\b", r"\busdc\b", r"\busdt\b", r"\busde\b", r"\bethena\b"],
    "perps": [r"\bhyperliquid\b", r"\bperp\b", r"\bfunding rate\b"],
    "rwa": [r"\brwa\b", r"\btokeniz", r"\bendo\b"],
    "unlock": [r"\bunlock\b", r"\bvesting\b"],
    "security": [r"\bhack\b", r"\bexploit\b", r"\boracle\b"],
}


def text_of(item: dict) -> str:
    return f"{item.get('title','')} {item.get('excerpt','')}".lower()


def tags_for(item: dict) -> list[str]:
    t = text_of(item)
    hit = []
    for name, pats in TAGS.items():
        if any(re.search(p, t) for p in pats):
            hit.append(name)
    return hit


def main() -> None:
    day = datetime.now(KST).date().isoformat()
    intake_path = ROOT / "intake" / f"{day}.json"
    if not intake_path.exists():
        raise SystemExit(f"missing {intake_path}")
    intake = json.loads(intake_path.read_text())
    items = list(intake.get("longform") or []) + list(intake.get("x_posts") or [])

    archive = ROOT / "archive" / "items.jsonl"
    archive.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if archive.exists():
        for line in archive.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line).get("url"))
    with archive.open("a") as f:
        for it in items:
            url = it.get("url")
            if not url or url in seen:
                continue
            rec = {
                "url": url,
                "title": it.get("title"),
                "source_id": it.get("source_id") or it.get("handle"),
                "layer": it.get("layer"),
                "published_at": it.get("published_at"),
                "captured_at": intake.get("captured_at"),
                "excerpt": it.get("excerpt"),
                "tags": tags_for(it),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            seen.add(url)

    buckets = defaultdict(list)
    for it in items:
        for tag in tags_for(it) or ["untagged"]:
            buckets[tag].append(
                {
                    "title": it.get("title"),
                    "url": it.get("url"),
                    "source_id": it.get("source_id") or it.get("handle"),
                    "layer": it.get("layer"),
                    "published_at": it.get("published_at"),
                }
            )

    candidates = []
    for tag, refs in buckets.items():
        sources = {r["source_id"] for r in refs if r.get("source_id")}
        layers = {r["layer"] for r in refs if r.get("layer")}
        if tag == "untagged":
            continue
        if len(sources) < 2 and len(refs) < 2:
            continue
        candidates.append(
            {
                "issue_key": tag,
                "repeat_count_today": len(refs),
                "distinct_sources": sorted(sources),
                "layers": sorted(layers),
                "promoted": len(sources) >= 2 or len(layers) >= 2,
                "items": refs[:20],
            }
        )
    candidates.sort(key=lambda x: (-int(x["promoted"]), -x["repeat_count_today"]))

    packet = {
        "packet_type": "collector_match",
        "for_agent": "research",
        "day": day,
        "window_start": intake.get("window_start"),
        "window_end": intake.get("window_end"),
        "captured_at": intake.get("captured_at"),
        "item_count": len(items),
        "data_snapshots": intake.get("data_snapshots"),
        "candidates": candidates,
        "note": "Research agent should use promoted=true candidates + snapshots. Do not treat journal-only clusters as evidence.",
    }
    out = ROOT / "matches" / f"{day}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, ensure_ascii=False, indent=2))
    print(json.dumps({"wrote": str(out), "candidates": [(c["issue_key"], c["repeat_count_today"], c["promoted"]) for c in candidates]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
