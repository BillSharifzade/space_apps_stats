"""Fetches every team of one Space Apps local event from the site's public GraphQL API.

    python3 fetch_teams.py [event-path] [out-folder]
    python3 fetch_teams.py /2026/local-events/dushanbe/ .

Writes teams.json (raw), teams.md (readable, sorted) and teams.csv. No browser is needed: the
teams tab of the website calls this same API. The site's servers send an incomplete certificate
chain, so the missing intermediate is downloaded and checked against the system's roots.
"""
import csv, html, json, re, ssl, subprocess, sys, time, urllib.request
from pathlib import Path

API = "https://api.spaceappschallenge.org/graphql"
SITE = "https://www.spaceappschallenge.org"
PATH = sys.argv[1] if len(sys.argv) > 1 else "/2026/local-events/dushanbe/"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
HEAD = {"content-type": "application/json", "user-agent": "Mozilla/5.0 (teams-list script)", "origin": SITE, "referer": SITE + "/"}

TEAMS = """
query Teams($first: Int!, $after: String, $filtering: [Filter!]) {
  teams(first: $first, after: $after, filtering: $filtering) {
    totalCount
    pageInfo { hasNextPage endCursor }
    edges { node {
      id title excerpt description desiredSkills languages projectSubmitted
      meta { slug relativeUrl firstPublishedAt lastPublishedAt }
      ownerDetails { username }
      challengeDetails { title meta { relativeUrl } }
      locationDetails { title country }
      memberships { userDetails { fullName username country } }
      nominationBadges awardBadges
      projectDetails { name summary demoLink projectLink details solution aiReferences aiToolsUsage
                       dataReferences projectReferences isSubmitted savedAt submittedAt }
    } }
  }
}"""


def context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    pem = OUT / ".spaceapps-intermediate.pem"
    if not pem.exists():
        der = urllib.request.urlopen("http://cert.ssl.com/SSL.com-TLS-I-RSA-R1.cer", timeout=30).read()
        pem.write_text(ssl.DER_cert_to_PEM_cert(der))
        # Trust it only if the system's own roots vouch for it.
        subprocess.run(["openssl", "verify", str(pem)], check=True, capture_output=True)
    ctx.load_verify_locations(str(pem))
    return ctx


CTX = None


def gql(query: str, variables: dict) -> dict:
    global CTX
    CTX = CTX or context()
    body = json.dumps({"query": query, "variables": variables}).encode()
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, body, HEAD), timeout=60, context=CTX) as r:
                answer = json.load(r)
            if answer.get("errors") and not answer.get("data"):
                raise RuntimeError(answer["errors"][0]["message"])
            return answer["data"]
        except Exception as e:  # network trouble or a busy server: wait and try again
            if attempt == 4:
                raise
            print("retry:", e, file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def text(value) -> str:
    """Rich text from the site (HTML) as plain text with links kept."""
    if not value:
        return ""
    s = str(value)
    s = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: m.group(2) if m.group(1) in m.group(2) else f"{m.group(2)} ({m.group(1)})", s, flags=re.S)
    s = re.sub(r"<li[^>]*>", "\n- ", s)
    s = re.sub(r"<(br|/p|/h\d|/div|/li)[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n\s*\n+", "\n\n", html.unescape(s)).strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page = gql("query($p: String!) { pageByPath(path: $p) { id title } }", {"p": PATH})["pageByPath"]
    teams, after = [], None
    while True:
        d = gql(TEAMS, {"first": 50, "after": after, "filtering": [{"field": "location", "value": page["id"], "compare": "id"}]})["teams"]
        teams += [e["node"] for e in d["edges"]]
        print(f"{len(teams)} of {d['totalCount']}", file=sys.stderr)
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
        time.sleep(0.5)
    assert len({t["id"] for t in teams}) == len(teams) == d["totalCount"], "the list is not complete"
    # The list leaves out the description and the members; each team's own page has them.
    DETAIL = """query($p: String!) { pageByPath(path: $p) { ... on TeamPage { description desiredSkills languages
      ownerDetails { username } memberships { userDetails { fullName username country } } nominationBadges awardBadges } } }"""
    for n, t in enumerate(teams, 1):
        try:
            more = gql(DETAIL, {"p": t["meta"]["relativeUrl"]})["pageByPath"] or {}
            t.update({k: v for k, v in more.items() if v is not None})
        except Exception as e:
            print("no detail for", t["title"], e, file=sys.stderr)
        t["memberships"] = t.get("memberships") or []
        if n % 25 == 0:
            print(f"details {n} of {len(teams)}", file=sys.stderr)
        time.sleep(0.25)
    teams.sort(key=lambda t: (not t["projectSubmitted"], ((t["challengeDetails"] or {}).get("title") or "~").lower(), t["title"].lower()))
    (OUT / "teams.json").write_text(json.dumps(teams, ensure_ascii=False, indent=1))

    rows, md = [], [f"# Space Apps 2026, {page['title']}: all teams", ""]
    done = sum(1 for t in teams if t["projectSubmitted"])
    md += [f"{len(teams)} teams, {done} with a submitted project. Source: {SITE}{PATH}?tab=teams", "",
           "Sorted: submitted projects first, then by challenge, then by team name.", "",
           "| # | Team | Challenge | Members | Submitted | Demo | Project |", "|---|---|---|---|---|---|---|"]
    for i, t in enumerate(teams, 1):
        p = t["projectDetails"] or {}
        ch = (t["challengeDetails"] or {}).get("title") or ""
        link = lambda u: f"[link]({u})" if u else ""
        md.append(f"| {i} | [{t['title']}](#team-{i}) | {ch} | {len(t['memberships'])} | {'yes' if t['projectSubmitted'] else 'no'} | {link(p.get('demoLink'))} | {link(p.get('projectLink'))} |")
    md.append("")
    for i, t in enumerate(teams, 1):
        p = t["projectDetails"] or {}
        ch = (t["challengeDetails"] or {}).get("title") or ""
        url = SITE + t["meta"]["relativeUrl"]
        members = ", ".join(f"{m['userDetails']['fullName'] or m['userDetails']['username']} (@{m['userDetails']['username']})" for m in t["memberships"] if m.get("userDetails"))
        md += [f'<a id="team-{i}"></a>', f"## {i}. {t['title']}", "",
               f"- **Team page:** {url}", f"- **Challenge:** {ch or 'not chosen'}",
               f"- **Members ({len(t['memberships'])}):** {members}",
               f"- **Project submitted:** {'yes' if t['projectSubmitted'] else 'no'}" + (f" ({p.get('submittedAt')})" if p.get("submittedAt") else "")]
        if p.get("name"): md.append(f"- **Project name:** {p['name']}")
        if p.get("demoLink"): md.append(f"- **Demo:** {p['demoLink']}")
        if p.get("projectLink"): md.append(f"- **Project link:** {p['projectLink']}")
        if t.get("awardBadges") or t.get("nominationBadges"): md.append(f"- **Badges:** {t.get('nominationBadges') or ''} {t.get('awardBadges') or ''}")
        if t.get("languages"): md.append(f"- **Languages:** {', '.join(map(str, t['languages']))}")
        if t.get("desiredSkills"): md.append(f"- **Skills wanted:** {', '.join(map(str, t['desiredSkills']))}")
        md.append("")
        for title, val in [("Team description", t["description"] or t["excerpt"]), ("Summary", p.get("summary")), ("Project details", p.get("details")),
                           ("Solution", p.get("solution")), ("Use of AI", p.get("aiToolsUsage")), ("AI references", p.get("aiReferences")),
                           ("Data references", p.get("dataReferences")), ("Project references", p.get("projectReferences"))]:
            if text(val):
                md += [f"### {title}", "", text(val), ""]
        md += ["---", ""]
        rows.append({"team": t["title"], "team_page": url, "challenge": ch, "members": len(t["memberships"]), "member_names": members,
                     "submitted": t["projectSubmitted"], "submitted_at": p.get("submittedAt") or "", "project": p.get("name") or "",
                     "demo": p.get("demoLink") or "", "project_link": p.get("projectLink") or "", "summary": text(p.get("summary")),
                     "team_description": text(t["description"] or t["excerpt"])})
    (OUT / "teams.md").write_text("\n".join(md))
    with open(OUT / "teams.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"{len(teams)} teams, {done} submitted -> {OUT}/teams.md, teams.csv, teams.json")


main()
