#!/usr/bin/env python3
"""
Generate a Cyberpunk-2077-styled "CODE_DISTRIBUTION" chart as an animated SVG
from a user's PUBLIC repositories. Self-hosted: runs in a GitHub Action with
the built-in GITHUB_TOKEN, commits the SVG to the repo. No third-party service.

Env:
  OWNER         GitHub user (default GeorgiF0x)
  GH_TOKEN / GITHUB_TOKEN   token for the API
Args:
  argv[1]       output path (default github-chart.svg)
"""
import os, sys, json, urllib.request

OWNER = os.environ.get("OWNER", "GeorgiF0x")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = sys.argv[1] if len(sys.argv) > 1 else "github-chart.svg"
IGNORE = {"HTML", "CSS", "SCSS", "Less", "Vue", "Svelte"}  # markup, not languages
TOP_N = 6


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "georgi-chart")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    langs, nrepo = {}, 0
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        nrepo += 1
        for k, v in api(f"/repos/{OWNER}/{repo['name']}/languages").items():
            if k in IGNORE:
                continue
            langs[k] = langs.get(k, 0) + v
    return langs, nrepo


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(langs, nrepo):
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda x: -x[1])[:TOP_N]
    maxb = top[0][1] if top else 1

    row_y = [70 + i * 22 for i in range(len(top))]
    bars = []
    for i, (name, b) in enumerate(top):
        y = row_y[i]
        pct = b / total * 100
        w = max(8, b / maxb * 470)
        bars.append(
            f'<text class="mono" x="40" y="{y}" font-size="12" fill="#cfcfcf">{esc(name)}</text>'
            f'<rect x="196" y="{y-6}" width="470" height="11" fill="#111108" stroke="#55ead4" stroke-opacity="0.25"/>'
            f'<rect class="bar b{i}" x="196" y="{y-6}" width="{w:.1f}" height="11" fill="url(#barGrad)"/>'
            f'<text class="mono" x="678" y="{y}" font-size="12" fill="#f3e600" font-weight="700">{pct:4.1f}%</text>'
        )
    bars = "\n      ".join(bars)

    data_mb = total / 1_000_000
    footer = (
        f'REPOS {nrepo}  //  DATA {data_mb:.1f}MB  //  LANGS {len(langs)}  //  '
        f'<tspan fill="#f3e600">UPLINK [OK]</tspan>'
    )
    scan = "\n      ".join(
        f'<line x1="0" y1="{y}" x2="880" y2="{y}"/>' for y in range(5, 230, 6)
    )
    delays = "".join(f".b{i}{{animation-delay:{0.2+i*0.1:.2f}s}}" for i in range(len(top)))

    h = 70 + len(top) * 22 + 34
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{h}" viewBox="0 0 880 {h}" fill="none" role="img" aria-label="Code distribution across public repositories">
  <defs>
    <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#55ead4"/><stop offset="1" stop-color="#f3e600"/>
    </linearGradient>
    <radialGradient id="cbg" cx="0.3" cy="0.3" r="1">
      <stop offset="0" stop-color="#0c0c05"/><stop offset="1" stop-color="#050505"/>
    </radialGradient>
    <clipPath id="cc"><rect x="0" y="0" width="880" height="{h}" rx="4"/></clipPath>
    <style>
      .mono {{ font-family:"JetBrains Mono","Cascadia Code",ui-monospace,Menlo,Consolas,monospace; }}
      .rj {{ font-family:"Rajdhani","Arial Narrow","Roboto Condensed",system-ui,sans-serif; }}
      text {{ dominant-baseline:middle; }}
      .bar {{ transform-box:fill-box; transform-origin:left center; transform:scaleX(0); animation:grow .9s cubic-bezier(.2,.7,.2,1) forwards; }}
      @keyframes grow {{ to {{ transform:scaleX(1); }} }}
      {delays}
      .scan {{ animation:scan 4.4s linear infinite; }}
      @keyframes scan {{ 0%{{transform:translateY(-24px)}} 100%{{transform:translateY({h}px)}} }}
      .beat {{ animation:beat 1.5s ease-in-out infinite; }} @keyframes beat {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
      @media (prefers-reduced-motion: reduce) {{ .bar{{transform:scaleX(1);animation:none}} .scan,.beat{{animation:none}} }}
    </style>
  </defs>
  <rect x="0" y="0" width="880" height="{h}" rx="4" fill="url(#cbg)"/>
  <g clip-path="url(#cc)">
    <g stroke="#55ead4" stroke-width="1.2" fill="none" stroke-opacity="0.9">
      <path d="M16,32 L16,16 L34,16"/><path d="M846,16 L864,16 L864,32"/>
      <path d="M16,{h-16} L16,{h-32} M16,{h-16} L34,{h-16}"/><path d="M864,{h-32} L864,{h-16} L846,{h-16}"/>
    </g>
    <text class="rj" x="40" y="38" font-size="15" fill="#f3e600" letter-spacing="2.5" font-weight="700">&#9656; CODE_DISTRIBUTION</text>
    <text class="rj" x="864" y="38" font-size="11" fill="#55ead4" text-anchor="end" letter-spacing="2">DATAMINE_V2 <tspan class="beat" fill="#f3e600">&#9679;</tspan></text>
    <line x1="40" y1="50" x2="840" y2="50" stroke="#55ead4" stroke-opacity="0.2"/>
      {bars}
    <text class="mono" x="40" y="{h-18}" font-size="10.5" fill="#6a6a6a" letter-spacing="1">{footer}</text>
    <g stroke="#000000" stroke-opacity="0.16" stroke-width="1">
      {scan}
    </g>
    <rect class="scan" x="0" y="0" width="880" height="16" fill="#f3e600" opacity="0.04"/>
    <rect x="0.5" y="0.5" width="879" height="{h-1}" rx="4" fill="none" stroke="#f3e600" stroke-opacity="0.2"/>
  </g>
</svg>
'''


def main():
    langs, nrepo = collect()
    svg = build(langs, nrepo)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT, "-", len(langs), "languages,", nrepo, "repos")


if __name__ == "__main__":
    main()
