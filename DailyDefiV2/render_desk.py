#!/usr/bin/env python3
"""packets/*.json -> desk.html + index.html (mindshare first)."""
from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))


def esc(s: str) -> str:
    return html.escape(s or "")


def lis(xs):
    out = []
    for x in xs or []:
        if isinstance(x, dict):
            out.append(
                f"<li><b>{esc(x.get('title'))}</b><div class='muted'>{esc(x.get('body'))}</div></li>"
            )
        else:
            out.append(f"<li>{esc(str(x))}</li>")
    return "".join(out)


def srcs(xs):
    return "".join(
        f'<li><a href="{esc(s.get("url"))}">{esc(s.get("label"))}</a></li>'
        for s in (xs or [])
        if s.get("url")
    )


def main() -> None:
    files = sorted((ROOT / "packets").glob("*.json"))
    if not files:
        raise SystemExit("no packets")
    pkt = json.loads(files[-1].read_text())
    issues = sorted(pkt.get("issues") or [], key=lambda x: x.get("rank", 99))
    if not issues:
        raise SystemExit("empty issues")

    widths = {1: 92, 2: 74, 3: 58, 4: 38, 5: 30, 6: 24}
    bars = rows = details = ""
    for iss in issues:
        ly = iss.get("layers") or {}
        nlayer = sum(1 for v in ly.values() if v)
        lab = f"층 {nlayer} · X{ly.get('x',0)} 아티클{ly.get('article',0)} 펌{ly.get('firm',0)}"
        w = widths.get(iss["rank"], 20)
        bars += (
            f'<div class="rv"><label><span>{iss["rank"]} {esc(iss["headline"][:32])}</span>'
            f"<span>{esc(lab)}</span></label>"
            f'<div class="track"><div class="fill" style="width:{w}%"></div></div></div>'
        )
        rows += (
            f'<a class="row" href="#i-{esc(iss["id"])}"><span class="num">{iss["rank"]}</span>'
            f'{esc(iss["headline"])}<div class="muted">{esc(iss.get("dek",""))}</div></a>'
        )
        who = " · ".join(iss.get("who") or [])
        att = f"X {ly.get('x',0)} · 아티클 {ly.get('article',0)} · 펌 {ly.get('firm',0)} · {esc(who)}"
        mech = (
            f"<h3>메커니즘</h3><p>{esc(iss.get('mechanism'))}</p>"
            if iss.get("mechanism")
            else ""
        )
        on = " on" if iss.get("rank") == 1 else ""
        details += f"""<article class="detail{on}" id="i-{esc(iss['id'])}">
    <div class="kicker">상세 {iss['rank']}</div>
    <h2>{esc(iss['headline'])}</h2>
    <p class="muted">{att}</p>
    <p>{esc(iss.get('dek',''))}</p>
    <h3>이유</h3><ol>{lis(iss.get('changes'))}</ol>
    {mech}
    <h3>가격</h3><p>{esc(iss.get('move',''))}</p>
    <h3>아직</h3><ol>{lis(iss.get('counters'))}</ol>
    <div class="src"><b>출처</b><ol>{srcs(iss.get('sources'))}</ol></div>
    </article>"""

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Depth</title>
<style>
:root {{ --bg:#0b0d10; --card:#15191f; --line:#2a313a; --muted:#9aa3ad; --text:#e8eaed; --acc:#8cb4ff; }}
body {{ margin:0; font-family:ui-sans-serif,system-ui,sans-serif; background:var(--bg); color:var(--text); }}
main {{ max-width:760px; margin:0 auto; padding:22px 16px 80px; }}
a {{ color:var(--acc); }}
h1 {{ font-size:22px; margin:6px 0 8px; }}
h2 {{ font-size:18px; margin:0 0 8px; line-height:1.35; }}
h3 {{ font-size:13px; color:var(--acc); margin:14px 0 6px; }}
.muted {{ color:var(--muted); font-size:13px; line-height:1.5; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px; margin-top:12px; }}
.kicker {{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--acc); margin-bottom:8px; }}
.rv {{ margin:10px 0 12px; }}
.rv label {{ display:flex; justify-content:space-between; gap:8px; font-size:13px; margin-bottom:4px; }}
.track {{ background:#0f1318; height:10px; border-radius:6px; overflow:hidden; }}
.fill {{ height:10px; background:#4d7cff; }}
.row {{ display:block; padding:11px 0; border-top:1px solid var(--line); color:inherit; text-decoration:none; }}
.row:first-of-type {{ border-top:0; }}
.num {{ color:var(--acc); font-weight:700; margin-right:6px; }}
.detail {{ display:none; }}
.detail.on {{ display:block; }}
ol {{ padding-left:18px; }}
li {{ margin:8px 0; line-height:1.55; }}
.src {{ margin-top:12px; padding-top:10px; border-top:1px solid var(--line); font-size:13px; }}
</style>
</head>
<body>
<main>
  <p class="muted">Depth · {esc(datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"))}</p>
  <section class="card">
    <div class="kicker">오늘 마인드셰어</div>
    <h1>누가 오늘 말을 많이 했나</h1>
    <p class="muted">팔로워 순이 아니다. 겹친 채널 수다.</p>
    {bars}
  </section>
  <section class="card">
    <div class="kicker">이슈</div>
    {rows}
  </section>
  {details}
</main>
<script>
document.querySelectorAll(".row").forEach(a => {{
  a.addEventListener("click", e => {{
    e.preventDefault();
    const id = a.getAttribute("href").slice(1);
    document.querySelectorAll(".detail").forEach(el => el.classList.toggle("on", el.id===id));
    const t = document.getElementById(id);
    if (t) t.scrollIntoView({{behavior:"smooth", block:"start"}});
  }});
}});
</script>
</body>
</html>
"""
    (ROOT / "desk.html").write_text(page)
    (ROOT / "index.html").write_text(page)
    print("wrote desk.html index.html", files[-1].name, "issues", len(issues))


if __name__ == "__main__":
    main()
