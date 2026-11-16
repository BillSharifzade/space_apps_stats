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
        s = scores.get(t["id"])
        if s:
            row["score"] = {c: int(s[c]) for c in CRIT} | {"total": s["total"], "raw": s["raw"], "one": s["one_line"], "plus": s["strengths"], "minus": s["weaknesses"],
                                                          "kind": s.get("kind", ""), "built": s.get("built", "")}
    teams.append(row)

data = {"fetched": "2026-11-16", "deadline": "2026-11-15T18:59:00Z", "event": "Dushanbe", "teams": teams,
        "participants": sum(r["members"] for r in teams), "mentions": {k: v.most_common() for k, v in mentions.items()}, "judged": len(scores), "batchMeans": BATCH}
(HERE / "site").mkdir(exist_ok=True)
(HERE / "site/data.js").write_text("window.DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(len(teams), "teams,", len(scores), "judged ->", HERE / "site/data.js", (HERE / "site/data.js").stat().st_size // 1024, "KB")
for k, v in mentions.items():
    print(k, v.most_common(8))
print(collections.Counter(r["homeKind"] for r in teams if r["submitted"]).most_common(), collections.Counter(r["demoKind"] for r in teams if r["submitted"]).most_common())
