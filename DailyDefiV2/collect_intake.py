#!/usr/bin/env python3
"""Collect dated intake from stored feed URLs + DefiLlama snapshots. No web search."""
from __future__ import annotations

import json
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
REG = json.loads((ROOT / "sources.registry.json").read_text())
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def window():
    end = now_kst()
    start = end.replace(hour=9, minute=0, second=0, microsecond=0)
    if end < start:
        start -= timedelta(days=1)
    else:
        start -= timedelta(days=1)
    return start, end


def get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "DepthDesk/0.1"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as res:
        return res.read()


def parse_feed(xml: bytes) -> list[dict]:
    root = ET.fromstring(xml)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or item.findtext("published") or ""
        desc = (item.findtext("description") or "")[:500]
        items.append({"title": title, "url": link, "published_raw": pub, "excerpt": desc})
    if items:
        return items
    for entry in root.findall("atom:entry", ns) or root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = "".join(entry.findtext("{http://www.w3.org/2005/Atom}title") or "")
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.get("href") if link_el is not None else ""
        pub = entry.findtext("{http://www.w3.org/2005/Atom}published") or entry.findtext(
            "{http://www.w3.org/2005/Atom}updated"
        ) or ""
        items.append({"title": title.strip(), "url": link, "published_raw": pub, "excerpt": ""})
    return items


def parse_time(raw: str):
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).astimezone(KST)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(KST)
    except Exception:
        return None


def main() -> None:
    start, end = window()
    captured_at = end.isoformat()
    longform = []
    feed_errors = []
    for feed in REG["feeds"]:
        try:
            items = parse_feed(get(feed["url"]))
            in_window = 0
            for it in items:
                ts = parse_time(it["published_raw"])
                it["published_at"] = ts.isoformat() if ts else None
                it["source_id"] = feed["id"]
                it["layer"] = feed["layer"]
                it["in_window"] = bool(ts and start <= ts <= end)
                if it["in_window"]:
                    in_window += 1
                longform.append(it)
            feed_errors.append({"id": feed["id"], "ok": True, "items": len(items), "in_window": in_window})
        except Exception as e:
            feed_errors.append({"id": feed["id"], "ok": False, "error": str(e)})

    snapshots = []
    for spec in REG["data_snapshots"]:
        try:
            raw = get(spec["url"])
            payload = json.loads(raw.decode("utf-8"))
            if spec["id"] == "llama-chains" and isinstance(payload, list):
                top = sorted(payload, key=lambda x: x.get("tvl") or 0, reverse=True)[:8]
                payload = [{"name": x.get("name"), "tvl": x.get("tvl")} for x in top]
            if spec["id"] == "llama-stablecoins" and isinstance(payload, dict):
                pegged = payload.get("peggedAssets") or []
                payload = [
                    {
                        "symbol": x.get("symbol"),
                        "name": x.get("name"),
                        "circ": (x.get("circulating") or {}).get("peggedUSD"),
                    }
                    for x in pegged[:8]
                ]
            snapshots.append(
                {
                    "id": spec["id"],
                    "url": spec["url"],
                    "captured_at": captured_at,
                    "ok": True,
                    "data": payload if spec["id"] != "llama-protocols-sample" else {
                        "name": payload.get("name") or payload.get("displayName"),
                        "keys": list(payload.keys())[:20],
                    },
                }
            )
        except Exception as e:
            snapshots.append(
                {"id": spec["id"], "url": spec["url"], "captured_at": captured_at, "ok": False, "error": str(e)}
            )

    out = {
        "captured_at": captured_at,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "method": "stored_feeds_plus_api_snapshots_no_search",
        "x_handles_registered": [x["handle"] for x in REG["x_always_on"]],
        "x_posts": [],
        "x_note": "X posts require from:handle + time window via X API or Grok X search; not in this script.",
        "longform": [x for x in longform if x.get("in_window")],
        "longform_seen_total": len(longform),
        "feed_status": feed_errors,
        "data_snapshots": snapshots,
    }
    dest = ROOT / "intake" / f"{end.date().isoformat()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({"wrote": str(dest), "in_window_articles": len(out["longform"]), "feeds": feed_errors}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
