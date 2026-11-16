"""Finds the GitHub repository of each submitted project and reads its public facts. Writes work/repos.json."""
import base64, collections, json, re, subprocess, sys
T = [t for t in json.load(open("teams.json")) if t["projectSubmitted"]]
TOKEN = subprocess.run(["gh", "auth", "token", "--user", "BillSharifzade"], capture_output=True, text=True).stdout.strip()

def api(path):
    r = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path], capture_output=True, text=True, env={"GH_TOKEN": TOKEN, "PATH": "/usr/bin:/bin"})
    if r.returncode: return None
    try: return json.loads(r.stdout)
    except Exception: return None

def find(t):
    p = t["projectDetails"]; blob = " ".join(str(p.get(k) or "") for k in ("projectLink", "demoLink", "details", "summary", "projectReferences", "dataReferences"))
    found = []
    for o, r in re.findall(r"github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)", blob):
        r = re.sub(r"\.git$", "", r).rstrip(".")
        if o.lower() not in ("nasa", "nasa-gibs", "topics", "orgs", "features") and (o, r) not in found: found.append((o, r))
    for o, r in re.findall(r"https?://([A-Za-z0-9-]+)\.github\.io/([A-Za-z0-9._-]+)", blob):
        if (o, r) not in found: found.append((o, r))
    return found

out = {}
for n, t in enumerate(T, 1):
    best = None
    for o, r in find(t)[:12]:
        m = api(f"repos/{o}/{r}")
        # Libraries and NASA repositories that a text merely cites are older than the event; skip them.
        if not m or m["created_at"] < "2026-09-15" or m["owner"]["login"].lower().startswith("nasa"):
            continue
        info = {"repo": m["full_name"], "url": m["html_url"], "created": m["created_at"], "pushed": m["pushed_at"], "sizeKb": m["size"], "license": (m.get("license") or {}).get("spdx_id"),
                "fork": m["fork"], "homepage": m.get("homepage") or "", "stars": m["stargazers_count"], "description": m.get("description") or ""}
        info["languages"] = api(f"repos/{o}/{r}/languages") or {}
        commits = []
        for page in (1, 2, 3):
            c = api(f"repos/{o}/{r}/commits?per_page=100&page={page}") or []
            commits += [(x["commit"]["author"]["date"], (x.get("author") or {}).get("login") or x["commit"]["author"]["name"]) for x in c]
            if len(c) < 100: break
        info["commits"] = len(commits); info["commitsCapped"] = len(commits) >= 300
        if commits:
            dates = sorted(d for d, _ in commits)
            info["firstCommit"], info["lastCommit"] = dates[0], dates[-1]
            info["before"] = sum(1 for d in dates if d < "2026-11-14T00:00:00Z")   # before Saturday 05:00 in Dushanbe
            info["during"] = sum(1 for d in dates if "2026-11-14T00:00:00Z" <= d <= "2026-11-15T19:00:00Z")
            info["after"] = sum(1 for d in dates if d > "2026-11-15T19:00:00Z")
            info["authors"] = len({a for _, a in commits})
        tree = api(f"repos/{o}/{r}/git/trees/{m['default_branch']}?recursive=1") or {}
        files = [x["path"] for x in tree.get("tree", []) if x["type"] == "blob"]
        info["files"] = len(files); info["top"] = sorted({f.split("/")[0] for f in files})[:30]
        info["ext"] = collections.Counter(f.rsplit(".", 1)[-1].lower() for f in files if "." in f.split("/")[-1]).most_common(8)
        info["tests"] = sum(1 for f in files if re.search(r"(^|/)(tests?|__tests__|spec)/|[._]test\.|_test\.|\.spec\.", f))
        info["hasReadme"] = any(f.lower().startswith("readme") for f in files)
        info["dataFiles"] = sum(1 for f in files if re.search(r"\.(csv|json|geojson|nc|tif|tiff|parquet|fits|h5|hdf)$", f, re.I))
        rd = api(f"repos/{o}/{r}/readme")
        if rd and rd.get("content"):
            txt = base64.b64decode(rd["content"]).decode("utf-8", "ignore"); info["readmeChars"] = len(txt); info["readme"] = txt[:1800]
        if not best or info["commits"] > best["commits"]: best = info
    out[t["id"]] = best
    print(n, t["title"], "->", best and (best["repo"], best["commits"], best["files"]), file=sys.stderr)
json.dump(out, open("work/repos.json", "w"), indent=1, ensure_ascii=False)
print(sum(1 for v in out.values() if v), "of", len(out), "projects have a public repository")
