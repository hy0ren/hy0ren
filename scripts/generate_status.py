#!/usr/bin/env python3
"""Generate assets for the profile Status Window from live GitHub data.

Runs in GitHub Actions with GITHUB_TOKEN; writes dist/status-window.svg.
"""
import json
import os
import urllib.request
from string import Template

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = os.environ.get("GH_USER", "hy0ren")
API = "https://api.github.com"


def api(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "status-window",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def gql(query):
    req = urllib.request.Request(
        f"{API}/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "status-window"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


user = api(f"{API}/users/{USER}")
repos = api(f"{API}/users/{USER}/repos?per_page=100&type=owner")
stars = sum(r["stargazers_count"] for r in repos)

langs = {}
for r in repos:
    if r["fork"]:
        continue
    try:
        for k, v in api(r["languages_url"]).items():
            langs[k] = langs.get(k, 0) + v
    except Exception:
        pass
top = sorted(langs.items(), key=lambda x: -x[1])[:4]
lang_total = sum(v for _, v in top) or 1

contrib = 0
try:
    d = gql(
        'query{user(login:"%s"){contributionsCollection'
        "{contributionCalendar{totalContributions}}}}" % USER
    )
    contrib = d["data"]["user"]["contributionsCollection"]["contributionCalendar"][
        "totalContributions"
    ]
except Exception:
    pass

rank = "E"
for r, threshold in [("S", 2000), ("A", 1200), ("B", 700), ("C", 400), ("D", 150)]:
    if contrib >= threshold:
        rank = r
        break

HEAD = Template("""<svg width="900" height="320" viewBox="0 0 900 320" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Status window: true rank S (surface scan $rank), $contrib contributions in the last year">
  <defs>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow2" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="7" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1" fill="#4CC9F0" opacity="0.04"/>
    </pattern>
    <linearGradient id="panelfade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0C1430"/>
      <stop offset="1" stop-color="#070B1A"/>
    </linearGradient>
  </defs>
  <style>
    text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; }
    .hdr { fill: #4CC9F0; font-size: 13px; letter-spacing: 5px; }
    .dot { fill: #4CC9F0; animation: blink 2s steps(1) infinite; }
    .rank { fill: #9D5CFF; font-size: 110px; font-weight: 700; }
    .ranklbl { fill: #55608A; font-size: 12px; letter-spacing: 4px; }
    .stat { fill: #8A94C0; font-size: 14px; letter-spacing: 1px; }
    .num { fill: #EAF2FF; font-size: 14px; font-weight: 700; }
    .lang { fill: #EAF2FF; font-size: 12px; }
    .pct { fill: #55608A; font-size: 11px; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.15; } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
  </style>
  <rect x="20" y="20" width="860" height="280" rx="10" fill="url(#panelfade)"/>
  <rect x="20" y="20" width="860" height="280" rx="10" fill="url(#scan)"/>
  <rect x="20.5" y="20.5" width="859" height="279" rx="9.5" stroke="#4CC9F0" stroke-opacity="0.55" filter="url(#glow)"/>
  <g stroke="#4CC9F0" stroke-width="2.5" filter="url(#glow)">
    <path d="M20 48 V20 H48"/><path d="M852 20 H880 V48"/>
    <path d="M20 272 V300 H48"/><path d="M852 300 H880 V272"/>
  </g>
  <text class="hdr" x="60" y="66"><tspan class="dot">◈</tspan> STATUS WINDOW · HUNTER LICENSE: $user</text>
  <text class="rank" x="76" y="204" filter="url(#glow2)">S</text>
  <text class="ranklbl" x="62" y="236">TRUE RANK</text>
""")

STAT_ROW = Template(
    '  <text class="stat" x="260" y="$y">$label</text>\n'
    '  <text class="num" x="560" y="$y" text-anchor="end">$value</text>\n'
)

LANG_ROW = Template(
    '  <text class="lang" x="620" y="$ty">$name</text>\n'
    '  <rect x="620" y="$by" width="200" height="6" rx="3" fill="#121A38"/>\n'
    '  <rect x="620" y="$by" width="0" height="6" rx="3" fill="$color">\n'
    '    <animate attributeName="width" from="0" to="$w" dur="1.1s" begin="$begin" '
    'fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1"/>\n'
    "  </rect>\n"
    '  <text class="pct" x="825" y="$ty">$pct%</text>\n'
)

svg = HEAD.substitute(rank=rank, contrib=contrib, user=USER.upper())

stats = [
    ("CONTRIBUTIONS · 12 MO", contrib),
    ("REPOSITORIES", user["public_repos"]),
    ("STARS EARNED", stars),
    ("ALLIES · FOLLOWERS", user["followers"]),
]
for i, (label, value) in enumerate(stats):
    svg += STAT_ROW.substitute(y=118 + i * 40, label=label, value=value)

svg += '  <text class="hdr" x="620" y="98" style="font-size:11px">MANA AFFINITY</text>\n'
colors = ["#4CC9F0", "#9D5CFF", "#4CC9F0", "#9D5CFF"]
for i, (name, size) in enumerate(top):
    pct = round(100 * size / lang_total)
    svg += LANG_ROW.substitute(
        ty=126 + i * 44,
        by=134 + i * 44,
        name=name,
        color=colors[i % len(colors)],
        w=round(200 * size / lang_total),
        begin=f"{0.2 + i * 0.15:.2f}s",
        pct=pct,
    )

svg += f'  <text class="ranklbl" x="260" y="272">SURFACE SCAN: {rank}-RANK · TRUE POWER CONCEALED · RE-SCANNED DAILY</text>\n'
svg += "</svg>\n"

os.makedirs("dist", exist_ok=True)
with open("dist/status-window.svg", "w") as f:
    f.write(svg)
print(f"rank={rank} contrib={contrib} stars={stars} langs={[n for n, _ in top]}")
