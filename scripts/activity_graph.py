"""Generate a green contribution line graph (smooth curve + points) as an SVG.

Usage: GH_TOKEN=... GH_USER=OthmaneAbder2303 python scripts/activity_graph.py
Optional: DAYS=31 OUT=activity-graph.svg
"""
import json
import math
import os
import random
import urllib.request
from datetime import datetime, timedelta, timezone

USER = os.environ.get("GH_USER", "OthmaneAbder2303")
TOKEN = os.environ.get("GH_TOKEN", "")
DAYS = int(os.environ.get("DAYS", "31"))
OUT = os.environ.get("OUT", "activity-graph.svg")

# Theme (matches the profile header)
BG, GRID, TEXT = "#071E16", "#123A2C", "#E8FFF4"
LINE, DOT, FILL_TOP = "#19A974", "#7DFFBE", "#19A974"


def fetch_counts():
    if os.environ.get("MOCK"):
        today = datetime.now(timezone.utc).date()
        random.seed(3)
        return [((today - timedelta(days=DAYS - 1 - i)), random.choice([0, 0, 1, 3, 5, 8, 12, 4, 2, 15])) for i in range(DAYS)]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS - 1)
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    payload = json.dumps({"query": query, "variables": {
        "login": USER,
        "from": start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
        "to": end.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=payload,
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    days = {}
    for w in data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days[datetime.fromisoformat(d["date"]).date()] = d["contributionCount"]
    today = end.date()
    return [(today - timedelta(days=DAYS - 1 - i), days.get(today - timedelta(days=DAYS - 1 - i), 0)) for i in range(DAYS)]


def smooth_path(pts):
    """Catmull-Rom -> cubic Bezier."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def main():
    data = fetch_counts()
    W, H = 900, 320
    L, R, T, B = 55, 25, 60, 45
    pw, ph = W - L - R, H - T - B
    peak = max(c for _, c in data) or 1
    step = max(1, math.ceil(peak / 4))
    ymax = step * 4
    xs = [L + pw * i / (len(data) - 1) for i in range(len(data))]
    base = T + ph
    ys = [base - ph * c / ymax for _, c in data]
    pts = list(zip(xs, ys))
    curve = smooth_path(pts)
    clamp_note = ""  # curve can overshoot slightly; clip to the plot area instead
    total = sum(c for _, c in data)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">',
         '<defs>',
         f'<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FILL_TOP}" stop-opacity="0.55"/><stop offset="1" stop-color="{FILL_TOP}" stop-opacity="0.02"/></linearGradient>',
         f'<clipPath id="plot"><rect x="{L}" y="{T - 6}" width="{pw}" height="{ph + 6}"/></clipPath>',
         '</defs>',
         f'<rect width="{W}" height="{H}" rx="12" fill="{BG}" stroke="#0C6B4F"/>',
         f'<text x="{L}" y="32" fill="{TEXT}" font-size="18" font-weight="700">Contribution activity</text>',
         f'<text x="{W - R}" y="32" fill="{DOT}" font-size="13" text-anchor="end">{total} contributions · last {DAYS} days</text>']
    for k in range(5):
        y = base - ph * k / 4
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W - R}" y2="{y:.1f}" stroke="{GRID}" stroke-dasharray="4 4"/>')
        s.append(f'<text x="{L - 10}" y="{y + 4:.1f}" fill="{TEXT}" opacity="0.7" font-size="11" text-anchor="end">{step * k}</text>')
    for i, (d, _) in enumerate(data):
        if i % 5 == 0 or i == len(data) - 1:
            s.append(f'<text x="{xs[i]:.1f}" y="{H - 18}" fill="{TEXT}" opacity="0.7" font-size="11" text-anchor="middle">{d.strftime("%b %d").replace(" 0", " ")}</text>')
    s.append('<g clip-path="url(#plot)">')
    s.append(f'<path d="{curve} L{xs[-1]:.1f},{base} L{xs[0]:.1f},{base} Z" fill="url(#fill)"/>')
    s.append(f'<path d="{curve}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    s.append('</g>')
    for (x, y), (d, c) in zip(pts, data):
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{DOT}" stroke="{BG}" stroke-width="1.5"><title>{d.isoformat()}: {c} contributions</title></circle>')
    s.append('</svg>')
    open(OUT, "w").write("\n".join(s))
    print(f"wrote {OUT}: {total} contributions over {DAYS} days")


main()
