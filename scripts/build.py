#!/usr/bin/env python3
"""Rebuild static SEO pages from data/*.json.
Outputs: best/<category>/index.html, sitemap.xml, robots.txt, llms.txt, llms-full.txt,
and refreshes the <!--SEO--> head block + pre-rendered directory in index.html / featured.html.
BASE is a PLACEHOLDER until the live domain is chosen: change it and rerun."""
import json, re, html, pathlib, os, sys, urllib.request, urllib.parse, urllib.error
BASE = "https://toolrank.io"  # PLACEHOLDER base URL
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.loads((ROOT/"data/tools.json").read_text())
N = json.loads((ROOT/"data/new-this-week.json").read_text())
UPD = D["updated"]; E = html.escape
LOGO = '<a class="logo" href="/"><img class="mark" src="/assets/logo.svg" alt="" width="46" height="28">Tool<b>Rank</b></a>'
ORG = {"@type": "Organization", "@id": BASE+"/#org", "name": "ToolRank", "url": BASE+"/"}
SITE = {"@type": "WebSite", "@id": BASE+"/#website", "name": "ToolRank", "url": BASE+"/", "publisher": {"@id": BASE+"/#org"},
        "potentialAction": {"@type": "SearchAction", "target": {"@type": "EntryPoint", "urlTemplate": BASE+"/?q={search_term_string}"},
                            "query-input": "required name=search_term_string"}}
REPO = "Toolrank/toolrank"
REVIEW_NEW = f"https://github.com/{REPO}/issues/new?template=review.yml"
def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
def review_url(name=""): return REVIEW_NEW + ("&tool_name=" + urllib.parse.quote(name) if name else "")
TOOLS = {slug(t["name"]): t for c in D["categories"] for t in c["tools"]}

def _sections(body):
    out, cur = {}, None
    for line in (body or "").replace("\r", "").split("\n"):
        m = re.match(r"^###\s+(.*)$", line)
        if m: cur = m.group(1).strip().lower(); out[cur] = []; continue
        if cur: out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}

def fetch_reviews():
    """Approved reviews = GitHub issues labelled BOTH 'review' and 'approved' (labels only maintainers can add). Never seeded."""
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"); items, page = [], 1
    while True:
        rq = urllib.request.Request(f"https://api.github.com/repos/{REPO}/issues?labels=review,approved&state=all&per_page=100&page={page}",
                                    headers={"Accept": "application/vnd.github+json", "User-Agent": "toolrank-build", **({"Authorization": f"Bearer {tok}"} if tok else {})})
        batch = json.loads(urllib.request.urlopen(rq, timeout=30).read())
        items += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100: break
        page += 1
    revs = []
    for i in items:
        f = _sections(i.get("body")); m = re.match(r"\s*([1-5])", f.get("rating", ""))
        name = f.get("tool name", "").strip(); text = f.get("review", "").strip()
        if not (m and name and text) or i.get("state_reason") == "not_planned": continue
        t = TOOLS.get(slug(name))
        revs.append({"id": i["number"], "tool": t["name"] if t else name, "tool_slug": slug(t["name"] if t else name), "listed": bool(t),
                     "rating": int(m.group(1)), "role": f.get("who you are", "").strip()[:20], "text": text[:2000],
                     "use_case": re.sub(r"^_No response_$", "", f.get("use case", "").strip())[:200], "author": i["user"]["login"], "date": i["created_at"][:10], "url": i["html_url"]})
    return sorted(revs, key=lambda r: (r["date"], r["id"]), reverse=True)

def load_reviews():
    p = ROOT/"data/reviews.json"
    try:
        revs = fetch_reviews()
        p.write_text(json.dumps({"updated": max([r["date"] for r in revs], default=None), "source": "GitHub issues labelled review + approved",
                                 "reviews": revs}, indent=1, ensure_ascii=False) + "\n")
        print(f"reviews: fetched {len(revs)} approved review(s) from GitHub")
    except Exception as e:
        if os.environ.get("REVIEWS_REQUIRED"): raise
        print(f"WARN reviews fetch failed ({e}); keeping existing data/reviews.json", file=sys.stderr)
    return json.loads(p.read_text())["reviews"]
R = load_reviews()
RB = {}
for r in R: RB.setdefault(r["tool_slug"], []).append(r)
def rstat(t):
    rs = [r for r in RB.get(slug(t["name"]), []) if r["listed"]]; n = len(rs)
    return n, (round(sum(r["rating"] for r in rs) / n, 1) if n else None)
def stars(a): return "★" * int(round(a)) + "☆" * (5 - int(round(a)))
def rv_line(t):
    n, a = rstat(t); s = slug(t["name"])
    lead = f'<a href="/reviews.html#{s}"><span class="st">★ {a}</span> · {n} review{"s" if n != 1 else ""}</a>' if n else f'<a href="/reviews.html#{s}">Reviews (0)</a>'
    return f'<div class="rvl">{lead}<a class="rvbtn" href="{E(review_url(t["name"]))}" target="_blank" rel="noopener">{"Review" if n else "Be the first to review"}</a></div>'
def review_html(r):
    return (f'<article class="card review"><div class="rh"><span class="st" aria-label="{r["rating"]} out of 5">{stars(r["rating"])}</span>'
            f'<span class="tag">{E(r["role"] or "User")}</span></div><h3>{E(r["tool"])}</h3><p>{E(r["text"])}</p>'
            + (f'<p class="muted">Use case: {E(r["use_case"])}</p>' if r["use_case"] else "") +
            f'<p class="muted">by <a href="https://github.com/{E(r["author"])}" rel="nofollow noopener" target="_blank">@{E(r["author"])}</a> · <a href="{E(r["url"])}" target="_blank" rel="nofollow noopener">{r["date"]}</a></p></article>')
NT = sum(len(c["tools"]) for c in D["categories"])
def stats_html():
    n = len(R)
    return (f'<!--STATS--><div class="stats"><span><b>{NT}</b> tools ranked</span><span><b>{n}</b> review{"s" if n != 1 else ""} collected'
            + ('' if n else ' · <a href="/reviews.html">Be the first to review</a>') + '</span></div><!--/STATS-->')
CTA = (f'<section class="wrap"><div class="cta"><div><h2>Using AI tools? Leave a review.</h2><p>Help builders and businesses pick the right AI tool.</p></div>'
       f'<a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></div></section>')

# ---- Trending: real public momentum signals only (GitHub stars delta vs stored snapshots; HN stories via Algolia). Refreshed at most every 20h.
import time, datetime as dt
def _get(url, gh=False):
    h = {"User-Agent": "toolrank-build"}
    tok = os.environ.get("GITHUB_TOKEN")
    if gh: h["Accept"] = "application/vnd.github+json"; h.update({"Authorization": f"Bearer {tok}"} if tok else {})
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30).read())
def gh_repo(u):
    m = re.match(r"https://github\.com/([^/]+/[^/#?]+)", u)
    return m.group(1).removesuffix(".git") if m and not m.group(1).startswith(("features/", "orgs/", "topics/")) else None
def hn_key(t):
    r = gh_repo(t["url"])
    if r: return "github.com/" + r
    pu = urllib.parse.urlparse(t["url"]); return (pu.netloc.removeprefix("www.") + pu.path).rstrip("/")
def momentum():
    tp, hp = ROOT/"data/trending.json", ROOT/"data/stars-history.json"
    old = json.loads(tp.read_text()) if tp.exists() else None
    if old and not os.environ.get("TRENDING_FORCE") and time.time() - old.get("fetched_ts", 0) < 20*3600: return old
    try:
        now = dt.datetime.now(dt.timezone.utc); today = now.strftime("%Y-%m-%d"); tools = [t for c in D["categories"] for t in c["tools"]]
        hist = json.loads(hp.read_text()) if hp.exists() else {}
        snap = {}
        for t in tools:
            r = gh_repo(t["url"])
            if r and r not in snap:
                try: snap[r] = _get(f"https://api.github.com/repos/{r}", gh=True)["stargazers_count"]
                except urllib.error.HTTPError as e:
                    if e.code != 404: raise
                    print(f"WARN trending: repo {r} not found (404)", file=sys.stderr)
        hist[today] = snap
        hist = {k: hist[k] for k in sorted(hist)[-30:]}
        base_day = max([k for k in hist if k <= (now - dt.timedelta(days=7)).strftime("%Y-%m-%d")], default=min(hist))
        stars = []
        for t in tools:
            r = gh_repo(t["url"])
            if r and r in snap and r in hist[base_day] and base_day != today:
                stars.append({"tool": t["name"], "repo": r, "gained": snap[r] - hist[base_day][r], "stars": snap[r], "url": t["url"]})
        stars = sorted([x for x in stars if x["gained"] > 0], key=lambda x: -x["gained"])[:10]
        keys = {}
        for t in tools: keys.setdefault(hn_key(t), []).append(t["name"])
        generic = {"github.com", "google.com", "chatgpt.com", "gemini.google.com", "openai.com", "microsoft.com", "aws.amazon.com", "adobe.com", "anthropic.com"}
        since = int((now - dt.timedelta(days=7)).timestamp()); hn = []
        for k, names in keys.items():
            if len(names) > 1 or k in generic: continue
            d = _get("https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(
                {"query": k, "restrictSearchableAttributes": "url", "tags": "story", "numericFilters": f"created_at_i>{since}", "hitsPerPage": 50}))
            hits = [h for h in d["hits"] if k in (h.get("url") or "")]
            if hits:
                top = max(hits, key=lambda h: h.get("points") or 0)
                hn.append({"tool": names[0], "stories": len(hits), "points": sum(h.get("points") or 0 for h in hits),
                           "top_title": top.get("title"), "top_url": f"https://news.ycombinator.com/item?id={top['objectID']}"})
            time.sleep(0.05)
        hn = sorted(hn, key=lambda x: (-x["points"], -x["stories"]))[:10]
        out = {"fetched": now.strftime("%Y-%m-%d %H:%M UTC"), "fetched_ts": int(now.timestamp()), "stars_baseline": base_day if base_day != today else None,
               "repos_tracked": len(snap), "stars": stars, "hn": hn}
        hp.write_text(json.dumps(hist, indent=1, sort_keys=True) + "\n"); tp.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
        print(f"trending: {len(snap)} repos snapshotted (baseline {out['stars_baseline']}), {len(stars)} gaining, {len(hn)} with HN stories")
        return out
    except Exception as e:
        print(f"WARN trending fetch failed ({e}); keeping previous data", file=sys.stderr)
        return old or {"fetched": None, "stars_baseline": None, "repos_tracked": 0, "stars": [], "hn": []}
TR = momentum()
def clicks():
    """Most-clicked tools from GoatCounter 'click/<slug>' events (last 7 days). Needs GOATCOUNTER_TOKEN; fetched at most every 50 min."""
    cp = ROOT/"data/clicks.json"; old = json.loads(cp.read_text()) if cp.exists() else None
    tok = os.environ.get("GOATCOUNTER_TOKEN")
    if not tok or (old and old.get("fetched_ts") and time.time() - old["fetched_ts"] < 50*60): return old
    try:
        now = dt.datetime.now(dt.timezone.utc); seen, hits, status = [], [], None
        for _ in range(5):
            q = {"start": (now - dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"), "end": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": 100}
            if seen: q["exclude_paths"] = ",".join(map(str, seen))
            rq = urllib.request.Request("https://toolrank.goatcounter.com/api/v0/stats/hits?" + urllib.parse.urlencode(q),
                                        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "Accept": "application/json",
                                                 "User-Agent": "Mozilla/5.0 (compatible; ToolRankBuild/1.0; +https://toolrank.io)"})
            for attempt in (1, 2):
                try:
                    with urllib.request.urlopen(rq, timeout=30) as r: status = r.status; d = json.loads(r.read()); break
                except urllib.error.HTTPError as e:
                    print(f"WARN clicks: GoatCounter HTTP {e.code} {e.reason} (attempt {attempt})", file=sys.stderr)
                    if attempt == 2 or e.code < 500 and e.code != 429: raise
                except Exception as e:
                    print(f"WARN clicks: {type(e).__name__}: {getattr(e, 'reason', e)!r} (attempt {attempt})", file=sys.stderr)
                    if attempt == 2:
                        # Fallback: system curl (different TLS stack). Token goes via stdin config, never argv or logs.
                        import subprocess
                        cfg = f'header = "Authorization: Bearer {tok}"\nheader = "Content-Type: application/json"\nheader = "Accept: application/json"\n'
                        cp_ = subprocess.run(["curl", "-sS", "--http1.1", "-m", "30", "-A", "Mozilla/5.0 (compatible; ToolRankBuild/1.0; +https://toolrank.io)",
                                              "-K", "-", "-w", "\n%{http_code}", rq.full_url], input=cfg, capture_output=True, text=True)
                        body, _, code = cp_.stdout.rpartition("\n")
                        print(f"clicks: curl fallback exit {cp_.returncode}, HTTP {code or 'none'} {cp_.stderr.strip()[:200]}", file=sys.stderr)
                        if cp_.returncode or code != "200": raise
                        status = 200; d = json.loads(body); break
                time.sleep(5)
            hits += d.get("hits") or []; seen += [h["path_id"] for h in d.get("hits") or []]
            if not d.get("more"): break
        print(f"clicks: GoatCounter API HTTP {status}, {len(hits)} path(s) returned")
        names = {slug(t["name"]): t["name"] for c in D["categories"] for t in c["tools"]}
        agg = {}
        for h in hits:
            pth = (h.get("path") or "").lstrip("/")
            if not pth.startswith("click/"): continue
            sl = pth[6:]; agg[sl] = agg.get(sl, 0) + int(h.get("count") or 0)
        top = sorted(({"slug": k, "tool": names.get(k, k), "count": v} for k, v in agg.items() if v > 0 and k in names), key=lambda x: (-x["count"], x["tool"]))[:10]
        out = {"fetched": now.strftime("%Y-%m-%d %H:%M UTC"), "fetched_ts": int(now.timestamp()), "window": "last 7 days", "source": "GoatCounter click/ events (unique visitors)", "top": top}
        cp.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n"); return out
    except Exception as e:
        print(f"WARN clicks fetch failed ({type(e).__name__}: {getattr(e, 'code', '')} {getattr(e, 'reason', e)!r}); keeping previous data", file=sys.stderr)
        return old
CL = clicks()
def clicks_card():
    if CL and CL.get("top"):
        body = '<ol class="tl">' + "".join(f'<li><a href="/reviews.html#{x["slug"]}">{E(x["tool"])}</a> <span class="up">{x["count"]:,}</span> <span class="muted">visitor{"s" if x["count"] != 1 else ""}</span></li>' for x in CL["top"]) + '</ol>'
    else:
        body = '<p class="muted">Collecting clicks, check back soon.</p>'
    upd = f' (updated {E(CL["fetched"])})' if CL and CL.get("fetched") else ""
    return f'<article class="card"><h3>Most clicked this week</h3><span class="tag">Source: GoatCounter, cookieless, last 7 days</span><p class="muted small">Visitors who clicked through to each tool from ToolRank{upd}.</p>{body}</article>'


# ---------------- v2 design ----------------
REDIRECTS = {"vibe-coding": "coding", "coding-assistants": "coding", "agent-builders": "automation", "productivity": "research"}
CAT = {c["id"]: c for c in D["categories"]}
TOOLCAT = {slug(t["name"]): c["id"] for c in D["categories"] for t in c["tools"]}
# Per-category art palette (brand purple / magenta / cyan family) + motif
PAL = {"ai-assistants": ("#7c5cff", "#22d3ee", "orb"), "coding": ("#5b8cff", "#c04cf0", "code"), "image": ("#f472b6", "#7c5cff", "venn"),
       "video": ("#c04cf0", "#ff6b9a", "play"), "writing": ("#22d3ee", "#7c5cff", "wave"), "voice-audio": ("#22d3ee", "#c04cf0", "bars"),
       "automation": ("#7c5cff", "#2dd4bf", "nodes"), "research": ("#38bdf8", "#7c5cff", "lens"), "marketing": ("#ff6b9a", "#ffb35c", "rise"),
       "business": ("#5b8cff", "#22d3ee", "cubes"), "restaurants": ("#ffb35c", "#c04cf0", "plate"), "hospitality": ("#ff8a5c", "#7c5cff", "arch"),
       "crypto": ("#a78bfa", "#22d3ee", "hex"), "education": ("#2dd4bf", "#5b8cff", "stack"), "health": ("#4ade80", "#22d3ee", "pulse"),
       "gaming": ("#c04cf0", "#22d3ee", "pad")}
def cat_art(cid):
    a, b, m = PAL[cid]
    g = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
         f'<linearGradient id="h" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>'
         f'<radialGradient id="s" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".25" stop-color="{a}"/><stop offset="1" stop-color="{b}" stop-opacity=".9"/></radialGradient>'
         '<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="38"/></filter></defs>')
    bg = (f'<rect width="400" height="400" fill="#10131c"/><circle cx="300" cy="90" r="120" fill="{a}" opacity=".55" filter="url(#b)"/>'
          f'<circle cx="90" cy="330" r="130" fill="{b}" opacity=".45" filter="url(#b)"/>')
    G = 'fill="url(#g)"'; H = 'fill="url(#h)"'
    shapes = {
     "orb": f'<circle cx="250" cy="170" r="110" fill="url(#s)"/><ellipse cx="250" cy="170" rx="170" ry="38" fill="none" stroke="url(#g)" stroke-width="10" transform="rotate(-20 250 170)"/><circle cx="250" cy="170" r="110" {H}/>',
     "code": "".join(f'<rect x="{110+i*40}" y="{60+i*70}" width="230" height="46" rx="23" {G} opacity="{1-i*.18:.2f}" transform="skewX(-17)"/>' for i in range(4)) + '<path d="M150 150 L95 200 L150 250" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>',
     "venn": f'<circle cx="200" cy="150" r="95" fill="{a}" opacity=".85"/><circle cx="290" cy="220" r="95" fill="{b}" opacity=".8" style="mix-blend-mode:screen"/><circle cx="180" cy="260" r="70" {G} opacity=".9"/><circle cx="200" cy="150" r="95" {H}/>',
     "play": f'<rect x="120" y="70" width="240" height="170" rx="36" {G} transform="rotate(-10 240 155)"/><rect x="90" y="110" width="240" height="170" rx="36" fill="#fff" fill-opacity=".12" stroke="#fff" stroke-opacity=".35" transform="rotate(-4 210 195)"/><path d="M190 150 L270 195 L190 240 Z" fill="#fff" fill-opacity=".9"/>',
     "wave": "".join(f'<path d="M-10 {130+i*45} C 90 {60+i*45}, 200 {210+i*45}, 410 {110+i*45}" fill="none" stroke="url(#g)" stroke-width="{26-i*4}" stroke-linecap="round" opacity="{1-i*.15:.2f}"/>' for i in range(5)),
     "bars": "".join(f'<rect x="{70+i*36}" y="{200-h/2}" width="22" height="{h}" rx="11" {G}/>' for i, h in enumerate([60, 140, 220, 120, 260, 180, 90, 40])),
     "nodes": f'<path d="M110 280 L210 150 L320 230 L280 90 M210 150 L280 90" stroke="url(#g)" stroke-width="10" fill="none"/>' + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#s)"/>' for x, y, r in [(110, 280, 38), (210, 150, 52), (320, 230, 34), (280, 90, 28)]),
     "lens": f'<circle cx="220" cy="170" r="100" fill="none" stroke="url(#g)" stroke-width="30"/><circle cx="220" cy="170" r="85" fill="#fff" fill-opacity=".08"/><rect x="290" y="250" width="40" height="120" rx="20" {G} transform="rotate(-45 310 310)"/><circle cx="190" cy="140" r="30" fill="#fff" fill-opacity=".35"/>',
     "rise": "".join(f'<rect x="{80+i*65}" y="{300-h}" width="48" height="{h}" rx="12" {G} opacity="{.55+i*.11:.2f}"/>' for i, h in enumerate([70, 120, 180, 250, 300][:5])) + '<path d="M70 250 L170 180 L230 210 L350 80" stroke="#fff" stroke-opacity=".85" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
     "cubes": "".join(f'<g transform="translate({x} {y})"><path d="M0 -50 L60 -20 L0 10 L-60 -20Z" fill="#fff" fill-opacity=".35"/><path d="M-60 -20 L0 10 L0 80 L-60 50Z" fill="{a}"/><path d="M60 -20 L0 10 L0 80 L60 50Z" fill="{b}"/></g>' for x, y in [(200, 120), (140, 220), (260, 220), (200, 300)]),
     "plate": f'<circle cx="210" cy="230" r="120" {G}/><circle cx="210" cy="230" r="80" fill="#10131c" fill-opacity=".45"/><circle cx="210" cy="230" r="120" {H}/>' + "".join(f'<path d="M{170+i*40} 90 c -18 -20 18 -30 0 -50" stroke="#fff" stroke-opacity=".6" stroke-width="9" fill="none" stroke-linecap="round"/>' for i in range(3)),
     "arch": f'<circle cx="210" cy="230" r="110" fill="url(#s)"/><rect x="0" y="230" width="400" height="170" fill="#10131c" fill-opacity=".7"/>' + "".join(f'<rect x="{60+i*20}" y="{250+i*30}" width="{280-i*40}" height="10" rx="5" {G} opacity="{.9-i*.2:.2f}"/>' for i in range(4)),
     "hex": f'<path d="M210 60 L320 125 L320 255 L210 320 L100 255 L100 125Z" {G}/><path d="M210 60 L320 125 L210 190 L100 125Z" fill="#fff" fill-opacity=".3"/><path d="M210 190 L210 320" stroke="#fff" stroke-opacity=".3" stroke-width="4"/>',
     "stack": "".join(f'<rect x="{90+i*14}" y="{250-i*55}" width="230" height="44" rx="10" {G} opacity="{1-i*.15:.2f}" transform="rotate({-8+i*5} 205 {272-i*55})"/>' for i in range(4)) + '<path d="M150 70 L230 40 L310 70 L230 100Z" fill="#fff" fill-opacity=".8"/>',
     "pulse": f'<circle cx="210" cy="200" r="120" fill="url(#s)" opacity=".8"/><path d="M40 210 H150 L180 140 L220 280 L250 180 L270 210 H370" stroke="#fff" stroke-width="14" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
     "pad": f'<rect x="80" y="120" width="260" height="150" rx="75" {G}/><rect x="80" y="120" width="260" height="150" rx="75" {H}/><path d="M135 180 h20 v-20 h20 v20 h20 v20 h-20 v20 h-20 v-20 h-20z" fill="#fff" fill-opacity=".85"/><circle cx="265" cy="180" r="13" fill="#fff" fill-opacity=".85"/><circle cx="292" cy="208" r="13" fill="#fff" fill-opacity=".6"/>',
    }
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">{g}{bg}{shapes[m]}</svg>'
def trend_art(i):
    a, b = [("#7c5cff", "#22d3ee"), ("#c04cf0", "#7c5cff"), ("#22d3ee", "#c04cf0")][i % 3]
    d = (f'<defs><radialGradient id="s" cx=".32" cy=".28" r=".8"><stop offset="0" stop-color="#fff"/><stop offset=".22" stop-color="{a}"/><stop offset=".85" stop-color="{b}"/><stop offset="1" stop-color="#0b0d12"/></radialGradient>'
         f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
         '<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="50"/></filter></defs>'
         f'<rect width="800" height="450" fill="#0f1220"/><circle cx="600" cy="80" r="200" fill="{a}" opacity=".45" filter="url(#b)"/><circle cx="160" cy="420" r="200" fill="{b}" opacity=".4" filter="url(#b)"/>')
    v = [f'<clipPath id="fr"><rect x="-200" y="225" width="1200" height="400" transform="rotate(-14 420 225)"/></clipPath><ellipse cx="420" cy="225" rx="300" ry="70" fill="none" stroke="url(#g)" stroke-width="22" opacity=".55" transform="rotate(-14 420 225)"/><circle cx="420" cy="215" r="130" fill="url(#s)"/><ellipse cx="420" cy="225" rx="300" ry="70" fill="none" stroke="url(#g)" stroke-width="22" clip-path="url(#fr)" transform="rotate(-14 420 225)"/>',
         "".join(f'<rect x="{250+k*55}" y="{70+k*35}" width="300" height="200" rx="34" fill="url(#g)" opacity="{.35+k*.2:.2f}" stroke="#fff" stroke-opacity=".35" transform="skewX(-12)"/>' for k in range(4)),
         "".join(f'<circle cx="{260+k*90}" cy="{300-k*55}" r="{70+k*14}" fill="url(#s)" opacity="{.6+k*.1:.2f}"/>' for k in range(4))][i % 3]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">{d}{v}</svg>'

def domain(u): return urllib.parse.urlparse(u).netloc.removeprefix("www.")
def logo_html(t, size=40):
    return (f'<span class="lg" data-l="{E(t["name"][:1].upper())}" aria-hidden="true"><img src="https://www.google.com/s2/favicons?domain={E(domain(t["url"]))}&amp;sz=64" '
            f'alt="" width="{size}" height="{size}" loading="lazy" decoding="async" onerror="this.remove()"></span>')
def tool_card(t, i, h="h3"):
    return (f'<article class="card tool" id="{slug(t["name"])}"><div class="th">{logo_html(t)}<div class="tt"><{h}><span class="rank">#{i}</span>{E(t["name"])}</{h}>'
            f'<div class="tm"><span class="tag {t["pricing"]}">{t["pricing"]}</span>{"<span class=\"tag feat\">Featured</span>" if t.get("featured") else ""}</div></div></div>'
            f'<p>{E(t["verdict"])}</p>{rv_line(t)}<a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t["name"])} →</a></article>')
def cards(c, h="h3"): return "".join(tool_card(t, i, h) for i, t in enumerate(c["tools"], 1))
def short(c): return c["title"]
def link(t): return t.get("affiliate_url") or t["url"]
def rel(t): return "noopener" + (" sponsored" if t.get("affiliate_url") else "")

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=Sora:wght@600;700;800&amp;display=swap">')
NAV = (f'<header class="top"><div class="bar">{LOGO}<nav aria-label="Main"><a href="/#browse">Categories</a><a href="/#trending">Trending</a>'
       f'<a href="/reviews.html">Reviews</a><a href="/services.html" class="hm">For makers</a><a class="btn sm" href="/submit.html">Submit a tool</a></nav></div></header>')
def FOOT_():
    cl = "".join(f'<a href="/best/{c["id"]}/">{E(c["title"])}</a>' for c in D["categories"])
    return (f'<footer class="foot"><div class="wrap"><div class="fg"><div class="fl">{LOGO}<p class="muted">Confused by AI? We&rsquo;ll find the right tool for you. Editorial rankings, updated <time datetime="{UPD}">{UPD}</time>.</p></div>'
            f'<nav class="fc2" aria-label="Categories">{cl}</nav><nav class="fc2" aria-label="ToolRank"><a href="/reviews.html">Reviews</a><a href="/submit.html">Submit a tool</a><a href="/services.html">Services</a><a href="/featured.html">Get featured</a><a href="/llms.txt">llms.txt</a></nav></div>'
            f'<p class="muted small">© {UPD[:4]} ToolRank. Some links may become affiliate links; featured placements are labelled. Reviews are user-submitted via GitHub and moderated; they never change the editorial rank.</p></div></footer>')
FOOT = FOOT_()
def head(title, desc, path, ld, otype="website"):
    url = BASE + path
    return f"""<!--SEO--><title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-snippet:-1"><meta name="theme-color" content="#0b0d12">
<meta property="og:type" content="{otype}"><meta property="og:site_name" content="ToolRank"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE}/assets/og.png">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script><!--/SEO-->"""
def doc(headblock, body, extra_head=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n{headblock}{FONTS}'
            f'<link rel="stylesheet" href="/assets/style.css">{extra_head}</head><body>\n{NAV}\n{body}\n{FOOT}</body></html>\n')

def tool_ld(t, c, i):
    o = {"@type": "SoftwareApplication", "name": t["name"], "url": t["url"], "description": t["verdict"], "applicationCategory": "AI tool: " + c["title"]}
    if t["pricing"] in ("free", "freemium"):
        o["offers"] = {"@type": "Offer", "price": "0", "priceCurrency": "USD", "description": t["pricing"] + " (free tier available)"}
    n, a = rstat(t)
    if n: o["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": a, "reviewCount": n, "bestRating": 5, "worstRating": 1}
    return o
def faqs(c):
    ts = c["tools"]; free = [t["name"] for t in ts if t["pricing"] in ("free", "freemium")]; paid = [t["name"] for t in ts if t["pricing"] == "paid"]
    return [(f"What is the best AI tool for {c['title'].lower()} right now?", f"In ToolRank's editorial ranking (updated {UPD}), {ts[0]['name']} is ranked #1: {ts[0]['verdict']}"),
            ("Which of these tools have a free option?",
             (", ".join(free) + " list a free or freemium tier." if free else "None of the ranked tools are listed as free or freemium.") +
             (" " + ", ".join(paid) + (" is" if len(paid) == 1 else " are") + " listed as paid." if paid else "") + " Pricing changes often; check each vendor's site."),
            ("How are these tools ranked?", "Rankings are editorial picks by ToolRank, ordered by position in the list. Featured placements are paid, clearly labelled and do not change the editorial rank."),
            ("When was this list last updated?", f"{UPD}.")]
def tile(c, cls="tile"):
    return (f'<a class="{cls}" href="/best/{c["id"]}/" data-cat="{c["id"]}"><img class="art" src="/assets/cat/{c["id"]}.svg" alt="" width="400" height="400" loading="lazy" decoding="async">'
            f'<span class="tn">{E(c["title"])}</span><span class="tc">{len(c["tools"])} tools</span></a>')
def page(c):
    path = f"/best/{c['id']}/"; fq = faqs(c)
    title = f"Best AI tools for {c['title']} ({UPD[:4]}): {', '.join(t['name'] for t in c['tools'][:3])} & more | ToolRank"
    desc = f"{c['blurb']} Ranked: " + ", ".join(f"#{i} {t['name']}" for i, t in enumerate(c["tools"][:12], 1)) + f"{' and more' if len(c['tools']) > 12 else ''}. Updated {UPD}."
    ld = [ORG, SITE, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "ToolRank", "item": BASE+"/"},
                                                                     {"@type": "ListItem", "position": 2, "name": c["title"], "item": BASE+path}]},
          {"@type": "ItemList", "name": "Best AI tools: " + c["title"], "description": c["blurb"], "url": BASE+path, "numberOfItems": len(c["tools"]),
           "itemListOrder": "https://schema.org/ItemListOrderAscending",
           "itemListElement": [{"@type": "ListItem", "position": i, "item": tool_ld(t, c, i)} for i, t in enumerate(c["tools"], 1)]},
          {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in fq]}]
    others = "".join(tile(o, "tile sm") for o in D["categories"] if o is not c)
    body = f"""<main><article><section class="hero cathero"><div class="wrap ch"><div><nav class="crumb" aria-label="Breadcrumb"><a href="/">ToolRank</a> › <a href="/#browse">Categories</a></nav>
<h1>{E(c['title'])}</h1><p class="lead">{E(c['blurb'])}</p><p class="muted small">{len(c['tools'])} tools · Editorial ranking · Updated <time datetime="{UPD}">{UPD}</time></p></div>
<img class="chart" src="/assets/cat/{c['id']}.svg" alt="" width="400" height="400"></div></section>
<section class="sec"><div class="wrap"><h2>The ranking</h2><div class="tgrid">{cards(c)}</div></div></section>
{cat_reviews(c)}<section class="sec faq"><div class="wrap"><h2>FAQ</h2>{''.join(f'<details><summary><h3>{E(a)}</h3></summary><p>{E(b)}</p></details>' for a, b in fq)}</div></section>
</article><section class="sec"><div class="wrap"><h2>More categories</h2><div class="tiles">{others}</div></div></section></main>"""
    return doc(head(title, desc, path, ld), body)
def redirect_page(old, new):
    c = CAT[new]; url = f"{BASE}/best/{new}/"
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Moved: {E(c["title"])} | ToolRank</title>'
            f'<meta name="description" content="This list moved to {E(c["title"])} on ToolRank."><link rel="canonical" href="{url}"><meta name="robots" content="noindex,follow">'
            f'<meta http-equiv="refresh" content="0; url=/best/{new}/"><script>location.replace("/best/{new}/"+location.hash)</script><link rel="stylesheet" href="/assets/style.css"></head>'
            f'<body><main class="wrap sec"><h1>This list has moved</h1><p><a href="/best/{new}/">Go to {E(c["title"])} →</a></p></main></body></html>\n')

def cat_reviews(c):
    rs = [r for t in c["tools"] for r in RB.get(slug(t["name"]), []) if r["listed"]]
    rs.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    body = (f'<div class="grid">{"".join(review_html(r) for r in rs[:12])}</div>' + (f'<p><a href="/reviews.html#cat-{c["id"]}">All {len(rs)} reviews →</a></p>' if len(rs) > 12 else "")) if rs else \
        f'<p class="muted">No reviews yet for {E(c["title"])} tools. Used one of them? Be the first to review.</p>'
    return (f'<section class="sec" id="reviews"><div class="wrap"><h2>Reviews</h2>{body}'
            f'<div class="cta"><div><h3>Using AI tools? Leave a review.</h3><p>Help builders and businesses pick the right AI tool.</p></div><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></div></div></section>')
def reviews_page():
    secs = []
    for c in D["categories"]:
        rows = []
        for t in c["tools"]:
            n, a = rstat(t); s = slug(t["name"]); rs = [r for r in RB.get(s, []) if r["listed"]]
            rows.append(f'<div class="rrow" id="{s}"><div class="rt">{logo_html(t, 28)}<strong>{E(t["name"])}</strong> ' +
                        (f'<span class="st">{stars(a)} {a}</span> <span class="muted">({n} review{"s" if n != 1 else ""})</span>' if n else '<span class="muted">No reviews yet</span>') +
                        f'<a class="rvbtn" href="{E(review_url(t["name"]))}" target="_blank" rel="noopener">{"Review" if n else "Be the first to review"}</a></div>' +
                        (f'<div class="grid">{"".join(review_html(r) for r in rs)}</div>' if rs else "") + '</div>')
        secs.append(f'<section class="sec" id="cat-{c["id"]}"><div class="wrap"><h2><a href="/best/{c["id"]}/">{E(c["title"])}</a></h2>{"".join(rows)}</div></section>')
    other = [r for r in R if not r["listed"]]
    if other: secs.append(f'<section class="sec"><div class="wrap"><h2>Other tools (not yet ranked)</h2><div class="grid">{"".join(review_html(r) for r in other)}</div></div></section>')
    latest = f'<section class="sec"><div class="wrap"><h2>Latest reviews</h2><div class="grid">{"".join(review_html(r) for r in R[:9])}</div></div></section>' if R else ""
    body = (f'<section class="hero sub"><div class="wrap"><h1>AI tool reviews</h1><p class="lead">Using AI tools? Leave a review. Help builders and businesses pick the right AI tool.</p>{stats_html()}'
            f'<p><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></p>'
            '<p class="muted small">Reviews are posted as public GitHub issues (free GitHub account needed) and appear here after a moderation check. We never write or buy reviews, and reviews never change the editorial rank.</p></div></section>'
            f'<main>{latest}{"".join(secs)}</main>')
    return doc(head("AI tool reviews from real users | ToolRank", "Honest, moderated reviews of AI tools from users, developers and businesses. Leave a review to help others pick the right AI tool.", "/reviews.html", [ORG, SITE]), body)
SERVICES = [
    ("Free listing", "Free", "Get your AI tool listed in the right category after an editorial review.", "/submit.html", "Submit your tool"),
    ("Review Boost", "Free", "Invite your users to review you on ToolRank, and show an embeddable 'Rated on ToolRank' badge on your site.", "/services.html#badge", "Get the badge"),
    ("Verified badge", "US$2", "A verified mark on your listing once we confirm you own the tool.", None, None),
    ("Featured spot", "US$5/mo", "A clearly labelled Featured placement in your category. Editorial rank is unchanged.", None, None),
    ("Launch spotlight", "US$9/wk", "A week at the top of New this week, labelled as a spotlight.", None, None),
    ("Comparison page", "US$15", "A Tool vs Tool SEO page comparing your product with an alternative, written editorially.", None, None),
    ("Launch Kit", "US$19", "Listing, a newsletter mention and an X post from ToolRank for your launch.", None, None),
    ("AI Stack Audit", "US$29", "For teams: we recommend the best AI tools for your team's workflow.", None, None),
]
def services_cards(limit=None):
    out = []
    for name, price, desc, href, lbl in SERVICES[:limit]:
        free = price == "Free"
        btn = f'<a class="btn" href="{href}">{lbl}</a>' if free else '<button class="btn ghost" disabled>Coming soon</button>'
        out.append(f'<article class="card plan{" hl" if free else ""}"><h3>{E(name)}</h3><div class="price">{price}</div>'
                   f'<span class="tag">{"Free" if free else "Founding price"}</span><p>{E(desc)}</p>{btn}</article>')
    return "".join(out)
OFFER = '<p class="offer"><b>Launch offer:</b> free for the first 100 tools, including a featured placement. Paid options below are founding prices and are not on sale yet.</p>'
def services_page():
    snippet = E('<a href="https://toolrank.io/reviews.html#YOUR-TOOL"><img src="https://toolrank.io/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></a>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{head("Services for AI makers: listing, reviews, featured spots | ToolRank", "Free listing and Review Boost for AI tools, plus founding prices for verified badges, featured spots, launch spotlights, Launch Kit, AI Stack Audit and comparison pages.", "/services.html", [ORG, SITE])}<link rel="stylesheet" href="/assets/style.css"></head><body>
{NAV}<section class="hero"><h1>Services for AI makers</h1><p>Get found by the people choosing AI tools. Rankings stay editorial; every paid placement is labelled.</p>{OFFER}</section>
<main><section class="wrap"><div class="grid">{services_cards()}</div></section>
<section class="wrap" id="badge"><h2>Review Boost: the 'Rated on ToolRank' badge</h2><p class="muted">Free. Ask your users to review you, and link the badge to your reviews. Replace YOUR-TOOL with your tool's anchor from the <a href="/reviews.html">reviews page</a>.</p>
<p><img src="/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></p><pre class="code">{snippet}</pre>
<p><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a> <a class="btn ghost" href="/submit.html">Submit your tool</a></p></section></main>{FOOT}</body></html>
"""
def makers_html():
    return (f'<!--MAKERS--><section class="wrap"><h2>For Makers</h2><p class="muted">Built an AI tool? Get listed for free, collect reviews and reach people choosing tools.</p>{OFFER}'
            f'<div class="grid">{services_cards()}</div><p><a href="/services.html">All services and the Review Boost badge →</a> · <a href="/featured.html">Get featured</a></p></section><!--/MAKERS-->')

WORDMARK = ('<div class="wm" aria-hidden="true"><svg viewBox="0 0 1200 230" preserveAspectRatio="xMidYMid meet"><defs>'
  '<linearGradient id="wmg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1200" y2="0" spreadMethod="reflect">'
  '<stop offset="0" stop-color="#7c5cff"/><stop offset=".35" stop-color="#c04cf0"/><stop offset=".65" stop-color="#22d3ee"/><stop offset="1" stop-color="#7c5cff"/>'
  '<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="1200 0" dur="9s" repeatCount="indefinite"/></linearGradient>'
  '<linearGradient id="wmf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity=".25"/></linearGradient>'
  '<mask id="wmm"><rect width="1200" height="230" fill="url(#wmf)"/></mask></defs><g mask="url(#wmm)" font-family="Sora,Inter,sans-serif" font-weight="800" font-size="210" text-anchor="middle" letter-spacing="-6">'
  + "".join(f'<text class="wl" x="600" y="{188 - k*7}" fill="none" stroke="url(#wmg)" stroke-width="{1.6 if k else 2.4}" opacity="{1 - k*0.17:.2f}" textLength="1130" lengthAdjust="spacingAndGlyphs">TOOLRANK</text>' for k in range(5))
  + '</g></svg></div><script>(function(){var w=document.querySelector(".wm"),s=w&&w.querySelector("svg");if(!s)return;'
  'if(matchMedia("(prefers-reduced-motion: reduce)").matches){s.pauseAnimations&&s.pauseAnimations();return}'
  'var ls=s.querySelectorAll(".wl"),t=0;function f(){t=0;var r=w.getBoundingClientRect(),p=Math.max(-1,Math.min(1,(r.top-innerHeight)/innerHeight));'
  'ls.forEach(function(l,i){l.style.transform="translateY("+(p*i*14).toFixed(1)+"px)"})}addEventListener("scroll",function(){if(!t){t=1;requestAnimationFrame(f)}},{passive:true});f()})()</script>')
FOOT = FOOT_().replace("</div></footer>", "</div>" + WORDMARK + "</footer>")

def services_page():
    snippet = E('<a href="https://toolrank.io/reviews.html#YOUR-TOOL"><img src="https://toolrank.io/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></a>')
    body = (f'<section class="hero sub"><div class="wrap"><h1>Services for AI makers</h1><p class="lead">Get found by the people choosing AI tools. Rankings stay editorial; every paid placement is labelled.</p>{OFFER}</div></section>'
            f'<main><section class="sec"><div class="wrap"><div class="grid">{services_cards()}</div></div></section>'
            f'<section class="sec" id="badge"><div class="wrap"><h2>Review Boost: the \'Rated on ToolRank\' badge</h2><p class="muted">Free. Ask your users to review you, and link the badge to your reviews. Replace YOUR-TOOL with your tool\'s anchor from the <a href="/reviews.html">reviews page</a>.</p>'
            f'<p><img src="/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></p><pre class="code">{snippet}</pre>'
            f'<p><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a> <a class="btn ghost" href="/submit.html">Submit your tool</a></p></div></section></main>')
    return doc(head("Services for AI makers: listing, reviews, featured spots | ToolRank", "Free listing and Review Boost for AI tools, plus founding prices for verified badges, featured spots, launch spotlights, Launch Kit, AI Stack Audit and comparison pages.", "/services.html", [ORG, SITE]), body)
def makers_html():
    return (f'<section class="sec"><div class="wrap"><p class="eyebrow">For makers</p><h2 class="big">Built an AI tool? Get listed free.</h2><p class="muted">Collect reviews and reach people choosing tools.</p>{OFFER}'
            f'<div class="grid">{services_cards()}</div><p><a href="/services.html">All services and the Review Boost badge →</a> · <a href="/featured.html">Get featured</a></p></div></section>')

def trending_html():
    T = TR; hn = T.get("hn") or []
    def tl(name):
        s = slug(name); c = TOOLCAT.get(s); return (f"/best/{c}/#{s}" if c else None), TOOLS.get(s)
    big = []
    for i, x in enumerate(hn[:3]):
        page_, t = tl(x["tool"])
        visit = f'<a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(x["tool"])} →</a>' if t else ""
        big.append(f'<article class="fcard"><div class="fv"><img src="/assets/trend/v{i+1}.svg" alt="" width="800" height="450"></div>'
                   f'<div class="fb"><div class="fm">{logo_html(t, 40) if t else ""}<p class="eyebrow">#{i+1} on Hacker News · {x["points"]} pts · {x["stories"]} stor{"ies" if x["stories"] != 1 else "y"}</p></div>'
                   f'<h3>{f"<a href=\"{page_}\">{E(x["tool"])}</a>" if page_ else E(x["tool"])}</h3><p class="hl">&ldquo;{E(x["top_title"] or "")}&rdquo;</p>'
                   f'<div class="fa">{visit}<a class="hnl" href="{E(x["top_url"])}" target="_blank" rel="noopener nofollow">HN discussion ↗</a></div></div></article>')
    rows = []
    for i, x in enumerate(hn[3:], 4):
        page_, t = tl(x["tool"])
        rows.append(f'<li><span class="n">{i}</span>{logo_html(t, 28) if t else ""}<div class="ri"><a class="rn" href="{page_ or E(x["top_url"])}">{E(x["tool"])}</a><span class="muted small">{E(x["top_title"] or "")}</span></div>'
                    f'<span class="up">{x["points"]} pts</span><span class="ra">{f"<a class=\"go\" href=\"{E(link(t))}\" target=\"_blank\" rel=\"{rel(t)}\">Visit {E(x["tool"])} →</a>" if t else ""}<a class="hnl" href="{E(x["top_url"])}" target="_blank" rel="noopener nofollow">HN ↗</a></span></li>')
    if not hn: big = ['<p class="muted">No Hacker News stories linking to ranked tools in the last 7 days.</p>']
    extra = []
    if T.get("stars"):
        extra.append(("GitHub stars gained", [(x["tool"], x["url"], f'+{x["gained"]:,}★', TOOLS.get(slug(x["tool"]))) for x in T["stars"]]))
    if CL and CL.get("top"):
        extra.append(("Most clicked on ToolRank", [(x["tool"], None, f'{x["count"]:,} clicks', TOOLS.get(x["slug"])) for x in CL["top"]]))
    def xrows(items):
        out = []
        for i, (name, url, val, t) in enumerate(items, 1):
            page_, _ = tl(name); href = page_ or url or "/reviews.html"
            out.append(f'<li><span class="n">{i}</span>{logo_html(t, 28) if t else ""}<div class="ri"><a class="rn" href="{E(href)}">{E(name)}</a></div><span class="up">{E(val)}</span>'
                       f'<span class="ra">{f"<a class=\"go\" href=\"{E(link(t))}\" target=\"_blank\" rel=\"{rel(t)}\">Visit {E(name)} →</a>" if t else ""}</span></li>')
        return "".join(out)
    ex = "".join(f'<h3 class="subh">{E(h)}</h3><ol class="trows">{xrows(it)}</ol>' for h, it in extra)
    upd = f' Last update {E(T["fetched"])}.' if T.get("fetched") else ""
    return (f'<section class="sec" id="trending"><div class="wrap"><div class="sh"><p class="eyebrow">Trending this week</p><h2 class="big">What people are talking about.</h2>'
            f'<p class="muted">Real public signals, refreshed daily. Not paid, not editorial rank.{upd}</p></div><div class="fcards">{"".join(big)}</div>'
            + (f'<ol class="trows">{"".join(rows)}</ol>' if rows else "") + ex +
            '<p class="muted small how">How we rank: Hacker News buzz, GitHub stars gained and clicks on ToolRank over the last 7 days.</p></div></section>')

ACR = {"ai", "ui", "api", "cad", "llm", "mcp", "cli", "sdk", "gpt", "ml", "rag", "pdf", "ios", "3d", "tts", "ocr"}
def pretty_repo(r):
    ws = re.split(r"[-_.\s]+", r)
    return " ".join(w.upper() if w.lower() in ACR else (w.lower() if i and w.lower() in ("to", "of", "and", "for", "in", "on", "the", "a") else w[:1].upper() + w[1:]) for i, w in enumerate(ws) if w)

def new_html():
    its = sorted(N["items"], key=lambda n: n["date"], reverse=True)[:8]
    def one(n):
        m = re.match(r"^([\w.-]+)/([\w.-]+)$", n["title"].strip()) if n.get("type") == "github" else None
        title, sub = (pretty_repo(m.group(2)), f'<span class="own">by {E(m.group(1))} on GitHub</span>') if m else (n["title"], "")
        return (f'<article class="card nw"><span class="date">{E(n["date"])} · {E(n["type"])}</span><h3><a class="cl" href="{E(n["url"])}" target="_blank" rel="noopener">{E(title)}</a></h3>{sub}'
                f'<p>{E(n["summary"])}</p><span class="more" aria-hidden="true">Read more →</span></article>')
    return (f'<section class="sec" id="new"><div class="wrap"><div class="sh"><p class="eyebrow">New this week</p><h2 class="big">Fresh launches.</h2></div><div class="hs">'
            + "".join(one(n) for n in its) + '</div></div></section>')

def home(cats):
    tiles = "".join(tile(c) for c in cats)
    body = f"""<section class="hero home"><div class="wrap hw">
<div class="seg" role="tablist" aria-label="Audience"><span class="ind" aria-hidden="true"></span><button type="button" role="tab" data-tab="you" aria-selected="true">For You</button><button type="button" role="tab" data-tab="business" aria-selected="false">For Business</button><button type="button" role="tab" data-tab="makers" aria-selected="false">For Makers</button></div>
<h1>Confused by AI? <span class="gt">We&rsquo;ll find the right tool for you.</span></h1>
<p class="lead" id="tagline">Hand-picked, editorially ranked AI tools across {len(cats)} categories. No fluff.</p>
<form class="search" id="sf" role="search" action="/"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="q" name="q" type="search" enterkeyhint="search" placeholder="What do you want to do? e.g. edit video" aria-label="Search tools" autocomplete="off"><select id="price" aria-label="Pricing"><option value="">Any price</option><option value="free">Free tier</option><option value="paid">Paid</option></select><button type="submit" class="btn">Search</button></form>
{stats_html()}</div></section>
<div id="dirwrap" class="pane"><section class="sec" id="results" hidden aria-live="polite"><div class="wrap"><div class="sh row"><h2 id="rtitle">Results</h2><button type="button" class="btn ghost sm" id="rclear">Clear</button></div><div class="tgrid" id="rgrid"></div></div></section>
<section class="sec" id="browse"><div class="wrap"><div class="sh"><p class="eyebrow">Browse</p><h2 class="big">Start with what you want to do.</h2><p class="muted" id="tabnote">Tap a category to see the ranked tools.</p></div>
<div class="tiles" id="tiles">{tiles}</div></div></section>
{trending_html()}
{new_html()}
<section class="sec"><div class="wrap"><div class="cta big"><div><h2>Using AI tools? Leave a review.</h2><p>Help builders and businesses pick the right AI tool.</p></div><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></div></div></section></div>
<div id="makerspane" class="pane" hidden>{makers_html()}</div>
<script src="/assets/app.js"></script>"""
    ild = [ORG, SITE] + [{"@type": "ItemList", "name": "Best AI tools: " + c["title"], "url": f"{BASE}/best/{c['id']}/",
                           "itemListElement": [{"@type": "ListItem", "position": i, "name": t["name"], "url": t["url"]} for i, t in enumerate(c["tools"], 1)]} for c in cats]
    return doc(head("ToolRank: the best AI tools ranked by use case (" + UPD[:4] + ")",
                    f"Confused by AI? Editorial rankings of {NT} AI tools across {len(cats)} categories: " + ", ".join(c["title"] for c in cats) + f". Updated {UPD}.", "/", ild), body)

def patch(fn, block, extra=None):
    p = ROOT/fn; s = p.read_text()
    s = re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda m: block, s, flags=re.S)
    s = re.sub(r'<link rel="preconnect".*?display=swap">', "", s)
    s = re.sub(r'<header class="top">.*?</header>', lambda m: NAV, s, flags=re.S)
    s = re.sub(r'<footer.*?</footer>', lambda m: FOOT, s, flags=re.S)
    s = s.replace('<link rel="stylesheet" href="/assets/style.css', FONTS + '<link rel="stylesheet" href="/assets/style.css', 1)
    if extra: s = extra(s)
    p.write_text(s)

def main():
    cats = D["categories"]
    (ROOT/"assets/cat").mkdir(exist_ok=True); (ROOT/"assets/trend").mkdir(exist_ok=True)
    for c in cats: (ROOT/f"assets/cat/{c['id']}.svg").write_text(cat_art(c["id"]))
    for i in range(3): (ROOT/f"assets/trend/v{i+1}.svg").write_text(trend_art(i))
    for c in cats:
        d = ROOT/"best"/c["id"]; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(page(c))
    for o, n in REDIRECTS.items():
        d = ROOT/"best"/o; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(redirect_page(o, n))
    (ROOT/"reviews.html").write_text(reviews_page()); (ROOT/"services.html").write_text(services_page()); (ROOT/"index.html").write_text(home(cats))
    opts = "".join(f"<option>{E(c['title'])}</option>" for c in cats) + "<option>Other / new category</option>"
    def sub(s): return re.sub(r'(<select name="category"[^>]*>).*?(</select>)', lambda m: m.group(1) + opts + m.group(2), s, flags=re.S)
    patch("featured.html", head("Get your AI tool featured | ToolRank", "Featured placements and newsletter sponsorship on ToolRank. Featured spots are clearly labelled; rankings stay editorial.", "/featured.html", [ORG, SITE]))
    patch("submit.html", head("Submit your AI tool for free | ToolRank", "Submit your AI tool to ToolRank for free. Every submission gets an editorial review; approved tools are listed in the right category.", "/submit.html", [ORG, SITE]), sub)
    urls = ["/", "/reviews.html", "/services.html", "/submit.html", "/featured.html"] + [f"/best/{c['id']}/" for c in cats]
    (ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{UPD}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended"]
    (ROOT/"robots.txt").write_text("# ToolRank: search engines and AI crawlers are welcome.\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) +
                                   f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    L = [f"# ToolRank\n\n> Confused by AI? Editorial rankings of AI tools by use case. Last updated {UPD}. Rankings are editorial; featured placements are labelled. Launch offer: free for the first 100 tools (including featured placement); after that, free listing plus paid options at founding prices.\n\n## Categories\n"]
    L += [f"\nAudiences: 'For You' (consumer and creator tools) and 'For Business' (B2B and developer tools). {NT} tools ranked across {len(cats)} categories; {len(R)} approved user reviews.\n"]
    L += [f"- [{c['title']}]({BASE}/best/{c['id']}/): {c['blurb']} {len(c['tools'])} tools; #1: {c['tools'][0]['name']}." for c in cats]
    L += [f"\n## Optional\n\n- [Full rankings]({BASE}/llms-full.txt)\n- [Submit a tool (free)]({BASE}/submit.html)\n- [Get featured]({BASE}/featured.html)\n- [Services for makers]({BASE}/services.html): free listing and Review Boost; founding prices (coming soon): Verified badge US$2, Featured spot US$5/mo, Launch spotlight US$9/wk, Comparison page US$15, Launch Kit US$19, AI Stack Audit US$29.\n- [Reviews]({BASE}/reviews.html): {len(R)} moderated user review(s) collected so far; leave one via GitHub.\n"]
    (ROOT/"llms.txt").write_text("\n".join(L))
    F = [f"# ToolRank: full rankings\n\nLast updated {UPD}. Source: {BASE}/. Editorial ranking; position 1 = top pick. Pricing labels: free / freemium / paid (as listed; verify with vendor).\n"]
    for c in cats:
        F.append(f"\n## {c['title']}\n\n{c['blurb']}\nPage: {BASE}/best/{c['id']}/\n")
        F += [f"{i}. {t['name']} ({t['pricing']}; audience: {t.get('audience','')}){' [Featured]' if t.get('featured') else ''}{f' [user rating {rstat(t)[1]}/5 from {rstat(t)[0]} review(s)]' if rstat(t)[0] else ''}: {t['verdict']} {t['url']}" for i, t in enumerate(c["tools"], 1)]
    F.append(f"\n## New this week (as of {N['updated']})\n")
    F += [f"- {n['date']} {n['title']} ({n['type']}): {n['summary']} {n['url']}" for n in sorted(N["items"], key=lambda n: n["date"], reverse=True)]
    (ROOT/"llms-full.txt").write_text("\n".join(F) + "\n")
    GC = ('<!--GC--><script data-goatcounter="https://toolrank.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'
          '<script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a.go");if(!a||!/^Visit /.test(a.textContent)||!window.goatcounter||!goatcounter.count)return;'
          'var n=a.textContent.replace(/^Visit\\s+|\\s*\u2192\\s*$/g,"").trim(),s=n.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");'
          'goatcounter.count({path:"click/"+s,title:n,event:true})});</script><!--/GC-->')
    PRIV = '<!--PRIV--><p class="small muted">Privacy: cookieless, privacy-friendly analytics via <a href="https://www.goatcounter.com" rel="noopener" target="_blank">GoatCounter</a>. No cookies, no personal data, no tracking across sites.</p><!--/PRIV-->'
    import hashlib
    V = {a: hashlib.sha1((ROOT/"assets"/a).read_bytes()).hexdigest()[:8] for a in ("app.js", "style.css", "hero.js")}
    for h in ROOT.rglob("*.html"):
        if "shots" in h.parts or h.parent.name in REDIRECTS: continue
        s = h.read_text(); n = re.sub(r"<!--GC-->.*?<!--/GC-->", "", s, flags=re.S); n = re.sub(r"<!--PRIV-->.*?<!--/PRIV-->", "", n, flags=re.S)
        n = n.replace('<p class="muted small">©', PRIV + '<p class="muted small">©', 1).replace("</body>", GC + "</body>", 1)
        if 'class="hero' in n and "assets/hero.js" not in n: n = n.replace("</body>", '<script defer src="/assets/hero.js"></script></body>', 1)
        n = re.sub(r'(assets/(app\.js|style\.css|hero\.js))(\?v=[0-9a-f]+)?"', lambda m: f'{m.group(1)}?v={V[m.group(2)]}"', n)
        if n != s: h.write_text(n)
    print(f"cache-bust: app.js?v={V['app.js']} style.css?v={V['style.css']}")
    print(f"built {len(cats)} category pages + {len(REDIRECTS)} redirects, sitemap ({len(urls)} urls), robots, llms.txt, llms-full.txt")
if __name__ == "__main__": main()
