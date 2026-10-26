#!/usr/bin/env python3
"""Checks: JSON validity (data + JSON-LD), internal links/assets, outbound URLs.
Usage: python3 scripts/check.py [--no-external]. Exit 1 on failure.
Outbound: 2xx/3xx pass; 401/403/429 (common bot-blocking) and favicon-service 404s are WARN, other errors FAIL.
Preconnect/dns-prefetch hints are skipped; attribute values are HTML-unescaped before checking."""
import json, re, sys, html, pathlib, urllib.request, urllib.error, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parent.parent; BASE = "https://toolrank.io"
fails, warns = [], []
FAVICON = "https://www.google.com/s2/favicons?"
for f in sorted((ROOT/"data").glob("*.json")):
    try: json.loads(f.read_text())
    except Exception as e: fails.append(f"JSON {f.name}: {e}")
d = json.loads((ROOT/"data/tools.json").read_text())
for c in d["categories"]:
    for t in c["tools"]:
        for k in ("name", "url", "verdict", "pricing"):
            if not t.get(k): fails.append(f"tools.json {c['id']}: missing {k}")
        if t["pricing"] not in ("free", "freemium", "paid"): fails.append(f"bad pricing {t['name']}")
        if t.get("audience") not in ("consumer", "business", "both"): fails.append(f"bad/missing audience {t['name']}")
rv = json.loads((ROOT/"data/reviews.json").read_text())
for r in rv.get("reviews", []):
    if not (isinstance(r.get("rating"), int) and 1 <= r["rating"] <= 5 and r.get("text") and r.get("url", "").startswith("https://github.com/Toolrank/toolrank/issues/")):
        fails.append(f"reviews.json: invalid review {r.get('id')}")
sc = json.loads((ROOT/"data/shop.json").read_text()); scat = {c["id"] for c in sc["categories"]}  # ToolRank Shop: products only go live with a real price + Stripe link
for pr in json.loads((ROOT/"data/products.json").read_text())["products"]:
    if pr.get("category") not in scat: fails.append(f"products.json {pr.get('id')}: unknown category")
    if pr.get("status") not in ("draft", "active", "paused"): fails.append(f"products.json {pr.get('id')}: bad status")
    if pr.get("status") == "active" and not (isinstance(pr.get("our_price"), (int, float)) and pr["our_price"] > 0 and str(pr.get("stripe_link") or "").startswith("https://buy.stripe.com/")):
        fails.append(f"products.json {pr.get('id')}: active but missing our_price or https://buy.stripe.com/ stripe_link")
    if isinstance(pr.get("our_price"), (int, float)) and isinstance(pr.get("supplier_cost"), (int, float)) and pr["our_price"] * 0.9835 - 0.30 <= pr["supplier_cost"]:
        warns.append(f"products.json {pr.get('id')}: our_price leaves no margin after Stripe fees")
    if pr.get("stripe_link") and pr.get("status") == "active" and not (ROOT/"shop/p"/pr["id"]/"index.html").exists(): fails.append(f"products.json {pr.get('id')}: active but page not built (run scripts/shop.py)")
idx = (ROOT/"index.html").read_text()
if f"<b>{sum(len(c['tools']) for c in d['categories'])}</b> tools ranked" not in idx: fails.append("index.html: tools counter does not match tools.json")
if f"<b>{len(rv.get('reviews', []))}</b> review" not in idx: fails.append("index.html: reviews counter does not match reviews.json")
pages = [p for p in ROOT.rglob("*.html") if not re.fullmatch(r"google[0-9a-f]+\.html", p.name)]  # search-console verification files are not pages
ext = set()
for p in pages:
    s = p.read_text(); r = p.relative_to(ROOT)
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try: json.loads(m)
        except Exception as e: fails.append(f"JSON-LD {r}: {e}")
    if "<title>" not in s or 'name="description"' not in s or 'rel="canonical"' not in s: fails.append(f"{r}: missing title/description/canonical")
    if len(re.findall(r"<h1[ >]", s)) != 1: fails.append(f"{r}: expected exactly one h1")
    for img in re.findall(r"<img[^>]*>", s):
        if "alt=" not in img: fails.append(f"{r}: img without alt")
    hints = set(re.findall(r'<link rel="(?:preconnect|dns-prefetch)" href="([^"]+)"', s))  # connection hints, not fetchable pages
    for h in re.findall(r'(?:href|src)="([^"]+)"', s):
        h = html.unescape(h)
        if h in hints: continue
        if h.startswith(("http://", "https://")):
            if not h.startswith(BASE): ext.add(h)
            continue
        if h.startswith(("#", "mailto:")): continue
        path = h.split("#")[0].split("?")[0]
        tgt = (ROOT/path.lstrip("/")) if path.startswith("/") else (p.parent/path)
        if tgt.is_dir(): tgt = tgt/"index.html"
        if not tgt.exists(): fails.append(f"{r}: broken internal link {h}")
for f in ("sitemap.xml", "robots.txt", "llms.txt", "llms-full.txt"):
    if not (ROOT/f).exists(): fails.append(f"missing {f}")
for u in re.findall(r"<loc>(.*?)</loc>", (ROOT/"sitemap.xml").read_text()):
    path = u.replace(BASE, "").lstrip("/"); tgt = ROOT/path
    if tgt.is_dir() or not path: tgt = tgt/"index.html"
    if not tgt.exists(): fails.append(f"sitemap entry missing file: {u}")
ext |= {t["url"] for c in d["categories"] for t in c["tools"]} | {n["url"] for n in json.loads((ROOT/"data/new-this-week.json").read_text())["items"]}
def get(u):
    for m in ("HEAD", "GET"):
        try:
            rq = urllib.request.Request(u, method=m, headers={"User-Agent": "Mozilla/5.0 (ToolRank link check)"})
            return u, urllib.request.urlopen(rq, timeout=20).status
        except urllib.error.HTTPError as e:
            if m == "GET" or e.code not in (403, 405, 400, 404, 501): return u, e.code
        except Exception as e:
            if m == "GET":
                try: return u, urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (ToolRank link check)"}), timeout=30).status  # one retry for transient timeouts
                except urllib.error.HTTPError as e2: return u, e2.code
                except Exception as e2: return u, str(e2)[:60]
ISSUE = "https://github.com/Toolrank/toolrank/issues/new?"  # one per tool, same template; checking hundreds trips GitHub throttling (false timeouts)
iss = sorted(u for u in ext if u.startswith(ISSUE)); ext = (ext - set(iss)) | set(iss[:1])
if "--no-external" not in sys.argv:
    with cf.ThreadPoolExecutor(12) as x:
        for u, st in sorted(x.map(get, sorted(ext))):
            if isinstance(st, int) and st < 400: continue
            soft = st in (401, 403, 429) or (st == 404 and u.startswith(FAVICON))  # favicon 404 = no icon; <img onerror> falls back to the letter badge
            (warns if soft else fails).append(f"outbound {u}: {st}")
print(f"pages checked: {len(pages)}, outbound urls: {len(ext)} ({len(iss)} review-issue links checked as one)")
for w in warns: print("WARN", w)
for f in fails: print("FAIL", f)
print("OK" if not fails else f"{len(fails)} failure(s)"); sys.exit(1 if fails else 0)
