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
SAMEAS = []  # official ToolRank social/profile URLs; left empty until the owner provides handles
ORG_DESC = "ToolRank publishes editorial rankings and side-by-side comparisons of AI tools by use case, with pricing and limits checked against vendor pages."
ORG = {"@type": "Organization", "@id": BASE+"/#org", "name": "ToolRank", "url": BASE+"/", "description": ORG_DESC,
       "logo": {"@type": "ImageObject", "url": BASE+"/assets/icon-512.png", "width": 512, "height": 512},
       "publishingPrinciples": BASE+"/methodology/", "sameAs": SAMEAS}
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
LOGO_DIR = ROOT/"assets/logos"
def ensure_logos():
    """Cache each tool's favicon locally (assets/logos/<slug>.png) so pages never hotlink a third-party icon service.
    Fetched once per tool; Google's service answers unknown domains with a 404 + generic globe PNG, which we keep as the icon."""
    LOGO_DIR.mkdir(parents=True, exist_ok=True); got = 0
    for s, t in TOOLS.items():
        f = LOGO_DIR/f"{s}.png"
        if f.exists(): continue
        u = f"https://www.google.com/s2/favicons?domain={urllib.parse.quote(domain(t['url']))}&sz=64"
        try: b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read()
        except urllib.error.HTTPError as e: b = e.read()
        except Exception: continue
        if b[:8] != b"\x89PNG\r\n\x1a\n":  # some domains come back as JPEG/ICO: convert to PNG if Pillow is available
            try:
                import io
                from PIL import Image
                o = io.BytesIO(); Image.open(io.BytesIO(b)).convert("RGBA").save(o, "PNG"); b = o.getvalue()
            except Exception: continue
        f.write_bytes(b); got += 1
    return got
def logo_src(t): return f"/assets/logos/{slug(t['name'])}.png"
def logo_html(t, size=40):
    if not (LOGO_DIR/f"{slug(t['name'])}.png").exists():
        return f'<span class="lg" data-l="{E(t["name"][:1].upper())}" aria-hidden="true"></span>'
    return (f'<span class="lg" data-l="{E(t["name"][:1].upper())}" aria-hidden="true"><img src="{logo_src(t)}" '
            f'alt="" width="{size}" height="{size}" loading="lazy" decoding="async" onerror="this.remove()"></span>')
def tool_card(t, i, h="h3"):
    return (f'<article class="card tool" id="{slug(t["name"])}"><div class="th">{logo_html(t)}<div class="tt"><{h}><span class="rank">#{i}</span>{E(t["name"])}</{h}>'
            f'{"<span class=\"sipick\" title=\"ToolRank Super Intelligence pick: our top choice for this use case\">SI Pick</span>" if i == 1 else ""}'
            f'<div class="tm"><span class="tag {t["pricing"]}">{t["pricing"]}</span>{"<span class=\"tag feat\">Featured</span>" if t.get("featured") else ""}</div></div></div>'
            f'<p>{E(t["verdict"])}</p>{rv_line(t)}<a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t["name"])} →</a></article>')
def cards(c, h="h3"): return "".join(tool_card(t, i, h) for i, t in enumerate(c["tools"], 1))
def short(c): return c["title"]
def link(t): return t.get("affiliate_url") or t["url"]
def rel(t): return "noopener" + (" sponsored" if t.get("affiliate_url") else "")

# Self-hosted, subsetted fonts (latin + common punctuation), variable weight axis clipped to the weights we use.
FONT_SRC = {"inter": ("https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2", 400, 700),
            "sora": ("https://fonts.gstatic.com/s/sora/v17/xMQ9uFFYT72X5wkB_18qmnndmSdSnh2BAfO5mnuyOo1lfiQwV6-x.woff2", 600, 800)}
FONT_UNI = "U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,U+2013-2014,U+2018-201A,U+201C-201E,U+2022,U+2026,U+2032-2033,U+20AC,U+2122,U+2190-2193,U+2212"
def ensure_fonts():
    """Download + subset fonts into assets/fonts/ once (needs fontTools + brotli). Skips if files exist."""
    d = ROOT/"assets/fonts"; d.mkdir(parents=True, exist_ok=True)
    for name, (u, lo, hi) in FONT_SRC.items():
        out = d/f"{name}.woff2"
        if out.exists(): continue
        import io
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
        from fontTools import subset
        f = TTFont(io.BytesIO(urllib.request.urlopen(u, timeout=30).read()), lazy=False)
        if "fvar" in f:
            f = instancer.instantiateVariableFont(f, {"wght": (lo, hi)}); buf = io.BytesIO(); f.save(buf); buf.seek(0); f = TTFont(buf, lazy=False)
        opt = subset.Options(); opt.flavor = "woff2"; opt.layout_features = ["kern", "liga", "calt", "tnum"]; opt.name_IDs = ["*"]
        sb = subset.Subsetter(opt); sb.populate(unicodes=subset.parse_unicodes(FONT_UNI)); sb.subset(f)
        f.flavor = "woff2"; f.save(str(out))
FONTS = ('<!--FONTS--><link rel="preload" href="/assets/fonts/inter.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/assets/fonts/sora.woff2" as="font" type="font/woff2" crossorigin>'
         '<style>' + "".join(f'@font-face{{font-family:{fam};font-style:normal;font-weight:{lo} {hi};font-display:swap;src:url(/assets/fonts/{n}.woff2) format("woff2");unicode-range:{FONT_UNI}}}'
                             for n, fam, lo, hi in (("inter", "Inter", 400, 700), ("sora", "Sora", 600, 800))) + '</style><!--/FONTS-->')
MENU = [("/#browse", "Categories"), ("/#trending", "Trending"), ("/compare/", "Compare"), ("/methodology/", "How we rank"), ("/reviews.html", "Reviews"), ("/services.html", "For makers"), ("/submit.html", "Submit a tool")]
NAV = (f'<header class="top"><div class="bar">{LOGO}<nav aria-label="Main"><a href="/#browse">Categories</a><a href="/#trending">Trending</a>'
       f'<a href="/compare/">Compare</a><a href="/methodology/">How we rank</a><a href="/reviews.html">Reviews</a><a href="/services.html" class="hm">For makers</a><a class="btn sm" href="/submit.html">Submit a tool</a></nav>'
       '<div class="mnav"><a class="cpill" href="/compare/">Compare</a><button type="button" class="hb" aria-expanded="false" aria-controls="mmenu" aria-label="Open menu"><span></span><span></span><span></span></button></div></div>'
       '<nav id="mmenu" class="mmenu" aria-label="Mobile" hidden>' + "".join(f'<a href="{h}">{l}</a>' for h, l in MENU) + '</nav>'
       '<script>(function(){var b=document.querySelector(".hb"),m=document.getElementById("mmenu");if(!b)return;function s(o){b.setAttribute("aria-expanded",o);b.setAttribute("aria-label",o?"Close menu":"Open menu");m.hidden=!o;document.documentElement.classList.toggle("mopen",o)}'
       'b.onclick=function(){s(m.hidden)};m.addEventListener("click",function(e){if(e.target.closest("a"))s(false)});addEventListener("keydown",function(e){if(e.key==="Escape"&&!m.hidden){s(false);b.focus()}})})()</script></header>')
NL_URL = "https://toolrank.beehiiv.com/subscribe"
def NL(cls="", hid="nl"):
    return (f'<div class="nl {cls}"><div class="nlt"><h2 id="{hid}-h">Get the weekly ToolRank brief</h2><p>New AI tools, verified price changes and fresh comparisons. One email a week. Unsubscribe anytime.</p></div>'
            f'<div class="nlf"><a class="btn" href="{NL_URL}" target="_blank" rel="noopener" aria-describedby="{hid}-h">Subscribe free</a></div></div>')
def FOOT_():
    cl = "".join(f'<a href="/best/{c["id"]}/">{E(c["title"])}</a>' for c in D["categories"])
    return (f'<footer class="foot"><div class="wrap">{NL("nl-foot", "nlf")}<div class="fg"><div class="fl">{LOGO}<p class="muted">Confused by AI? We&rsquo;ll find the right tool for you. Editorial rankings, updated <time datetime="{UPD}">{UPD}</time>.</p></div>'
            f'<nav class="fc2" aria-label="Categories">{cl}</nav><nav class="fc2" aria-label="ToolRank"><a href="/about/">About</a><a href="/methodology/">How we rank</a><a href="/compare/">Compare tools</a><a href="/claim/">Claim your listing</a><a href="/reviews.html">Reviews</a><a href="/submit.html">Submit a tool</a><a href="/services.html">Services</a><a href="/featured.html">Get featured</a><a href="/llms.txt">llms.txt</a></nav></div>'
            f'<p class="si-tag small">ToolRank · Super Intelligence, ranked.</p><p class="muted small">© {UPD[:4]} ToolRank. Some links may become affiliate links; featured placements are labelled. Reviews are user-submitted via GitHub and moderated; they never change the editorial rank.</p></div></footer>')
FOOT = FOOT_()
def fit_title(*cands):
    """First candidate of 60 chars or fewer; else the last one cut at a word boundary."""
    for c in cands:
        if len(c) <= 60: return c
    c = cands[-1].removesuffix(" | ToolRank")
    return c if len(c) <= 60 else c[:59].rsplit(" ", 1)[0].rstrip(",:;&-") + "…"
def dot(x): x = (x or "").strip(); return x if not x or x[-1] in ".!?…" else x + "."
def fit_desc(*sents):
    """Join sentences in priority order, keeping the result within 70-160 chars."""
    out = ""
    for x in (dot(x) for x in sents if x):
        if len(x) > 160 and not out: x = x[:159].rsplit(" ", 1)[0].rstrip(",:;") + "…"
        c = (out + " " + x).strip()
        if len(c) <= 160: out = c
    if len(out) < 70: out = (out + " Editorial AI tool rankings with sources, by ToolRank.").strip()
    return out
def head(title, desc, path, ld, otype="website"):
    url = BASE + path; title = fit_title(title); desc = desc if 70 <= len(desc) <= 160 else fit_desc(desc)
    return f"""<!--SEO--><title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-snippet:-1"><meta name="theme-color" content="#0b1220"><meta name="color-scheme" content="dark">
<meta property="og:type" content="{otype}"><meta property="og:site_name" content="ToolRank"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE}/assets/og.png">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script><!--/SEO-->"""
def doc(headblock, body, extra_head=""):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n{headblock}{FONTS}'
            f'<link rel="stylesheet" href="/assets/style.css"><link rel="stylesheet" href="/assets/ev.css">{extra_head}</head><body>\n{NAV}\n{body}\n{FOOT}</body></html>\n')

APPCAT = {"ai-assistants": "UtilitiesApplication", "coding": "DeveloperApplication", "image": "DesignApplication", "video": "MultimediaApplication",
          "writing": "UtilitiesApplication", "voice-audio": "MultimediaApplication", "automation": "BusinessApplication", "research": "ReferenceApplication",
          "marketing": "BusinessApplication", "business": "BusinessApplication", "restaurants": "BusinessApplication", "hospitality": "BusinessApplication",
          "crypto": "FinanceApplication", "education": "EducationalApplication", "health": "HealthApplication", "gaming": "GameApplication"}
CUR = {"$": "USD", "€": "EUR", "£": "GBP"}
def offers_ld(t):
    """Offers from verified pricing_detail only (free tier and/or the starting paid price as listed by the vendor). Never ratings."""
    if not verified(t): return None
    p = PD(t); out = []; src = next((x["url"] for x in t.get("sources", [])), t["url"])
    if p.get("free_tier"): out.append({"@type": "Offer", "name": "Free plan", "price": "0", "priceCurrency": "USD", "description": p["free_tier"][:300], "url": src})
    m = re.search(r"(?<![A-Za-z])([$€£])\s?([0-9][0-9,]*(?:\.[0-9]+)?)", p.get("starting_price") or "")
    if m: out.append({"@type": "Offer", "name": "Starting paid plan", "price": m.group(2).replace(",", ""), "priceCurrency": CUR[m.group(1)], "description": p["starting_price"], "url": src})
    return out or None
def app_ld(t, c, desc):
    o = {"@type": "SoftwareApplication", "name": t["name"], "url": t["url"], "description": desc, "applicationCategory": APPCAT.get(c["id"], "UtilitiesApplication"), "applicationSubCategory": c["title"]}
    if t.get("platforms"): o["operatingSystem"] = ", ".join(t["platforms"])
    of = offers_ld(t)
    if of: o["offers"] = of if len(of) > 1 else of[0]
    return o
def tool_ld(t, c, i): return app_ld(t, c, t["verdict"])
def sp_txt(t): return PD(t).get("starting_price") if verified(t) else ""
def andl(xs): return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
def cat_summary(c):
    """Answer-first summary for a /best/ page: editorial rank + vendor-verified facts only."""
    ts = c["tools"]; t1 = ts[0]
    s = [f"Our top pick for {c['title']} is {t1['name']}: {dot(t1['verdict'])}"]
    if len(ts) > 2: s.append(f"Also ranked: #2 {ts[1]['name']} and #3 {ts[2]['name']}.")
    pr = [f"{t['name']} from {sp_txt(t)}" for t in ts[:3] if sp_txt(t)]
    if pr: s.append("Verified starting prices: " + "; ".join(pr) + ".")
    fr = [t["name"] for t in ts if verified(t) and PD(t).get("free_tier")]
    if fr: s.append(f"{andl(fr)} {'has' if len(fr) == 1 else 'have'} a free plan confirmed on the vendor's pricing page.")
    s.append(f"{len(ts)} tools ranked; updated {fmt_date(CHECK_DATE)}.")
    return " ".join(s)
def faqs(c):
    ts = c["tools"]; vf = [t["name"] for t in ts if verified(t) and PD(t).get("free_tier")]; vn = [t["name"] for t in ts if free_plan(t) == "no"]
    nv = sum(1 for t in ts if not verified(t))
    top = f"In ToolRank's editorial ranking (updated {UPD}), {ts[0]['name']} is ranked #1: {dot(ts[0]['verdict'])}" + (f" Paid plans start at {sp_txt(ts[0])} (vendor pricing page, checked {fmt_date(ts[0]['last_verified'])})." if sp_txt(ts[0]) else "")
    free_a = ((andl(vf) + (" has" if len(vf) == 1 else " have") + " a free plan confirmed on the vendor's pricing page." if vf else "None of the tools we have verified list a free plan.") +
              (" " + andl(vn) + " list no free plan." if vn else "") + (f" Pricing for the other {nv} tool{'s' if nv != 1 else ''} is not yet verified." if nv else "") + " Pricing changes often; check each vendor's site.")
    return [(f"What is the best AI tool for {c['title'].lower()} right now?", top),
            ("Which of these tools have a free plan?", free_a),
            ("How are these tools ranked?", "Rankings are editorial picks by ToolRank, ordered by position in the list. Featured placements are paid, clearly labelled and do not change the editorial rank."),
            ("When was this list last updated?", f"{UPD}.")]
def tile(c, cls="tile"):
    return (f'<a class="{cls}" href="/best/{c["id"]}/" data-cat="{c["id"]}"><img class="art" src="/assets/cat/{c["id"]}.svg" alt="" width="400" height="400" loading="lazy" decoding="async">'
            f'<span class="tn">{E(c["title"])}</span><span class="tc">{len(c["tools"])} tools</span></a>')
def page(c):
    path = f"/best/{c['id']}/"; fq = faqs(c)
    yr = UPD[:4]
    title = fit_title(f"{c['title']}: best AI tools ({yr}) | ToolRank", f"Best {c['title']} AI tools ({yr})", f"{c['title']} ({yr}) | ToolRank")
    desc = fit_desc(c["blurb"], "Top picks: " + ", ".join(f"#{i} {t['name']}" for i, t in enumerate(c["tools"][:3], 1)), f"Updated {fmt_date(CHECK_DATE)}")
    ld = [ORG, SITE, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "ToolRank", "item": BASE+"/"},
                                                                     {"@type": "ListItem", "position": 2, "name": c["title"], "item": BASE+path}]},
          {"@type": "ItemList", "name": "Best AI tools: " + c["title"], "description": c["blurb"], "url": BASE+path, "numberOfItems": len(c["tools"]),
           "itemListOrder": "https://schema.org/ItemListOrderAscending",
           "itemListElement": [{"@type": "ListItem", "position": i, "item": tool_ld(t, c, i)} for i, t in enumerate(c["tools"], 1)]},
          {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in fq]},
          {"@type": "WebPage", "@id": BASE+path, "url": BASE+path, "name": title, "dateModified": CHECK_DATE, "abstract": cat_summary(c), "publisher": {"@id": BASE+"/#org"}}]
    others = "".join(tile(o, "tile sm") for o in D["categories"] if o is not c)
    body = f"""<main><article><section class="hero cathero"><div class="wrap ch"><div><nav class="crumb" aria-label="Breadcrumb"><a href="/">ToolRank</a> › <a href="/#browse">Categories</a></nav>
<h1>{E(c['title'])}</h1><p class="lead">{E(c['blurb'])}</p><p class="muted small">{len(c['tools'])} tools · Editorial ranking</p><p class="updl">Updated {fmt_date(CHECK_DATE)} · Rankings are editorial, never paid. <a href="/methodology/">How we rank →</a></p></div>
<img class="chart" src="/assets/cat/{c['id']}.svg" alt="" width="400" height="400"></div></section>
<section class="sec ans"><div class="wrap"><div class="card pick"><h2>The short answer</h2><p>{E(cat_summary(c))}</p></div></div></section>
<section class="sec"><div class="wrap"><h2>The ranking</h2><div class="tgrid">{"".join(ev_card(t, i, c) for i, t in enumerate(c["tools"], 1))}</div></div></section>
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
    ("Verified badge", "US$2", "A verified mark on your listing once we confirm you own the tool.", "https://buy.stripe.com/3cI28r6zg9TE6x99bTbEA00", "Buy now"),
    ("Featured spot", "US$5/mo", "A clearly labelled Featured placement in your category. Editorial rank is unchanged.", "https://buy.stripe.com/9B600j3n40j49Jl73LbEA01", "Subscribe"),
    ("Launch spotlight", "US$9/wk", "A week at the top of New this week, labelled as a spotlight.", "https://buy.stripe.com/14A4gz4r83vgg7Jco5bEA02", "Book spotlight"),
    ("Comparison page", "US$15", "A Tool vs Tool SEO page comparing your product with an alternative, written editorially.", "https://buy.stripe.com/fZueVdf5M9TE08LfAhbEA03", "Buy now"),
    ("Launch Kit", "US$19", "Listing, a newsletter mention and an X post from ToolRank for your launch.", "https://buy.stripe.com/28E00j4r80j49Jl4VDbEA04", "Buy now"),
    ("AI Stack Audit", "US$29", "For teams: we recommend the best AI tools for your team's workflow.", "https://buy.stripe.com/14A5kD7Dk4zkcVx87PbEA05", "Buy now"),
]
def services_cards(limit=None):
    out = []
    for name, price, desc, href, lbl in SERVICES[:limit]:
        free = price == "Free"
        btn = f'<a class="btn" href="{href}">{lbl}</a>' if free else f'<a class="btn" href="{E(href)}" target="_blank" rel="noopener">{E(lbl)}</a>'
        out.append(f'<article class="card plan{" hl" if free else ""}"><h3>{E(name)}</h3><div class="price">{price}</div>'
                   f'<span class="tag">{"Free" if free else "Founding price"}</span><p>{E(desc)}</p>{btn}</article>')
    return "".join(out)
OFFER = '<p class="offer"><b>Launch offer:</b> free for the first 100 tools, including a featured placement. Paid options below are founding prices, available now with secure checkout by Stripe.</p>'
PAYNOTE = '<p class="muted small">Secure checkout by Stripe. After payment we confirm by email within 1 business day. Paid placements are always labelled and never change editorial rank.</p>'
def services_page():
    snippet = E('<a href="https://toolrank.io/reviews.html#YOUR-TOOL"><img src="https://toolrank.io/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></a>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{head("Services for AI makers: listing, reviews, featured spots | ToolRank", "Free listing and Review Boost for AI tools, plus founding prices for verified badges, featured spots, launch spotlights, Launch Kit, AI Stack Audit and comparison pages.", "/services.html", [ORG, SITE])}<link rel="stylesheet" href="/assets/style.css"></head><body>
{NAV}<section class="hero"><h1>Services for AI makers</h1><p>Get found by the people choosing AI tools. Rankings stay editorial; every paid placement is labelled.</p>{OFFER}</section>
<main><section class="wrap"><div class="grid">{services_cards()}</div>{PAYNOTE}</section>
<section class="wrap" id="badge"><h2>Review Boost: the 'Rated on ToolRank' badge</h2><p class="muted">Free. Ask your users to review you, and link the badge to your reviews. Replace YOUR-TOOL with your tool's anchor from the <a href="/reviews.html">reviews page</a>.</p>
<p><img src="/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></p><pre class="code">{snippet}</pre>
<p><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a> <a class="btn ghost" href="/submit.html">Submit your tool</a></p></section></main>{FOOT}</body></html>
"""
def makers_html():
    return (f'<!--MAKERS--><section class="wrap"><h2>For Makers</h2><p class="muted">Built an AI tool? Get listed for free, collect reviews and reach people choosing tools.</p>{OFFER}'
            f'<div class="grid">{services_cards()}</div>{PAYNOTE}<p><a href="/services.html">All services and the Review Boost badge →</a> · <a href="/featured.html">Get featured</a></p></section><!--/MAKERS-->')

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
            f'<main><section class="sec"><div class="wrap"><h2>Services and founding prices</h2><div class="grid">{services_cards()}</div>{PAYNOTE}</div></section>'
            f'<section class="sec" id="badge"><div class="wrap"><h2>Review Boost: the \'Rated on ToolRank\' badge</h2><p class="muted">Free. Ask your users to review you, and link the badge to your reviews. Replace YOUR-TOOL with your tool\'s anchor from the <a href="/reviews.html">reviews page</a>.</p>'
            f'<p><img src="/assets/badge.svg" alt="Rated on ToolRank" width="180" height="40"></p><pre class="code">{snippet}</pre>'
            f'<p><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a> <a class="btn ghost" href="/submit.html">Submit your tool</a></p></div></section></main>')
    return doc(head("Services for AI makers: listings & featured spots | ToolRank", "Free listing and Review Boost for AI tools, plus founding prices for verified badges, featured spots, launch spotlights and comparison pages.", "/services.html", [ORG, SITE]), body)
def makers_html():
    return (f'<section class="sec"><div class="wrap"><p class="eyebrow">For makers</p><h2 class="big">Built an AI tool? Get listed free.</h2><p class="muted">Collect reviews and reach people choosing tools.</p>{OFFER}'
            f'<div class="grid">{services_cards()}</div>{PAYNOTE}<p><a href="/services.html">All services and the Review Boost badge →</a> · <a href="/featured.html">Get featured</a></p></div></section>')

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

def FRESH():
    return '<p class="fresh"><span class="fl0">Fresh comparisons:</span>' + ''.join(f'<a class="chip" href="/compare/{k}/">{E(cmp_title(ids))}</a>' for k, ids in COMPARES[:6]) + '<a class="btn" href="/compare/">All comparisons →</a><a href="/methodology/">How we rank →</a></p>'
def home(cats):
    tiles = "".join(tile(c) for c in cats)
    body = f"""<main id="main"><section class="hero home"><div class="wrap hw">
<div class="seg" role="tablist" aria-label="Audience"><span class="ind" aria-hidden="true"></span><button type="button" role="tab" data-tab="you" aria-selected="true">For You</button><button type="button" role="tab" data-tab="business" aria-selected="false">For Business</button><button type="button" role="tab" data-tab="makers" aria-selected="false">For Makers</button></div>
<p class="si-eyebrow"><span>Super Intelligence, ranked.</span></p>
<h1>Confused by AI? <span class="gt">We&rsquo;ll find the right tool for you.</span></h1>
<p class="lead" id="tagline">Hand-picked, editorially ranked AI tools across {len(cats)} categories. No fluff.</p>
<form class="search" id="sf" role="search" action="/"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="q" name="q" type="search" enterkeyhint="search" placeholder="What do you want to do? e.g. edit video" aria-label="Search tools" autocomplete="off"><select id="price" aria-label="Pricing"><option value="">Any price</option><option value="free">Free tier</option><option value="paid">Paid</option></select><button type="submit" class="btn">Search</button></form>
{stats_html()}{FRESH()}</div></section>
<div id="dirwrap" class="pane"><section class="sec" id="results" hidden aria-live="polite"><div class="wrap"><div class="sh row"><h2 id="rtitle">Results</h2><button type="button" class="btn ghost sm" id="rclear">Clear</button></div><div class="tgrid" id="rgrid"></div></div></section>
<section class="sec" id="browse"><div class="wrap"><div class="sh"><p class="eyebrow">Browse</p><h2 class="big">Start with what you want to do.</h2><p class="muted" id="tabnote">Tap a category to see the ranked tools.</p></div>
<div class="tiles" id="tiles">{tiles}</div></div></section>
{trending_html()}
{new_html()}
<section class="sec"><div class="wrap"><div class="cta big"><div><h2>Using AI tools? Leave a review.</h2><p>Help builders and businesses pick the right AI tool.</p></div><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></div></div></section></div>
<div id="makerspane" class="pane" hidden>{makers_html()}</div>
<section class="sec"><div class="wrap">{NL("nl-home", "nlh")}</div></section>
</main><script src="/assets/app.js"></script>"""
    ild = [ORG, SITE] + [{"@type": "ItemList", "name": "Best AI tools: " + c["title"], "url": f"{BASE}/best/{c['id']}/",
                           "itemListElement": [{"@type": "ListItem", "position": i, "name": t["name"], "url": t["url"]} for i, t in enumerate(c["tools"], 1)]} for c in cats]
    return doc(head("ToolRank: the best AI tools ranked by use case (" + UPD[:4] + ")",
                    f"Confused by AI? Editorial rankings of {NT} AI tools across {len(cats)} categories, with pricing and limits checked against vendor pages. Updated {UPD}.", "/", ild), body)

# ================= Evidence layer (profiles, methodology, comparisons, claim) =================
CHECK_DATE = "2026-10-16"
def fmt_date(s):
    try: return dt.date.fromisoformat(s).strftime("%-d %b %Y")
    except Exception: return s or ""
NV = '<span class="nv">Not yet verified</span>'
ALLT = [(c, i, t) for c in D["categories"] for i, t in enumerate(c["tools"], 1)]
def PD(t): return t.get("pricing_detail") or {}
def verified(t): return bool(t.get("last_verified"))
def ev(x): return E(x) if x else NV
def free_plan(t):
    p = PD(t)
    if p.get("free_tier"): return "yes"
    if verified(t) and p.get("model") == "paid": return "no"
    return None
def free_trial(t):
    p = PD(t); s = (p.get("free_tier", "") + " " + p.get("notes", "")).lower()
    return "trial" in s
def yn(v): return {"yes": '<span class="yes">✓ Yes</span>', "no": '<span class="no">✕ No</span>'}.get(v, NV)
def price_num(s):
    m = re.search(r"[$€£]\s?([0-9][0-9,]*(?:\.[0-9]+)?)", s or "")
    return float(m.group(1).replace(",", "")) if m else None
def prof(t): return f"/tools/{slug(t['name'])}/"
def cmp_url(*ts, static=True):
    """Static /compare/<key>/ page when one exists for this exact set; otherwise the interactive ?tools= URL (made rel=nofollow at build end)."""
    ids = [slug(t["name"]) for t in ts]
    k = STATIC_CMP.get(frozenset(ids)) if static and len(ids) > 1 else None
    return f"/compare/{k}/" if k else "/compare/?tools=" + ",".join(ids)
CJ = json.loads((ROOT/"data/comparisons.json").read_text())["comparisons"]  # editorial comparison pages (pick + FAQ per page)
CMP = {c["key"]: c for c in CJ}
COMPARES = [(c["key"], c["ids"]) for c in CJ] + [(k, i) for k, i in (("lovable-vs-bolt-new", ["lovable", "bolt-new"]), ("make-vs-n8n-vs-zapier", ["make", "n8n", "zapier"])) if k not in CMP]
CTITLE = {tuple(c["ids"]): c["title"] for c in CJ}
STATIC_CMP = {frozenset(i): k for k, i in COMPARES}
def cmp_title(ids): return CTITLE.get(tuple(ids)) or " vs ".join(TOOLS[i]["name"] for i in ids)
METH_LINK = '<a href="/methodology/">How we rank →</a>'
DISCLOSE = '<p class="muted small disc">Some links may be affiliate links. They never affect rank.</p>'

def ev_card(t, i, c):
    """Ranking-page card with the evidence summary."""
    p = PD(t); s = slug(t["name"]); v = verified(t)
    sp = E(p["starting_price"]) if p.get("starting_price") else (("Free" if p.get("model") == "free" else NV) if v else NV)
    rows = (f'<dl class="evd"><dt>Why ranked</dt><dd>{ev(t.get("why_rank"))}</dd>'
            f'<dt>Starts at</dt><dd>{sp}{f" · <span class=\"tag {E(p.get("model",""))}\">{E(p.get("model",""))}</span>" if p.get("model") else ""}</dd>'
            f'<dt>Free plan</dt><dd>{yn(free_plan(t))}</dd><dt>Best for</dt><dd>{ev(t.get("best_for"))}</dd><dt>Avoid if</dt><dd>{ev(t.get("avoid_if"))}</dd>'
            f'<dt>Verified</dt><dd>{E(fmt_date(t["last_verified"])) if v else NV}</dd></dl>')
    return (f'<article class="card tool" id="{s}"><div class="th">{logo_html(t)}<div class="tt"><h3><span class="rank">#{i}</span><a class="tl" href="{prof(t)}">{E(t["name"])}</a></h3>'
            f'{"<span class=\"sipick\" title=\"ToolRank Super Intelligence pick: our top choice for this use case\">SI Pick</span>" if i == 1 else ""}'
            f'<div class="tm"><span class="tag {t["pricing"]}">{t["pricing"]}</span>{"<span class=\"tag feat\">Featured</span>" if t.get("featured") else ""}</div></div></div>'
            f'<p>{E(t["verdict"])}</p>{rows if i <= 5 else ""}{rv_line(t)}'
            f'<div class="acts"><a href="{prof(t)}">Profile</a><a href="{E(cmp_url(t))}">Compare</a><a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t["name"])} →</a></div></article>')

def pricing_table(t):
    p = PD(t)
    if not p.get("tiers") and not p.get("free_tier") and not p.get("starting_price"):
        return f'<p>{NV}. We haven&rsquo;t confirmed this tool&rsquo;s pricing against the vendor&rsquo;s own page yet, so we show nothing rather than guess.</p>'
    rows = f'<tr><th scope="row">Pricing model</th><td>{ev(p.get("model"))}</td></tr><tr><th scope="row">Starting price</th><td>{ev(p.get("starting_price"))}</td></tr>'
    rows += f'<tr><th scope="row">Free tier</th><td>{ev(p.get("free_tier")) if p.get("free_tier") or not verified(t) else ("None listed" if p.get("model")=="paid" else NV)}</td></tr>'
    tiers = "".join(f'<tr><td>{E(x["name"])}</td><td>{E(x["price"])}</td><td>{E(x.get("notes",""))}</td></tr>' for x in p.get("tiers", []))
    return (f'<div class="tbl"><table><tbody>{rows}</tbody></table></div>' +
            (f'<div class="tbl"><table><thead><tr><th>Plan</th><th>Price</th><th>Includes</th></tr></thead><tbody>{tiers}</tbody></table></div>' if tiers else "") +
            (f'<p class="muted small">Notes: {E(p["notes"])}</p>' if p.get("notes") else "") +
            f'<p class="muted small">Prices as shown on the vendor&rsquo;s pricing page on {fmt_date(t.get("last_verified"))}, USD unless stated. Vendors change prices; check before you buy.</p>')

def profile_page(c, i, t):
    s = slug(t["name"]); path = prof(t); v = verified(t); p = PD(t)
    srcs = "".join(f'<li><a href="{E(x["url"])}" target="_blank" rel="noopener nofollow">{E(x["label"])}</a> <span class="muted small">checked {fmt_date(x["checked"])}</span></li>' for x in t.get("sources", []))
    srcs = f'<ul class="srcs">{srcs}</ul>' if srcs else f'<p>{NV}. No vendor sources recorded yet.</p>'
    plats = t.get("platforms") or []; ints = t.get("integrations") or []
    chips = lambda xs: "".join(f'<span class="chip">{E(x)}</span>' for x in xs) if xs else NV
    rel_c = [(k, ids) for k, ids in COMPARES if s in ids][:8]
    peers = [x for x in c["tools"][:4] if x is not t and not any(slug(x["name"]) in ids for _, ids in rel_c)][:3]
    relh = "".join(f'<li><a href="/compare/{k}/">{E(cmp_title(ids))}</a></li>' for k, ids in rel_c) + "".join(f'<li><a href="{E(cmp_url(t, x))}">{E(t["name"])} vs {E(x["name"])}</a> <span class="muted small">(interactive)</span></li>' for x in peers)
    rs = [r for r in RB.get(s, []) if r["listed"]]; n, a = rstat(t)
    revs = (f'<div class="grid">{"".join(review_html(r) for r in rs)}</div>' if rs else '<p class="muted">No reviews yet.</p>') + \
           f'<p><a class="btn ghost" href="{E(review_url(t["name"]))}" target="_blank" rel="noopener">{"Write a review" if n else "Be the first to review"}</a></p>'
    claim = f"https://github.com/{REPO}/issues/new?template=claim-listing.yml&tool=" + urllib.parse.quote(t["name"])
    o = app_ld(t, c, t.get("why_rank") or t["verdict"])
    summ = tool_summary(c, i, t); fq = tool_faqs(c, i, t)
    ld = [ORG, SITE, o, {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in fq]}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "ToolRank", "item": BASE+"/"},
          {"@type": "ListItem", "position": 2, "name": c["title"], "item": f"{BASE}/best/{c['id']}/"}, {"@type": "ListItem", "position": 3, "name": t["name"], "item": BASE+path}]}]
    body = f"""<main class="prof"><section class="hero sub phero"><div class="wrap"><nav class="crumb" aria-label="Breadcrumb"><a href="/">ToolRank</a> › <a href="/best/{c['id']}/">{E(c['title'])}</a></nav>
<div class="pt">{logo_html(t, 56)}<div><h1>{E(t['name'])}</h1><p class="lead">{E(t.get('job') or t['verdict'])}</p></div></div>
<p class="pmeta"><span class="rankpill">#{i} in {E(c['title'])}</span>{'<span class="sipick">SI Pick</span>' if i == 1 else ''}<span class="tag {t['pricing']}">{t['pricing']}</span><span class="muted small">Last verified: {E(fmt_date(t['last_verified'])) if v else NV}</span></p>
<p class="pacts"><a class="btn" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t['name'])} site →</a> <a class="btn ghost" href="{E(cmp_url(t))}">Compare</a></p>{DISCLOSE}</div></section>
<div class="wrap pgrid"><div>
<section class="psec ans"><div class="card pick"><h2>The short answer</h2><p>{E(summ)}</p></div></section>
<section class="psec"><h2>Why it&rsquo;s ranked here</h2><p>{ev(t.get('why_rank'))}</p><p class="muted small">Editorial verdict: {E(t['verdict'])} {METH_LINK}</p></section>
<section class="psec warn"><h2>Main limitation</h2><p>{ev(t.get('main_limitation'))}</p></section>
<section class="psec"><h2>Pricing</h2>{pricing_table(t)}</section>
<section class="psec bf"><div><h2>Best for</h2><p>{ev(t.get('best_for'))}</p></div><div><h2>Avoid if</h2><p>{ev(t.get('avoid_if'))}</p></div></section>
<section class="psec"><h2>Platforms &amp; integrations</h2><p class="muted small">Platforms</p><div class="chips">{chips(plats)}</div><p class="muted small">Integrations</p><div class="chips">{chips(ints)}</div>
<p class="muted small">Model / provider: {ev(t.get('model_provider'))}</p></section>
<section class="psec"><h2>Evidence &amp; sources</h2>{srcs}<p class="muted small">Every fact on this page comes from the sources above. Anything we could not confirm says &ldquo;Not yet verified&rdquo;.</p></section>
<section class="psec faq" id="faq"><h2>FAQ</h2>{''.join(f'<details><summary><h3>{E(q)}</h3></summary><p>{E(a)}</p></details>' for q, a in fq)}</section>
<section class="psec" id="reviews"><h2>Reviews</h2>{revs}</section></div>
<aside class="pside"><div class="card"><h3>Quick facts</h3><dl class="evd"><dt>Starts at</dt><dd>{ev(p.get('starting_price'))}</dd><dt>Free plan</dt><dd>{yn(free_plan(t))}</dd><dt>Verified</dt><dd>{E(fmt_date(t['last_verified'])) if v else NV}</dd></dl>
<a class="btn" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit site →</a>{DISCLOSE}</div>
<div class="card"><h3>Related comparisons</h3><ul class="rlist">{relh}</ul></div>
<div class="card"><h3>Is this your tool?</h3><p>Correct facts, add a demo or pricing link. Free.</p><a href="{E(claim)}" target="_blank" rel="noopener">Claim it free →</a> <a class="muted small" href="/claim/">How claiming works</a></div>{NL("nl-compact", "nlc")}</aside></div></main>"""
    yr = UPD[:4]; nm = t["name"]
    title = (fit_title(f"{nm} review: pricing & limitations ({yr}) | ToolRank", f"{nm} review, pricing & limits ({yr}) | ToolRank", f"{nm}: pricing & review ({yr}) | ToolRank", f"{nm} review ({yr}) | ToolRank")
             if v else fit_title(f"{nm} review & ranking ({yr}) | ToolRank", f"{nm} ({yr}) | ToolRank"))
    desc = fit_desc(t.get("why_rank") or t["verdict"], f"Starts at {p['starting_price']}" if v and p.get("starting_price") else "", f"Ranked #{i} in {c['title']} on ToolRank")
    return doc(head(title, desc, path, ld, "article"), body)

def tool_summary(c, i, t):
    """Answer-first summary: editorial rank + verdict, then vendor-verified facts only."""
    v = verified(t); p = PD(t); nm = t["name"]
    s = [f"{nm} is ranked #{i} of {len(c['tools'])} in {c['title']} on ToolRank.", dot(t.get("why_rank") or t["verdict"])]
    if v:
        if p.get("starting_price"): s.append(f"Paid plans start at {p['starting_price']}.")
        if p.get("free_tier"): s.append(f"Free plan: {dot(p['free_tier'])}")
        elif free_plan(t) == "no": s.append("No free plan is listed.")
        if t.get("best_for"): s.append(f"Best for: {dot(t['best_for'])}")
        if t.get("main_limitation"): s.append(f"Main limitation: {dot(t['main_limitation'])}")
        s.append(f"Facts checked against vendor pages on {fmt_date(t['last_verified'])}.")
    else: s.append(f"Pricing and limits for {nm} are not yet verified against the vendor's own pages.")
    return " ".join(s)
def tool_faqs(c, i, t):
    v = verified(t); p = PD(t); nm = t["name"]; d = fmt_date(t.get("last_verified")); out = []
    if v:
        sp = p.get("starting_price")
        if p.get("free_tier"): out.append((f"Is {nm} free?", f"Yes. {nm}'s pricing page lists a free plan: {dot(p['free_tier'])} Checked {d}."))
        elif free_plan(t) == "no": out.append((f"Is {nm} free?", f"No free plan is listed on {nm}'s pricing page (checked {d})." + (f" Paid plans start at {sp}." if sp else "")))
        tiers = [f"{x['name']} ({x['price']})" for x in p.get("tiers", []) if re.search(r"[0-9]", x.get("price", ""))]
        if sp or tiers: out.append((f"How much does {nm} cost?", (f"Paid plans start at {sp}. " if sp else "") + (f"Plans listed: {'; '.join(tiers)}. " if tiers else "") + f"Prices as shown on the vendor's pricing page on {d}; they can change."))
        if t.get("best_for"): out.append((f"What is {nm} best for?", dot(t["best_for"]) + (f" Avoid it if: {dot(t['avoid_if'][:1].lower() + t['avoid_if'][1:])}" if t.get("avoid_if") else "")))
        if t.get("main_limitation"): out.append((f"What is the main limitation of {nm}?", dot(t["main_limitation"])))
        if t.get("platforms"): out.append((f"Which platforms does {nm} run on?", f"{andl(t['platforms'])}, per the vendor's pages (checked {d})."))
    out.append((f"How does ToolRank rank {nm}?", f"{nm} is #{i} of {len(c['tools'])} in {c['title']}. Rankings are editorial: capability and reliability weigh more than popularity, and paid placements never change rank."))
    return out

def methodology_page():
    body = f"""<main><section class="hero sub"><div class="wrap"><h1>How we rank</h1><p class="lead">Rankings on ToolRank are editorial. They are not votes, and they are never paid for.</p></div></section>
<section class="sec"><div class="wrap prose">
<h2>What we look at</h2><p>For every category we ask one question: which tool does the core job best for most people? We weigh:</p>
<ol><li><b>Capability on the core job.</b> Does it actually do the thing the category is about, and do it well?</li><li><b>Reliability.</b> Does it work consistently, without surprises?</li><li><b>Pricing and value.</b> What does it cost to get real use out of it, and is there a usable free tier?</li><li><b>Speed of improvement.</b> Is the product shipping meaningful updates?</li><li><b>Docs and support.</b> Can you get unstuck?</li><li><b>Known limitations.</b> Every tool has one. We name the main one on its profile.</li></ol>
<p><b>Capability and reliability are weighted higher than popularity.</b> A famous tool can rank below a smaller one that does the job better.</p>
<h2>Money never changes rank</h2><p>Sponsored or featured placements never affect rank, and they are always labelled. Some outbound links may become affiliate links; they never affect rank either. User reviews are shown alongside rankings but don&rsquo;t move them.</p>
<h2>Evidence, not guesses</h2><p>Pricing, free tier limits, platforms, integrations and limitations come from the vendor&rsquo;s own pricing and docs pages. Each profile lists its sources and the date we checked them. If we can&rsquo;t confirm a fact, we show &ldquo;Not yet verified&rdquo; instead of guessing.</p>
<h2>How often we re-check</h2><p>We re-check the top five tools in every category at least monthly, and any tool when a vendor or reader reports a change. The &ldquo;Last verified&rdquo; date on each profile tells you when we last looked.</p>
<h2>Vendors: correcting facts</h2><p>If something about your tool is wrong or out of date, <a href="/claim/">claim your listing</a> (free) and send the correction with a link to your pricing or docs page. We verify and update; corrections never buy a higher rank.</p>
<p class="muted small">Last updated {fmt_date(CHECK_DATE)}.</p></div></section></main>"""
    return doc(head("How ToolRank ranks AI tools: methodology | ToolRank", "Editorial, evidence-based rankings: capability and reliability over popularity, sources and check dates on every profile, sponsorships never affect rank.", "/methodology/", [ORG, SITE]), body)

def about_page():
    nv = sum(1 for _, _, t in ALLT if verified(t))
    body = f"""<main><section class="hero sub"><div class="wrap"><h1>About ToolRank</h1><p class="lead">{E(ORG_DESC)}</p></div></section>
<section class="sec"><div class="wrap prose">
<h2>What ToolRank is</h2><p>ToolRank is an independent directory of AI tools. Each category page ranks tools for one job, such as coding, image generation or customer support, so you can see which tool we think does that job best and why.</p>
<h2>What we cover</h2><p>As of {fmt_date(CHECK_DATE)}, ToolRank ranks {NT} tools across {len(D['categories'])} categories and publishes {len(COMPARES)} head-to-head comparison pages. {nv} tool profiles have pricing, free-tier limits and platforms checked against the vendor&rsquo;s own pages, with sources and the check date listed on each profile. Profiles we have not checked yet say &ldquo;Not yet verified&rdquo; instead of guessing.</p>
<h2>How rankings work</h2><p>Rankings are editorial. Capability and reliability on the core job weigh more than popularity. The full criteria are on <a href="/methodology/">How we rank</a>.</p>
<h2>How ToolRank is funded</h2><p>Listing is free. Makers can buy clearly labelled placements and services, listed with prices on the <a href="/services.html">services page</a>. Some outbound links may become affiliate links. Paid placements and affiliate links never change a tool&rsquo;s rank.</p>
<h2>Reviews and corrections</h2><p>User reviews are submitted through public GitHub issues and moderated before they appear. They are shown next to rankings but do not move them. Vendors can <a href="/claim/">claim a listing</a> for free to correct facts, with a link to their own pricing or docs page.</p>
<h2>Contact</h2><p>The fastest way to reach us is a <a href="https://github.com/{REPO}/issues/new" target="_blank" rel="noopener">GitHub issue</a>. To suggest a tool, use <a href="/submit.html">Submit a tool</a>.</p>
<p class="muted small">Last updated {fmt_date(CHECK_DATE)}.</p></div></section></main>"""
    ld = [ORG, SITE, {"@type": "AboutPage", "url": BASE+"/about/", "name": "About ToolRank", "dateModified": CHECK_DATE, "about": {"@id": BASE+"/#org"}, "mainEntity": {"@id": BASE+"/#org"}}]
    return doc(head("About ToolRank: independent AI tool rankings", "What ToolRank is, what it covers, how rankings work, how the site is funded and how to send corrections or reviews.", "/about/", ld), body)

def claim_page():
    url = f"https://github.com/{REPO}/issues/new?template=claim-listing.yml"
    body = f"""<main><section class="hero sub"><div class="wrap"><h1>Claim your listing</h1><p class="lead">Free for every tool on ToolRank.</p><p><a class="btn" href="{url}" target="_blank" rel="noopener">Claim your listing on GitHub →</a></p></div></section>
<section class="sec"><div class="wrap prose"><h2>What claiming lets you do</h2><ul><li>Correct facts on your profile: pricing, free tier limits, platforms, integrations.</li><li>Add a demo link and a link to your official pricing page.</li><li>Tell us when something changes so we re-verify sooner.</li></ul>
<h2>How it works</h2><ol><li>Open the claim form (a public GitHub issue, free GitHub account needed).</li><li>Tell us the tool, your role and your work email domain so we can confirm you work there.</li><li>Add corrections with links to your own pricing or docs pages. We check every fact against those pages before publishing.</li></ol>
<p>Claiming is free and never changes your rank. See <a href="/methodology/">how we rank</a>.</p><p class="muted">Vendor Pro analytics coming soon.</p></div></section></main>"""
    return doc(head("Claim your AI tool listing (free) | ToolRank", "Vendors can claim their ToolRank listing for free to correct facts and add demo and pricing links. Claiming never changes rank.", "/claim/", [ORG, SITE]), body)

PICK = {
 "cursor-vs-claude-code": "Pick <b>Cursor</b> if you want an AI-first editor: a desktop app with agents, cloud automations and code review, and a free tier to try it. Pick <b>Claude Code</b> if you live in the terminal and want an agent that works across your repo; it has no free tier of its own and comes with a paid Claude plan (Pro from $17/month billed annually). Many developers use both: Cursor for editing, Claude Code for long agentic tasks.",
 "lovable-vs-bolt-new": "Pick <b>Lovable</b> if you want to describe an app in plain language and get a hosted web app with Lovable Cloud; its free plan gives 5 build credits a day. Pick <b>Bolt.new</b> if you want a bigger free allowance measured in tokens (300K a day, 1M a month) and clear pricing from $25/month. Both are browser-based; neither needs you to install anything.",
 "make-vs-n8n-vs-zapier": "Pick <b>Zapier</b> if you want the easiest setup and the biggest app catalogue; the free plan gives 100 tasks a month. Pick <b>Make</b> if you like building visual, branching scenarios; its free plan gives 1,000 credits a month. Pick <b>n8n</b> if you're technical, want unlimited steps per execution or the option to self-host; cloud plans start at €20/month billed annually.",
}
def cmp_page(key, ids):
    ts = [TOOLS[i] for i in ids]; title = cmp_title(ids); path = f"/compare/{key}/"
    cols = len(ts); hdr = "".join(f'<th scope="col" class="c{k}"><a href="{prof(t)}">{E(t["name"])}</a></th>' for k, t in enumerate(ts))
    def row(lbl, f): return f'<tr><th scope="row">{lbl}</th>' + "".join(f"<td>{f(t)}</td>" for t in ts) + "</tr>"
    feats = lambda t: "<ul>" + "".join(f'<li>{E(x["name"])}: {E(x.get("notes") or x["price"])}</li>' for x in PD(t).get("tiers", [])[:3]) + "</ul>" if PD(t).get("tiers") else NV
    tbl = (f'<div class="tbl mx"><table class="cmp"><thead><tr><th></th>{hdr}</tr></thead><tbody>' + row("Starting price", lambda t: ev(PD(t).get("starting_price"))) +
           row("Pricing model", lambda t: ev(PD(t).get("model"))) + row("Free tier", lambda t: E(PD(t)["free_tier"]) if PD(t).get("free_tier") else ('<span class="no">✕ None listed</span>' if free_plan(t) == "no" else NV)) + row("Best for", lambda t: ev(t.get("best_for"))) +
           row("Main limitation", lambda t: ev(t.get("main_limitation"))) + row("Key plans &amp; features", feats) +
           row("Platforms", lambda t: E(", ".join(t.get("platforms") or [])) or NV) + row("Integrations", lambda t: E(", ".join(t.get("integrations") or [])) or NV) + row("Model / provider", lambda t: ev(t.get("model_provider"))) +
           row("Last checked", lambda t: E(fmt_date(t.get("last_verified"))) if verified(t) else NV) + row("", lambda t: f'<a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t["name"])} →</a>') + '</tbody></table></div>')
    nums = [(t, price_num(PD(t).get("starting_price"))) for t in ts]; mx = max([n for _, n in nums if n] or [1])
    bars = "".join(f'<div class="pbar"><span class="bl">{E(t["name"])}</span><span class="bt"><i class="c{k}" style="width:{max(4, n / mx * 100):.0f}%"></i></span><span class="bv">{E(PD(t)["starting_price"])}</span></div>' if n else
                   f'<div class="pbar"><span class="bl">{E(t["name"])}</span><span class="bt"></span><span class="bv">{NV}</span></div>' for k, (t, n) in enumerate(nums))
    srcs = "".join(f'<li>{E(t["name"])}: <a href="{E(x["url"])}" target="_blank" rel="noopener nofollow">{E(x["label"])}</a> <span class="muted small">checked {fmt_date(x["checked"])}</span></li>' for t in ts for x in t.get("sources", []))
    cj = CMP.get(key, {}); faq = cj.get("faq", [])
    ld = [ORG, SITE, {"@type": "WebPage", "name": title, "url": BASE+path, "dateModified": CHECK_DATE, "about": [{"@type": "SoftwareApplication", "name": t["name"], "url": t["url"]} for t in ts]},
          {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "ToolRank", "item": BASE+"/"}, {"@type": "ListItem", "position": 2, "name": "Compare", "item": BASE+"/compare/"}, {"@type": "ListItem", "position": 3, "name": title, "item": BASE+path}]}]
    if faq: ld.append({"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    faqh = ('<h2 id="faq">FAQ</h2><div class="faq">' + "".join(f'<details class="card"><summary><b>{E(q)}</b></summary><p>{E(a)}</p></details>' for q, a in faq) + '</div>') if faq else ""
    relc = [(k, i) for k, i in COMPARES if k != key and set(i) & set(ids)]
    relc = sorted(relc, key=lambda x: -len(set(x[1]) & set(ids)))[:8]
    relh = ('<h2>Related comparisons</h2><ul class="rlist">' + "".join(f'<li><a href="/compare/{k}/">{E(cmp_title(i))}</a></li>' for k, i in relc) + '<li><a href="/compare/">All comparisons →</a></li></ul>')
    profs = " · ".join(f'<a href="{prof(t)}">{E(t["name"])} profile</a>' for t in ts)
    body = f"""<main><section class="hero sub"><div class="wrap"><nav class="crumb" aria-label="Breadcrumb"><a href="/">ToolRank</a> › <a href="/compare/">Compare</a></nav><h1>{E(title)}</h1>
<p class="muted small">Updated {fmt_date(CHECK_DATE)} · Facts from vendor pages · {METH_LINK}</p></div></section>
<section class="sec"><div class="wrap"><div class="card pick"><h2>Who should pick which</h2><p>{cj["pick"] if cj else PICK[key]}</p></div>
<h2>Side by side</h2>{tbl}<p class="muted small">Prices as listed by each vendor on the check date, before tax. Plans and limits change; follow the sources below.</p>
<h2>Starting price</h2><div class="bars">{bars}</div><p class="muted small">Lowest paid plan shown on each vendor&rsquo;s pricing page, checked {fmt_date(CHECK_DATE)}. Currencies as listed.</p>
<p><a class="btn ghost" href="{E(cmp_url(*ts, static=False))}">Open in the interactive comparer →</a></p><p class="small">Full profiles: {profs}</p>
{faqh}
<h2>Sources</h2><ul class="srcs">{srcs}</ul>{relh}{DISCLOSE}{NL("nl-compact", "nlc")}</div></section></main>"""
    yr = UPD[:4]; ht = fit_title(f"{title} ({yr}): which to pick | ToolRank", f"{title} ({yr}) | ToolRank", f"{title}: which to pick ({yr})", f"{title} | ToolRank")
    desc = f"{title} compared from vendor pages checked {fmt_date(CHECK_DATE)}: pricing, free tiers, limits, platforms and who should pick which."
    return doc(head(ht, desc, path, ld), body)

def compare_ui_page():
    cats = "".join(f'<option value="{c["id"]}">{E(c["title"])}</option>' for c in D["categories"])
    presets = "".join(f'<a class="chip" href="/compare/{k}/">{E(cmp_title(ids))}</a>' for k, ids in COMPARES[:6]) + '<a class="chip" href="#all">All comparisons ↓</a>'
    groups = {}
    for k, ids in COMPARES: groups.setdefault(TOOLS[ids[0]]["name"], []).append((k, ids))
    hub = "".join(f'<div class="card"><h3>{E(g)}</h3><ul class="rlist">' + "".join(f'<li><a href="/compare/{k}/">{E(cmp_title(ids))}</a></li>' for k, ids in xs) + '</ul></div>' for g, xs in groups.items())
    hub = f'<section class="sec" id="all"><div class="wrap"><h2>All comparisons ({len(COMPARES)})</h2><p class="muted">Head-to-head pages with pricing checked against vendor pages, who-should-pick-which advice and FAQs.</p><div class="grid">{hub}</div></div></section>'
    body = f"""<main class="cmpui"><section class="hero sub"><div class="wrap"><h1>Compare AI tools</h1><p class="lead">Pick up to 4 tools. Every fact comes from vendor pages; gaps say &ldquo;Not yet verified&rdquo;.</p><div class="chips">{presets}<a class="chip" href="/methodology/">How we rank →</a></div></div></section>
<div class="wrap cwrap"><aside class="cside" aria-label="Filters"><h2 class="sh3">Filters</h2>
<label>Category<select id="fcat"><option value="">All categories</option>{cats}</select></label>
<label class="ck"><input type="checkbox" id="ffree"> Free plan</label><label class="ck"><input type="checkbox" id="ftrial"> Free trial</label>
<label>Max starting price: <b id="fpv">Any</b><input type="range" id="fprice" min="0" max="100" step="5" value="100"></label>
<fieldset><legend>Platforms</legend><div id="fplat"></div></fieldset>
<label class="ck"><input type="checkbox" id="fver"> Verified only</label>
<div class="picker"><label for="fq">Add a tool</label><input id="fq" type="search" placeholder="Search tools…" autocomplete="off"><ul id="fres" aria-label="Matching tools"></ul></div></aside>
<section class="cmain" aria-label="Comparison" aria-live="polite"><div id="ccards" class="ccards"></div><div id="cmatrix"></div><p class="muted small">Ratings are from moderated user reviews. Some links may be affiliate links. They never affect rank.</p></section></div>{hub}</main>
<dialog id="pick" class="pick-d" aria-labelledby="pickh"><div class="pin"><div class="phd"><h2 id="pickh" class="sh3">Add a tool</h2><button type="button" id="pclose" class="pcl" aria-label="Close">×</button></div><input id="pq" type="search" placeholder="Search tools or categories…" autocomplete="off" aria-label="Search tools" autofocus><div class="pbody"><div id="pres"></div><div id="ppop"></div></div></div></dialog>
<script src="/assets/compare.js" defer></script>"""
    return doc(head("Compare AI tools: pricing, free tiers & limits | ToolRank", "Interactive comparison of AI tools: starting price, free tier limits, platforms, integrations, best for and main limitation, from vendor pages.", "/compare/", [ORG, SITE, {"@type": "ItemList", "name": "AI tool comparisons", "itemListElement": [{"@type": "ListItem", "position": n, "name": cmp_title(ids), "url": f"{BASE}/compare/{k}/"} for n, (k, ids) in enumerate(COMPARES, 1)]}]), body)

COMPARE_JS = r"""(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const slug=n=>n.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");const NV='<span class="nv">Not yet verified</span>';
const dom=u=>{try{return new URL(u).hostname.replace(/^www\./,"")}catch(e){return""}};
const fd=s=>{if(!s)return"";const d=new Date(s+"T00:00:00");return d.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"})};
const pn=s=>{const m=/[$€£]\s?([0-9][0-9,]*(?:\.[0-9]+)?)/.exec(s||"");return m?parseFloat(m[1].replace(/,/g,"")):null};
let T=[],RV={},sel=[];const P=t=>t.pricing_detail||{};
const freeP=t=>P(t).free_tier?"yes":(t.last_verified&&P(t).model==="paid"?"no":null);
const trial=t=>/trial/i.test((P(t).free_tier||"")+" "+(P(t).notes||""));
const yn=v=>v==="yes"?'<span class="yes">✓ Yes</span>':v==="no"?'<span class="no">✕ No</span>':NV;
const nv=v=>v?esc(v):NV;
function url(){history.replaceState(null,"",location.pathname+(sel.length?"?tools="+sel.join(","):"")+location.hash)}
function filt(){const c=$("#fcat").value,f=$("#ffree").checked,tr=$("#ftrial").checked,v=$("#fver").checked,mx=+$("#fprice").value,pl=[...document.querySelectorAll("#fplat input:checked")].map(x=>x.value),q=$("#fq").value.toLowerCase().trim();
 return T.filter(t=>(!c||t.cat===c)&&(!f||freeP(t)==="yes")&&(!tr||trial(t))&&(!v||t.last_verified)&&(mx>=100||(pn(P(t).starting_price)??(freeP(t)==="yes"?0:1e9))<=mx)&&(!pl.length||pl.some(p=>(t.platforms||[]).includes(p)))&&(!q||t.name.toLowerCase().includes(q)))}
function list(){const r=filt().filter(t=>!sel.includes(t.s)).slice(0,40);$("#fres").innerHTML=r.map(t=>`<li><button type="button" data-add="${t.s}"><img src="https://www.google.com/s2/favicons?domain=${esc(dom(t.url))}&amp;sz=32" alt="" width="18" height="18">${esc(t.name)}<span class="muted small">${esc(t.ct)}</span>${t.last_verified?'<span class="vb">verified</span>':""}</button></li>`).join("")||'<li class="muted small">No tools match these filters.</li>'}
function rating(t){const rs=RV[t.s]||[];if(!rs.length)return'<span class="muted small">No reviews yet</span>';const a=Math.round(rs.reduce((x,r)=>x+r.rating,0)/rs.length*10)/10;return`<span class="st">★ ${a}</span> <span class="muted small">${rs.length} review${rs.length>1?"s":""}</span>`}
function render(){const ts=sel.map(s=>T.find(t=>t.s===s)).filter(Boolean);
 $("#ccards").innerHTML=ts.map((t,k)=>`<article class="ccard c${k}"><div class="cg"><span class="lg" data-l="${esc(t.name[0])}"><img src="https://www.google.com/s2/favicons?domain=${esc(dom(t.url))}&amp;sz=64" alt="" width="40" height="40" onerror="this.remove()"></span><button type="button" class="rm" data-rm="${t.s}" aria-label="Remove ${esc(t.name)}">×</button></div>
 <div class="cb"><h3><a href="/tools/${t.s}/">${esc(t.name)}</a></h3><p class="muted small">#${t.r} in ${esc(t.ct)}</p><div>${rating(t)}</div><dl class="evd"><dt>Starts at</dt><dd>${nv(P(t).starting_price)}</dd><dt>Free plan</dt><dd>${yn(freeP(t))}</dd><dt>Best for</dt><dd>${nv(t.best_for)}</dd><dt>Main limitation</dt><dd>${nv(t.main_limitation)}</dd><dt>Last verified</dt><dd>${t.last_verified?fd(t.last_verified):NV}</dd></dl>
 <a class="btn sm" href="${esc(t.affiliate_url||t.url)}" target="_blank" rel="noopener${t.affiliate_url?" sponsored":""}">Visit site →</a></div></article>`).join("")+(ts.length<4?`<button type="button" class="ccard add" id="addf" aria-haspopup="dialog"><span class="plus" aria-hidden="true">+</span><span class="al">Add tool</span><span class="muted small">${4-ts.length} slot${4-ts.length>1?"s":""} left</span></button>`:"");
 const a=$("#addf");if(a)a.onclick=openPick;
 const rows=[["Pricing model",t=>nv(P(t).model)],["Starting price",t=>nv(P(t).starting_price)],["Free tier",t=>freeP(t)==="yes"?'<span class="yes">✓</span> '+esc(P(t).free_tier):freeP(t)==="no"?'<span class="no">✕ None listed</span>':NV],["Free trial",t=>trial(t)?'<span class="yes">✓ Yes</span>':(t.last_verified?'<span class="no">✕ Not listed</span>':NV)],
  ["Platforms",t=>(t.platforms||[]).length?esc(t.platforms.join(", ")):NV],["Integrations",t=>(t.integrations||[]).length?esc(t.integrations.join(", ")):NV],["Model / provider",t=>nv(t.model_provider)],["Best for",t=>nv(t.best_for)],["Avoid if",t=>nv(t.avoid_if)],["Last verified",t=>t.last_verified?fd(t.last_verified):NV],["Sources",t=>(t.sources||[]).length?t.sources.map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener nofollow">${esc(x.label)}</a>`).join("<br>"):NV]];
 $("#cmatrix").innerHTML=ts.length?`<h2>Feature matrix</h2><div class="tbl mx"><table class="cmp"><thead><tr><th>Feature</th>${ts.map((t,k)=>`<th class="c${k}">${esc(t.name)}</th>`).join("")}</tr></thead><tbody>${rows.map(([l,f])=>`<tr><th scope="row">${l}</th>${ts.map(t=>`<td>${f(t)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`:'<p class="muted">Pick tools to compare, or start with a preset above.</p>';
 url();list()}
const logo=t=>`<img src="https://www.google.com/s2/favicons?domain=${esc(dom(t.url))}&amp;sz=64" alt="" width="28" height="28" loading="lazy">`;
const prow=t=>`<li><button type="button" data-add="${t.s}" class="pr">${logo(t)}<span class="pn">${esc(t.name)}<span class="muted small">${esc(t.ct)} · #${t.r}</span></span>${t.last_verified?'<span class="vb">verified</span>':""}</button></li>`;
function pickList(){const q=$("#pq").value.toLowerCase().trim(),av=T.filter(t=>!sel.includes(t.s));
 const c0=T.find(t=>t.s===sel[0]),cat=c0?c0.cat:"coding",ct=c0?c0.ct:"Coding & App Building";
 $("#ppop").innerHTML=q?"":`<h3 class="ph3">Popular in ${esc(ct)}</h3><ul class="plist">${av.filter(t=>t.cat===cat).slice(0,6).map(prow).join("")}</ul>`;
 const r=q?av.filter(t=>t.name.toLowerCase().includes(q)||t.ct.toLowerCase().includes(q)).slice(0,30):[];
 $("#pres").innerHTML=q?(r.length?`<h3 class="ph3">Results</h3><ul class="plist">${r.map(prow).join("")}</ul>`:'<p class="muted">No tools match.</p>'):""}
function openPick(){const d=$("#pick");$("#pq").value="";pickList();d.showModal();$("#pq").focus()}
document.addEventListener("click",e=>{const a=e.target.closest("[data-add]"),r=e.target.closest("[data-rm]");if(a&&sel.length<4){sel.push(a.dataset.add);const d=$("#pick");if(d.open)d.close();render();const n=$("#addf");if(n)n.focus()}else if(a){alert("You can compare up to 4 tools. Remove one first.")}if(r){sel=sel.filter(s=>s!==r.dataset.rm);render()}});
Promise.all([fetch("/data/tools.json").then(r=>r.json()),fetch("/data/reviews.json").then(r=>r.json()).catch(()=>({reviews:[]}))]).then(([d,rv])=>{
 d.categories.forEach(c=>c.tools.forEach((t,i)=>T.push({...t,s:slug(t.name),cat:c.id,ct:c.title,r:i+1})));
 (rv.reviews||[]).filter(r=>r.listed).forEach(r=>(RV[r.tool_slug]=RV[r.tool_slug]||[]).push(r));
 const pls=[...new Set(T.flatMap(t=>t.platforms||[]))].sort();$("#fplat").innerHTML=pls.map(p=>`<label class="ck"><input type="checkbox" value="${esc(p)}"> ${esc(p)}</label>`).join("");
 const q=new URLSearchParams(location.search).get("tools");sel=(q?q.split(","):["cursor","claude-code"]).filter(s=>T.some(t=>t.s===s)).filter((s,i,a)=>a.indexOf(s)===i).slice(0,4);
 const c0=T.find(t=>t.s===sel[0]);if(c0&&q&&sel.length===1)$("#fcat").value=c0.cat;
 ["#fcat","#ffree","#ftrial","#fver","#fprice","#fq"].forEach(s=>$(s).addEventListener("input",()=>{if(s==="#fprice"){const v=+$(s).value;$("#fpv").textContent=v>=100?"Any":"$"+v}list()}));$("#fplat").addEventListener("change",list);$("#pq").addEventListener("input",pickList);$("#pclose").onclick=()=>$("#pick").close();$("#pick").addEventListener("click",e=>{if(e.target.id==="pick")$("#pick").close()});render()})})();
"""

EV_CSS = """
.mnav{display:none;align-items:center;gap:10px}.cpill{background:var(--btn);color:#fff!important;font-weight:700;font-size:14px;padding:8px 16px;border-radius:99px;box-shadow:0 4px 16px #2563eb55}
.hb{width:42px;height:42px;border-radius:12px;border:1px solid var(--line);background:#ffffff0a;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:5px;cursor:pointer}.hb span{width:18px;height:2px;background:#fff;border-radius:2px;transition:transform .2s,opacity .2s}
.hb[aria-expanded=true] span:nth-child(1){transform:translateY(7px) rotate(45deg)}.hb[aria-expanded=true] span:nth-child(2){opacity:0}.hb[aria-expanded=true] span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
.mmenu{display:flex;flex-direction:column;padding:8px 16px 18px;border-top:1px solid var(--line);background:#0b1220f2}.mmenu[hidden]{display:none}.mmenu a{color:var(--txt);font:600 17px var(--hf);padding:13px 4px;border-bottom:1px solid #ffffff0d}.mmenu a:last-child{border:0;margin-top:10px;text-align:center;background:var(--btn);border-radius:99px;color:#fff}
@media(max-width:760px){.top nav[aria-label=Main]{display:none}.mnav{display:flex}.top .mmenu a{display:block!important;color:var(--txt)}.fresh .chip{display:block;width:100%;box-sizing:border-box}.top .mmenu{align-items:stretch;text-align:left}.top .mmenu a:last-child{text-align:center}}@media(min-width:761px){.mmenu{display:none!important}}
.fresh .btn{padding:9px 16px;font-size:14px}
@media(max-width:760px){.fresh{flex-direction:column;align-items:stretch;background:linear-gradient(135deg,#2563eb1f,#60a5fa12);border:1px solid #2563eb55;border-radius:20px;padding:16px;margin-top:22px}.fresh .chip{text-align:center;padding:10px 12px;font-size:15px}.fresh .btn{width:100%}.fresh .fl0{color:#fff;font:700 16px var(--hf)}}
.nv{color:#fbbf24;font-size:.92em;font-weight:500}.yes{color:#4ade80;font-weight:600}.no{color:#f87171;font-weight:600}
.evd{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;margin:4px 0;font-size:14px}.evd dt{color:var(--mut);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;padding-top:2px}.evd dd{margin:0;color:#cbd5e1}
.acts{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:auto;font-size:14px}.acts a{color:var(--mut);font-weight:600}.acts a:hover{color:#fff}.acts .go{margin-left:auto;color:var(--acc2)}
a.tl{color:inherit}a.tl:hover{color:var(--acc2)}.updl{margin:10px 0 0;font-size:14px;color:var(--mut)}
.prof .phero{text-align:left}.pt{display:flex;gap:18px;align-items:center;margin:14px 0}.pt .lg{width:64px;height:64px;flex:none}.pt h1{font-size:clamp(34px,5vw,54px);font-weight:800;margin:0}.pt .lead{margin:6px 0 0}
.pmeta{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.rankpill{background:#2563eb26;border:1px solid #2563eb66;border-radius:99px;padding:4px 12px;font-weight:600;font-size:13.5px}
.pacts{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0 6px}.disc{margin:6px 0 0}
.pgrid{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:32px;padding-bottom:60px}.pside{display:flex;flex-direction:column;gap:16px;position:sticky;top:90px;align-self:start}
.psec{border-bottom:1px solid var(--line);padding:26px 0}.psec h2{font-size:22px}.psec.warn h2::before{content:"⚠ ";color:#fbbf24}.psec.bf{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.tbl{overflow-x:auto;margin:10px 0;border:1px solid var(--line);border-radius:16px}.tbl table{border-collapse:collapse;width:100%;font-size:14.5px}.tbl th,.tbl td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.tbl tr:last-child>*{border-bottom:0}.tbl th[scope=row]{color:var(--mut);font-weight:600;white-space:nowrap}.tbl thead th{background:#ffffff08;font-family:var(--hf)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}.chip{border:1px solid var(--line);border-radius:99px;padding:5px 12px;font-size:13.5px;color:#cbd5e1;background:#ffffff06}a.chip:hover{border-color:var(--acc)}
.srcs{padding-left:18px}.srcs li{margin:6px 0}.rlist{padding-left:18px;margin:0}.rlist li{margin:6px 0}
.prose{max-width:760px}.prose li{margin:8px 0;color:#cbd5e1}.prose p{color:#cbd5e1}
.cmp thead th.c0{background:linear-gradient(135deg,#2563eb,#1d4ed8)}.cmp thead th.c1{background:linear-gradient(135deg,#3b82f6,#5b8cff)}.cmp thead th.c2{background:linear-gradient(135deg,#0891b2,#60a5fa)}.cmp thead th.c3{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}
.cmp thead th a,.cmp thead th{color:#fff}.cmp td ul{margin:0;padding-left:16px}.pick{border-color:#2563eb55;background:linear-gradient(135deg,#2563eb14,#60a5fa0d);margin-bottom:26px}.pick p{font-size:16.5px;line-height:1.65}
.bars{display:flex;flex-direction:column;gap:10px;margin:12px 0}.pbar{display:grid;grid-template-columns:130px 1fr minmax(120px,auto);gap:12px;align-items:center;font-size:14px}.bt{height:14px;background:#ffffff0a;border-radius:99px;overflow:hidden}.bt i{display:block;height:100%;border-radius:99px}
.bt i.c0{background:linear-gradient(90deg,#2563eb,#93c5fd)}.bt i.c1{background:linear-gradient(90deg,#3b82f6,#5b8cff)}.bt i.c2{background:linear-gradient(90deg,#0891b2,#60a5fa)}.bt i.c3{background:linear-gradient(90deg,#1d4ed8,#3b82f6)}
.fresh{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;align-items:center;margin:18px auto 0;font-size:14px}.fresh .fl0{color:var(--mut);font-weight:600}
.cwrap{display:grid;grid-template-columns:270px minmax(0,1fr);gap:26px;padding-bottom:60px}.cside{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px;display:flex;flex-direction:column;gap:14px;align-self:start;position:sticky;top:90px;max-height:calc(100vh - 110px);overflow:auto}
.sh3{font-size:17px;margin:0}.cside label{display:flex;flex-direction:column;gap:6px;font-size:14px;color:var(--mut);font-weight:600}.cside label.ck{flex-direction:row;align-items:center;gap:8px;color:var(--txt);font-weight:500}
.cside select,.cside input[type=search]{background:var(--bg2);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:9px 10px;font:500 14px Inter}.cside input[type=range]{accent-color:#2563eb}.cside input[type=checkbox]{accent-color:#2563eb;width:16px;height:16px}
.cside fieldset{border:0;padding:0;margin:0}.cside legend{font-size:14px;color:var(--mut);font-weight:600;margin-bottom:6px}#fplat{display:grid;grid-template-columns:1fr 1fr;gap:4px}#fplat label{font-size:13px}
#fres{list-style:none;padding:0;margin:6px 0 0;max-height:280px;overflow:auto}#fres button{display:flex;gap:8px;align-items:center;width:100%;background:none;border:0;border-radius:8px;color:var(--txt);padding:7px 6px;font:500 14px Inter;text-align:left;cursor:pointer}#fres button:hover{background:#ffffff0d}#fres button .muted{margin-left:auto}#fres img{border-radius:4px;background:#fff}.vb{font-size:10.5px;color:#4ade80;border:1px solid #4ade8055;border-radius:99px;padding:1px 6px}
.ccards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:26px}.ccard{background:var(--card);border:1px solid var(--line);border-radius:20px;overflow:hidden;display:flex;flex-direction:column}
.ccard .cg{height:74px;position:relative;padding:16px}.ccard.c0 .cg{background:linear-gradient(135deg,#2563eb,#3b82f6)}.ccard.c1 .cg{background:linear-gradient(135deg,#3b82f6,#2563eb)}.ccard.c2 .cg{background:linear-gradient(135deg,#0891b2,#60a5fa)}.ccard.c3 .cg{background:linear-gradient(135deg,#3b82f6,#f87171)}
.ccard .cg .lg{position:absolute;bottom:-22px;left:16px;width:52px;height:52px;border:3px solid var(--card)}.ccard .rm{position:absolute;top:10px;right:10px;width:30px;height:30px;border-radius:50%;border:0;background:#0006;color:#fff;font-size:18px;cursor:pointer}
.ccard .cb{padding:30px 16px 16px;display:flex;flex-direction:column;gap:8px;flex:1}.ccard h3{margin:0}.ccard h3 a{color:#fff}.ccard .btn{margin-top:auto}.ccard .evd{font-size:13px}
.ccard.add{align-items:center;justify-content:center;text-align:center;padding:24px;gap:10px;cursor:pointer;color:var(--txt);font:inherit;min-height:300px;border:3px dashed var(--bg);background:linear-gradient(var(--card),var(--card)) padding-box,linear-gradient(135deg,#2563eb,#3b82f6,#60a5fa) border-box;transition:transform .2s}.ccard.add:hover,.ccard.add:focus-visible{transform:translateY(-3px)}
.plus{width:64px;height:64px;border-radius:50%;background:var(--btn);display:grid;place-items:center;font:300 44px/1 Inter;color:#fff;box-shadow:0 8px 28px #2563eb66}.al{font:800 19px var(--hf)}
.pick-d{border:1px solid var(--line);border-radius:22px;background:var(--card);color:var(--txt);padding:0;width:min(520px,94vw);max-height:80vh}.pick-d::backdrop{background:#000a;backdrop-filter:blur(4px)}.pin{display:flex;flex-direction:column;gap:12px;padding:18px;max-height:80vh;box-sizing:border-box}
.phd{display:flex;align-items:center;justify-content:space-between}.pcl{width:38px;height:38px;border-radius:50%;border:1px solid var(--line);background:#ffffff0a;color:#fff;font-size:22px;cursor:pointer}
#pq{background:var(--bg2);border:1px solid var(--line);color:var(--txt);border-radius:12px;padding:12px 14px;font:500 16px Inter}#pq:focus{outline:2px solid var(--acc);border-color:transparent}.pbody{overflow:auto}
.ph3{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:6px 0}.plist{list-style:none;margin:0 0 8px;padding:0}.pr{display:flex;align-items:center;gap:12px;width:100%;background:none;border:0;border-radius:12px;padding:10px 8px;color:var(--txt);font:600 15px Inter;text-align:left;cursor:pointer}.pr:hover,.pr:focus-visible{background:#ffffff0d}.pr img{border-radius:6px;background:#fff}.pn{display:flex;flex-direction:column;flex:1}.pn .muted{font-weight:500}
@media(max-width:760px){.pick-d{width:100vw;max-width:100vw;margin:auto 0 0;border-radius:22px 22px 0 0;max-height:85vh}.ccard.add{min-height:240px}}.btn.sm{padding:9px 16px;font-size:14px}
.cwrap>*{min-width:0}main p a:not([class]),main li a:not([class]){text-decoration:underline;text-underline-offset:2px}.ans .pick{margin:0}.sec.ans{padding-bottom:0}.psec.ans{border:0;padding-bottom:0}.psec.faq details{margin:8px 0}.psec.faq summary h3{display:inline;font-size:16px}
#ccards:empty{min-height:340px}#cmatrix:empty{min-height:700px}.mx th[scope=row]{position:sticky;left:0;background:var(--card);z-index:1}.mx table{min-width:640px}
@media(max-width:900px){.pgrid{grid-template-columns:1fr}.pside{position:static}.psec.bf{grid-template-columns:1fr}.cwrap{grid-template-columns:1fr}.cside{position:static;max-height:none;order:2}.cmain{min-height:120vh}
.ccards{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:6px}.ccard{flex:0 0 82%;scroll-snap-align:start}.pbar{grid-template-columns:90px 1fr;}.pbar .bv{grid-column:1/-1;font-size:13px;color:var(--mut)}}
"""

def patch(fn, block, extra=None):
    p = ROOT/fn; s = p.read_text()
    s = re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda m: block, s, flags=re.S)
    s = re.sub(r'<link rel="preconnect".*?display=swap">', "", s); s = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", "", s, flags=re.S)
    s = re.sub(r'<header class="top">.*?</header>', lambda m: NAV, s, flags=re.S)
    s = re.sub(r'<footer.*?</footer>', lambda m: FOOT, s, flags=re.S)
    s = re.sub(r'<link rel="stylesheet" href="/assets/ev\.css[^"]*">', "", s)
    s = re.sub(r'(<link rel="stylesheet" href="/assets/style\.css[^"]*">)', lambda m: FONTS + m.group(1) + '<link rel="stylesheet" href="/assets/ev.css">', s, count=1)
    if extra: s = extra(s)
    p.write_text(s)

def build_search_index():
    """data/search-index.json: tools, categories and every generated SEO page (/compare/<slug>/, /best/<id>/, /best-of/<slug>/).
    Scans built HTML so pages added by any generator appear on the next rebuild."""
    import html as H
    def meta(f):
        s = f.read_text(errors="ignore")
        if 'http-equiv="refresh"' in s: return None
        g = lambda r: H.unescape(re.sub(r"<[^>]+>", "", (re.search(r, s, re.S | re.I) or [None, ""])[1])).strip()
        return g(r"<title>(.*?)</title>"), g(r"<h1[^>]*>(.*?)</h1>"), g(r'<meta name="description" content="([^"]*)"')
    pages = []
    for kind, base in (("compare", "compare"), ("guide", "best"), ("guide", "best-of")):
        for f in sorted((ROOT/base).glob("*/index.html")):
            m = meta(f)
            if not m: continue
            title, h1, blurb = m; sl = f.parent.name
            keys = sorted(set(re.split(r"[^a-z0-9]+", (sl + " " + h1).lower())) - {"", "vs", "best", "ai", "tools", "the", "and", "for"})
            pages.append({"type": kind, "url": f"/{base}/{sl}/", "title": title, "h1": h1, "blurb": blurb[:200], "keys": keys})
    cats = [{"id": c["id"], "title": c["title"], "blurb": c["blurb"], "url": f"/best/{c['id']}/"} for c in D["categories"]]
    tools = [{"name": t["name"], "slug": slug(t["name"]), "cat": c["id"], "url": f"/tools/{slug(t['name'])}/"} for c in D["categories"] for t in c["tools"]]
    (ROOT/"data"/"search-index.json").write_text(json.dumps({"updated": UPD, "pages": pages, "categories": cats, "tools": tools}, separators=(",", ":"), ensure_ascii=False) + "\n")
    return len(pages)

def main():
    cats = D["categories"]
    ensure_fonts(); print(f"logos: fetched {ensure_logos()} new")
    (ROOT/"assets/cat").mkdir(exist_ok=True); (ROOT/"assets/trend").mkdir(exist_ok=True)
    for c in cats: (ROOT/f"assets/cat/{c['id']}.svg").write_text(cat_art(c["id"]))
    for i in range(3): (ROOT/f"assets/trend/v{i+1}.svg").write_text(trend_art(i))
    for c in cats:
        d = ROOT/"best"/c["id"]; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(page(c))
    for o, n in REDIRECTS.items():
        d = ROOT/"best"/o; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(redirect_page(o, n))
    (ROOT/"assets/ev.css").write_text(EV_CSS); (ROOT/"assets/compare.js").write_text(COMPARE_JS.replace("https://www.google.com/s2/favicons?domain=${esc(dom(t.url))}&amp;sz=32\" alt=\"\"", "/assets/logos/${t.s}.png\" alt=\"\" onerror=\"this.remove()\"").replace('&amp;sz=64" alt="" width="28" height="28" loading="lazy"', '&amp;sz=64" alt="" width="28" height="28" loading="lazy" onerror="this.remove()"').replace("https://www.google.com/s2/favicons?domain=${esc(dom(t.url))}&amp;sz=64", "/assets/logos/${t.s}.png"))
    for c, i, t in ALLT:
        d = ROOT/"tools"/slug(t["name"]); d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(profile_page(c, i, t))
    for name, fn in (("methodology", methodology_page), ("claim", claim_page), ("compare", compare_ui_page), ("about", about_page)):
        (ROOT/name).mkdir(exist_ok=True); (ROOT/name/"index.html").write_text(fn())
    for k, ids in COMPARES:
        (ROOT/"compare"/k).mkdir(parents=True, exist_ok=True); (ROOT/"compare"/k/"index.html").write_text(cmp_page(k, ids))
    (ROOT/"reviews.html").write_text(reviews_page()); (ROOT/"services.html").write_text(services_page()); (ROOT/"index.html").write_text(home(cats))
    opts = "".join(f"<option>{E(c['title'])}</option>" for c in cats) + "<option>Other / new category</option>"
    def sub(s): return re.sub(r'(<select name="category"[^>]*>).*?(</select>)', lambda m: m.group(1) + opts + m.group(2), s, flags=re.S)
    patch("featured.html", head("Get your AI tool featured | ToolRank", "Featured placements and newsletter sponsorship on ToolRank. Featured spots are clearly labelled; rankings stay editorial.", "/featured.html", [ORG, SITE]))
    patch("submit.html", head("Submit your AI tool for free | ToolRank", "Submit your AI tool to ToolRank for free. Every submission gets an editorial review; approved tools are listed in the right category.", "/submit.html", [ORG, SITE]), sub)
    urls = ["/", "/reviews.html", "/services.html", "/submit.html", "/featured.html", "/methodology/", "/claim/", "/compare/", "/about/"] + [f"/best/{c['id']}/" for c in cats] + [f"/compare/{k}/" for k, _ in COMPARES] + [prof(t) for _, _, t in ALLT]
    (ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{UPD}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended"]
    (ROOT/"robots.txt").write_text("# ToolRank: search engines and AI crawlers are welcome.\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) +
                                   f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    L = [f"# ToolRank\n\n> Confused by AI? Editorial rankings of AI tools by use case. Last updated {UPD}. Rankings are editorial; featured placements are labelled. Launch offer: free for the first 100 tools (including featured placement); after that, free listing plus paid options at founding prices.\n\n## Categories\n"]
    L += [f"\nAudiences: 'For You' (consumer and creator tools) and 'For Business' (B2B and developer tools). {NT} tools ranked across {len(cats)} categories; {len(R)} approved user reviews.\n"]
    L += [f"- [{c['title']}]({BASE}/best/{c['id']}/): {c['blurb']} {len(c['tools'])} tools; #1: {c['tools'][0]['name']}." for c in cats]
    def LLM_EV(): return (f"- [How we rank]({BASE}/methodology/): editorial, evidence-based; sources and check dates on every tool profile at {BASE}/tools/<slug>/.\n- [Compare tools (interactive)]({BASE}/compare/)\n" + "".join(f"- [{cmp_title(ids)}]({BASE}/compare/{k}/)\n" for k, ids in COMPARES) + f"- [Claim your listing (free)]({BASE}/claim/)\n")
    L += [f"\n## Optional\n\n- [About ToolRank]({BASE}/about/)\n- [Full rankings]({BASE}/llms-full.txt)\n- [Submit a tool (free)]({BASE}/submit.html)\n- [Get featured]({BASE}/featured.html)\n- [Services for makers]({BASE}/services.html): free listing and Review Boost; founding prices (available now via Stripe checkout): Verified badge US$2, Featured spot US$5/mo, Launch spotlight US$9/wk, Comparison page US$15, Launch Kit US$19, AI Stack Audit US$29.\n" + LLM_EV() + f"- [Reviews]({BASE}/reviews.html): {len(R)} moderated user review(s) collected so far; leave one via GitHub.\n"]
    (ROOT/"llms.txt").write_text("\n".join(L))
    F = [f"# ToolRank: full rankings\n\nLast updated {UPD}. Source: {BASE}/. Editorial ranking; position 1 = top pick. Pricing labels: free / freemium / paid (as listed; verify with vendor).\n"]
    for c in cats:
        F.append(f"\n## {c['title']}\n\n{c['blurb']}\nPage: {BASE}/best/{c['id']}/\n")
        F += [f"{i}. {t['name']} ({t['pricing']}; audience: {t.get('audience','')}){' [Featured]' if t.get('featured') else ''}{f' [user rating {rstat(t)[1]}/5 from {rstat(t)[0]} review(s)]' if rstat(t)[0] else ''}: {t['verdict']} {t['url']}" for i, t in enumerate(c["tools"], 1)]
    F.append(f"\n## Comparisons (facts checked {fmt_date(CHECK_DATE)})\n")
    F += [f"- {cmp_title(c['ids'])}: {BASE}/compare/{c['key']}/ | " + re.sub(r"<[^>]+>", "", c["pick"]) for c in CJ]
    F.append(f"\n## New this week (as of {N['updated']})\n")
    F += [f"- {n['date']} {n['title']} ({n['type']}): {n['summary']} {n['url']}" for n in sorted(N["items"], key=lambda n: n["date"], reverse=True)]
    (ROOT/"llms-full.txt").write_text("\n".join(F) + "\n")
    GC = ('<!--GC--><script data-goatcounter="https://toolrank.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'
          '<script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a.go");if(!a||!/^Visit /.test(a.textContent)||!window.goatcounter||!goatcounter.count)return;'
          'var n=a.textContent.replace(/^Visit\\s+|\\s*\u2192\\s*$/g,"").trim(),s=n.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");'
          'goatcounter.count({path:"click/"+s,title:n,event:true})});</script><!--/GC-->')
    PRIV = '<!--PRIV--><p class="small muted">Privacy: cookieless, privacy-friendly analytics via <a href="https://www.goatcounter.com" rel="noopener" target="_blank">GoatCounter</a>. No cookies, no personal data, no tracking across sites.</p><!--/PRIV-->'
    npg = build_search_index(); print(f"search-index: {npg} pages")
    import hashlib
    V = {a: hashlib.sha1((ROOT/"assets"/a).read_bytes()).hexdigest()[:8] for a in ("app.js", "style.css", "hero.js", "ev.css", "compare.js")}
    for h in ROOT.rglob("*.html"):
        if "shots" in h.parts or h.parent.name in REDIRECTS: continue
        s = h.read_text(); n = re.sub(r"<!--GC-->.*?<!--/GC-->", "", s, flags=re.S); n = re.sub(r"<!--PRIV-->.*?<!--/PRIV-->", "", n, flags=re.S)
        n = n.replace('<p class="muted small">©', PRIV + '<p class="muted small">©', 1).replace("</body>", GC + "</body>", 1)
        n = re.sub(r'<a (?![^>]*\brel=)([^>]*href="/compare/\?tools=[^"]*"[^>]*)>', r'<a rel="nofollow" \1>', n)
        if 'class="hero' in n and "assets/hero.js" not in n: n = n.replace("</body>", '<script defer src="/assets/hero.js"></script></body>', 1)
        n = re.sub(r'(assets/(app\.js|style\.css|hero\.js|ev\.css|compare\.js))(\?v=[0-9a-f]+)?"', lambda m: f'{m.group(1)}?v={V[m.group(2)]}"', n)
        if n != s: h.write_text(n)
    print(f"cache-bust: app.js?v={V['app.js']} style.css?v={V['style.css']}")
    print(f"built {len(cats)} category pages + {len(REDIRECTS)} redirects, sitemap ({len(urls)} urls), robots, llms.txt, llms-full.txt")
if __name__ == "__main__": main()
