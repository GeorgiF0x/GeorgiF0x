#!/usr/bin/env python3
"""
Generate a Cyberpunk-2077-styled "STACK.MATRIX" radar chart as an animated SVG
from a user's PUBLIC repositories. Self-hosted: runs in a GitHub Action with the
built-in GITHUB_TOKEN and commits the SVG. No third-party rendering service.

Env:  OWNER (default GeorgiF0x), GH_TOKEN / GITHUB_TOKEN
Args: argv[1] output path (default github-chart.svg)
"""
import os, sys, json, math, urllib.request

OWNER = os.environ.get("OWNER", "GeorgiF0x")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = sys.argv[1] if len(sys.argv) > 1 else "github-chart.svg"
IGNORE = {"HTML", "CSS", "SCSS", "Less", "Vue", "Svelte"}  # markup, not languages
TOP_N = 6

LANGCOL = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Java": "#e76f00",
    "Python": "#4B8BBE", "PHP": "#8892be", "Astro": "#ff5d01",
    "PLpgSQL": "#4a90c2", "C#": "#178600", "Go": "#00ADD8", "Shell": "#89e051",
    "Ruby": "#cc342d", "Kotlin": "#A97BFF", "Dart": "#00B4AB", "C++": "#f34b7d",
}


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
    n = len(top)
    maxb = top[0][1] if top else 1

    CX, CY, R = 232, 150, 100
    H = 288

    def pt(i, r):
        a = math.radians(-90 + 360 * i / n)
        return (CX + r * math.cos(a), CY + r * math.sin(a))

    # concentric hexagon rings
    rings = []
    for k in (0.25, 0.5, 0.75, 1.0):
        poly = " ".join("%.1f,%.1f" % pt(i, R * k) for i in range(n))
        op = 0.25 if k == 1.0 else 0.09
        rings.append('<polygon points="%s" fill="none" stroke="#55ead4" stroke-opacity="%s" stroke-width="1"/>' % (poly, op))
    rings = "".join(rings)

    axes = "".join(
        '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#55ead4" stroke-opacity="0.15"/>'
        % (CX, CY, *pt(i, R)) for i in range(n)
    )

    # data polygon: sqrt scale (relative to the largest language) so a skewed
    # distribution still fills the hexagon and small langs stay visible, with a
    # floor so no vertex collapses to the centre.
    dpts = [pt(i, R * max(0.16, math.sqrt(b / maxb))) for i, (nm, b) in enumerate(top)]
    dpoly = " ".join("%.1f,%.1f" % p for p in dpts)
    verts = "".join('<circle cx="%.1f" cy="%.1f" r="2.8" fill="#f3e600"/>' % p for p in dpts)

    # vertex labels
    labels = []
    for i, (nm, b) in enumerate(top):
        lx, ly = pt(i, R + 15)
        anchor = "middle" if abs(lx - CX) < 12 else ("end" if lx < CX else "start")
        labels.append(
            '<text x="%.0f" y="%.0f" text-anchor="%s" class="rj" font-size="11" fill="#dcdcdc" letter-spacing="0.5">%s</text>'
            % (lx, ly, anchor, esc(nm.upper()))
        )
    labels = "".join(labels)

    # legend (right)
    leg = []
    for i, (nm, b) in enumerate(top):
        y = 66 + i * 28
        pct = b / total * 100
        col = LANGCOL.get(nm, "#55ead4")
        bw = max(4, pct / (top[0][1] / total * 100) * 150)
        leg.append(
            '<rect x="452" y="%d" width="9" height="9" fill="%s"/>' % (y - 5, col)
            + '<text x="470" y="%d" class="mono" font-size="12" fill="#d8d8d8">%s</text>' % (y, esc(nm))
            + '<rect x="620" y="%d" width="150" height="7" fill="#111108" stroke="#55ead4" stroke-opacity="0.2"/>' % (y - 4)
            + '<rect class="bar b%d" x="620" y="%d" width="%.1f" height="7" fill="%s"/>' % (i, y - 4, bw, col)
            + '<text x="792" y="%d" class="mono" font-size="11.5" fill="#f3e600" font-weight="700" text-anchor="end">%4.1f%%</text>' % (y, pct)
        )
    leg = "".join(leg)
    delays = "".join(".b%d{animation-delay:%.2fs}" % (i, 0.6 + i * 0.1) for i in range(n))

    # sonar sweep wedge (44 deg, subtle), rotates around the radar centre
    wx, wy = R * math.sin(math.radians(44)), -R * math.cos(math.radians(44))
    wedge = 'M0,0 L0,%.1f A%d,%d 0 0 1 %.1f,%.1f Z' % (-R, R, R, wx, wy)

    data_mb = total / 1_000_000
    footer = 'REPOS %d  //  DATA %.1fMB  //  LANGS %d  //  <tspan fill="#f3e600">UPLINK [OK]</tspan>' % (nrepo, data_mb, len(langs))
    scan = "".join('<line x1="0" y1="%d" x2="880" y2="%d"/>' % (y, y) for y in range(5, H, 6))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{H}" viewBox="0 0 880 {H}" fill="none" role="img" aria-label="Language stack radar across public repositories">
  <defs>
    <radialGradient id="poly" cx="0.5" cy="0.5" r="0.6">
      <stop offset="0" stop-color="#f3e600" stop-opacity="0.28"/><stop offset="1" stop-color="#55ead4" stop-opacity="0.14"/>
    </radialGradient>
    <radialGradient id="cbg" cx="0.28" cy="0.35" r="1">
      <stop offset="0" stop-color="#0c0c05"/><stop offset="1" stop-color="#050505"/>
    </radialGradient>
    <linearGradient id="sweepGrad" x1="0" y1="1" x2="0.5" y2="0">
      <stop offset="0" stop-color="#55ead4" stop-opacity="0"/><stop offset="1" stop-color="#55ead4" stop-opacity="0.28"/>
    </linearGradient>
    <filter id="pglow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="cc"><rect x="0" y="0" width="880" height="{H}" rx="4"/></clipPath>
    <clipPath id="radar"><circle cx="{CX}" cy="{CY}" r="{R}"/></clipPath>
    <style>
      .mono {{ font-family:"JetBrains Mono","Cascadia Code",ui-monospace,Menlo,Consolas,monospace; }}
      .rj {{ font-family:"Rajdhani","Arial Narrow","Roboto Condensed",system-ui,sans-serif; }}
      text {{ dominant-baseline:middle; }}
      .bar {{ transform-box:fill-box; transform-origin:left center; transform:scaleX(0); animation:grow .9s cubic-bezier(.2,.7,.2,1) forwards; }}
      @keyframes grow {{ to {{ transform:scaleX(1); }} }}
      {delays}
      .poly {{ opacity:0; transform-box:fill-box; transform-origin:{CX}px {CY}px; transform:scale(.6); animation:pin .8s .3s cubic-bezier(.2,.8,.2,1) forwards; }}
      @keyframes pin {{ to {{ opacity:1; transform:scale(1); }} }}
      .pulse {{ animation:pulse 3.2s ease-in-out infinite; }} @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.55}} }}
      .beat {{ animation:beat 1.5s ease-in-out infinite; }} @keyframes beat {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
      .scanl {{ animation:scanl 4.4s linear infinite; }} @keyframes scanl {{ 0%{{transform:translateY(-24px)}} 100%{{transform:translateY({H}px)}} }}
      @media (prefers-reduced-motion: reduce) {{ .bar{{transform:scaleX(1);animation:none}} .poly{{opacity:1;transform:none;animation:none}} .sweep,.scanl,.beat,.pulse{{animation:none}} .sweep{{display:none}} }}
    </style>
  </defs>
  <rect x="0" y="0" width="880" height="{H}" rx="4" fill="url(#cbg)"/>
  <g clip-path="url(#cc)">
    <g stroke="#55ead4" stroke-width="1.2" fill="none" stroke-opacity="0.9">
      <path d="M16,32 L16,16 L34,16"/><path d="M846,16 L864,16 L864,32"/>
      <path d="M16,{H-16} L16,{H-32} M16,{H-16} L34,{H-16}"/><path d="M864,{H-32} L864,{H-16} L846,{H-16}"/>
    </g>
    <text class="rj" x="40" y="36" font-size="15" fill="#f3e600" letter-spacing="2.5" font-weight="700">&#9656; STACK.MATRIX</text>
    <text class="rj" x="864" y="36" font-size="11" fill="#55ead4" text-anchor="end" letter-spacing="2">SCAN <tspan class="beat" fill="#f3e600">&#9679;</tspan></text>
    <line x1="40" y1="48" x2="840" y2="48" stroke="#55ead4" stroke-opacity="0.2"/>

    <!-- radar -->
    {rings}
    {axes}
    <g clip-path="url(#radar)"><g class="sweep" transform="translate({CX},{CY})"><path d="{wedge}" fill="url(#sweepGrad)"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="5s" repeatCount="indefinite"/></path></g></g>
    <polygon class="poly" points="{dpoly}" fill="url(#poly)" stroke="#f3e600" stroke-width="1.6" filter="url(#pglow)"/>
    <g class="poly">{verts}</g>
    <circle class="pulse" cx="{CX}" cy="{CY}" r="2.5" fill="#55ead4"/>
    {labels}

    <!-- legend -->
    <text class="rj" x="452" y="44" font-size="10.5" fill="#55ead4" letter-spacing="2">LANG_ALLOC ///</text>
    {leg}
    <text class="mono" x="452" y="{H-20}" font-size="10.5" fill="#6a6a6a" letter-spacing="1">{footer}</text>

    <g stroke="#000000" stroke-opacity="0.16" stroke-width="1">{scan}</g>
    <rect class="scanl" x="0" y="0" width="880" height="16" fill="#f3e600" opacity="0.04"/>
    <rect x="0.5" y="0.5" width="879" height="{H-1}" rx="4" fill="none" stroke="#f3e600" stroke-opacity="0.2"/>
  </g>
</svg>
'''


def main():
    langs, nrepo = collect()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(langs, nrepo))
    print("wrote", OUT, "-", len(langs), "languages,", nrepo, "repos")


if __name__ == "__main__":
    main()
