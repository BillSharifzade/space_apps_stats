"""Builds site/data.js for the dashboard from teams.json, work/links.json and work/scores*.json.

    python3 build_site.py

Member names stay out of the page on purpose: only the number of members is published.
"""
import collections, glob, html, json, re, statistics
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).parent
T = json.loads((HERE / "teams.json").read_text())
LINKS = json.loads((HERE / "work/links.json").read_text())
CODES = json.loads((HERE / "work/codes.json").read_text())
CRIT = ["impact", "creativity", "validity", "relevance", "presentation"]


def text(v) -> str:
    if not v:
        return ""
    if isinstance(v, list):
        return "; ".join(map(str, v))
    s = re.sub(r"<li[^>]*>", "\n- ", str(v))
    s = re.sub(r"<(br|/p|/h\d|/div|/li)[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n\s*\n+", "\n\n", html.unescape(s)).strip()


def host(url) -> str:
    return urlparse(url or "").netloc.replace("www.", "").lower()


def demo_kind(url) -> str:
    h, u = host(url), (url or "").lower()
    if not h: return "No link"
    if h in ("youtu.be", "youtube.com"): return "Video on YouTube"
    if h == "docs.google.com": return "Google Slides or Docs"
    if h == "drive.google.com": return "File on Google Drive"
    if "canva" in h: return "Canva"
    if "gamma.app" in h: return "Gamma"
    if h == "github.com": return "GitHub repository"
    return "A web page of their own"


def home_kind(url) -> str:
    h = host(url)
    if not h: return "No link"
    if h == "github.com": return "GitHub repository"
    if h.endswith("github.io"): return "GitHub Pages"
    if h.endswith("vercel.app"): return "Vercel"
    if h.endswith("netlify.app"): return "Netlify"
    if h == "drive.google.com" or h == "docs.google.com": return "Google Drive"
    if h.endswith("onrender.com"): return "Render"
    if h.endswith("streamlit.app"): return "Streamlit"
    if "canva" in h: return "Canva"
    if h in ("youtu.be", "youtube.com"): return "YouTube"
    if any(h.endswith(x) for x in ("lovable.app", "bolt.host", "replit.app", "chatgpt.site", "claude.ai", "base44.app", "v0.app", "manus.space")): return "AI app builder"
    if any(h.endswith(x) for x in ("pages.dev", "web.app", "firebaseapp.com", "railway.app", "fly.dev", "huggingface.co", "hf.space", "itch.io", "pythonanywhere.com")): return "Other free hosting"
    return "Own domain"


WORDS = {
    "ai": {"ChatGPT / OpenAI": r"chat ?gpt|openai|gpt-?[345o]", "Claude": r"\bclaude\b|anthropic", "Gemini": r"\bgemini\b|google ai studio", "Copilot": r"copilot",
           "Cursor": r"\bcursor\b", "DeepSeek": r"deepseek", "Grok": r"\bgrok\b", "Lovable / Bolt / v0": r"lovable|bolt\.new|\bv0\b", "Midjourney / DALL·E": r"midjourney|dall.?e",
           "Canva AI": r"canva ai|magic (studio|design)", "Perplexity": r"perplexity", "ElevenLabs": r"elevenlabs", "Gamma": r"\bgamma\b"},
    "tech": {"Python": r"\bpython\b", "JavaScript / TypeScript": r"javascript|typescript", "React": r"\breact\b", "Next.js": r"next\.?js", "HTML / CSS": r"\bhtml\b",
             "Three.js / WebGL": r"three\.?js|webgl", "Unity": r"\bunity\b", "Godot": r"godot", "Streamlit": r"streamlit", "Flask / FastAPI / Django": r"flask|fastapi|django",
             "Node.js": r"node\.?js", "Leaflet / Mapbox / Cesium": r"leaflet|mapbox|cesium", "TensorFlow / PyTorch / scikit": r"tensorflow|pytorch|scikit|sklearn",
             "pandas / NumPy": r"pandas|numpy", "Google Earth Engine": r"earth engine", "Arduino / ESP32 / Raspberry": r"arduino|esp32|raspberry", "Tailwind": r"tailwind",
             "Rust": r"\brust\b", "Flutter / React Native": r"flutter|react native", "Telegram bot": r"telegram"},
    "data": {"MODIS": r"\bmodis\b", "VIIRS": r"\bviirs\b", "FIRMS": r"\bfirms\b", "Landsat": r"landsat", "Sentinel": r"sentinel", "NASA POWER": r"nasa power|power\.larc",
             "SMAP": r"\bsmap\b", "GPM / IMERG": r"\bgpm\b|imerg", "GRACE": r"\bgrace\b", "Earthdata": r"earthdata", "Worldview / GIBS": r"worldview|\bgibs\b",
             "LRO / LOLA": r"\blro\b|\blola\b|lunar reconnaissance", "Mars rovers and orbiters": r"perseverance|curiosity|\bmro\b|hirise|mars trek|\bmola\b", "SAR (radar)": r"\bsar\b|synthetic aperture|\balos\b|nisar",
             "ISS / astronaut health data": r"\bgenelab\b|osdr|human research program|\blsda\b", "SPHEREx / IRSA": r"spherex|\birsa\b", "JPL Horizons": r"horizons", "Open-Meteo / other weather": r"open-?meteo|openweather",
             "Kaggle": r"kaggle", "OpenStreetMap": r"openstreetmap|\bosm\b"},
}

# The judges' scores, keyed by team id. Each batch was a random mix of challenges. Scores are
# used as given: the batch means differ by up to 4 points of 50, which the page states.
scores, by_batch = {}, collections.defaultdict(list)
for f in sorted(glob.glob(str(HERE / "work/scores*.json"))):
    for s in json.loads(Path(f).read_text()):
        if s["code"] in CODES:
            s["raw"] = s["total"] = sum(int(s[c]) for c in CRIT)
            scores[CODES[s["code"]]] = s
            by_batch[s["code"][:2]].append(s["raw"])
first = {k: v["raw"] for k, v in scores.items()}
final, by_batch = {}, collections.defaultdict(list)
for f in sorted(glob.glob(str(HERE / "work/final*.json"))):
    for s in json.loads(Path(f).read_text()):
        if s["code"] in CODES:
            s["raw"] = s["total"] = sum(int(s[c]) for c in CRIT)
            final[CODES[s["code"]]] = s
            by_batch[s["code"][:2]].append(s["raw"])
if final:
    scores = final
PROBE = json.loads((HERE / "work/probe2.json").read_text()) if (HERE / "work/probe2.json").exists() else {}
REPOS = json.loads((HERE / "work/repos.json").read_text()) if (HERE / "work/repos.json").exists() else {}
BATCH = {b: round(statistics.mean(v), 1) for b, v in sorted(by_batch.items())}
print("batch means", BATCH)

teams = []
mentions = {k: collections.Counter() for k in WORDS}
for t in T:
    p = t["projectDetails"] or {}
    sub = bool(t["projectSubmitted"])
    blob = " ".join(text(p.get(k)) for k in ("summary", "details", "dataReferences", "projectReferences")).lower()
    row = {
        "id": t["id"], "team": t["title"], "url": "https://www.spaceappschallenge.org" + t["meta"]["relativeUrl"],
        "challenge": (t["challengeDetails"] or {}).get("title") or "No challenge chosen", "members": len(t["memberships"]),
        "created": t["meta"]["firstPublishedAt"], "submitted": sub, "languages": t.get("languages") or [], "skills": t.get("desiredSkills") or [],
    }
    if sub:
        l = LINKS.get(t["id"], {})
        row.update({
            "project": p.get("name") or "", "demo": p.get("demoLink") or "", "link": p.get("projectLink") or "", "at": p.get("submittedAt"),
            "demoKind": demo_kind(p.get("demoLink")), "homeKind": home_kind(p.get("projectLink")),
            "demoState": l.get("demoLink", {}).get("state", "missing"), "linkState": l.get("projectLink", {}).get("state", "missing"),
            "ai": p.get("aiToolsUsage") or [], "chars": len(blob), "summary": text(p.get("summary"))[:700],
            "refs": len(re.findall(r"https?://", text(p.get("dataReferences")) + text(p.get("projectReferences")))),
        })
        for group, words in WORDS.items():
            found = [name for name, rx in words.items() if re.search(rx, blob)]
            row[group + "Words"] = found
            mentions[group].update(found)
        pr, rp = PROBE.get(t["id"]) or {}, REPOS.get(t["id"])
        if pr.get("kind") == "site":
            cert = lambda e: "CERT_AUTHORITY" in e or "openfreemap" in e   # faults of the test network, not of the site
            row["probe"] = {"loaded": bool(pr.get("shot")), "loadS": round(pr.get("loadMs", 0) / 1000, 1), "clicks": pr.get("clicks", 0), "changed": pr.get("clicksChanged", 0),
                            "errors": len([e for e in pr.get("errors", []) if not cert(e)]), "http": len(pr.get("httpErrors", [])), "overflow": pr.get("phoneOverflow") or 0,
                            "small": pr.get("phoneSmallText") or 0, "api": pr.get("apiCalls", 0), "requests": pr.get("requests", 0), "canvas": pr.get("canvas", 0)}
        if rp:
            row["repo"] = {"url": rp["url"], "commits": rp["commits"], "files": rp["files"], "tests": rp["tests"], "license": rp["license"], "authors": rp.get("authors"),
                           "lang": max(rp["languages"], key=rp["languages"].get) if rp["languages"] else "", "readme": rp.get("readmeChars", 0)}
        row["requests"] = pr.get("requests", 0) if pr.get("shot") else None
    teams.append(row)


# ---- extra statistics
from datetime import datetime, timedelta, timezone
TZ = timezone(timedelta(hours=5))
SUB = [r for r in teams if r["submitted"]]
shot = [v for v in PROBE.values() if v.get("shot")]
GENERIC = {"sans-serif", "serif", "monospace", "system-ui", "-apple-system", "ui-monospace", "ui-sans-serif", "ui-serif", "BlinkMacSystemFont", "inherit", ""}
fonts = collections.Counter(f for v in shot for f in set(v.get("fonts") or []) if f not in GENERIC).most_common(12)
GROUPS = {"Google Fonts": r"fonts\.g(oogleapis|static)\.com", "A script CDN (jsDelivr, unpkg, cdnjs)": r"jsdelivr|unpkg\.com|cdnjs|cdn\.tailwindcss|cdn\.plot\.ly|ajax\.googleapis",
          "A NASA server, live": r"nasa\.gov$", "Esri / ArcGIS map tiles": r"arcgisonline", "OpenStreetMap tiles": r"openstreetmap|openfreemap|carto|maptiler|eox\.at", "Open-Meteo weather": r"open-meteo",
          "Visitor analytics": r"googletagmanager|google-analytics|cloudflareinsights|heap|plausible|yandex", "A hosted database (Supabase, Firebase)": r"supabase|firebase|firestore", "Amazon S3 data": r"amazonaws"}
services = sorted(((g, sum(1 for v in shot if any(re.search(rx, h) for h in v.get("hosts", {})))) for g, rx in GROUPS.items()), key=lambda x: -x[1])
nasa = collections.Counter(h for v in shot for h in v.get("hosts", {}) if h.endswith("nasa.gov")).most_common(10)
CT = json.loads((HERE / "work/commit_times.json").read_text()) if (HERE / "work/commit_times.json").exists() else {}
start = datetime(2026, 11, 14, 0, 0, tzinfo=TZ); hours = [0] * 48; before = after = 0; night = 0
for dates in CT.values():
    for d in dates:
        k = int((datetime.fromisoformat(d.replace("Z", "+00:00")) - start).total_seconds() // 3600)
        if k < 0: before += 1
        elif k >= 48: after += 1
        else:
            hours[k] += 1
            if k % 24 < 6: night += 1
langs = collections.Counter()
for r in REPOS.values():
    if r:
        for k, v in r["languages"].items(): langs[k] += v
tot = sum(langs.values()) or 1
STOP = set("the a an of for and to in on with from by at is your our my nasa space apps challenge project app 2026 de la".split())
words = collections.Counter(w for r in SUB for w in set(re.findall(r"[a-zа-яё]{3,}", r["project"].lower())) if w not in STOP).most_common(14)
names = [r["team"] for r in teams]
emoji = sum(1 for n in names if re.search(r"[^\x00-\u024f\u0400-\u04ff]", n))
countries = collections.Counter(m["userDetails"]["country"] for t in T for m in t["memberships"] if m.get("userDetails") and m["userDetails"].get("country")).most_common()
dl = datetime.fromisoformat("2026-11-15T18:59:59+00:00"); stamp = lambda r: datetime.fromisoformat(r["at"].replace("Z", "+00:00"))
intime = [r for r in SUB if stamp(r) <= dl]
first, last = min(SUB, key=stamp), max(intime, key=stamp)
rep = lambda r: (REPOS.get(r["id"]) or {})
pb = lambda r: (PROBE.get(r["id"]) or {})
fast = min((r for r in SUB if pb(r).get("shot") and "koinotinav" not in r["link"]), key=lambda r: pb(r)["loadMs"])  # the test ran next to that one server, so it is left out
mostc = max(SUB, key=lambda r: rep(r).get("commits", 0)); mostf = max(SUB, key=lambda r: rep(r).get("files", 0)); mostt = max(SUB, key=lambda r: rep(r).get("tests", 0))
longest = max(SUB, key=lambda r: r["chars"]); mostrefs = max(SUB, key=lambda r: r["refs"]); mostbtn = max((r for r in SUB if pb(r).get("shot")), key=lambda r: pb(r).get("buttons", 0))
mosttech = max(SUB, key=lambda r: len(r["techWords"])); mostdata = max(SUB, key=lambda r: len(r["dataWords"]))
secs = int((dl - stamp(last)).total_seconds())
records = [
    ["First to submit", stamp(first).astimezone(TZ).strftime("%a %H:%M"), first["team"], "the first project handed in, local time"],
    ["Closest to the deadline", f"{secs} s", last["team"], "to spare before 23:59:59 on Sunday"],
    ["Most commits", str(rep(mostc).get("commits", 0)) + ("+" if rep(mostc).get("commitsCapped") else ""), mostc["team"], "in a public repository"],
    ["Most test files", str(rep(mostt).get("tests", 0)), mostt["team"], "in a public repository"],
    ["Largest repository", f"{rep(mostf).get('files', 0):,} files", mostf["team"], "counted in the default branch"],
    ["Fastest site", f"{pb(fast)['loadMs'] / 1000:.1f} s", fast["team"], "until the page was ready in the test"],
    ["Most to press", f"{pb(mostbtn).get('buttons', 0)} buttons", mostbtn["team"], "on the first screen of the site"],
    ["Longest write-up", f"{longest['chars']:,} chars", longest["team"], "of project text and references"],
    ["Most sources cited", f"{mostrefs['refs']} links", mostrefs["team"], "in data and project references"],
    ["Most data sets named", str(len(mostdata["dataWords"])), mostdata["team"], "different NASA and open data sources in one text"],
]
extra = {"fonts": fonts, "services": services, "nasaHosts": nasa, "commitHours": hours, "commitsBefore": before, "commitsAfter": after, "commitsNight": night, "commitsTotal": sum(len(v) for v in CT.values()),
         "langs": [(k, round(100 * v / tot, 1)) for k, v in langs.most_common(8)], "words": words, "records": records, "countries": countries, "sitesShot": len(shot),
         "names": {"avg": round(statistics.mean(len(n) for n in names), 1), "emoji": emoji, "digits": sum(1 for n in names if re.search(r"\d", n)), "caps": sum(1 for n in names if n.isupper() and len(n) > 2), "oneWord": sum(1 for n in names if " " not in n.strip())}}
data = {"fetched": "2026-11-16", "deadline": "2026-11-15T18:59:00Z", "event": "Dushanbe", "teams": teams,
        "participants": sum(r["members"] for r in teams), "mentions": {k: v.most_common() for k, v in mentions.items()}, "extra": extra}
(HERE / "site").mkdir(exist_ok=True)
(HERE / "site/data.js").write_text("window.DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(len(teams), "teams,", len(scores), "judged ->", HERE / "site/data.js", (HERE / "site/data.js").stat().st_size // 1024, "KB")
for k, v in mentions.items():
    print(k, v.most_common(8))
print(collections.Counter(r["homeKind"] for r in teams if r["submitted"]).most_common(), collections.Counter(r["demoKind"] for r in teams if r["submitted"]).most_common())
