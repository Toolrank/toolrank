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

def trending_html():
    T = TR
    if T["stars"]:
        sb = "".join(f'<li><a href="{E(x["url"])}" target="_blank" rel="noopener">{E(x["tool"])}</a> <span class="up">+{x["gained"]:,}★</span> <span class="muted">({x["stars"]:,} total)</span></li>' for x in T["stars"])
        sb = f'<ol class="tl">{sb}</ol>'
    elif T.get("stars_baseline"):
        sb = '<p class="muted">No tracked repo gained stars in this window.</p>'
    else:
        sb = f'<p class="muted">Tracking {T.get("repos_tracked", 0)} GitHub repos. First snapshot taken {E(str(T.get("fetched") or "soon"))}; star gains appear after the next daily update.</p>'
    hb = (f'<ol class="tl">' + "".join(f'<li><a href="{E(x["top_url"])}" target="_blank" rel="noopener nofollow">{E(x["tool"])}</a> <span class="up">{x["points"]} pts</span> <span class="muted">· {x["stories"]} stor{"ies" if x["stories"] != 1 else "y"}</span></li>' for x in T["hn"]) + '</ol>') \
        if T["hn"] else '<p class="muted">No Hacker News stories linking to ranked tools in the last 7 days.</p>'
    base = f'since {T["stars_baseline"]}' if T.get("stars_baseline") else "last 7 days"
    return (f'<!--TREND--><section id="trending" class="wrap"><h2>🔥 Trending this week</h2><p class="muted small">Real public signals, refreshed daily{" (last update " + E(T["fetched"]) + ")" if T.get("fetched") else ""}. Not paid, not editorial rank.</p>'
            f'<div class="grid"><article class="card"><h3>GitHub stars gained</h3><span class="tag">Source: GitHub API, {base}</span>{sb}</article>'
            f'<article class="card"><h3>Hacker News buzz</h3><p class="muted small">Stories linking to a ranked tool, by points.</p><span class="tag">Source: HN Algolia API, last 7 days</span>{hb}</article>'
            + clicks_card() + '</div></section><!--/TREND-->')

def short(c): return re.sub(r"^Best (for )?", "", c["title"])
def link(t): return t.get("affiliate_url") or t["url"]
def rel(t): return "noopener" + (" sponsored" if t.get("affiliate_url") else "")

NAV = f'<header class="top">{LOGO}<nav><a href="/">Directory</a><a href="/reviews.html">Reviews</a><a href="/submit.html">Submit a tool</a><a href="/services.html">Services</a></nav></header>'
FOOT = f'<footer class="wrap muted">© {UPD[:4]} ToolRank. Some links may become affiliate links; featured placements are labelled. Reviews are user-submitted via GitHub and moderated; they never change the editorial rank.</footer>'
def head(title, desc, path, ld, otype="website"):
    url = BASE + path
    return f"""<!--SEO--><title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-snippet:-1">
<meta property="og:type" content="{otype}"><meta property="og:site_name" content="ToolRank"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{BASE}/assets/og.png">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script><!--/SEO-->"""

def tool_ld(t, c, i):
    # Only facts present in data: name, url, category, and free tier yes/no from pricing field. No ratings invented.
    o = {"@type": "SoftwareApplication", "name": t["name"], "url": t["url"], "description": t["verdict"],
         "applicationCategory": "AI tool: " + short(c)}
    if t["pricing"] in ("free", "freemium"):
        o["offers"] = {"@type": "Offer", "price": "0", "priceCurrency": "USD", "description": t["pricing"] + " (free tier available)"}
    n, a = rstat(t)
    if n: o["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": a, "reviewCount": n, "bestRating": 5, "worstRating": 1}
    return o

def faqs(c):
    ts = c["tools"]; free = [t["name"] for t in ts if t["pricing"] in ("free", "freemium")]; paid = [t["name"] for t in ts if t["pricing"] == "paid"]
    q = [(f"What is the best AI tool for {short(c).lower()} right now?" if c["title"].startswith("Best for") else f"What is the top-ranked tool in ToolRank's {short(c).lower()} list?",
          f"In ToolRank's editorial ranking (updated {UPD}), {ts[0]['name']} is ranked #1: {ts[0]['verdict']}"),
         ("Which of these tools have a free option?",
          (", ".join(free) + " list a free or freemium tier." if free else "None of the ranked tools are listed as free or freemium.") +
          (" " + ", ".join(paid) + (" is" if len(paid) == 1 else " are") + " listed as paid." if paid else "") + " Pricing changes often; check each vendor's site."),
         ("How are these tools ranked?",
          "Rankings are editorial picks by ToolRank, ordered by position in the list. Featured placements are paid, clearly labelled and do not change the editorial rank."),
         ("When was this list last updated?", f"{UPD}.")]
    return q

def cards(c, h="h3", base_rank=True):
    out = []
    for i, t in enumerate(c["tools"], 1):
        out.append(f'<article class="card">{"<span class=\"tag feat\">Featured</span>" if t.get("featured") else ""}<{h}><span class="rank">#{i}</span>{E(t["name"])}</{h}><p>{E(t["verdict"])}</p>'
                   f'<span class="tag {t["pricing"]}">{t["pricing"]}</span>{rv_line(t)}<a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t["name"])} →</a></article>')
    return "".join(out)

def page(c):
    path = f"/best/{c['id']}/"; fq = faqs(c)
    title = f"{c['title']} ({UPD[:4]}): {', '.join(t['name'] for t in c['tools'][:3])} & more | ToolRank"
    desc = f"{c['blurb']} Ranked: " + ", ".join(f"#{i} {t['name']}" for i, t in enumerate(c["tools"], 1)) + f". Updated {UPD}."
    ld = [ORG, SITE,
          {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "ToolRank", "item": BASE+"/"},
                                                          {"@type": "ListItem", "position": 2, "name": c["title"], "item": BASE+path}]},
          {"@type": "ItemList", "name": c["title"], "description": c["blurb"], "url": BASE+path, "numberOfItems": len(c["tools"]),
           "itemListOrder": "https://schema.org/ItemListOrderAscending",
           "itemListElement": [{"@type": "ListItem", "position": i, "item": tool_ld(t, c, i)} for i, t in enumerate(c["tools"], 1)]},
          {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in fq]}]
    others = "".join(f'<li><a href="/best/{o["id"]}/">{E(o["title"])}</a></li>' for o in D["categories"] if o is not c)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{head(title, desc, path, ld)}<link rel="stylesheet" href="/assets/style.css"></head><body>
{NAV}
<nav class="wrap muted" aria-label="Breadcrumb"><a href="/">ToolRank</a> › {E(c['title'])}</nav>
<main><article><section class="hero"><h1>{E(c['title'])}</h1><p>{E(c['blurb'])}</p><p class="muted">Last updated <time datetime="{UPD}">{UPD}</time>. Editorial ranking.</p></section>
<section class="wrap"><h2>The ranking</h2><ol class="muted">{''.join(f'<li><strong>{E(t["name"])}</strong> ({t["pricing"]}): {E(t["verdict"])}</li>' for t in c["tools"])}</ol><div class="grid">{cards(c)}</div></section>
{cat_reviews(c)}<section class="wrap faq"><h2>FAQ</h2>{''.join(f'<details open><summary><h3 style="display:inline">{E(a)}</h3></summary><p>{E(b)}</p></details>' for a, b in fq)}</section>
</article><section class="wrap"><h2>More categories</h2><ul>{others}</ul></section></main>
{FOOT}</body></html>
"""

def cat_reviews(c):
    rs = [r for t in c["tools"] for r in RB.get(slug(t["name"]), []) if r["listed"]]
    rs.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    body = (f'<div class="grid">{"".join(review_html(r) for r in rs[:12])}</div>' + (f'<p><a href="/reviews.html#cat-{c["id"]}">All {len(rs)} reviews →</a></p>' if len(rs) > 12 else "")) if rs else \
        f'<p class="muted">No reviews yet for {E(short(c).lower())} tools. Used one of them? Be the first to review.</p>'
    return (f'<section class="wrap" id="reviews"><h2>Reviews: {E(short(c)[:1].upper() + short(c)[1:])}</h2>{body}'
            f'<div class="cta"><div><h3>Using AI tools? Leave a review.</h3><p>Help builders and businesses pick the right AI tool.</p></div><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></div></section>')

def reviews_page():
    secs = []
    for c in D["categories"]:
        rows = []
        for t in c["tools"]:
            n, a = rstat(t); s = slug(t["name"]); rs = [r for r in RB.get(s, []) if r["listed"]]
            rows.append(f'<div class="rrow" id="{s}"><div class="rt"><strong>{E(t["name"])}</strong> ' +
                        (f'<span class="st">{stars(a)} {a}</span> <span class="muted">({n} review{"s" if n != 1 else ""})</span>' if n else '<span class="muted">No reviews yet</span>') +
                        f'<a class="rvbtn" href="{E(review_url(t["name"]))}" target="_blank" rel="noopener">{"Review" if n else "Be the first to review"}</a></div>' +
                        (f'<div class="grid">{"".join(review_html(r) for r in rs)}</div>' if rs else "") + '</div>')
        secs.append(f'<section class="wrap" id="cat-{c["id"]}"><h2><a href="/best/{c["id"]}/">{E(c["title"])}</a></h2>{"".join(rows)}</section>')
    other = [r for r in R if not r["listed"]]
    if other: secs.append(f'<section class="wrap"><h2>Other tools (not yet ranked)</h2><div class="grid">{"".join(review_html(r) for r in other)}</div></section>')
    latest = f'<section class="wrap"><h2>Latest reviews</h2><div class="grid">{"".join(review_html(r) for r in R[:9])}</div></section>' if R else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{head("AI tool reviews from real users | ToolRank", "Honest, moderated reviews of AI tools from users, developers and businesses. Leave a review to help others pick the right AI tool.", "/reviews.html", [ORG, SITE])}<link rel="stylesheet" href="/assets/style.css"></head><body>
{NAV}<section class="hero"><h1>AI tool reviews</h1><p>Using AI tools? Leave a review. Help builders and businesses pick the right AI tool.</p>{stats_html()}
<p><a class="btn" href="{E(REVIEW_NEW)}" target="_blank" rel="noopener">Leave a Review</a></p>
<p class="muted small">Reviews are posted as public GitHub issues (free GitHub account needed) and appear here after a moderation check. We never write or buy reviews, and reviews never change the editorial rank.</p></section>
<main>{latest}{"".join(secs)}</main>{FOOT}</body></html>
"""

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

def patch(fn, block, extra=None):
    p = ROOT/fn; s = p.read_text()
    s = re.sub(r"<!--SEO-->.*?<!--/SEO-->", lambda m: block, s, flags=re.S) if "<!--SEO-->" in s else \
        re.sub(r"<title>.*?<link rel=\"stylesheet\"", lambda m: block + "<link rel=\"stylesheet\"", s, flags=re.S)
    if extra: s = extra(s)
    p.write_text(s)

def main():
    for c in D["categories"]:
        d = ROOT/"best"/c["id"]; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(page(c))
    cats = D["categories"]
    (ROOT/"reviews.html").write_text(reviews_page()); (ROOT/"services.html").write_text(services_page())
    ild = [ORG, SITE] + [{"@type": "ItemList", "name": c["title"], "url": f"{BASE}/best/{c['id']}/",
                           "itemListElement": [{"@type": "ListItem", "position": i, "name": t["name"], "url": t["url"]} for i, t in enumerate(c["tools"], 1)]} for c in cats]
    pre = "<!--PRE-->" + "".join(f'<section id="{c["id"]}"><h2><a href="/best/{c["id"]}/">{E(c["title"])}</a></h2><p class="muted">{E(c["blurb"])}</p><div class="grid">{cards(c)}</div></section>' for c in cats) + "<!--/PRE-->"
    def idx(s):
        s = re.sub(r'<main id="cats">.*?</main>', lambda m: f'<main id="cats">{pre}</main>', s, flags=re.S)
        s = s.replace('<a href="index.html"', '<a href="/"')
        s = re.sub(r"<!--STATS-->.*?<!--/STATS-->", lambda m: stats_html(), s, flags=re.S)
        s = re.sub(r"<!--CTA-->.*?<!--/CTA-->", lambda m: "<!--CTA-->" + CTA + "<!--/CTA-->", s, flags=re.S)
        s = re.sub(r"<!--TREND-->.*?<!--/TREND-->", lambda m: trending_html(), s, flags=re.S)
        s = re.sub(r"<!--MAKERS-->.*?<!--/MAKERS-->", lambda m: makers_html(), s, flags=re.S)
        return s
    patch("index.html", head("ToolRank: the best AI tools ranked by use case (" + UPD[:4] + ")",
          f"Editorial rankings of AI tools across {len(cats)} use cases: " + ", ".join(short(c) for c in cats) + f". Updated {UPD}.", "/", ild), idx)
    patch("featured.html", head("Get your AI tool featured | ToolRank", "Featured placements and newsletter sponsorship on ToolRank. Featured spots are clearly labelled; rankings stay editorial.", "/featured.html", [ORG, SITE]))
    patch("submit.html", head("Submit your AI tool for free | ToolRank", "Submit your AI tool to ToolRank for free. Every submission gets an editorial review; approved tools are listed in the right category.", "/submit.html", [ORG, SITE]))
    urls = ["/", "/reviews.html", "/services.html", "/submit.html", "/featured.html"] + [f"/best/{c['id']}/" for c in cats]
    (ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{UPD}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended"]
    (ROOT/"robots.txt").write_text("# ToolRank: search engines and AI crawlers are welcome.\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) +
                                   f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    L = [f"# ToolRank\n\n> Editorial rankings of AI tools by use case. Last updated {UPD}. Rankings are editorial; featured placements are labelled. Launch offer: free for the first 100 tools (including featured placement); after that, free listing plus paid options at founding prices.\n\n## Categories\n"]
    L += [f"\nAudiences: 'For You' (consumer and creator tools) and 'For Business' (B2B and developer tools). {NT} tools ranked; {len(R)} approved user reviews.\n"]
    L += [f"- [{c['title']}]({BASE}/best/{c['id']}/): {c['blurb']} #1: {c['tools'][0]['name']}." for c in cats]
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
    PRIV = '<!--PRIV--><p class="small">Privacy: cookieless, privacy-friendly analytics via <a href="https://www.goatcounter.com" rel="noopener" target="_blank">GoatCounter</a>. No cookies, no personal data, no tracking across sites.</p><!--/PRIV-->'
    for h in ROOT.rglob("*.html"):
        if "shots" in h.parts: continue
        s = h.read_text(); n = re.sub(r"<!--GC-->.*?<!--/GC-->", "", s, flags=re.S); n = re.sub(r"<!--PRIV-->.*?<!--/PRIV-->", "", n, flags=re.S)
        n = n.replace("</footer>", PRIV + "</footer>", 1).replace("</body>", GC + "</body>", 1)
        if n != s: h.write_text(n)
    import hashlib
    V = {a: hashlib.sha1((ROOT/"assets"/a).read_bytes()).hexdigest()[:8] for a in ("app.js", "style.css", "hero.js")}
    for h in ROOT.rglob("*.html"):
        if "shots" in h.parts: continue
        s = h.read_text(); s2 = s if ('class="hero' not in s or "assets/hero.js" in s) else s.replace("</body>", '<script defer src="/assets/hero.js"></script></body>', 1)
        n = re.sub(r'(assets/(app\.js|style\.css|hero\.js))(\?v=[0-9a-f]+)?"', lambda m: f'{m.group(1)}?v={V[m.group(2)]}"', s2)
        if n != s: h.write_text(n)
    print(f"cache-bust: app.js?v={V['app.js']} style.css?v={V['style.css']}")
    print(f"built {len(cats)} category pages, sitemap ({len(urls)} urls), robots, llms.txt, llms-full.txt")
if __name__ == "__main__": main()
