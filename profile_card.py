#!/usr/bin/env python3
"""
Regenerates dark_mode.svg and light_mode.svg for the GitHub profile README.

The ASCII portrait comes from ascii_dark.txt / ascii_light.txt (see make_ascii.py).

Runs locally with no token (falls back to placeholder stats) or in CI with
ACCESS_TOKEN set, in which case it pulls live numbers from the GitHub GraphQL API.

    python profile_card.py
"""

import datetime as dt
import os
import sys
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
import json

# ----------------------------------------------------------------- EDIT ME ---
USER = "mudassarbinqaiser"
NAME = "Mudassar Bin Qaiser"
TITLE = "Senior AI & ML Engineer"
BIRTHDAY = dt.date(2002, 12, 6)
HOST = "Lahore, Pakistan"
KERNEL = "Enterprise On-Prem and Cloud"
OS_LINE = "Windows 11, WSL2, Ubuntu"
IDE = "VS Code, Claude Code, Cursor"
EMAIL = "mudasserqaiser14@gmail.com"
LINKEDIN = "/in/mudassar-bin-qaiser-ai-ml-engineer"
# ------------------------------------------------------------------------------

COL = 62          # character columns in the right-hand panel
X = 400           # x offset of the panel (clears the 62-col ASCII block)
LH = 20           # line height in px
CH = 10.1         # measured advance of the widest common mono face at 16px
ASCII_FS = 10     # 62 cols x ~0.6em fits inside the 385px portrait column
ASCII_LH = 10
ASCII_TOP = 36
ASCII = {"dark_mode.svg": "ascii_dark.txt", "light_mode.svg": "ascii_light.txt"}
WIDTH = X + int(COL * CH) + 18

# Pick one: "slate" (teal on deep navy), "amber" (warm terminal), "github" (stock).
PALETTE = "slate"

PALETTES = {
    "slate": {
        "dark_mode.svg": dict(bg="#0b1220", fg="#cbd5e1", key="#5eead4", value="#e2e8f0",
                              add="#4ade80", dele="#fb7185", cc="#475569"),
        "light_mode.svg": dict(bg="#f8fafc", fg="#0f172a", key="#0f766e", value="#1e293b",
                               add="#15803d", dele="#be123c", cc="#94a3b8"),
    },
    "amber": {
        "dark_mode.svg": dict(bg="#12100c", fg="#e8dcc8", key="#f0b429", value="#fce8b2",
                              add="#84cc16", dele="#f87171", cc="#6b5f4b"),
        "light_mode.svg": dict(bg="#fffbf2", fg="#3b2f1c", key="#a16207", value="#422006",
                               add="#4d7c0f", dele="#b91c1c", cc="#a8a29e"),
    },
    "github": {
        "dark_mode.svg": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff",
                              add="#3fb950", dele="#f85149", cc="#616e7f"),
        "light_mode.svg": dict(bg="#ffffff", fg="#24292f", key="#953800", value="#0a3069",
                               add="#1a7f37", dele="#cf222e", cc="#57606a"),
    },
}
THEMES = PALETTES[PALETTE]

GRAPHQL = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, isFork: false) {
      totalCount
      nodes { stargazerCount }
    }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) {
      totalCount
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch_stats():
    """Live stats when ACCESS_TOKEN is present, otherwise sensible placeholders."""
    fallback = dict(repos="--", contrib="--", commits="--", stars="--",
                    followers="--", contributions="--")
    token = os.environ.get("ACCESS_TOKEN")
    if not token:
        print("! ACCESS_TOKEN not set - writing placeholder stats", file=sys.stderr)
        return fallback

    body = json.dumps({"query": GRAPHQL, "variables": {"login": USER}}).encode()
    req = urlrequest.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": USER})
    try:
        with urlrequest.urlopen(req, timeout=30) as r:
            payload = json.load(r)
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"! GitHub API call failed ({e}) - keeping placeholders", file=sys.stderr)
        return fallback

    if "errors" in payload:
        print(f"! GraphQL errors: {payload['errors']}", file=sys.stderr)
        return fallback

    u = payload["data"]["user"]
    cc = u["contributionsCollection"]
    repos = u["repositories"]
    return dict(
        repos=f"{repos['totalCount']:,}",
        contrib=f"{u['repositoriesContributedTo']['totalCount']:,}",
        commits=f"{cc['totalCommitContributions'] + cc['restrictedContributionsCount']:,}",
        stars=f"{sum(n['stargazerCount'] for n in repos['nodes']):,}",
        followers=f"{u['followers']['totalCount']:,}",
        contributions=f"{cc['contributionCalendar']['totalContributions']:,}",
    )


def uptime():
    today = dt.date.today()
    y = today.year - BIRTHDAY.year
    m = today.month - BIRTHDAY.month
    d = today.day - BIRTHDAY.day
    if d < 0:
        m -= 1
        prev = today.replace(day=1) - dt.timedelta(days=1)
        d += prev.day
    if m < 0:
        y -= 1
        m += 12
    plural = lambda n: "s" if n != 1 else ""
    return f"{y} year{plural(y)}, {m} month{plural(m)}, {d} day{plural(d)}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def kv(label, value, trailing=""):
    """'. label: ....... value trailing' padded with a dot leader to COL."""
    plain_trail = trailing_plain(trailing)
    used = 2 + len(label) + 1 + 1 + len(value) + 1 + len(plain_trail)
    dots = max(3, COL - used)
    lead = " " + "." * dots + " "
    return (f'. <tspan class="key">{esc(label)}</tspan>:'
            f'<tspan class="cc">{lead}</tspan>'
            f'<tspan class="value">{esc(value)}</tspan>{trailing}')


def trailing_plain(markup):
    """Strip tags so the dot leader maths counts visible characters only."""
    out, depth = [], 0
    for ch in markup:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def rule(title):
    return f'▸ {esc(title)} <tspan class="cc">{"─" * max(3, COL - len(title) - 3)}</tspan>'


def build_lines(s):
    contributed = (f'<tspan class="cc"> {{</tspan>'
                   f'<tspan class="key">Contributed to</tspan>'
                   f'<tspan class="cc">: </tspan>'
                   f'<tspan class="value">{esc(s["contrib"])}</tspan>'
                   f'<tspan class="cc">}}</tspan>')
    last_year = f'<tspan class="cc"> (last year)</tspan>'
    return [
        f'{USER} <tspan class="cc">{"─" * max(3, COL - len(USER) - 1)}</tspan>',
        kv("OS", OS_LINE),
        kv("Uptime", uptime()),
        kv("Host", HOST),
        kv("Kernel", KERNEL),
        kv("IDE", IDE),
        "",
        kv("Languages.Programming", "Python, TypeScript, JavaScript"),
        kv("Languages.Computer", "YAML, JSON, SQL, HTML, CSS"),
        kv("Languages.Real", "Urdu, English, Punjabi"),
        "",
        kv("Stack.Agents", "LangGraph, LangChain, DeepAgents, MCP"),
        kv("Stack.Serving", "FastAPI, Docker, Kubernetes"),
        kv("Stack.Voice", "LiveKit, multilingual pipelines"),
        "",
        rule("Contact"),
        kv("Email", EMAIL),
        kv("LinkedIn", LINKEDIN),
        "",
        rule("GitHub Stats"),
        kv("Repos", s["repos"], trailing=contributed),
        kv("Commits", s["commits"]),
        kv("Stars earned", s["stars"]),
        kv("Followers", s["followers"]),
        kv("Contributions", s["contributions"], trailing=last_year),
    ]


def main():
    art = {f: open(a, encoding="utf-8").read().rstrip("\n").split("\n")
           for f, a in ASCII.items()}
    lines = build_lines(fetch_stats())
    art_rows = max(len(v) for v in art.values())
    art_bottom = ASCII_TOP + art_rows * ASCII_LH
    name_y = art_bottom + 26
    title_y = name_y + 22
    text_h = (len(lines) - 1) * LH
    height = max(title_y + 22, text_h + 60)
    text_y0 = (height - text_h) // 2 + 5     # centre the panel vertically
    cx = X // 2                                 # centre of the portrait column

    for fname, t in THEMES.items():
        out = [
            "<?xml version='1.0' encoding='UTF-8'?>",
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'font-family="Consolas,&apos;DejaVu Sans Mono&apos;,&apos;Liberation Mono&apos;,'
            f'&apos;Courier New&apos;,monospace" '
            f'width="{WIDTH}px" height="{height}px" font-size="16px">',
            "<style>",
            f".key {{fill: {t['key']};}}",
            f".value {{fill: {t['value']};}}",
            f".addColor {{fill: {t['add']};}}",
            f".delColor {{fill: {t['dele']};}}",
            f".cc {{fill: {t['cc']};}}",
            "text, tspan {white-space: pre;}",
            "</style>",
            "",
            f'<rect width="{WIDTH}px" height="{height}px" fill="{t["bg"]}" rx="15"/>',
            "",
            f'<text x="15" y="{ASCII_TOP}" fill="{t["fg"]}" font-size="{ASCII_FS}px">',
        ]
        for i, row in enumerate(art[fname]):
            out.append(f'<tspan x="15" y="{ASCII_TOP + i * ASCII_LH}">{esc(row)}</tspan>')
        out += [
            "</text>",
            "",
            f'<text x="{cx}" y="{name_y}" text-anchor="middle" fill="{t["fg"]}" '
            f'font-size="17px" font-weight="600">{esc(NAME)}</text>',
            f'<text x="{cx}" y="{title_y}" text-anchor="middle" fill="{t["key"]}" '
            f'font-size="12px" letter-spacing="1.5">{esc(TITLE.upper())}</text>',
            "",
            f'<text x="{X}" y="{text_y0}" fill="{t["fg"]}">',
        ]
        for i, line in enumerate(lines):
            out.append(f'<tspan x="{X}" y="{text_y0 + i * LH}">{line}</tspan>')
        out += ["</text>", "</svg>"]
        open(fname, "w", encoding="utf-8", newline="\n").write("\n".join(out))
        print(f"wrote {fname} ({WIDTH}x{height})")


if __name__ == "__main__":
    main()
