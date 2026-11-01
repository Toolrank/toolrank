#!/usr/bin/env python3
"""ToolRank store: static pages from data/shop.json + data/products.json (navy/yellow marketplace design).
Outputs: index.html (store home), shop/index.html, shop/<category>/index.html, shop/p/<product>/index.html (listed products only),
shop/{shipping,returns,terms,privacy}/index.html. Styles: assets/shop.css. Photos: assets/img/ (hero, category tiles, banner), assets/shop/p/ (products).
A product is listed only when status == "active" AND our_price is a number AND it has an order method (stripe_link, or order_by_email = mailto order).
Private product fields (supplier, supplier_url, costs, margins) are never written to HTML.
Fonts and analytics/PWA scripts are copied from about/index.html; header, nav and footer are the store's own.
Run standalone:  python3 scripts/shop.py      Preview with drafts (outside the repo):  python3 scripts/shop.py --preview /workspace/store-preview
scripts/build.py calls build() too (hourly workflow), so a full site build regenerates the store and adds its URLs to sitemap.xml."""
import json, re, html, pathlib, shutil, sys, hashlib, urllib.parse, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://toolrank.io"; E = html.escape
CFG = json.loads((ROOT/"data/shop.json").read_text())
PJ = json.loads((ROOT/"data/products.json").read_text())
CATS = CFG["categories"]; CAT = {c["id"]: c for c in CATS}
DSZF = ROOT/"data/dsz/cards.json"  # bulk-imported products (scripts/dsz_import.py): public card data only
DZ = json.loads(DSZF.read_text()) if DSZF.exists() else {"items": [], "img_base": "", "updated": ""}
CH = 48  # cards per data chunk / per "Show more"
MAIL = CFG["contact_email"]
POLICIES = [("shipping", "Shipping"), ("returns", "Returns & refunds"), ("terms", "Terms of sale"), ("privacy", "Privacy")]
TAGLINE = "Tools for every trade"

def store_ld():
    o = {"@type": "OnlineStore", "@id": BASE + "/#store", "name": "ToolRank", "url": BASE + "/", "email": MAIL, "slogan": TAGLINE,
         "description": "Tools and equipment for every trade, shipped direct from Australian suppliers.",
         "logo": BASE + "/assets/icons/icon-512.png", "areaServed": {"@type": "Country", "name": "Australia"},
         "contactPoint": {"@type": "ContactPoint", "contactType": "customer service", "email": MAIL, "areaServed": "AU", "availableLanguage": "en"}}
    return o
def seller_line():
    return "ToolRank"
def operator():
    return "The seller is ToolRank, Sydney NSW."
def sellable(p):
    return (p.get("status") == "active" and isinstance(p.get("our_price"), (int, float)) and p["our_price"] > 0
            and (bool(p.get("stripe_link")) or p.get("order_by_email") is True))
def money(v): return f"A${v:,.2f}"
def img(p): return p.get("image") or f"/assets/img/cat-{p['category']}.webp"
def on_sale(p):
    if not (isinstance(p.get("regular_price"), (int, float)) and p["regular_price"] > p["our_price"] and p.get("sale_ends")): return False
    return datetime.date.today().isoformat() <= p["sale_ends"]
def nice_date(iso):
    d = datetime.date.fromisoformat(iso[:10]); return f"{d.day} {d.strftime('%b %Y')}"
def order_href(p):
    subj = f'Order {p.get("sku", p["id"])}: {p["name"]}'
    body = (f'Hi ToolRank,\n\nI would like to order:\n{p["name"]}\nProduct ID: {p.get("sku", p["id"])}\nPrice: {money(p["our_price"])}\nQuantity: 1\n\n'
            f'Name:\nDelivery address (incl. postcode):\nPhone:\n\nThanks')
    return f"mailto:{MAIL}?subject={urllib.parse.quote(subj)}&body={urllib.parse.quote(body)}"
def buy_href(p):
    return p["stripe_link"] if p.get("stripe_link") else order_href(p)

# ---------- icons (24px stroke) ----------
IC = {
 "power-tools": '<path d="M3 7h11a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2h-4l-1.2 7H6l1-7H3zM16 9.5h5"/>',
 "hand-tools": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
 "hardware": '<path d="M12 2.5l8.2 4.75v9.5L12 21.5l-8.2-4.75v-9.5z"/><circle cx="12" cy="12" r="3.2"/>',
 "building": '<path d="M3 5h18v14H3zM3 9.7h18M3 14.3h18M9 5v4.7M15 9.7v4.6M9 14.3V19"/>',
 "automotive": '<path d="M3 13l2.2-5.5h13.6L21 13v4H3zM3 13h18"/><circle cx="7.5" cy="17" r="1.8"/><circle cx="16.5" cy="17" r="1.8"/>',
 "garden": '<path d="M12 21v-9M12 13c-5 0-8-3-8-8 5 0 8 3 8 8zm0-1.5c0-5 3-8 8-8 0 5-3 8-8 8z"/>',
 "cleaning": '<path d="M5.5 8h13l-1.6 12H7.1zM4 8h16M9 8V5h6v3"/>',
 "safety": '<path d="M3 18h18M5 18v-2a7 7 0 0 1 14 0v2M10 9.2V6h4v3.2"/>',
 "workshop-storage": '<path d="M3 9h18v10H3zM8.5 9V6h7v3M3 13.5h18M11 13.5v2h2v-2"/>',
 "bbq-camping": '<path d="M12 4 3 20h18zM12 4v0M9 20l3-6 3 6M2 20h20"/>',
 "music-gear": '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
 "furniture": '<path d="M4 11V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3M3 11h18v6H3zM5 17v2M19 17v2"/>',
 "home-living": '<path d="M3 11 12 4l9 7M5 10v10h14V10M10 20v-5h4v5"/>',
 "kitchen": '<path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4zM2 10h20M9 6.5c0-1.2 1.2-2 3-2s3 .8 3 2"/>',
 "bathroom": '<path d="M3 12h18v3a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4zM6 12V5.5a2 2 0 0 1 4 0M7 19l-1 2M17 19l1 2"/>',
 "appliances": '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="13" r="4"/><path d="M8 6.5h2"/>',
 "electronics": '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/>',
 "office": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5h6v2M3 12h18"/>',
 "sports-fitness": '<path d="M6 7v10M3 9.5v5M18 7v10M21 9.5v5M6 12h12"/>',
 "pets": '<circle cx="6.5" cy="10" r="1.8"/><circle cx="10" cy="5.8" r="1.8"/><circle cx="14" cy="5.8" r="1.8"/><circle cx="17.5" cy="10" r="1.8"/><path d="M12 12c-2.8 0-5 3-5 5.3 0 1.6 1.4 2.2 2.8 1.7 1-.4 1.6-.5 2.2-.5s1.2.1 2.2.5c1.4.5 2.8-.1 2.8-1.7 0-2.3-2.2-5.3-5-5.3z"/>',
 "baby-kids": '<path d="M4 5h7v8H4zM11 5a8 8 0 0 1 8 8H4M2 3h2"/><circle cx="7" cy="18" r="2"/><circle cx="16" cy="18" r="2"/>',
 "toys-games": '<rect x="3" y="12" width="8" height="8" rx="1"/><rect x="13" y="12" width="8" height="8" rx="1"/><rect x="8" y="3" width="8" height="8" rx="1"/>',
 "health-beauty": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
 "fashion": '<path d="M8 3 3 6l2 4 2-1v12h10V9l2 1 2-4-5-3a4 4 0 0 1-8 0z"/>',
 "party-gifts": '<rect x="3" y="8" width="18" height="4"/><path d="M5 12v9h14v-9M12 8v13M12 8c-2-4-6-4-6-1s6 1 6 1zm0 0c2-4 6-4 6-1s-6 1-6 1z"/>',
 "search": '<circle cx="11" cy="11" r="7"/><path d="M20.5 20.5 16 16"/>',
 "quote": '<path d="M4 5h16v11H8l-4 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
 "help": '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.4M12 17h.01"/>',
 "pin": '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
 "truck": '<path d="M2 6h12v10H2zM14 9h4.5l3.5 3.5V16h-8"/><circle cx="6" cy="17.5" r="1.8"/><circle cx="17.5" cy="17.5" r="1.8"/>',
 "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
 "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
 "chev": '<path d="m9 6 6 6-6 6"/>',
 "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.4"/>',
 "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
 "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 7 8.5-7"/>',
}
def ic(k, cls="ic"):
    return f'<svg class="{cls}" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{IC[k]}</svg>'
LOGO = ('<a class="logo" href="/" aria-label="ToolRank home"><svg class="lm" viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="#f5c518" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + IC["hand-tools"] + '</svg><span class="lt"><span class="ln">Tool<b>Rank</b></span><span class="lg">' + TAGLINE + '</span></span></a>')

# ---------- page chrome ----------
def search_index(prods):
    ix = [{"t": "All products", "u": "/shop/", "k": "Shop"}]
    ix += [{"t": c["title"], "u": f'/shop/{c["id"]}/', "k": "Category", "x": c["blurb"]} for c in CATS]
    ix += [{"t": t, "u": f"/shop/{k}/", "k": "Help"} for k, t in POLICIES]
    ix += [{"t": p["name"], "u": f'/shop/p/{p["id"]}/', "k": money(p["our_price"]), "x": CAT[p["category"]]["title"] + " " + p.get("sku", "")} for p in prods]
    return json.dumps(ix, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def search_form(cls, fid, big=False):
    return (f'<form class="sf {cls}" action="/shop/" method="get" role="search" data-search><label class="sr" for="{fid}">Search the store</label>'
            f'<input id="{fid}" name="q" type="search" placeholder="Search products&hellip;" autocomplete="off">'
            f'<button type="submit" aria-label="Search">{ic("search")}</button><div class="sres" role="listbox" hidden></div></form>')

def header(icons=True):
    cats = "".join(f'<a href="/shop/{c["id"]}/">{ic(c["id"]) if icons else ""}{E(c["title"])}</a>' for c in CATS)
    trade = f"mailto:{MAIL}?subject={urllib.parse.quote('Trade / bulk quote')}"
    return ('<a class="skip" href="#main">Skip to content</a><header class="hd"><div class="wrap hdr">' + LOGO + search_form("hs", "q1") +
            f'<nav class="hico" aria-label="Help"><a href="/shop/shipping/">{ic("help")}<span>Help</span></a><a href="mailto:{MAIL}?subject={urllib.parse.quote("Quote request")}">{ic("quote")}<span>Get a quote</span></a></nav></div>'
            '<div class="nb"><div class="wrap nbr"><details class="allc"><summary>' + ic("menu") + 'All Categories</summary><div class="allm">' + cats + '<a href="/shop/">All products</a></div></details>'
            '<nav class="nl" aria-label="Main"><a href="/">Home</a><a href="/shop/">Shop</a><a href="/shop/furniture/">Furniture</a><a href="/shop/home-living/">Home</a><a href="/shop/kitchen/">Kitchen</a><a href="/shop/bbq-camping/">BBQ &amp; Camping</a><a href="/shop/#sale">Launch sale</a>'
            f'<a href="{trade}">Trade &amp; Bulk</a><a class="nx" href="/shop/shipping/">Shipping</a><a class="nx" href="/shop/returns/">Returns</a><a href="mailto:{MAIL}">Contact</a></nav>'
            '<p class="strip">' + ic("pin") + 'Australian suppliers<span>|</span>' + ic("truck") + 'Ships direct</p></div></div></header>')

def footer():
    yr = CFG.get("policies_updated", "2026")[:4]; sl = seller_line()
    return ('<footer class="ft"><div class="wrap ftg"><div class="ftb">' + LOGO + '<p>Shipped direct from Australian suppliers.</p>'
            f'<p><a href="mailto:{MAIL}">{ic("mail")}{MAIL}</a></p></div>'
            '<nav aria-label="Shop"><p class="fh">Shop</p><a href="/shop/">All products</a>' + "".join(f'<a href="/shop/{c["id"]}/">{E(c["title"])}</a>' for c in CATS) + '</nav>'
            '<nav aria-label="Help"><p class="fh">Help</p>' + "".join(f'<a href="/shop/{k}/">{t}</a>' for k, t in POLICIES) + f'<a href="mailto:{MAIL}">Contact</a></nav></div>'
            f'<div class="wrap ftl"><p>&copy; {yr} ToolRank. Prices in Australian dollars.{(" Seller: " + sl + ".") if sl else ""}</p>'
            '<p>' + ic("pin", "ic sm") + 'Australian suppliers &middot; Ships direct &middot; Secure checkout</p></div></footer>')

SEARCH_JS = r"""<script>(function(){var I=JSON.parse(document.getElementById("six").textContent);function n(s){return(s||"").toLowerCase()}
document.querySelectorAll("[data-search]").forEach(function(f){var q=f.querySelector("input"),r=f.querySelector(".sres");
function go(){var v=n(q.value).trim();if(!v){r.hidden=true;r.innerHTML="";return[]}var w=v.split(/\s+/),m=I.filter(function(x){var h=n(x.t+" "+(x.x||"")+" "+x.k);return w.every(function(t){return h.indexOf(t)>-1})}).slice(0,8);
r.innerHTML=m.length?"":'<p>No match. Email <a href="mailto:hello@toolrank.io">hello@toolrank.io</a> and we&rsquo;ll find it.</p>';m.forEach(function(x){var a=document.createElement("a"),s=document.createElement("span"),k=document.createElement("small");a.setAttribute("role","option");a.href=x.u;s.textContent=x.t;k.textContent=x.k;a.appendChild(s);a.appendChild(k);r.appendChild(a)});r.hidden=false;return m}
q.addEventListener("input",go);q.addEventListener("focus",go);f.addEventListener("submit",function(e){var m=go();if(m.length){e.preventDefault();location.href=m[0].u}});
document.addEventListener("click",function(e){if(!f.contains(e.target))r.hidden=true});q.addEventListener("keydown",function(e){if(e.key==="Escape")r.hidden=true})});
document.querySelectorAll("[data-car]").forEach(function(c){var t=c.querySelector(".track");c.querySelectorAll("[data-dir]").forEach(function(b){b.addEventListener("click",function(){t.scrollBy({left:(+b.dataset.dir)*t.clientWidth*.9,behavior:"smooth"})})})});
document.querySelectorAll(".gal").forEach(function(g){var m=g.querySelector(".gm img");g.querySelectorAll(".gt button").forEach(function(b){b.addEventListener("click",function(){m.src=b.dataset.src||b.querySelector("img").src;g.querySelectorAll(".gt button").forEach(function(x){x.removeAttribute("aria-current")});b.setAttribute("aria-current","true")})})});
var u=new URLSearchParams(location.search).get("q");if(u){var i=document.querySelector("[data-search] input");if(i){i.value=u;i.dispatchEvent(new Event("input"));i.focus()}}
document.addEventListener("click",function(e){var d=document.querySelector(".allc[open]");if(d&&!d.contains(e.target))d.removeAttribute("open")})})()</script>"""

def chrome():
    s = (ROOT/"about/index.html").read_text()
    pre = s.split("<!--SEO-->", 1)[0]
    fonts = re.search(r"<!--FONTS-->.*?<!--/FONTS-->", s, re.S)
    tail = s.split("</footer>", 1)[1] if "</footer>" in s else "</body></html>"
    tail = re.sub(r'<script defer src="/assets/hero\.js[^"]*"></script>', "", tail)
    v = hashlib.sha1((ROOT/"assets/shop.css").read_bytes()).hexdigest()[:8]
    h = (fonts.group(0) if fonts else "") + f'<link rel="stylesheet" href="/assets/shop.css?v={v}"></head><body class="store">'
    return pre, h, tail

def head(title, desc, path, ld, robots="index,follow,max-snippet:-1", image="/assets/img/hero.webp"):
    url = BASE + path
    if len(title) > 60: title = title[:59].rsplit(" ", 1)[0] + "…"
    if len(desc) > 160: desc = desc[:159].rsplit(" ", 1)[0] + "…"
    return (f'<!--SEO--><title>{E(title)}</title><meta name="description" content="{E(desc)}">\n<link rel="canonical" href="{url}"><meta name="robots" content="{robots}">'
            f'<meta name="theme-color" content="#1b2333"><meta name="color-scheme" content="light"><meta property="og:type" content="website"><meta property="og:site_name" content="ToolRank">'
            f'<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}{image}">'
            f'<meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png">'
            f'<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png"><link rel="manifest" href="/manifest.webmanifest">\n'
            f'<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": [store_ld()] + ld}, ensure_ascii=False)}</script><!--/SEO-->')

def doc(C, prods, headblock, main, preview=False):
    pre, h, tail = C
    banner = '<div class="pvbar" role="note">PREVIEW BUILD: draft products shown for layout only. Not for publishing.</div>' if preview else ""
    return (pre + headblock + h + header() + '<main id="main" class="shop">' + banner + main + "</main>" + footer()
            + shop_js_tag() + tail)

def crumbs(*items):
    parts = ['<a href="/">Home</a>', '<a href="/shop/">Shop</a>'] + [f'<a href="{u}">{E(t)}</a>' if u else f'<span aria-current="page">{E(t)}</span>' for t, u in items]
    return '<nav class="crumb" aria-label="Breadcrumb">' + " <span>›</span> ".join(parts) + "</nav>"
def crumb_ld(*items):
    li = [("Home", BASE + "/"), ("Shop", BASE + "/shop/")] + list(items)
    return {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(li, 1)]}

def sidebar(active=""):
    return ('<aside class="side" aria-label="Shop by category"><p class="sh3">Shop by Category</p><nav>' +
            "".join(f'<a href="/shop/{c["id"]}/"{" aria-current=page" if active == c["id"] else ""}>{ic(c["id"])}<span>{E(c["title"])}</span>{ic("chev", "ic cv")}</a>' for c in CATS)
            + f'<a href="/shop/"{" aria-current=page" if active == "all" else ""}>{ic("tag")}<span>All products</span>{ic("chev", "ic cv")}</a></nav>'
            f'<div class="sbox"><p><b>Need something else?</b></p><p>Email <a href="mailto:{MAIL}">{MAIL}</a> for a quote.</p></div></aside>')

def price_html(p, big=False):
    s = f'<span class="pr">{money(p["our_price"])}</span>'
    if on_sale(p):
        s = (f'<span class="badge">Launch price</span>' + s +
             f'<span class="reg">{money(p["regular_price"])} after {nice_date(p["sale_ends"])}</span>')
    return f'<p class="pp{" big" if big else ""}">{s}</p>'

def stock_html(p):
    return f'<p class="stk">{ic("check", "ic sm")}In stock</p>' if p.get("stock") == "in_stock" else ""

def fit_html(p):
    o = '<p class="uf">Universal fit</p>' if p.get("universal") else ""
    if p.get("fit"): o += f'<p class="fit"><b>Fit:</b> {E(p["fit"])}</p>'
    if p.get("model_no"): o += f'<p class="fit"><b>Model / part no.:</b> {E(p["model_no"])}</p>'
    return o
def gslug(g): return "g-" + re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-")
def grouped(c, items, preview):
    gs = [g for g in c.get("groups", []) if any(p.get("group") == g for p in items)]
    if not gs: return grid(items, preview)
    rest = [p for p in items if p.get("group") not in gs]
    chips = '<nav class="chips" aria-label="Jump to group">' + "".join(f'<a href="#{gslug(g)}">{E(g)} <span>{sum(1 for p in items if p.get("group") == g)}</span></a>' for g in gs) + '</nav>'
    out = chips + "".join(f'<section class="grp" id="{gslug(g)}"><h2>{E(g)}</h2>' + grid([p for p in items if p.get("group") == g], preview) + '</section>' for g in gs)
    if rest: out += '<section class="grp" id="g-more"><h2>More</h2>' + grid(rest, preview) + '</section>'
    return out
def card(p, preview=False, lazy=True):
    href = f'/shop/p/{p["id"]}/'
    if not sellable(p):
        return (f'<article class="pc"><a class="pci" href="{href}"><img src="{E(img(p))}" alt="{E(p["name"])}" width="400" height="400" loading="lazy"></a>'
                f'<div class="pcb"><p class="pcc">{E(CAT[p["category"]]["title"])}</p><h3><a href="{href}">{E(p["name"])}</a></h3><p class="pp"><span class="tbc">Draft, not for sale</span></p></div></article>')
    return (f'<article class="pc"><a class="pci" href="{href}"><img src="{E(img(p))}" alt="{E(p["name"])}" width="400" height="400"{" loading=lazy" if lazy else ""}></a>'
            f'<div class="pcb"><p class="pcc">{E(CAT[p["category"]]["title"])}</p><h3><a href="{href}">{E(p["name"])}</a></h3>{'<p class="uf">Universal fit</p>' if p.get("universal") else ""}{price_html(p)}{stock_html(p)}'
            f'<a class="btn ob" href="{E(buy_href(p))}">Order now</a></div></article>')

def carousel(title, items, more_href, hid, preview=False):
    if not items: return ""
    return (f'<section class="blk car" id="{hid}" data-car><div class="bh"><h2>{E(title)}</h2><div class="cnav"><a href="{more_href}">View all</a>'
            f'<button type="button" data-dir="-1" aria-label="Scroll left">‹</button><button type="button" data-dir="1" aria-label="Scroll right">›</button></div></div>'
            f'<div class="track">{"".join(card(p, preview) for p in items)}</div></section>')

def grid(items, preview=False):
    if not items: return empty()
    return '<div class="pg">' + "".join(card(p, preview) for p in items) + "</div>"

def empty():
    return f'<div class="empty"><h3>New stock landing soon.</h3><p>Email <a href="mailto:{MAIL}">{MAIL}</a> for a quote.</p></div>'

def alt(c): return c.get("alt") or ALT.get(c["id"]) or c["title"]
def tiles():
    t = "".join(f'<a class="tile" href="/shop/{c["id"]}/"><img src="/assets/img/cat-{c["id"]}.webp" alt="{E(alt(c))}" width="640" height="480" loading="lazy"><span>{E(c["title"])}</span></a>' for c in CATS)
    if len(CATS) % 5: t += '<a class="tile" href="/shop/"><img src="/assets/img/hero.webp" alt="Tools on a workbench by Sydney Harbour" width="640" height="360" loading="lazy"><span>All products</span></a>'
    n = len(CATS) + (1 if len(CATS) % 5 else 0)
    return f'<div class="tiles{" t6" if n % 6 == 0 and n % 5 else ""}">' + t + "</div>"  # t6: 12 tiles sit in two even rows of 6 on desktop
ALT = {"power-tools": "Cordless drill with drill bits and a saw blade on a workbench", "hand-tools": "Spanners, screwdrivers, pliers and a hammer on a wooden bench",
       "hardware": "Screws, bolts, nuts, washers and a brass hinge", "building": "Hard hat on a stack of bricks with a trowel and spirit levels",
       "automotive": "Car wheel, socket set, torque wrench and floor jack in a garage", "garden": "Secateurs, garden fork, rake, hose and gloves on a lawn",
       "cleaning": "Bucket, scrubbing brushes, squeegee, cloths and a spray bottle", "safety": "Hi-vis vest, safety glasses, earmuffs, work gloves and a hard hat",
       "workshop-storage": "Steel tool chest, workbench, pegboard and shelving in a workshop",
       "bbq-camping": "Charcoal BBQ with fresh vegetables in front of a canvas bell tent",
       "music-gear": "Acoustic guitar on a stand, boom mic stand, cables, drumsticks and a music stand"}

TRUST = ('<ul class="trust"><li>' + ic("pin") + '<span>Australian<br>suppliers</span></li><li>' + ic("truck") + '<span>Ships<br>direct</span></li>'
         '<li>' + ic("lock") + '<span>Secure<br>checkout</span></li></ul>')

def banner():
    return ('<section class="blk bnr"><img src="/assets/img/ship.webp" alt="Boxed orders being loaded into a delivery van at a warehouse" width="1280" height="720" loading="lazy">'
            '<div><h2>Sourced from Australian suppliers, shipped direct.</h2><p>Your order goes straight from the supplier&rsquo;s warehouse to your door.</p>'
            '<a class="btn dk" href="/shop/shipping/">Shipping info</a></div></section>')

# ---------- pages ----------
def listed(prods): return [p for p in prods if sellable(p)]
def sale_items(prods): return [p for p in listed(prods) if on_sale(p)]
def newest(prods):
    rest = [p for p in listed(prods) if not on_sale(p)]
    seen, out = set(), []
    for p in rest:  # one per category first, then the rest
        if p["category"] not in seen: seen.add(p["category"]); out.append(p)
    return out + [p for p in rest if p not in out]

def site_home(C, prods, preview):
    """toolrank.io/ : the store front."""
    main = ('<div class="wrap"><section class="hero"><img class="hbg" src="/assets/img/hero.webp" alt="" width="1280" height="720" fetchpriority="high">'
            '<div class="hin"><p class="eye">Your Australian tool store</p><h1>Tools for <span>every trade</span></h1>'
            '<p class="sub">Tools, home, garden, outdoor and more. Shipped direct from Australian suppliers.</p>'
            + search_form("hsf", "q2") + TRUST + '</div></section>'
            '<div class="lay">' + sidebar() + '<div class="mc">'
            '<section class="blk"><div class="bh"><h2>Popular Categories</h2></div>' + tiles() + '</section>'
            + carousel("Launch sale", sale_items(prods), "/shop/#sale", "sale", preview)
            + carousel("Just landed", newest(prods)[:14], "/shop/", "new", preview) + explore()
            + (empty() if not listed(prods) else "") + banner() + '</div></div></div>')
    ld = [{"@type": "WebSite", "@id": BASE + "/#website", "name": "ToolRank", "url": BASE + "/", "publisher": {"@id": BASE + "/#store"},
           "potentialAction": {"@type": "SearchAction", "target": BASE + "/shop/?q={q}", "query-input": "required name=q"}},
          {"@type": "ItemList", "name": "Shop categories", "itemListElement": [{"@type": "ListItem", "position": i, "name": c["title"], "url": f'{BASE}/shop/{c["id"]}/'} for i, c in enumerate(CATS, 1)]}]
    return doc(C, prods, head("ToolRank | Tools for every trade, shipped direct",
                       f"{n_live():,} products: tools, hardware, furniture, home, kitchen, garden, outdoor, pets, sports and more, shipped direct from Australian suppliers.", "/", ld), main, preview)

def home_page(C, prods, preview):
    L = listed(prods) if not preview else prods
    sale = sale_items(prods)
    def sec(c):
        hb = [p for p in L if p["category"] == c["id"]]
        body = grid(hb, preview) if hb else ('<div class="pg">' + "".join(dcard(x) for x in dz_slice(c["id"], 0, 8)) + '</div>')
        return f'<section class="blk" id="c-{c["id"]}"><div class="bh"><h2>{E(c["title"])}</h2><div class="cnav"><a href="/shop/{c["id"]}/">View all {n_cat(c["id"]):,}</a></div></div>{body}</section>'
    by = "".join(sec(c) for c in CATS if any(p["category"] == c["id"] for p in L) or dz_has(c["id"]))
    main = ('<div class="wrap">' + crumbs() + '<div class="lay">' + sidebar("all") + '<div class="mc"><div class="ph"><h1>Shop all products</h1>'
            f'<p>{n_live():,} products. Prices include delivery to most metro areas.</p></div>'
            '<section class="blk" id="sr" hidden><div class="bh"><h2>Search results</h2></div><div class="pg" id="srg"></div><p class="more"><button type="button" class="btn dk" id="srm" hidden>Show more</button></p></section>'
            + (f'<section class="blk" id="sale"><div class="bh"><h2>Launch sale</h2></div><p class="note">Launch prices until {nice_date(sale[0]["sale_ends"])}. After that, the regular price shown applies.</p>{grid(sale, preview)}</section>' if sale else "")
            + (by or empty()) + '</div></div></div>')
    ld = [{"@type": "CollectionPage", "name": "ToolRank Shop", "url": BASE + "/shop/"},
          {"@type": "ItemList", "name": "Products", "itemListElement": [{"@type": "ListItem", "position": i, "name": p["name"], "url": f'{BASE}/shop/p/{p["id"]}/'} for i, p in enumerate(listed(prods), 1)]}]
    return doc(C, prods, head("Shop all products | ToolRank", f"{n_live():,} products: tools, home, garden, outdoor and more, shipped direct from Australian suppliers. Order by email, pay by secure link.", "/shop/", ld), main, preview)

def guide(c, items):
    """Optional short buying guide for a category (data/shop.json "guide"); links only to listed products."""
    if not c.get("guide"): return ""
    live = {p["id"]: p for p in items}; out = []
    for g in c["guide"]:
        ln = " &middot; ".join(f'<a href="/shop/p/{i}/">{E(live[i]["name"])}</a>' for i in g.get("links", []) if i in live)
        out.append(f'<h3>{E(g["h"])}</h3><p>{g["p"]}</p>' + (f'<p class="gl">{ln}</p>' if ln else ""))
    return f'<section class="guide"><h2>{E(c["title"])} buying guide</h2>' + "".join(out) + "</section>"

def cat_page(C, c, prods, preview):
    items = [p for p in (prods if preview else listed(prods)) if p["category"] == c["id"]]
    main = ('<div class="wrap">' + crumbs((c["title"], None)) + '<div class="lay">' + sidebar(c["id"]) + '<div class="mc">'
            f'<div class="ph cph"><img src="/assets/img/cat-{c["id"]}.webp" alt="{E(alt(c))}" width="640" height="480"><div><h1>{E(c["title"])}</h1><p>{E(c["blurb"])}</p></div></div>'
            + ((grouped(c, items, preview) if items else "") + dz_block(c, bool(items)) if (items or dz_has(c["id"])) else empty()) + guide(c, items) + '<p class="note">Prices in Australian dollars, delivery included to most metro areas. <a href="/shop/shipping/">Shipping</a> &middot; <a href="/shop/returns/">Returns</a></p>'
            + '</div></div></div>')
    ld = [{"@type": "CollectionPage", "name": c["title"], "url": f'{BASE}/shop/{c["id"]}/'}, crumb_ld((c["title"], f'{BASE}/shop/{c["id"]}/'))]
    if items: ld.append({"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i, "name": p["name"], "url": f'{BASE}/shop/p/{p["id"]}/'} for i, p in enumerate(items, 1)]})
    return doc(C, prods, head(f'{c["title"]} | ToolRank', f'{c["title"]}: {c["blurb"]} Shipped direct from Australian suppliers.', f'/shop/{c["id"]}/', ld, image=f'/assets/img/cat-{c["id"]}.webp'), main, preview)

def product_page(C, p, prods, preview):
    c = CAT[p["category"]]; ok = sellable(p)
    ims = p.get("images") or [img(p)]
    thumbs = "".join(f'<button type="button" data-src="{E(u)}"{" aria-current=true" if i == 0 else ""} aria-label="Photo {i+1}"><img src="{E(u)}" alt="" width="80" height="80" loading="lazy"></button>' for i, u in enumerate(ims)) if len(ims) > 1 else ""
    gal = f'<div class="gal"><figure class="gm"><img src="{E(ims[0])}" alt="{E(p["name"])}" width="800" height="800"></figure>{f"<div class=gt>{thumbs}</div>" if thumbs else ""}</div>'
    if ok:
        buy = (f'<p class="buy"><a class="btn ob xl" href="{E(buy_href(p))}">Order now</a></p>'
               + ('<p class="small">We&rsquo;ll confirm stock and send a secure payment link.</p>' if not p.get("stripe_link") else '<p class="small">Secure checkout by Stripe.</p>'))
    else:
        buy = '<p class="small">Not available to buy yet.</p>'
    specs = "".join(f"<li>{E(s)}</li>" for s in p.get("specs") or [])
    stock = (f'<p class="stk">{ic("check", "ic sm")}In stock <span>(checked {nice_date(p["stock_checked"])})</span></p>' if p.get("stock") == "in_stock" and p.get("stock_checked") else stock_html(p))
    price = price_html(p, True) if ok else '<p class="pp big"><span class="tbc">Price to be confirmed</span></p>'
    main = ('<div class="wrap">' + crumbs((c["title"], f'/shop/{c["id"]}/'), (p["name"], None)) + '<div class="prd">' + gal +
            f'<div class="pinf"><p class="pcc"><a href="/shop/{c["id"]}/">{E(c["title"])}</a></p><h1>{E(p["name"])}</h1><p class="sku">Product ID: {E(p.get("sku") or p["id"])}</p>' + fit_html(p) +
            f'{price}{stock}{buy}<p class="dsc">{E(str(p.get("description") or ""))}</p>'
            + (f'<h2>Specs</h2><ul class="spec">{specs}</ul>' if specs else "") +
            f'<ul class="pfacts"><li>{ic("truck", "ic sm")}Ships direct from an Australian supplier, usually within 1&ndash;3 business days. Delivery included to most metro areas.</li>'
            f'<li>{ic("check", "ic sm")}Australian Consumer Law guarantees apply. <a href="/shop/returns/">Returns</a></li>'
            f'<li>{ic("mail", "ic sm")}Questions? <a href="mailto:{MAIL}?subject={urllib.parse.quote("Question: " + p.get("sku", "") + " " + p["name"])}">{MAIL}</a></li></ul></div></div>'
            + carousel("More in " + c["title"], [x for x in listed(prods) if x["category"] == c["id"] and x["id"] != p["id"]], f'/shop/{c["id"]}/', "more", preview) + '</div>')
    ld = [crumb_ld((c["title"], f'{BASE}/shop/{c["id"]}/'), (p["name"], f'{BASE}/shop/p/{p["id"]}/'))]
    prod = {"@type": "Product", "name": p["name"], "sku": p.get("sku"), "description": str(p.get("description") or ""), "image": [BASE + u if u.startswith("/") else u for u in ims], "category": c["title"]}
    if ok: prod["offers"] = {"@type": "Offer", "price": f'{p["our_price"]:.2f}', "priceCurrency": "AUD", "url": f'{BASE}/shop/p/{p["id"]}/',
                             "availability": "https://schema.org/InStock" if p.get("stock") == "in_stock" else "https://schema.org/LimitedAvailability",
                             **({"priceValidUntil": p["sale_ends"]} if on_sale(p) else {})}
    ld.append(prod)
    return doc(C, prods, head(f'{p["name"]} | ToolRank', f'{p["name"]}, {money(p["our_price"])}. {p.get("description") or ""}', f'/shop/p/{p["id"]}/', ld, image=ims[0]), main, preview)

# ---------- bulk catalogue (data/dsz/cards.json): category/subcategory listings, data chunks, sharded search ----------
IMGB = DZ.get("img_base", "")
def pid(n): return f"TR-DZ-{n:06d}"
def purl(n): return f"/shop/i/{pid(n).lower()}/"
def sslug(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-") or "more"
def _index():
    """Global display order: categories in shop.json order; inside a category the subcategories are interleaved (round-robin by rank)
    so the first page of a category is varied. Each subcategory keeps its own ranked list for its page."""
    by = {}
    for x in DZ["items"]: by.setdefault(x[2], {}).setdefault(x[3], []).append(x)
    G, CATR, SUBS = [], {}, {}
    for c in CATS:
        subs = by.get(c["id"], {})
        order = sorted(subs, key=lambda t: (-len(subs[t]), t.lower()))
        used = set(); lst = []
        for t in sorted(subs, key=str.lower):
            sl = sslug(t); k = 2
            while sl in used or sl in ("p", "i") or sl in dict(POLICIES): sl = f"{sslug(t)}-{k}"; k += 1
            used.add(sl); lst.append((sl, t, subs[t]))
        SUBS[c["id"]] = lst
        start = len(G); qs = [list(subs[t]) for t in order]; i = 0
        while any(qs):
            for q in qs:
                if i < len(q): G.append(q[i])
            i += 1
            if all(i >= len(q) for q in qs): break
        CATR[c["id"]] = (start, len(G))
    return G, CATR, SUBS
G, CATR, SUBS = _index()
SUBIX = {(c, t): i for i, (c, t) in enumerate((c["id"], t) for c in CATS for _, t, _ in SUBS.get(c["id"], []))}
CATIX = {c["id"]: i for i, c in enumerate(CATS)}
def n_live(): return len(G) + sum(1 for p in PJ["products"] if sellable(p))
def n_cat(cid): return CATR.get(cid, (0, 0))[1] - CATR.get(cid, (0, 0))[0] + sum(1 for p in PJ["products"] if sellable(p) and p["category"] == cid)
def dz_has(cid): a, b = CATR.get(cid, (0, 0)); return b > a
def dz_slice(cid, i, j): a, b = CATR.get(cid, (0, 0)); return G[a + i:min(b, a + j)]
def dcard(x):
    h = purl(x[0])
    return (f'<article class="pc"><a class="pci" href="{h}"><img src="{E(IMGB + x[5])}" alt="{E(x[1])}" width="400" height="400" loading="lazy"></a>'
            f'<div class="pcb"><p class="pcc">{E(x[3])}</p><h3><a href="{h}">{E(x[1])}</a></h3><p class="pp"><span class="pr">{money(x[4] / 100)}</span></p>'
            f'<a class="btn ob" href="{h}">View details</a></div></article>')
def more_grid(gid, cards, lst, frm, to):
    return (f'<div class="pg" id="{gid}" data-list="{lst}" data-from="{frm}" data-to="{to}">' + "".join(dcard(x) for x in cards) + '</div>'
            + (f'<p class="more"><button type="button" class="btn dk" data-more="{gid}">Show more</button></p>' if to > frm else ""))
def chips(c, active=None):
    return ('<nav class="chips subs" aria-label="Subcategories">' + "".join(
        f'<a href="/shop/{c["id"]}/{sl}/"{" aria-current=page" if sl == active else ""}>{E(t)} <span>{len(l):,}</span></a>' for sl, t, l in SUBS.get(c["id"], [])) + '</nav>')
def dz_block(c, after_hand):
    if not dz_has(c["id"]): return ""
    a, b = CATR[c["id"]]
    return (f'<section class="blk" id="all">' + (f'<div class="bh"><h2>More {E(c["title"].lower())}</h2></div>' if after_hand else "")
            + chips(c) + more_grid("cg", G[a:a + CH], "/shop-data/c/", a + CH, b) + '</section>')
def sub_page(C, c, sl, t, lst, prods):
    path = f'/shop/{c["id"]}/{sl}/'
    main = ('<div class="wrap">' + crumbs((c["title"], f'/shop/{c["id"]}/'), (t, None)) + '<div class="lay">' + sidebar(c["id"]) + '<div class="mc">'
            f'<div class="ph"><h1>{E(t)}</h1><p>{len(lst):,} products in <a href="/shop/{c["id"]}/">{E(c["title"])}</a>.</p></div>' + chips(c, sl)
            + more_grid("cg", lst[:CH], f"/shop-data/s/{c['id']}/{sl}/", CH, len(lst))
            + '<p class="note">Prices in Australian dollars and include standard delivery to Sydney metro. Other areas: we confirm delivery before you pay. <a href="/shop/shipping/">Shipping</a> &middot; <a href="/shop/returns/">Returns</a></p></div></div></div>')
    ld = [{"@type": "CollectionPage", "name": t, "url": BASE + path}, crumb_ld((c["title"], f'{BASE}/shop/{c["id"]}/'), (t, BASE + path)),
          {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i, "name": x[1], "url": BASE + purl(x[0])} for i, x in enumerate(lst[:CH], 1)]}]
    return doc(C, prods, head(f'{t} | {c["title"]} | ToolRank', f'{t}: {len(lst):,} products in {c["title"]}, shipped direct from Australian suppliers.', path, ld,
                              image=f'/assets/img/cat-{c["id"]}.webp'), main)
def explore():
    picks = [G[CATR[c["id"]][0]] for c in CATS if dz_has(c["id"]) and not any(p["category"] == c["id"] and sellable(p) for p in PJ["products"])]
    if not picks: return ""
    return ('<section class="blk car" id="explore" data-car><div class="bh"><h2>More to explore</h2><div class="cnav"><a href="/shop/">View all</a>'
            '<button type="button" data-dir="-1" aria-label="Scroll left">‹</button><button type="button" data-dir="1" aria-label="Scroll right">›</button></div></div>'
            f'<div class="track">{"".join(dcard(x) for x in picks)}</div></section>')

STOP = set("and for with the of in to an or on by at from as is pcs pc".split())
def toks(s): return [w for w in re.sub(r"[^a-z0-9]+", " ", s.lower()).split() if len(w) > 1 and w not in STOP]
def dver():
    return hashlib.sha1(DSZF.read_bytes()).hexdigest()[:8] if DSZF.exists() else "0"
def shop_js_tag():
    return f'<script defer src="/assets/shop.js?v={hashlib.sha1(SHOP_JS.encode()).hexdigest()[:8]}" data-d="{DVER}"></script>'
DVER = dver()
def jd(o): return json.dumps(o, ensure_ascii=False, separators=(",", ":"))
def write_data(out, prods):
    """/shop-data/: base.json (categories, subcategories, hand-built products, help pages), c/<k>.json (global card chunks),
    s/<cat>/<sub>/<k>.json (subcategory chunks), q/<key>.json (search shards: token -> global positions). Also assets/shop.js and sitemap-items-N.xml."""
    D = out/"shop-data"
    if D.exists(): shutil.rmtree(D)
    (D/"c").mkdir(parents=True); (D/"q").mkdir()
    subs = [[CATIX[c["id"]], t, sl, len(l)] for c in CATS for sl, t, l in SUBS.get(c["id"], [])]
    i = [{"t": c["title"], "u": f'/shop/{c["id"]}/', "k": "Category", "x": c["blurb"]} for c in CATS]
    i += [{"t": t, "u": f'/shop/{CATS[ci]["id"]}/{sl}/', "k": CATS[ci]["title"]} for ci, t, sl, n in subs]
    i += [{"t": t, "u": f"/shop/{k}/", "k": "Help"} for k, t in POLICIES]
    i += [{"t": p["name"], "u": f'/shop/p/{p["id"]}/', "k": money(p["our_price"]), "x": CAT[p["category"]]["title"] + " " + p.get("sku", "")} for p in prods if sellable(p)]
    (D/"base.json").write_text(jd({"img": IMGB, "ch": CH, "cats": [[c["id"], c["title"]] for c in CATS], "subs": subs, "i": i}))
    def row(x): return [x[0], x[1], x[4], x[5], CATIX[x[2]], SUBIX[(x[2], x[3])]]
    for k in range(0, len(G), CH): (D/"c"/f"{k // CH}.json").write_text(jd([row(x) for x in G[k:k + CH]]))
    for c in CATS:
        for sl, t, l in SUBS.get(c["id"], []):
            sd = D/"s"/c["id"]/sl; sd.mkdir(parents=True)
            for k in range(0, len(l), CH): (sd/f"{k // CH}.json").write_text(jd([row(x) for x in l[k:k + CH]]))
    sh = {}
    for pos, x in enumerate(G):
        for w in set(toks(x[1]) + toks(x[3])):
            sh.setdefault(w[:3], {}).setdefault(w, []).append(pos)
    for k, v in sh.items(): (D/"q"/f"{k}.json").write_text(jd(dict(sorted(v.items()))))
    (out/"assets/shop.js").write_text(SHOP_JS); (out/"assets/icons.svg").write_text(sprite())
    for f in out.glob("sitemap-items-*.xml"): f.unlink()
    ids = sorted(x[0] for x in G); upd = DZ.get("updated") or ""
    for k in range(0, len(ids), 40000):
        (out/f"sitemap-items-{k // 40000 + 1}.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"<url><loc>{BASE}{purl(n)}</loc><lastmod>{upd}</lastmod></url>\n" for n in ids[k:k + 40000]) + "</urlset>\n")

def icu(k, cls="ic"):
    """Icon from the shared sprite /assets/icons.svg (compact pages)."""
    return f'<svg class="{cls}" width="24" height="24" aria-hidden="true"><use href="/assets/icons.svg#{k}"/></svg>'
def sprite():
    sy = "".join(f'<symbol id="{k}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{v}</symbol>' for k, v in IC.items())
    sy += f'<symbol id="logo" viewBox="0 0 24 24" fill="none" stroke="#f5c518" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{IC["hand-tools"]}</symbol>'
    return f'<svg xmlns="http://www.w3.org/2000/svg">{sy}</svg>'
def header_lite():
    return ('<a class="skip" href="#main">Skip to content</a><header class="hd"><div class="wrap hdr"><a class="logo" href="/" aria-label="ToolRank home"><svg class="lm" width="34" height="34" aria-hidden="true"><use href="/assets/icons.svg#logo"/></svg>'
            f'<span class="lt"><span class="ln">Tool<b>Rank</b></span><span class="lg">{TAGLINE}</span></span></a>'
            '<form class="sf hs" action="/shop/" method="get" role="search" data-search><label class="sr" for="q1">Search the store</label><input id="q1" name="q" type="search" placeholder="Search products&hellip;" autocomplete="off">'
            f'<button type="submit" aria-label="Search">{icu("search")}</button><div class="sres" role="listbox" hidden></div></form>'
            f'<nav class="hico" aria-label="Help"><a href="/shop/shipping/">{icu("help")}<span>Help</span></a><a href="mailto:{MAIL}?subject=Quote%20request">{icu("quote")}<span>Get a quote</span></a></nav></div>'
            f'<div class="nb"><div class="wrap nbr"><details class="allc"><summary>{icu("menu")}All Categories</summary><div class="allm" data-cats><a href="/shop/">All products</a></div></details>'
            '<nav class="nl" aria-label="Main"><a href="/">Home</a><a href="/shop/">Shop</a><a href="/shop/furniture/">Furniture</a><a href="/shop/home-living/">Home</a><a href="/shop/kitchen/">Kitchen</a>'
            f'<a href="/shop/bbq-camping/">BBQ &amp; Camping</a><a href="/shop/shipping/">Shipping</a><a href="mailto:{MAIL}">Contact</a></nav></div></div></header>')
def footer_lite():
    yr = CFG.get("policies_updated", "2026")[:4]
    return ('<footer class="ft"><div class="wrap ftl"><p><a href="/shop/">All products</a> &middot; ' + " &middot; ".join(f'<a href="/shop/{k}/">{t}</a>' for k, t in POLICIES)
            + f' &middot; <a href="mailto:{MAIL}">{MAIL}</a></p><p>&copy; {yr} ToolRank. Prices in Australian dollars. Seller: ToolRank.</p></div></footer>')
def dz_order_href(it):
    subj = f'Order {it["id"]}: {it["title"][:80]}'
    body = (f'Hi ToolRank,\n\nI would like to order:\n{it["title"]}\nProduct ID: {it["id"]}\nPrice: {money(it["price"])}\nQuantity: 1\n\n'
            f'Name:\nDelivery address (incl. postcode):\nPhone:\n\nThanks')
    return f"mailto:{MAIL}?subject={urllib.parse.quote(subj)}&body={urllib.parse.quote(body)}"
def dsz_page(C, it, feed_date):
    """Compact static page for one bulk-imported product (written by scripts/dsz_import.py). No supplier data."""
    pre, h, tail = C
    c = CAT[it["cat"]]; sl = next((s for s, t, _ in SUBS.get(it["cat"], []) if t == it["sub"]), None)
    path = purl(it["n"]); ims = it["imgs"][:5]; T = E(it["title"])
    thumbs = "".join(f'<button type="button"{" aria-current=true" if i == 0 else ""} aria-label="Photo {i+1}"><img src="{E(u)}" alt="" width="80" height="80" loading="lazy"></button>' for i, u in enumerate(ims)) if len(ims) > 1 else ""
    gal = f'<div class="gal"><figure class="gm"><img src="{E(ims[0])}" alt="{T}" width="800" height="800"></figure>{f"<div class=gt>{thumbs}</div>" if thumbs else ""}</div>'
    specs = []
    if it.get("color") and it["color"].lower() not in ("does not apply", "n/a", "na", "-", "/", "multi", "as picture", "as shown"): specs.append(f"Colour: {it['color']}")
    if it.get("weight"): specs.append(f"Shipping weight: {it['weight']:g} kg")
    dm = it.get("dims") or []
    if len(dm) == 3 and all(dm): specs.append("Carton: " + " × ".join(f"{v:g}" for v in dm) + " cm")
    sp = "".join(f"<li>{E(x)}</li>" for x in specs)
    days = f' Usually delivered in {it["days"]} business days.' if it.get("days") else ""
    crumb_items = [(c["title"], f'/shop/{c["id"]}/')] + ([(it["sub"], f'/shop/{c["id"]}/{sl}/')] if sl else []) + [(it["title"], None)]
    main = ('<div class="wrap">' + crumbs(*crumb_items) + '<div class="prd">' + gal +
            f'<div class="pinf"><p class="pcc"><a href="/shop/{c["id"]}/">{E(c["title"])}</a></p><h1>{T}</h1><p class="sku">Product ID: {it["id"]}</p>'
            f'<p class="pp big"><span class="pr">{money(it["price"])}</span></p>'
            f'<p class="stk">{icu("check", "ic sm")}In stock <span>(checked {nice_date(feed_date.isoformat())})</span></p>'
            f'<p class="buy"><a class="btn ob xl" href="{E(dz_order_href(it))}" data-id="{it["id"]}" data-price-cents="{int(round(it["price"] * 100))}">Order now</a></p>'
            '<p class="small">We&rsquo;ll confirm stock and send a secure payment link.</p>'
            f'<ul class="pfacts"><li>{icu("truck", "ic sm")}Price includes standard delivery to Sydney metro. Other areas: we confirm delivery before you pay.{days}</li>'
            f'<li>{icu("check", "ic sm")}Australian Consumer Law guarantees apply. <a href="/shop/returns/">Returns</a></li>'
            f'<li>{icu("mail", "ic sm")}Questions? <a href="mailto:{MAIL}?subject=Question%3A%20{it["id"]}">{MAIL}</a></li></ul></div></div>'
            + (f'<section class="pdesc"><h2>Details</h2><div class="dsc">{it["desc"]}</div>' + (f'<ul class="spec">{sp}</ul>' if sp else "") + '</section>' if it.get("desc") or sp else "")
            + (f'<p class="note"><a href="/shop/{c["id"]}/{sl}/">More {E(it["sub"].lower())}</a></p>' if sl else "") + '</div>')
    ld = {"@context": "https://schema.org", "@graph": [
          {"@type": "Product", "name": it["title"], "sku": it["id"], "image": ims[0], "description": plain_text(it.get("desc") or it["title"], 160), "category": c["title"],
           **({"gtin13": it["ean"]} if re.fullmatch(r"\d{13}", it.get("ean") or "") else {}),
           "offers": {"@type": "Offer", "price": f'{it["price"]:.2f}', "priceCurrency": "AUD", "availability": "https://schema.org/InStock", "seller": {"@type": "Organization", "name": "ToolRank", "url": BASE + "/"}}}]}
    title = f'{it["title"]}'
    if len(title) > 60: title = title[:59].rsplit(" ", 1)[0] + "…"
    desc = f'{it["title"]}, {money(it["price"])} incl. delivery to Sydney metro.'
    hd = (f'<!--SEO--><title>{E(title)} | ToolRank</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{BASE}{path}">'
          f'<meta name="theme-color" content="#1b2333"><meta property="og:title" content="{E(title)}"><meta property="og:image" content="{E(ims[0])}">'
          '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="manifest" href="/manifest.webmanifest">'
          f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")}</script><!--/SEO-->')
    return pre + hd + h + header_lite() + '<main id="main" class="shop">' + main + "</main>" + footer_lite() + shop_js_tag() + tail
def moved_page(p):
    u = f'/shop/i/{p["replaced_by"].lower()}/'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{E(p["name"])} | ToolRank</title><meta name="description" content="{E(p["name"])} is now listed as {p["replaced_by"]} at a lower price.">'
            f'<link rel="canonical" href="{BASE}{u}"><meta name="robots" content="noindex,follow"><meta http-equiv="refresh" content="0; url={u}"></head>'
            f'<body><h1>{E(p["name"])}</h1><p>This item has a new, lower-priced listing: <a href="{u}">{p["replaced_by"]}</a>.</p></body></html>')
def plain_text(hh, n=300):
    t = html.unescape(re.sub(r"<[^>]+>", " ", hh)); t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"

SHOP_JS = r"""/* ToolRank store script (generated by scripts/shop.py). Search: /shop-data/base.json + sharded index /shop-data/q/; listings load /shop-data chunks. */
(function(){var CH=__CH__,sc=document.currentScript,DV=(sc&&sc.getAttribute("data-d"))||"",M={};
function get(u){return M[u]||(M[u]=fetch(u+"?d="+DV).then(function(r){if(!r.ok)throw new Error(r.status);return r.json()}))}
function base(){return get("/shop-data/base.json")}
var ST=" and for with the of in to an or on by at from as is pcs pc ";
function toks(v){return(v||"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim().split(" ").filter(function(w){return w.length>1&&ST.indexOf(" "+w+" ")<0})}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function money(c){return"A$"+(c/100).toLocaleString("en-AU",{minimumFractionDigits:2,maximumFractionDigits:2})}
function pid(n){var s=String(n);while(s.length<6)s="0"+s;return"tr-dz-"+s}
function find(v){var w=toks(v);if(!w.length)return Promise.resolve([]);
return Promise.all(w.map(function(t){return get("/shop-data/q/"+t.slice(0,3)+".json").catch(function(){return{}}).then(function(s){var o={};for(var k in s){if(k.lastIndexOf(t,0)===0){var a=s[k],b=k===t?3:1;for(var i=0;i<a.length;i++)o[a[i]]=Math.max(o[a[i]]||0,b)}}return o})}))
.then(function(L){L.sort(function(a,b){return Object.keys(a).length-Object.keys(b).length});var r=[],f=L[0];for(var p in f){var sc=f[p],ok=1;for(var i=1;i<L.length;i++){if(!(p in L[i])){ok=0;break}sc+=L[i][p]}if(ok)r.push([+p,sc])}
r.sort(function(a,b){return b[1]-a[1]||a[0]-b[0]});return r.map(function(x){return x[0]})})}
function items(pre,ps){var need={};ps.forEach(function(p){need[Math.floor(p/CH)]=1});var ks=Object.keys(need);
return Promise.all(ks.map(function(k){return get(pre+k+".json")})).then(function(A){var m={};ks.forEach(function(k,i){m[k]=A[i]});return ps.map(function(p){return m[Math.floor(p/CH)][p%CH]})})}
function card(x,B){var h="/shop/i/"+pid(x[0])+"/";return'<article class="pc"><a class="pci" href="'+h+'"><img src="'+esc(B.img+x[3])+'" alt="'+esc(x[1])+'" width="400" height="400" loading="lazy"></a><div class="pcb"><p class="pcc">'+esc(B.subs[x[5]][1])+'</p><h3><a href="'+h+'">'+esc(x[1])+'</a></h3><p class="pp"><span class="pr">'+money(x[2])+'</span></p><a class="btn ob" href="'+h+'">View details</a></div></article>'}
function more(b,g){b.addEventListener("click",function(){var f=+g.getAttribute("data-from"),t=+g.getAttribute("data-to"),e=Math.min(t,f+CH),ps=[];for(var p=f;p<e;p++)ps.push(g.P?g.P[p]:p);b.disabled=true;
Promise.all([base(),items(g.getAttribute("data-list"),ps)]).then(function(r){g.insertAdjacentHTML("beforeend",r[1].map(function(x){return card(x,r[0])}).join(""));g.setAttribute("data-from",e);b.disabled=false;if(e>=t)b.hidden=true}).catch(function(){b.disabled=false})})}
document.querySelectorAll("[data-more]").forEach(function(b){var g=document.getElementById(b.getAttribute("data-more"));if(g)more(b,g)});
document.querySelectorAll("[data-search]").forEach(function(f){var q=f.querySelector("input"),r=f.querySelector(".sres"),seq=0;
function row(t,k,u){var a=document.createElement("a"),s=document.createElement("span"),m=document.createElement("small");a.setAttribute("role","option");a.href=u;s.textContent=t;m.textContent=k;a.appendChild(s);a.appendChild(m);r.appendChild(a)}
function go(){var v=q.value.trim(),my=++seq;if(!v){r.hidden=true;r.innerHTML="";return}
base().then(function(B){var w=v.toLowerCase().split(/\s+/),m=B.i.filter(function(x){var h=(x.t+" "+(x.x||"")+" "+x.k).toLowerCase();return w.every(function(t){return h.indexOf(t)>-1})}).slice(0,3);
return find(v).then(function(ps){return items("/shop-data/c/",ps.slice(0,6)).then(function(xs){if(my!==seq)return;r.innerHTML="";m.forEach(function(x){row(x.t,x.k,x.u)});
xs.forEach(function(x){row(x[1],money(x[2]),"/shop/i/"+pid(x[0])+"/")});
if(!m.length&&!xs.length)r.innerHTML='<p>No match. Email <a href="mailto:hello@toolrank.io">hello@toolrank.io</a> and we&rsquo;ll find it.</p>';else if(ps.length>6)row("See all "+ps.length.toLocaleString("en-AU")+" results","",'/shop/?q='+encodeURIComponent(v));r.hidden=false})})}).catch(function(){})}
q.addEventListener("input",go);q.addEventListener("focus",go);f.addEventListener("submit",function(e){e.preventDefault();var v=q.value.trim();if(v)location.href="/shop/?q="+encodeURIComponent(v)});
document.addEventListener("click",function(e){if(!f.contains(e.target))r.hidden=true});q.addEventListener("keydown",function(e){if(e.key==="Escape")r.hidden=true})});
var u=new URLSearchParams(location.search).get("q"),sr=document.getElementById("sr");
if(u){document.querySelectorAll("[data-search] input").forEach(function(i){i.value=u});
if(sr){var g=document.getElementById("srg"),b=document.getElementById("srm");sr.hidden=false;sr.querySelector("h2").textContent="Results for \u201c"+u+"\u201d";
base().then(function(B){var w=u.toLowerCase().split(/\s+/),m=B.i.filter(function(x){return x.k!=="Help"&&w.every(function(t){return(x.t+" "+(x.x||"")+" "+x.k).toLowerCase().indexOf(t)>-1})}).slice(0,6);
if(m.length)g.insertAdjacentHTML("beforebegin",'<nav class="chips">'+m.map(function(x){return'<a href="'+esc(x.u)+'">'+esc(x.t)+' <span>'+esc(x.k)+'</span></a>'}).join("")+"</nav>");
return find(u).then(function(ps){g.P=ps;g.setAttribute("data-list","/shop-data/c/");g.setAttribute("data-from",0);g.setAttribute("data-to",ps.length);
if(!ps.length){g.innerHTML='<p>No products found. Email <a href="mailto:hello@toolrank.io">hello@toolrank.io</a> and we&rsquo;ll find it.</p>';return}
b.hidden=false;more(b,g);b.click()})}).catch(function(){});sr.scrollIntoView()}}
document.querySelectorAll("[data-car]").forEach(function(c){var t=c.querySelector(".track");c.querySelectorAll("[data-dir]").forEach(function(b){b.addEventListener("click",function(){t.scrollBy({left:(+b.dataset.dir)*t.clientWidth*.9,behavior:"smooth"})})})});
document.querySelectorAll(".gal").forEach(function(g){var m=g.querySelector(".gm img");g.querySelectorAll(".gt button").forEach(function(b){b.addEventListener("click",function(){m.src=b.dataset.src||b.querySelector("img").src;g.querySelectorAll(".gt button").forEach(function(x){x.removeAttribute("aria-current")});b.setAttribute("aria-current","true")})})});
document.querySelectorAll("[data-cats]").forEach(function(m){var d=m.closest("details");d&&d.addEventListener("toggle",function(){if(!d.open||m.F)return;m.F=1;base().then(function(B){m.insertAdjacentHTML("afterbegin",B.cats.map(function(c){return'<a href="/shop/'+c[0]+'/">'+esc(c[1])+"</a>"}).join(""))})})});
document.addEventListener("click",function(e){var d=document.querySelector(".allc[open]");if(d&&!d.contains(e.target))d.removeAttribute("open")})})();
""".replace("__CH__", str(CH))

# ---------- policy pages (Australian Consumer Law) ----------
def policy(C, prods, key, title, lead, body, preview):
    upd = CFG.get("policies_updated", "")
    main = (f'<div class="wrap">{crumbs((title, None))}<div class="lay">{sidebar()}<div class="mc"><div class="ph"><h1>{E(title)}</h1><p>{lead}</p></div>'
            f'<div class="prose">{body}<p class="small">{operator()} Contact: <a href="mailto:{MAIL}">{MAIL}</a>. Last updated <time datetime="{upd}">{upd}</time>.</p></div></div></div></div>')
    return doc(C, prods, head(f"{title} | ToolRank", f"{title} for ToolRank: {re.sub('<[^>]+>', '', lead)}", f"/shop/{key}/", [crumb_ld((title, f"{BASE}/shop/{key}/"))]), main, preview)

ACL = ("Our goods come with guarantees that cannot be excluded under the Australian Consumer Law. You are entitled to a replacement or refund for a major failure and "
       "compensation for any other reasonably foreseeable loss or damage. You are also entitled to have the goods repaired or replaced if the goods fail to be of acceptable "
       "quality and the failure does not amount to a major failure.")
def policies(C, prods, preview):
    com = CFG.get("change_of_mind_days")
    com_txt = (f"<p>If you change your mind, you can return an unused item in its original packaging within {int(com)} days of delivery for a refund of the item price. Return postage for change-of-mind returns is paid by you.</p>"
               if com else "<p>We don&rsquo;t offer refunds or exchanges for change of mind (for example, if you ordered the wrong size or no longer need the item), unless a product page says otherwise. This doesn&rsquo;t affect your rights under the Australian Consumer Law if an item is faulty, not as described or doesn&rsquo;t match a sample.</p>")
    shipping = f"""<h2>Where we deliver</h2><p>We deliver within Australia. Orders ship directly from our Australian supplier&rsquo;s warehouse to you.</p>
<h2>Delivery cost</h2><p>Our prices include standard delivery to most metro addresses. Before you pay, we confirm stock and delivery to your postcode. If delivery to your address would cost more, we tell you first and you decide. You won&rsquo;t be charged anything extra after you pay.</p>
<h2>Dispatch and delivery times</h2><p>Orders are usually dispatched within 1&ndash;3 business days after payment. Most arrive sooner, but please allow up to 15 business days (excluding weekends and public holidays). We email tracking details once your order is dispatched.</p>
<h2>Small and large items</h2><ul><li><b>Smaller items</b> go by Australia Post and can be delivered to any Australian address, including PO boxes.</li><li><b>Large or heavy items</b> go by freight. Freight delivers to metro street addresses only (no PO boxes or parcel lockers). Outside metro areas you may need to collect from your local freight depot. We tell you before you pay if this applies.</li></ul>
<h2>On delivery day</h2><p>Delivery is to the front door, ground floor, by one driver. For large items, please help the driver unload. Someone needs to be there to receive freight.</p>
<h2>Damaged, lost or wrong items</h2><p>If your order arrives damaged, doesn&rsquo;t arrive, or the wrong item turns up, email <a href="mailto:{MAIL}">{MAIL}</a> with your order number (and photos for damage). We deal with the supplier and courier for you.</p>
<h2>Undeliverable orders</h2><p>If a parcel comes back because the address was wrong or freight couldn&rsquo;t be received, the supplier charges return and re-delivery costs. We&rsquo;ll tell you the amount before re-sending or refunding.</p>
<h2>Changing or cancelling an order</h2><p>Email us as soon as possible. If your order hasn&rsquo;t been dispatched yet, we can change it or cancel it with a full refund.</p>"""
    returns = f"""<h2>Your rights under the Australian Consumer Law</h2><p class="acl">{ACL}</p>
<h2>Major failures: refund or replacement</h2><p>If an item has a major failure (for example it&rsquo;s unsafe, significantly different from its description, or has a problem that would have stopped you buying it if you&rsquo;d known about it), you can choose a refund or a replacement.</p>
<h2>Minor failures: repair or replacement</h2><p>If the problem is minor, we&rsquo;ll repair or replace the item within a reasonable time. If we can&rsquo;t or don&rsquo;t, you can choose a refund or replacement instead.</p>
<h2>We handle your claim</h2><p>As the seller, we handle all returns and consumer-guarantee claims. You don&rsquo;t need to contact the supplier or manufacturer (though any manufacturer warranty is in addition to your rights).</p>
<h2>How to make a claim</h2><ol><li>Email <a href="mailto:{MAIL}">{MAIL}</a> with your order number, what&rsquo;s wrong, and photos if you can.</li><li>We&rsquo;ll reply, usually within 1&ndash;2 business days, and tell you what happens next. If the item needs to come back, we&rsquo;ll arrange the return and cover the cost for faulty or incorrect items.</li><li>Approved refunds go back to your original payment method.</li></ol>
<h2>Change of mind</h2>{com_txt}
<h2>What isn&rsquo;t covered</h2><p>Consumer guarantees don&rsquo;t cover damage caused by misuse, abnormal use, or ignoring the instructions, or normal wear and tear.</p>"""
    who = operator()
    terms = f"""<h2>Who we are</h2><p>{who} &ldquo;We&rdquo;, &ldquo;us&rdquo; and &ldquo;our&rdquo; refer to ToolRank. Contact: <a href="mailto:{MAIL}">{MAIL}</a>.</p>
<h2>Products</h2><p>We try to describe and picture every product accurately. Photos are supplied by our supplier; check the product details for specifications. We sell tools, equipment and household goods.</p>
<h2>Prices</h2><p>Prices are in Australian dollars and are the final price, including standard delivery to most metro areas. We are not registered for GST, so no GST is charged. Launch sale prices apply until the date shown; after that the regular price shown applies.</p>
<h2>How ordering works</h2><p>Click &ldquo;Order now&rdquo; to email us your order. We confirm stock, delivery and the total, then send you a secure payment link. Your order is accepted once you pay. We never see or store your full card details.</p>
<h2>Your order</h2><p>After you pay, you&rsquo;ll receive an order confirmation by email. If an item turns out to be unavailable, or was listed at an obviously wrong price, we&rsquo;ll tell you and give you a full refund for that item.</p>
<h2>Delivery</h2><p>Delivery is covered in our <a href="/shop/shipping/">shipping policy</a>. Risk in the goods passes to you on delivery.</p>
<h2>Returns and your consumer rights</h2><p>{ACL}</p><p>See <a href="/shop/returns/">returns &amp; refunds</a> for how to make a claim. Nothing in these terms excludes, restricts or modifies any right or remedy you have under the Australian Consumer Law.</p>
<h2>Using tools safely</h2><p>Always read and follow the manufacturer&rsquo;s instructions and safety warnings, and use appropriate protective equipment.</p>
<h2>Liability</h2><p>To the extent permitted by law, and except for the guarantees above, our liability is limited to replacing the goods, supplying equivalent goods, or refunding the price you paid.</p>
<h2>Privacy</h2><p>How we handle your details is set out in our <a href="/shop/privacy/">privacy policy</a>.</p>
<h2>Governing law</h2><p>These terms are governed by the laws of New South Wales, Australia.</p>
<h2>Changes</h2><p>We may update these terms. The version published when you place your order applies to that order.</p>"""
    privacy = f"""<h2>What we collect</h2><p>When you order, we collect your name, email address, phone number, delivery address and the details of your order. Payment card details are collected and processed by our payment provider (Stripe) through a secure payment link; we never see or store them.</p>
<h2>Why we collect it</h2><p>To process and deliver your order, send order and tracking updates, handle returns and questions, prevent fraud, and keep the business records the law requires.</p>
<h2>Who we share it with</h2><ul><li><b>Stripe</b>, to take your payment.</li><li><b>Our supplier</b>, who receives your name, delivery address and phone number so it can ship your order directly to you.</li><li><b>Couriers</b>, who receive your name, delivery address and phone number so they can ship your order directly to you.</li><li>Government or regulators, only where the law requires it.</li></ul><p>We don&rsquo;t sell your personal information, and we don&rsquo;t use it for marketing unless you ask us to.</p>
<h2>Overseas processing</h2><p>Stripe and some of our service providers may store or process information outside Australia, under their own privacy and security commitments.</p>
<h2>Analytics</h2><p>This website uses cookieless, privacy-friendly analytics (GoatCounter) that collect no personal data and don&rsquo;t track you across sites.</p>
<h2>How long we keep it</h2><p>We keep order records for as long as needed for tax and legal requirements (generally five years), then delete them.</p>
<h2>Access, correction and complaints</h2><p>You can ask to see or correct the personal information we hold about you, or make a privacy complaint, by emailing <a href="mailto:{MAIL}">{MAIL}</a>. We&rsquo;ll respond within 30 days. If you&rsquo;re not satisfied with our response, you can contact the Office of the Australian Information Commissioner (oaic.gov.au).</p>"""
    return {"shipping": policy(C, prods, "shipping", "Shipping", "Shipped direct from our Australian supplier. Usually dispatched in 1&ndash;3 business days.", shipping, preview),
            "returns": policy(C, prods, "returns", "Returns & refunds", "Your rights under the Australian Consumer Law, and how we handle faulty or incorrect items.", returns, preview),
            "terms": policy(C, prods, "terms", "Terms of sale", "The terms that apply when you buy from ToolRank.", terms, preview),
            "privacy": policy(C, prods, "privacy", "Privacy", "What we collect when you order, why, and who we share it with.", privacy, preview)}

def urls():
    return (["/", "/shop/"] + [f'/shop/{c["id"]}/' for c in CATS] + [f'/shop/{c["id"]}/{sl}/' for c in CATS for sl, _, _ in SUBS.get(c["id"], [])]
            + [f"/shop/{k}/" for k, _ in POLICIES] + [f'/shop/p/{p["id"]}/' for p in PJ["products"] if sellable(p)])

def build(out=None, preview=False):
    out = pathlib.Path(out) if out else ROOT
    bad = [p["id"] for p in PJ["products"] if p.get("category") not in CAT]
    if bad: raise SystemExit(f"products.json: unknown category for {bad}")
    today = datetime.date.today().isoformat()
    for p in PJ["products"]:  # launch sale over: the stated regular price applies from the day after sale_ends
        if p.get("sale_ends") and today > p["sale_ends"] and isinstance(p.get("regular_price"), (int, float)): p["our_price"] = p["regular_price"]
    C = chrome()
    prods = [p for p in PJ["products"] if preview or sellable(p)]
    def w(rel, s): d = out/rel; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(s)
    if (out/"shop/p").exists(): shutil.rmtree(out/"shop/p")  # hidden/removed products must disappear
    w("shop", home_page(C, prods, preview))
    (out/"index.html").write_text(site_home(C, prods, preview))  # toolrank.io/ is the store home
    for c in CATS: w(f"shop/{c['id']}", cat_page(C, c, prods, preview))
    for p in prods: w(f"shop/p/{p['id']}", product_page(C, p, prods, preview))
    for p in PJ["products"]:  # replaced by a cheaper identical item: keep the old URL working
        if p.get("replaced_by") and not sellable(p) and p["replaced_by"].startswith("TR-DZ-"): w(f"shop/p/{p['id']}", moved_page(p))
    for k, s in policies(C, prods, preview).items(): w(f"shop/{k}", s)
    for c in CATS:  # bulk subcategory pages; stale ones removed
        want = {sl for sl, _, _ in SUBS.get(c["id"], [])}
        cd = out/"shop"/c["id"]
        for d in (cd.iterdir() if cd.exists() else []):
            if d.is_dir() and d.name not in want: shutil.rmtree(d)
        for sl, t, lst in SUBS.get(c["id"], []): w(f"shop/{c['id']}/{sl}", sub_page(C, c, sl, t, lst, prods))
    write_data(out, prods)
    if preview:
        for a in ("assets", "manifest.webmanifest"):
            if not (out/a).exists(): (out/a).symlink_to(ROOT/a)
    n = sum(1 for p in PJ["products"] if sellable(p))
    print(f"shop: {len(CATS)} categories, {sum(len(v) for v in SUBS.values())} subcategory pages, {len(prods)} product page(s) ({n} listed of {len(PJ['products'])} in products.json), {len(G):,} bulk products{' [PREVIEW incl. drafts]' if preview else ''} -> {out/'shop'}")
    return urls()

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--preview"]:
        if len(a) < 2 or pathlib.Path(a[1]).resolve() == ROOT or ROOT in pathlib.Path(a[1]).resolve().parents: raise SystemExit("--preview needs a directory OUTSIDE the repo")
        build(a[1], preview=True)
    else: build()
