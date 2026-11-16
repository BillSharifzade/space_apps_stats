"""Checks whether every submitted demo and project link opens without a login. Writes work/links.json."""
import json, re, ssl, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
UA = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36", "accept-language": "en"}

def get(url, limit=400_000):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25)
    return r.status, r.geturl(), r.headers.get("content-type", ""), r.read(limit).decode("utf-8", "ignore")

def check(url):
    if not url or not url.startswith("http"):
        return {"state": "missing"}
    host = urllib.parse.urlparse(url).netloc.replace("www.", "")
    out = {"host": host}
    try:
        if host in ("youtu.be", "youtube.com", "m.youtube.com"):
            out["state"] = "unchecked"  # YouTube does not answer from the network this was run on
            return out
        if host.startswith(("localhost", "127.")):
            out["state"] = "broken"; out["error"] = "address on the team's own computer"
            return out
        s, final, ctype, body = get(url)
        out["final"] = final[:200]
        low = body.lower()
        if "accounts.google.com" in final or "servicelogin" in final.lower():
            out["state"] = "login"
        elif host.endswith("google.com") and ("you need access" in low or "request access" in low or "you need permission" in low):
            out["state"] = "login"
        else:
            out["state"] = "ok"
            m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
            if m: out["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:120]
            if "text/html" in ctype: out["size"] = len(body)
    except urllib.error.HTTPError as e:
        # 403, 429 and redirect loops are how sites turn away scripts; a person may still get in.
        out.update(state="login" if e.code in (401, 403) and host.endswith("google.com") else "broken" if e.code in (404, 410) else "unchecked", code=e.code)
    except Exception as e:
        slow = "timed out" in str(e).lower() or type(e).__name__ == "TimeoutError"
        out.update(state="unchecked" if slow else "broken", error=type(e).__name__ + (" (slow)" if slow else ""))
    return out

T = [t for t in json.load(open("teams.json")) if t["projectSubmitted"]]
jobs = [(t["id"], k, (t["projectDetails"] or {}).get(k)) for t in T for k in ("demoLink", "projectLink")]
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(lambda j: check(j[2]), jobs))
out = {}
for (tid, k, url), r in zip(jobs, res):
    out.setdefault(tid, {})[k] = r
json.dump(out, open("work/links.json", "w"), indent=1)
import collections
print(collections.Counter((k, v[k]["state"]) for v in out.values() for k in v))
