// Opens every submitted project site in a headless browser, clicks through it and records what happens.
//   cd <folder with puppeteer-core installed> && node probe.mjs <data folder>
// Safe by design: nothing is typed or submitted, and buttons that delete, pay, send or log in are skipped.
import puppeteer from "puppeteer-core";
import fs from "node:fs";
const DIR = process.argv[2];
const teams = JSON.parse(fs.readFileSync(DIR + "/teams.json")).filter((t) => t.projectSubmitted);
const codes = JSON.parse(fs.readFileSync(DIR + "/work/codes.json"));
const codeOf = Object.fromEntries(Object.entries(codes).map(([c, id]) => [id, c]));
const FILE = DIR + "/work/probe2.json";
const out = fs.existsSync(FILE) ? JSON.parse(fs.readFileSync(FILE)) : {};
const SKIP = /(^|\.)(drive\.google\.com|docs\.google\.com|youtube\.com|youtu\.be|github\.com|canva\.link|canva\.com)$/;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: "/usr/bin/google-chrome-stable", headless: "new", args: ["--no-first-run", "--hide-scrollbars", "--mute-audio", "--deny-permission-prompts", "--enable-unsafe-swiftshader", "--use-angle=swiftshader"] });

const measure = () => {
  const q = (s) => document.querySelectorAll(s).length, text = (document.body?.innerText || "").replace(/\s+/g, " ").trim();
  const links = [...document.querySelectorAll("a[href]")].map((a) => a.href);
  const fonts = new Set(), sizes = new Set();
  for (const el of [...document.querySelectorAll("h1,h2,h3,p,button,a,li,span,div")].slice(0, 400)) { const c = getComputedStyle(el); fonts.add(c.fontFamily.split(",")[0].replace(/["']/g, "").trim()); sizes.add(c.fontSize); }
  return { title: document.title.slice(0, 120), textChars: text.length, text: text.slice(0, 1200), buttons: q("button, [role=button], [role=tab]"), inputs: q("input, select, textarea"), links: links.length,
    internal: new Set(links.filter((h) => { try { return new URL(h).host === location.host; } catch { return false; } }).map((h) => h.split("#")[0])).size,
    canvas: q("canvas"), svg: q("svg"), images: q("img"), brokenImages: [...document.images].filter((i) => i.complete && !i.naturalWidth).length, video: q("video"), iframes: q("iframe"),
    height: document.documentElement.scrollHeight, fonts: [...fonts].slice(0, 6), fontSizes: sizes.size, viewportMeta: !!document.querySelector("meta[name=viewport]"),
    placeholder: (text.match(/lorem ipsum|coming soon|todo|under construction|placeholder|mock data|sample data|demo data/gi) || []).slice(0, 5) };
};
const state = () => (document.body?.innerText || "").length + ":" + document.querySelectorAll("*").length + ":" + location.href + ":" + [...document.querySelectorAll("canvas")].map((c) => { try { return c.toDataURL().length; } catch { return 0; } }).join(",");

async function probe(t) {
  const code = codeOf[t.id], url = t.projectDetails.projectLink || "";
  let host = ""; try { host = new URL(url).hostname.replace(/^www\./, ""); } catch { return { code, url, kind: "no link" }; }
  if (SKIP.test(host)) return { code, url, host, kind: "not a site" };
  if (/^(localhost|127\.)/.test(host)) return { code, url, host, kind: "local address" };
  const r = { code, url, host, kind: "site", hosts: {}, errors: [], netFailed: 0, httpErrors: [], requests: 0, apiCalls: 0 };
  const ctx = await browser.createBrowserContext(); const page = await ctx.newPage();
  try {
    await page.setViewport({ width: 1280, height: 800 });
    page.on("dialog", (d) => d.dismiss().catch(() => {}));
    page.on("console", (m) => { if (m.type() === "error" && r.errors.length < 8) r.errors.push(m.text().slice(0, 110)); });
    page.on("pageerror", (e) => { if (r.errors.length < 8) r.errors.push("uncaught: " + String(e.message || e).slice(0, 100)); });
    page.on("requestfailed", (q) => { if (!/ERR_ABORTED/.test(q.failure()?.errorText || "")) r.netFailed++; });
    page.on("response", (res) => { r.requests++; try { const u = new URL(res.url()); r.hosts[u.hostname] = (r.hosts[u.hostname] || 0) + 1; const ty = res.request().resourceType(); if (ty === "xhr" || ty === "fetch") r.apiCalls++; if (res.status() >= 400 && r.httpErrors.length < 8) r.httpErrors.push(res.status() + " " + u.hostname + u.pathname.slice(0, 50)); } catch {} });
    const t0 = Date.now();
    const res = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    r.status = res ? res.status() : 0;
    await page.waitForNetworkIdle({ idleTime: 1200, timeout: 20000 }).catch(() => { r.neverIdle = true; });
    // Free hosts put apps to sleep: wait for real content, and press a "wake up" button if there is one.
    for (let k = 0; k < 10; k++) {
      const n = await page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /get this app back up|wake/i.test(x.innerText)); if (b) b.click(); return (document.body?.innerText || "").trim().length; }).catch(() => 0);
      if (n > 150) break; await sleep(2500);
    }
    await sleep(1500);
    r.loadMs = Date.now() - t0; r.final = page.url().slice(0, 200);
    let app = page, most = 0;
    for (const f of page.frames()) { const n = await f.evaluate(() => (document.body?.innerText || "").trim().length).catch(() => 0); if (n > most + 100) { most = n; app = f; } }
    if (app !== page) r.inFrame = true;
    Object.assign(r, await app.evaluate(measure));
    await page.screenshot({ path: `${DIR}/work/shots/${code}-a.jpg`, type: "jpeg", quality: 60 });
    // Click through: tabs, buttons and in-page navigation, up to ten different ones.
    const clicks = []; const home = page.url(); const errBefore = r.errors.length, httpBefore = r.httpErrors.length;
    for (let k = 0; k < 10; k++) {
      const before = await app.evaluate(state).catch(() => "");
      const label = await app.evaluate((done) => {
        const bad = /delete|remove|log ?out|sign ?out|pay|buy|submit|send|reset|clear|download|export|share|log ?in|sign ?in|sign ?up|register|print|удал|выйти|войти|отправ|скач|оплат/i;
        const els = [...document.querySelectorAll("button, [role=button], [role=tab], nav a, a[href^='#'], summary")].filter((e) => {
          const b = e.getBoundingClientRect(), s = getComputedStyle(e), txt = (e.innerText || e.getAttribute("aria-label") || "").trim().slice(0, 40);
          if (!txt || done.includes(txt) || bad.test(txt) || e.disabled || e.type === "submit") return false;
          if (e.tagName === "A") { try { if (new URL(e.href).host !== location.host || e.target === "_blank") return false; } catch { return false; } }
          return b.width > 8 && b.height > 8 && s.visibility !== "hidden" && s.display !== "none";
        });
        const e = els[0]; if (!e) return null;
        e.scrollIntoView({ block: "center" }); e.click(); return (e.innerText || e.getAttribute("aria-label") || "").trim().slice(0, 40);
      }, clicks.map((c) => c.label)).catch(() => null);
      if (!label) break;
      await sleep(1100);
      let host2 = ""; try { host2 = new URL(page.url()).host; } catch {}
      if (host2 && host2 !== new URL(home).host) { clicks.push({ label, changed: true, left: true }); await page.goto(home, { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {}); await sleep(1500); continue; }
      const after = await app.evaluate(state).catch(() => "");
      clicks.push({ label, changed: after !== before });
    }
    r.clicks = clicks.length; r.clicksChanged = clicks.filter((c) => c.changed).length; r.dead = clicks.filter((c) => !c.changed).map((c) => c.label).slice(0, 6);
    r.errorsOnClick = r.errors.length - errBefore; r.httpErrorsOnClick = r.httpErrors.length - httpBefore;
    await page.screenshot({ path: `${DIR}/work/shots/${code}-b.jpg`, type: "jpeg", quality: 60 });
    r.after = await app.evaluate(() => (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 500)).catch(() => "");
    // Phone view of the start page.
    await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
    await page.goto(home, { waitUntil: "domcontentloaded", timeout: 40000 }).catch(() => {});
    await page.waitForNetworkIdle({ idleTime: 1000, timeout: 12000 }).catch(() => {}); await sleep(1500);
    r.phoneOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth).catch(() => null);
    r.phoneSmallText = await page.evaluate(() => [...document.querySelectorAll("p,li,a,button,span")].slice(0, 300).filter((e) => e.innerText && parseFloat(getComputedStyle(e).fontSize) < 11).length).catch(() => null);
    await page.screenshot({ path: `${DIR}/work/shots/${code}-c.jpg`, type: "jpeg", quality: 60 });
    r.shot = true;
  } catch (e) { r.error = String(e.message || e).slice(0, 140); }
  await ctx.close().catch(() => {});
  return r;
}

const todo = teams.filter((t) => !out[t.id]); let i = 0;
async function worker() { while (i < todo.length) { const t = todo[i++]; out[t.id] = await Promise.race([probe(t), sleep(170000).then(() => ({ code: codeOf[t.id], url: t.projectDetails.projectLink, kind: "site", error: "gave up after 170 s" }))]); fs.writeFileSync(FILE, JSON.stringify(out, null, 1)); process.stderr.write(`${Object.keys(out).length}/${teams.length} ${out[t.id].host || ""} ${out[t.id].status || out[t.id].kind} clicks ${out[t.id].clicksChanged}/${out[t.id].clicks} ${out[t.id].error || ""}\n`); } }
await Promise.all([worker(), worker()]);
await browser.close(); console.log("done", Object.keys(out).length);
