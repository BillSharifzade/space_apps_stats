"""Builds one picture and one evidence text per project for the second judging round.
Run with a Python that has Pillow:  python evidence.py"""
import html, json, re
from pathlib import Path
from PIL import Image, ImageDraw
H = Path(__file__).parent
T = {t["id"]: t for t in json.load(open(H / "teams.json"))}
P = json.load(open(H / "work/probe2.json")); R = json.load(open(H / "work/repos.json")); L = json.load(open(H / "work/links.json"))
CODES = json.load(open(H / "work/codes.json")); CH = json.load(open(H / "work/challenges.json"))

def text(v):
    if not v: return ""
    if isinstance(v, list): return "; ".join(map(str, v))
    s = re.sub(r"<li[^>]*>", "\n- ", str(v)); s = re.sub(r"<(br|/p|/h\d|/div|/li)[^>]*>", "\n", s); s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n\s*\n+", "\n\n", html.unescape(s)).strip()

def montage(code):
    parts = [H / f"work/shots/{code}-{k}.jpg" for k in "abc"]
    if not all(p.exists() for p in parts): return None
    a, b, c = (Image.open(p).convert("RGB") for p in parts)
    a = a.resize((640, 400)); b = b.resize((640, 400)); c = c.resize((185, 400))
    out = Image.new("RGB", (640 + 640 + 185 + 20, 424), "white"); d = ImageDraw.Draw(out)
    for x, im, name in ((0, a, "1. desktop, on load"), (650, b, "2. desktop, after the automatic clicks"), (1300, c, "3. phone")):
        out.paste(im, (x, 24)); d.text((x + 4, 6), name, fill="black")
    f = H / f"work/shots/{code}.jpg"; out.save(f, quality=70); return f

for b in range(1, 6):
    lines = []
    used = sorted({T[CODES[c]]["challengeDetails"]["title"] for c in CODES if c.startswith(f"B{b}-")})
    lines.append("# CHALLENGES IN THIS BATCH\n")
    for c in used: lines.append(f"## {c}\n{text(CH.get(c, {}).get('excerpt'))}\n")
    lines.append("\n# PROJECTS\n")
    for code in sorted(c for c in CODES if c.startswith(f"B{b}-")):
        t = T[CODES[code]]; p = t["projectDetails"]; pr = P.get(t["id"], {}); rp = R.get(t["id"]); l = L[t["id"]]
        img = montage(code) if pr.get("shot") else None
        lines.append(f"\n=================== PROJECT {code} ===================\nTeam: {t['title']}   (members: {len(t['memberships'])})\nChallenge: {t['challengeDetails']['title']}\nProject name: {p['name']}\nProject link: {p['projectLink']}\nDemo link: {p['demoLink']}  (automatic check: {l['demoLink']['state']})\nAI use declared: {text(p['aiToolsUsage'])}\n")
        lines.append("--- EVIDENCE A: THE SITE, OPENED AND CLICKED BY A SCRIPT ---")
        if pr.get("kind") != "site":
            lines.append(f"No site to test: the project link is {pr.get('kind')} ({pr.get('host', '')}). Link check: {l['projectLink']['state']}.")
        elif pr.get("error") and not pr.get("shot"):
            lines.append(f"THE SITE DID NOT LOAD: {pr['error']} (HTTP status {pr.get('status')}).")
        else:
            nasa = sorted(h for h in pr.get("hosts", {}) if re.search(r"nasa\.gov|earthdata|usgs\.gov|ipac\.caltech|jpl\.|esa\.int|copernicus|open-meteo|amazonaws|noaa\.gov", h))
            other = sorted(pr.get("hosts", {}), key=lambda h: -pr["hosts"][h])[:8]
            lines.append(f"Picture (desktop on load, desktop after clicks, phone): {img}\nHTTP status {pr.get('status')}, ready after {pr.get('loadMs', 0) / 1000:.0f} s, {pr.get('requests')} requests, {pr.get('apiCalls')} data requests (fetch/XHR).\n"
                f"Hosts contacted most: {', '.join(other)}\nScience or open-data hosts contacted live by the page: {', '.join(nasa) or 'none (data may still be bundled or prepared beforehand)'}\n"
                f"On the page: {pr.get('textChars')} characters of text, {pr.get('buttons')} buttons, {pr.get('inputs')} inputs, {pr.get('internal')} internal links, {pr.get('canvas')} canvas, {pr.get('svg')} svg, {pr.get('images')} images ({pr.get('brokenImages')} broken), page height {pr.get('height')} px.\n"
                f"Typefaces: {', '.join(pr.get('fonts') or [])}; {pr.get('fontSizes')} different text sizes.\n"
                f"Click test: {pr.get('clicks')} controls clicked, {pr.get('clicksChanged')} changed the page. No visible change after: {pr.get('dead') or 'none'} (a 3D or game canvas may change without the test seeing it).\n"
                f"Console errors ({len(pr.get('errors', []))}, of which {pr.get('errorsOnClick')} after clicks): {pr.get('errors') or 'none'}\nFailed requests: network {pr.get('netFailed')}; HTTP errors {pr.get('httpErrors') or 'none'}\n"
                f"Phone (390 px): sideways overflow {pr.get('phoneOverflow')} px, {pr.get('phoneSmallText')} text elements under 11 px, viewport tag {'present' if pr.get('viewportMeta') else 'MISSING'}.\n"
                f"Placeholder words found: {pr.get('placeholder') or 'none'}\nText on load: {pr.get('text', '')[:900]}\nText after clicks: {pr.get('after', '')[:350]}" + (f"\nNote from the test: {pr['error']}" if pr.get("error") else ""))
        lines.append("\n--- EVIDENCE B: PUBLIC CODE REPOSITORY ---")
        if not rp: lines.append("No public repository was found in the submission.")
        else:
            langs = rp["languages"]; tot = sum(langs.values()) or 1
            lines.append(f"{rp['url']} (created {rp['created'][:10]}, licence {rp['license']}, fork: {rp['fork']})\n{rp['commits']}{'+' if rp.get('commitsCapped') else ''} commits by {rp.get('authors')} author(s); first {str(rp.get('firstCommit'))[:16]}, last {str(rp.get('lastCommit'))[:16]} (UTC). "
                f"Before the weekend: {rp.get('before')}, during: {rp.get('during')}, after the deadline: {rp.get('after')}.\n{rp['files']} files, {rp['tests']} test files, {rp['dataFiles']} data files. Languages: {', '.join(f'{k} {100 * v // tot}%' for k, v in sorted(langs.items(), key=lambda x: -x[1])[:5])}. Top level: {', '.join(rp['top'][:20])}\n"
                f"README ({rp.get('readmeChars', 0)} characters), start:\n{(rp.get('readme') or '')[:1200]}")
        lines.append(f"\n--- WHAT THE TEAM WROTE: SUMMARY ---\n{text(p['summary'])[:1800]}\n\n--- WHAT THE TEAM WROTE: DETAILS ---\n{text(p['details'])[:6000]}\n\n--- DATA REFERENCES ---\n{text(p['dataReferences'])[:1000]}\n")
    (H / f"work/evidence{b}.txt").write_text("\n".join(lines))
    print(b, (H / f"work/evidence{b}.txt").stat().st_size)
