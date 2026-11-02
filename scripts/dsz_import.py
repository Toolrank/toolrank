#!/usr/bin/env python3
"""Bulk catalogue import from the supplier's zone-rates CSV (re-runnable; the daily ops routine runs it after downloading a fresh file).

  python3 scripts/dsz_import.py [path/to/sku_list_zone_rates.csv] [--target 50000] [--dry-run]
  python3 scripts/dsz_import.py --reprice-only [--dry-run]   re-price the CURRENT listing with dsz_rules (same items, ids, categories and
      recorded costs; text and photos re-read from the feed recorded in dsz_costs.json). Items that can no longer keep the 5% floor under RRP are dropped.

Default CSV: newest /workspace/dsz/x_sku_list_zone_rates_*/sku_list_zone_rates.csv.
Streams the CSV (never loads it into RAM), applies eligibility + safety rules (scripts/dsz_rules.py), prices every item, collapses
colour/size variants and identical items to the cheapest, then keeps up to --target items spread fairly across subcategories.

Writes (PUBLIC, in the repo; no costs, supplier names, supplier SKUs or rebates):
  data/dsz/cards.json          compact card data (id, name, category, subcategory, price in cents, image path) read by scripts/shop.py
  shop/i/<id>/index.html       one compact static page per product (stale pages are removed)
Writes (PRIVATE, outside the repo; TOOLRANK_PRIVATE_DIR, default /workspace/toolrank-private):
  dsz_costs.json   cost record per listed product (supplier SKU/URL, cost, Sydney metro delivery, price, margin, rebate)
  dsz_ids.json     permanent supplier SKU -> TR-DZ number map (keeps product URLs stable across re-syncs; back it up)
  dsz_report.json  counts: rows read, exclusions by rule, pricing outcomes, per-category counts
Then run: python3 scripts/shop.py (category pages, search shards) and python3 scripts/check.py --no-external."""
import csv, json, os, re, sys, glob, html, math, time, shutil, pathlib, datetime, collections, urllib.parse
from html.parser import HTMLParser
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dsz_rules as R
csv.field_size_limit(10**9)
ROOT = pathlib.Path(__file__).resolve().parent.parent
PRIV = pathlib.Path(os.environ.get("TOOLRANK_PRIVATE_DIR", "/workspace/toolrank-private"))
IMG_BASE = "https://cdn.dropshipzone.com.au/media/catalog/product/"
OUT_PAGES = ROOT/"shop/i"
CARDS = ROOT/"data/dsz/cards.json"
MAX_IMGS = 5; DESC_MAX = 1500

def pid(n): return f"TR-DZ-{n:06d}"
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ---------- description sanitiser ----------
ALLOW = {"p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "h3", "h4"}
REMAP = {"h1": "h4", "h2": "h4", "h3": "h4", "h5": "h4", "h6": "h4", "b": "strong", "div": "p", "section": "p", "dt": "p", "dd": "p"}
DROP = {"script", "style", "iframe", "object", "embed", "details", "table", "noscript", "svg", "video", "audio", "form", "button", "select", "textarea", "head", "title"}
BLOCK = {"p", "h4", "ul", "ol"}
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr"}
BOILER = re.compile(r"(returns?, refunds? and replacements|products received faulty|change of mind|delivery timeframe|delivery is approximately|business days|working days|letterbox|shipped as|for customers in|dispatch(ed)? within|shipping (time|info)|postcodes?|we are committed to ensuring|warehouse|drop ?ship|dropshipzone|wholesale|supplier|https?://|www\.|@[a-z0-9-]+\.|\bebay\b|\bamazon\b|\bkogan\b|\bcatch\.com)", re.I)
class San(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.out = []; s.stack = []; s.skip = 0; s.n = 0; s.full = False
    def handle_starttag(s, tag, a):
        if s.skip or tag in DROP:
            if tag not in VOID: s.skip += 1 if (s.skip or tag in DROP) else 0
            return
        t = REMAP.get(tag, tag)
        if t == "br": s.out.append("<br>"); return
        if t in ALLOW and not s.full:
            if t in BLOCK:  # block elements cannot sit inside <p> or inline tags: close them first
                while s.stack and s.stack[-1] in ("p", "strong", "em", "i"): s.out.append(f"</{s.stack.pop()}>")
            if t == "li" and "li" in s.stack:
                while s.stack and s.stack[-1] != "li": s.out.append(f"</{s.stack.pop()}>")
                if s.stack: s.out.append(f"</{s.stack.pop()}>")
            s.out.append(f"<{t}>"); s.stack.append(t)
    def handle_endtag(s, tag):
        if s.skip:
            if tag not in VOID: s.skip -= 1
            return
        t = REMAP.get(tag, tag)
        if t in ALLOW and t in s.stack:
            while s.stack:
                x = s.stack.pop(); s.out.append(f"</{x}>")
                if x == t: break
    def handle_data(s, d):
        if s.skip or s.full: return
        d = re.sub(r"\s+", " ", d)
        if not d.strip(): s.out.append(" ") if s.out and not s.out[-1].endswith(" ") else None; return
        s.out.append(html.escape(d, quote=False)); s.n += len(d)
        if s.n > DESC_MAX: s.full = True
def sanitize(raw):
    p = San()
    try: p.feed(raw or ""); p.close()
    except Exception: pass
    while p.stack: p.out.append(f"</{p.stack.pop()}>")
    h = "".join(p.out)
    # drop boilerplate blocks (returns/delivery/supplier text, links) block by block
    blocks = re.split(r"(?=<(?:p|h4|ul|ol|li)>)", h)
    keep = [b for b in blocks if not BOILER.search(b)]
    h = "".join(keep)
    h = re.sub(r"(<br>\s*){3,}", "<br><br>", h)
    h = re.sub(r"<(p|h4|strong|em|i|li|ul|ol)>\s*(<br>\s*)*\s*</\1>", "", h)
    h = re.sub(r"<(p|h4|strong|em|i|li|ul|ol)>\s*</\1>", "", h)
    h = re.sub(r"^(\s*<br>)+|(<br>\s*)+$", "", h.strip())
    h = re.sub(r"\s+", " ", h).strip()
    # balance check: any unclosed tags after block filtering -> fall back to plain text paragraphs
    opens = collections.Counter(re.findall(r"<(p|h4|ul|ol|li|strong|em|i)>", h)); closes = collections.Counter(re.findall(r"</(p|h4|ul|ol|li|strong|em|i)>", h))
    if opens != closes:
        txt = re.sub(r"<[^>]+>", "\n", h); txt = "\n".join(x.strip() for x in txt.split("\n") if x.strip())
        h = "".join(f"<p>{x}</p>" for x in txt.split("\n")[:40])
    return h
def plain(h, n=300):
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)); t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
R_DAYS = re.compile(r"(?:deliver\w*|shipping|arriv\w*)[^.<]{0,40}?(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*(?:business|working) days", re.I)

# ---------- run ----------
def default_csv():
    c = sorted(glob.glob("/workspace/dsz/x_sku_list_zone_rates_*/sku_list_zone_rates.csv"), key=os.path.getmtime)
    if not c: raise SystemExit("no CSV found; pass the path")
    return c[-1]

# Supplier categories are noisy (about 1 in 6 items sits in an unrelated subcategory). A naive-Bayes model trained on the
# supplier's own labels flags titles that clearly belong elsewhere (log-odds > T) and moves them; most labels are right, so
# the model learns from them and the outliers stand out.
RC_STOP = set("the and for with set pcs piece pieces pack packs new premium portable large small mini heavy duty black white grey gray blue red green pink yellow orange purple brown silver gold beige navy khaki multi color colour colors colours style design high quality inch cm mm size sizes type home use made from your easy adjustable durable universal compatible includes include each per two three four five six one pair x".split())
def rc_toks(t):
    return [w for w in set(re.findall(r"[a-z]{3,}", t.lower())) if w not in RC_STOP]
def reclassify(items, T=10.0, a=0.1, debug=False):
    import numpy as np
    t0 = time.time()
    cls = sorted({(it["cat"], it["sub"]) for it in items}); ci = {c: i for i, c in enumerate(cls)}
    TK = [rc_toks(it["title"]) for it in items]
    df = collections.Counter(w for ts in TK for w in ts)
    voc = {w: i for i, w in enumerate(w for w, n in df.items() if n >= 3)}
    V, C = len(voc), len(cls)
    N = np.zeros((V, C), np.float32); Nc = np.zeros(C, np.float32)
    ids = []
    for it, ts in zip(items, TK):
        v = [voc[w] for w in ts if w in voc]; ids.append(v); c = ci[(it["cat"], it["sub"])]
        N[v, c] += 1; Nc[c] += len(v)
    LP = np.log((N + a) / (Nc + a * V)).astype(np.float32)
    moved = []
    for k, (it, v) in enumerate(zip(items, ids)):
        if len(v) < 2: continue
        c = ci[(it["cat"], it["sub"])]
        s = LP[v].sum(0)
        s[c] = np.log((N[v, c] - 1 + a) / (Nc[c] - len(v) + a * V)).sum()  # leave-one-out for its own class
        b = int(s.argmax())
        if b != c and s[b] - s[c] > T: moved.append((k, cls[b], float(s[b] - s[c])))
    if debug: print(f"  reclassify: V={V} C={C} moved {len(moved)} ({time.time()-t0:.0f}s)")
    return moved, cls

def load_json(p, d):
    try: return json.loads(p.read_text())
    except Exception: return d

def main():
    a = sys.argv[1:]
    target = int(a[a.index("--target") + 1]) if "--target" in a else 50000
    dry = "--dry-run" in a
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i-1] != "--target")]
    if "--reprice-only" in a: return reprice_only(pos[0] if pos else None, dry)
    src = pos[0] if pos else default_csv()
    today = datetime.date.today()
    feed_date = datetime.date.fromtimestamp(os.path.getmtime(src))
    t0 = time.time(); print(f"dsz_import: reading {src} (file date {feed_date})")
    ids = load_json(PRIV/"dsz_ids.json", {})
    prev = set(c.get("supplier_sku") for c in load_json(PRIV/"dsz_costs.json", {}).get("products", {}).values())
    pairs = load_json(PRIV/"dsz_pairs.json", {}); pins = pairs.get("pin", {}); supp = pairs.get("suppress", {})
    cnt = collections.Counter(); cands = {}  # dedupe key -> best candidate
    by_ean = {}
    with open(src, newline="", encoding="utf-8", errors="replace") as f:
        rd = csv.reader(f); h = next(rd); ix = {k: i for i, k in enumerate(h)}
        def g(r, k): return r[ix[k]] if k in ix and ix[k] < len(r) else ""
        for r in rd:
            cnt["rows"] += 1
            if len(r) != len(h): cnt["x_malformed_row"] += 1; continue
            sku = g(r, "SKU").strip(); title = re.sub(r"\s+", " ", g(r, "Title")).strip(); cat = g(r, "Category").strip()
            if g(r, "Status").strip().lower() != "in stock": cnt["x_status_not_active"] += 1; continue
            if g(r, "Discontinued").strip().lower() not in ("no", "", "0", "false"): cnt["x_discontinued"] += 1; continue
            stock = R.num(g(r, "Stock Qty")) or 0
            if stock < 3: cnt["x_stock_below_3"] += 1; continue
            price = R.num(g(r, "price"))
            if not price or price <= 0 or price >= 9000: cnt["x_no_real_price"] += 1; continue
            imgs = [g(r, f"Image {i}").strip() for i in range(1, 17)]; imgs = [u for u in imgs if u.startswith("https://")]
            if not imgs: cnt["x_no_image"] += 1; continue
            nsw = R.num(g(r, "NSW_M"))
            if R.placeholder_rate(nsw): cnt["x_nsw_m_placeholder"] += 1; continue
            if not title or not sku or not cat: cnt["x_missing_title_or_category"] += 1; continue
            if sku in supp: cnt["x_duplicate_of_cheaper_listing"] += 1; continue
            desc_raw = g(r, "Description")
            ex = R.exclusion(title, cat, desc_raw)
            if ex: cnt["x_" + ex] += 1; continue
            sp, spe = R.num(g(r, "Special Price")), g(r, "Special Price End Date").strip()
            cost = price; special = False
            if sp and 0 < sp < price and spe:
                try:
                    if datetime.date.fromisoformat(spe[:10]) > today: cost = sp; special = True
                except ValueError: pass
            rrp = R.num(g(r, "RrpPrice"))
            sell, why = R.sell_price(cost + nsw, rrp if rrp and rrp > 0 else None)
            if not sell: cnt["x_" + why] += 1; continue
            cnt["priced_" + why] += 1
            c, sub = R.map_category(cat, title)
            it = {"sku": sku, "title": title, "cat": c, "sub": sub, "src_cat": cat, "price": sell, "cost": cost, "ship": nsw, "rrp": rrp, "special": special,
                  "special_end": spe if special else None, "stock": int(stock), "imgs": imgs[:MAX_IMGS], "url": g(r, "Url"), "supplier": g(r, "Supplier"),
                  "rebate_pct": g(r, "Rebate %"), "rebate_start": g(r, "Rebate Start Date"), "rebate_end": g(r, "Rebate End Date"),
                  "ean": g(r, "EAN Code").strip(), "color": g(r, "Color").strip(), "weight": R.num(g(r, "Weight (kg)")),
                  "dims": [R.num(g(r, "Carton Length (cm)")), R.num(g(r, "Carton Width (cm)")), R.num(g(r, "Carton Height (cm)"))], "prev": sku in prev, "pin": sku in pins}
            it["ratio"] = sell / rrp if rrp and rrp > 0 else 0.95
            k = R.dedupe_key(title)
            o = cands.get(k)
            if o is None or (it["pin"] and not o["pin"]): better = True
            elif o["pin"]: better = False
            else: better = (sell, -stock) < (o["price"], -o["stock"]) or (it["prev"] and not o["prev"] and sell <= o["price"] * 1.02)
            if o is not None: cnt["dup_variant_collapsed"] += 1
            if better: cands[k] = it
    print(f"  pass 1: {cnt['rows']} rows, {len(cands)} unique candidates ({time.time()-t0:.0f}s)")
    # identical item (same EAN) from several suppliers: keep the cheapest
    best_ean = {}
    for k, it in cands.items():
        e = it["ean"]
        if re.fullmatch(r"\d{12,14}", e) and e not in ("0000000000000",):
            o = best_ean.get(e)
            if o is None or it["price"] < cands[o]["price"]: best_ean[e] = k
    drop = [k for k, it in cands.items() if re.fullmatch(r"\d{12,14}", it["ean"]) and best_ean.get(it["ean"]) != k and not it["pin"]]
    for k in drop: del cands[k]
    cnt["dup_same_ean_collapsed"] = len(drop)
    items = list(cands.values()); moved, cls = reclassify(items)
    for k, (c, sub), _ in moved: items[k]["cat"], items[k]["sub"] = c, sub
    cnt["recategorised_by_title"] = len(moved); print(f"  recategorised by title: {len(moved)}")
    if os.environ.get("DSZ_PICKLE"):
        import pickle; pickle.dump(cands, open(os.environ["DSZ_PICKLE"], "wb"))
    # fair spread across subcategories (water-filling cap), best value first
    groups = collections.defaultdict(list)
    for it in cands.values(): groups[(it["cat"], it["sub"])].append(it)
    for gk in groups: groups[gk].sort(key=lambda x: (not x["pin"], not x["prev"], round(x["ratio"], 3), -x["stock"], x["price"], x["sku"]))
    sizes = sorted(len(v) for v in groups.values())
    if sum(sizes) <= target: cap = max(sizes or [0])
    else:
        lo, hi = 0, max(sizes)
        while lo < hi:
            m = (lo + hi + 1) // 2
            if sum(min(s, m) for s in sizes) <= target: lo = m
            else: hi = m - 1
        cap = lo
    sel = [it for gk in sorted(groups) for it in groups[gk][:cap]]
    cnt["not_selected_over_target"] = len(cands) - len(sel)
    print(f"  selected {len(sel)} of {len(cands)} (per-subcategory cap {cap})")
    # ids (permanent)
    nxt = max(ids.values() or [0]) + 1
    for it in sorted(sel, key=lambda x: x["sku"]):
        if it["sku"] not in ids: ids[it["sku"]] = nxt; nxt += 1
        it["n"] = ids[it["sku"]]; it["id"] = pid(it["n"])
    if dry:
        print(json.dumps(cnt, indent=1)); return
    # pass 2: descriptions (sanitised) only for the selected items
    want = {it["sku"]: it for it in sel}
    with open(src, newline="", encoding="utf-8", errors="replace") as f:
        rd = csv.reader(f); h = next(rd); si, di = h.index("SKU"), h.index("Description")
        for r in rd:
            if len(r) != len(h): continue
            it = want.get(r[si].strip())
            if it is None: continue
            d = r[di]
            m = R_DAYS.search(re.sub(r"<[^>]+>", " ", d)); it["days"] = f"{m.group(1)}–{m.group(2)}" if m and int(m.group(1)) < int(m.group(2)) <= 30 else None
            it["desc"] = sanitize(d)
    for it in sel: it.setdefault("desc", ""); it.setdefault("days", None)
    print(f"  pass 2: descriptions ({time.time()-t0:.0f}s)")
    write_all(sel, cnt, src, feed_date, ids, target, cap)
    apply_pins(sel, pins)
    print(f"dsz_import: done in {time.time()-t0:.0f}s")

def write_all(sel, cnt, src, feed_date, ids, target, cap):
    PRIV.mkdir(parents=True, exist_ok=True)
    (PRIV/"dsz_ids.json").write_text(json.dumps(ids, separators=(",", ":"), sort_keys=True))
    costs = {it["id"]: {"supplier_sku": it["sku"], "supplier_url": it["url"], "supplier_code": it["supplier"], "supplier_category": it["src_cat"],
                        "cost": it["cost"], "special_price_used": it["special"], "special_end": it["special_end"], "shipping_nsw_m": it["ship"],
                        "cost_total": round(it["cost"] + it["ship"], 2), "rrp": it["rrp"], "our_price": it["price"],
                        "margin_aud": round(R.net(it["price"]) - it["cost"] - it["ship"], 2), "margin_pct": R.margin_pct(it["price"], it["cost"] + it["ship"]),
                        "stock_qty": it["stock"], "rebate_pct": it["rebate_pct"], "rebate_start": it["rebate_start"], "rebate_end": it["rebate_end"]} for it in sel}
    (PRIV/"dsz_costs.json").write_text(json.dumps({"_note": "PRIVATE. Supplier cost records for TR-DZ products. Never commit or publish.", "feed": src,
                                                    "feed_date": feed_date.isoformat(), "generated": datetime.datetime.now().isoformat(timespec="minutes"), "products": costs}, separators=(",", ":")))
    # public cards (sorted by category order, subcategory, then rank)
    order = {c["id"]: i for i, c in enumerate(json.loads((ROOT/"data/shop.json").read_text())["categories"])}
    for it in sel:
        if it["cat"] not in order: raise SystemExit(f"category {it['cat']} missing from data/shop.json")
    rank = {id(it): i for i, it in enumerate(sel)}
    sel.sort(key=lambda x: (order[x["cat"]], x["sub"].lower(), rank[id(x)]))
    items = [[it["n"], it["title"], it["cat"], it["sub"], int(round(it["price"] * 100)), it["imgs"][0].replace(IMG_BASE, "")] for it in sel]
    CARDS.parent.mkdir(parents=True, exist_ok=True)
    pub = {"_note": "Public card data for bulk-imported products (TR-DZ-######). id, name, category, subcategory, price_cents (final AUD price incl. standard delivery to Sydney metro), image path (relative to img_base). Generated by scripts/dsz_import.py; no costs or supplier data.",
           "updated": feed_date.isoformat(), "img_base": IMG_BASE, "fields": ["n", "name", "cat", "sub", "price_cents", "img"], "items": items}
    CARDS.write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")).replace("],[", "],\n["))
    # pages (shop.py is imported only now, so it reads the new cards.json)
    import shop
    C = shop.chrome(); OUT_PAGES.mkdir(parents=True, exist_ok=True)
    keep = set()
    for it in sel:
        d = OUT_PAGES/it["id"].lower(); keep.add(d.name); d.mkdir(exist_ok=True)
        s = shop.dsz_page(C, it, feed_date)
        f = d/"index.html"
        if not f.exists() or f.read_text() != s: f.write_text(s)
    gone = 0
    for d in OUT_PAGES.iterdir():
        if d.is_dir() and d.name not in keep: shutil.rmtree(d); gone += 1
    per = collections.Counter(it["cat"] for it in sel)
    prices = sorted(it["price"] for it in sel)
    rep = {"generated": datetime.datetime.now().isoformat(timespec="minutes"), "feed": src, "feed_date": feed_date.isoformat(), "target": target, "subcategory_cap": cap,
           "listed": len(sel), "pages_removed": gone, "counts": dict(sorted(cnt.items())), "per_category": dict(per.most_common()),
           "price_min": prices[0] if prices else None, "price_median": prices[len(prices)//2] if prices else None, "price_max": prices[-1] if prices else None}
    (PRIV/"dsz_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))

def reprice_only(src, dry):
    t0 = time.time(); today = datetime.date.today()
    old = load_json(PRIV/"dsz_costs.json", {}); costs = old.get("products", {})
    if not costs: raise SystemExit("reprice-only: no dsz_costs.json")
    src = src or old["feed"]; feed_date = datetime.date.fromisoformat(old["feed_date"])
    ids = load_json(PRIV/"dsz_ids.json", {}); pairs = load_json(PRIV/"dsz_pairs.json", {})
    cards = load_json(CARDS, {}).get("items", [])
    by_n = {x[0]: x for x in cards}; cnt = collections.Counter(); want = {}; sel = []
    for x in cards:  # keep current order (category, subcategory, rank)
        i = pid(x[0]); c = costs.get(i)
        if not c: raise SystemExit(f"reprice-only: {i} has no cost record")
        if c.get("special_price_used") and c.get("special_end"):
            try:
                if datetime.date.fromisoformat(c["special_end"][:10]) <= today: cnt["special_price_expired_kept_recorded_cost"] += 1
            except ValueError: pass
        ct = round(c["cost"] + c["shipping_nsw_m"], 2); rrp = c.get("rrp")
        sell, why = R.sell_price(ct, rrp if rrp and rrp > 0 else None)
        if not sell: cnt["x_" + why] += 1; continue
        cnt["priced_" + why] += 1
        it = {"sku": c["supplier_sku"], "n": x[0], "id": i, "title": x[1], "cat": x[2], "sub": x[3], "src_cat": c["supplier_category"], "price": sell,
              "old_price": x[4] / 100, "cost": c["cost"], "ship": c["shipping_nsw_m"], "rrp": rrp, "special": c["special_price_used"], "special_end": c["special_end"],
              "stock": c["stock_qty"], "url": c["supplier_url"], "supplier": c["supplier_code"], "rebate_pct": c["rebate_pct"], "rebate_start": c["rebate_start"],
              "rebate_end": c["rebate_end"], "card_img": x[5]}
        if ids.get(it["sku"]) != x[0]: raise SystemExit(f"reprice-only: id map mismatch for {i}")
        want[it["sku"]] = it; sel.append(it)
    print(f"reprice-only: {len(cards)} listed -> {len(sel)} kept; {dict(cnt)}")
    if dry: return sel, cnt
    with open(src, newline="", encoding="utf-8", errors="replace") as f:  # text, photos and specs for the page (unchanged data)
        rd = csv.reader(f); h = next(rd); ix = {k: i for i, k in enumerate(h)}
        def g(r, k): return r[ix[k]] if k in ix and ix[k] < len(r) else ""
        for r in rd:
            if len(r) != len(h): continue
            it = want.get(g(r, "SKU").strip())
            if it is None or "desc" in it: continue
            imgs = [g(r, f"Image {i}").strip() for i in range(1, 17)]; it["imgs"] = [u for u in imgs if u.startswith("https://")][:MAX_IMGS]
            it.update(ean=g(r, "EAN Code").strip(), color=g(r, "Color").strip(), weight=R.num(g(r, "Weight (kg)")),
                      dims=[R.num(g(r, "Carton Length (cm)")), R.num(g(r, "Carton Width (cm)")), R.num(g(r, "Carton Height (cm)"))])
            d = r[ix["Description"]]
            m = R_DAYS.search(re.sub(r"<[^>]+>", " ", d)); it["days"] = f"{m.group(1)}–{m.group(2)}" if m and int(m.group(1)) < int(m.group(2)) <= 30 else None
            it["desc"] = sanitize(d)
    miss = [it["id"] for it in sel if "desc" not in it]
    if miss: raise SystemExit(f"reprice-only: {len(miss)} listed items not found in {src}, e.g. {miss[:5]}")
    bad = [it["id"] for it in sel if not it["imgs"] or it["imgs"][0].replace(IMG_BASE, "") != it["card_img"]]
    if bad: raise SystemExit(f"reprice-only: feed photos differ from the listing for {len(bad)} items, e.g. {bad[:5]}")
    print(f"  feed re-read ({time.time()-t0:.0f}s)")
    target = load_json(PRIV/"dsz_report.json", {}).get("target", 50000); cap = load_json(PRIV/"dsz_report.json", {}).get("subcategory_cap")
    cnt["reprice_only"] = 1
    write_all(sel, cnt, src, feed_date, ids, target, cap)
    apply_pins(sel, pairs.get("pin", {}))
    print(f"reprice-only: done in {time.time()-t0:.0f}s")
    return sel, cnt

def apply_pins(sel, pins):
    """Hand-built products with a cheaper identical bulk item: pause them and point their URL at the bulk page (scripts/shop.py writes a redirect).
    Un-pauses them again if the bulk item is no longer listed or no longer cheaper."""
    F = ROOT/"data/products.json"; d = json.loads(F.read_text()); by = {it["sku"]: it for it in sel}; n = 0
    for p in d["products"]:
        sku = next((k for k, v in pins.items() if v == p["id"]), None)
        it = by.get(sku) if sku else None
        if it and isinstance(p.get("our_price"), (int, float)) and it["price"] < p["our_price"]:
            if p.get("replaced_by") != it["id"] or p.get("status") != "paused": n += 1
            p.update(status="paused", paused_reason="cheaper_alternative", replaced_by=it["id"])
        elif p.get("paused_reason") == "cheaper_alternative":
            p["status"] = "active"; p.pop("paused_reason", None); p.pop("replaced_by", None); n += 1
    F.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    print(f"  hand-built products replaced by a cheaper identical item: {sum(1 for p in d['products'] if p.get('replaced_by'))} ({n} changed)")

if __name__ == "__main__": main()
