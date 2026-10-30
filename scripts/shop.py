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
 "music-gear": '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
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
            f'<input id="{fid}" name="q" type="search" placeholder="Search tools, categories&hellip;" autocomplete="off">'
            f'<button type="submit" aria-label="Search">{ic("search")}</button><div class="sres" role="listbox" hidden></div></form>')

def header():
    cats = "".join(f'<a href="/shop/{c["id"]}/">{ic(c["id"])}{E(c["title"])}</a>' for c in CATS)
    trade = f"mailto:{MAIL}?subject={urllib.parse.quote('Trade / bulk quote')}"
    return ('<a class="skip" href="#main">Skip to content</a><header class="hd"><div class="wrap hdr">' + LOGO + search_form("hs", "q1") +
            f'<nav class="hico" aria-label="Help"><a href="/shop/shipping/">{ic("help")}<span>Help</span></a><a href="mailto:{MAIL}?subject={urllib.parse.quote("Quote request")}">{ic("quote")}<span>Get a quote</span></a></nav></div>'
            '<div class="nb"><div class="wrap nbr"><details class="allc"><summary>' + ic("menu") + 'All Categories</summary><div class="allm">' + cats + '<a href="/shop/">All products</a></div></details>'
            '<nav class="nl" aria-label="Main"><a href="/">Home</a><a href="/shop/">Shop</a><a href="/shop/music-gear/">Music gear</a><a href="/shop/#sale">Launch sale</a>'
            f'<a href="{trade}">Trade &amp; Bulk</a><a href="/shop/shipping/">Shipping</a><a href="/shop/returns/">Returns</a><a href="mailto:{MAIL}">Contact</a></nav>'
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
document.querySelectorAll(".gal").forEach(function(g){var m=g.querySelector(".gm img");g.querySelectorAll(".gt button").forEach(function(b){b.addEventListener("click",function(){m.src=b.dataset.src;g.querySelectorAll(".gt button").forEach(function(x){x.removeAttribute("aria-current")});b.setAttribute("aria-current","true")})})});
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
            + f'<script type="application/json" id="six">{search_index(prods)}</script>' + SEARCH_JS + tail)

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

def card(p, preview=False, lazy=True):
    href = f'/shop/p/{p["id"]}/'
    if not sellable(p):
        return (f'<article class="pc"><a class="pci" href="{href}"><img src="{E(img(p))}" alt="{E(p["name"])}" width="400" height="400" loading="lazy"></a>'
                f'<div class="pcb"><p class="pcc">{E(CAT[p["category"]]["title"])}</p><h3><a href="{href}">{E(p["name"])}</a></h3><p class="pp"><span class="tbc">Draft, not for sale</span></p></div></article>')
    return (f'<article class="pc"><a class="pci" href="{href}"><img src="{E(img(p))}" alt="{E(p["name"])}" width="400" height="400"{" loading=lazy" if lazy else ""}></a>'
            f'<div class="pcb"><p class="pcc">{E(CAT[p["category"]]["title"])}</p><h3><a href="{href}">{E(p["name"])}</a></h3>{price_html(p)}{stock_html(p)}'
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

def tiles():
    t = "".join(f'<a class="tile" href="/shop/{c["id"]}/"><img src="/assets/img/cat-{c["id"]}.webp" alt="{E(ALT[c["id"]])}" width="640" height="480" loading="lazy"><span>{E(c["title"])}</span></a>' for c in CATS)
    if len(CATS) % 5: t += '<a class="tile" href="/shop/"><img src="/assets/img/hero.webp" alt="Tools on a workbench by Sydney Harbour" width="640" height="360" loading="lazy"><span>All products</span></a>'
    return '<div class="tiles">' + t + "</div>"
ALT = {"power-tools": "Cordless drill with drill bits and a saw blade on a workbench", "hand-tools": "Spanners, screwdrivers, pliers and a hammer on a wooden bench",
       "hardware": "Screws, bolts, nuts, washers and a brass hinge", "building": "Hard hat on a stack of bricks with a trowel and spirit levels",
       "automotive": "Car wheel, socket set, torque wrench and floor jack in a garage", "garden": "Secateurs, garden fork, rake, hose and gloves on a lawn",
       "cleaning": "Bucket, scrubbing brushes, squeegee, cloths and a spray bottle", "safety": "Hi-vis vest, safety glasses, earmuffs, work gloves and a hard hat",
       "workshop-storage": "Steel tool chest, workbench, pegboard and shelving in a workshop",
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
            '<p class="sub">Hand tools, hardware, garden and workshop gear. Shipped direct from Australian suppliers.</p>'
            + search_form("hsf", "q2") + TRUST + '</div></section>'
            '<div class="lay">' + sidebar() + '<div class="mc">'
            '<section class="blk"><div class="bh"><h2>Popular Categories</h2></div>' + tiles() + '</section>'
            + carousel("Launch sale", sale_items(prods), "/shop/#sale", "sale", preview)
            + carousel("Just landed", newest(prods)[:14], "/shop/", "new", preview)
            + (empty() if not listed(prods) else "") + banner() + '</div></div></div>')
    ld = [{"@type": "WebSite", "@id": BASE + "/#website", "name": "ToolRank", "url": BASE + "/", "publisher": {"@id": BASE + "/#store"},
           "potentialAction": {"@type": "SearchAction", "target": BASE + "/shop/?q={q}", "query-input": "required name=q"}},
          {"@type": "ItemList", "name": "Shop categories", "itemListElement": [{"@type": "ListItem", "position": i, "name": c["title"], "url": f'{BASE}/shop/{c["id"]}/'} for i, c in enumerate(CATS, 1)]}]
    return doc(C, prods, head("ToolRank | Tools for every trade, shipped direct",
                       "Hand tools, hardware, building, automotive, garden, cleaning, safety and workshop storage gear, shipped direct from Australian suppliers.", "/", ld), main, preview)

def home_page(C, prods, preview):
    L = listed(prods) if not preview else prods
    sale = sale_items(prods)
    by = "".join(f'<section class="blk" id="c-{c["id"]}"><div class="bh"><h2>{E(c["title"])}</h2><div class="cnav"><a href="/shop/{c["id"]}/">View all</a></div></div>{grid([p for p in L if p["category"] == c["id"]], preview)}</section>'
                 for c in CATS if any(p["category"] == c["id"] for p in L))
    main = ('<div class="wrap">' + crumbs() + '<div class="lay">' + sidebar("all") + '<div class="mc"><div class="ph"><h1>Shop all tools</h1>'
            f'<p>{len(listed(prods))} products. Prices include delivery to most metro areas.</p></div>'
            + (f'<section class="blk" id="sale"><div class="bh"><h2>Launch sale</h2></div><p class="note">Launch prices until {nice_date(sale[0]["sale_ends"])}. After that, the regular price shown applies.</p>{grid(sale, preview)}</section>' if sale else "")
            + (by or empty()) + '</div></div></div>')
    ld = [{"@type": "CollectionPage", "name": "ToolRank Shop", "url": BASE + "/shop/"},
          {"@type": "ItemList", "name": "Products", "itemListElement": [{"@type": "ListItem", "position": i, "name": p["name"], "url": f'{BASE}/shop/p/{p["id"]}/'} for i, p in enumerate(listed(prods), 1)]}]
    return doc(C, prods, head("Shop all tools | ToolRank", f"{len(listed(prods))} tools and workshop products, shipped direct from Australian suppliers. Order by email, pay by secure link.", "/shop/", ld), main, preview)

def cat_page(C, c, prods, preview):
    items = [p for p in (prods if preview else listed(prods)) if p["category"] == c["id"]]
    main = ('<div class="wrap">' + crumbs((c["title"], None)) + '<div class="lay">' + sidebar(c["id"]) + '<div class="mc">'
            f'<div class="ph cph"><img src="/assets/img/cat-{c["id"]}.webp" alt="{E(ALT[c["id"]])}" width="640" height="480"><div><h1>{E(c["title"])}</h1><p>{E(c["blurb"])}</p></div></div>'
            + grid(items, preview) + '<p class="note">Prices in Australian dollars, delivery included to most metro areas. <a href="/shop/shipping/">Shipping</a> &middot; <a href="/shop/returns/">Returns</a></p>'
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
            f'<div class="pinf"><p class="pcc"><a href="/shop/{c["id"]}/">{E(c["title"])}</a></p><h1>{E(p["name"])}</h1><p class="sku">Product ID: {E(p.get("sku") or p["id"])}</p>'
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

# ---------- policy pages (Australian Consumer Law) ----------
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
<h2>Products</h2><p>We try to describe and picture every product accurately. Photos are supplied by our supplier; check the product details for specifications. We sell non-electrical tools and equipment.</p>
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
    return ["/", "/shop/"] + [f'/shop/{c["id"]}/' for c in CATS] + [f"/shop/{k}/" for k, _ in POLICIES] + [f'/shop/p/{p["id"]}/' for p in PJ["products"] if sellable(p)]

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
    for k, s in policies(C, prods, preview).items(): w(f"shop/{k}", s)
    if preview:
        for a in ("assets", "manifest.webmanifest"):
            if not (out/a).exists(): (out/a).symlink_to(ROOT/a)
    n = sum(1 for p in PJ["products"] if sellable(p))
    print(f"shop: {len(CATS)} categories, {len(prods)} product page(s) ({n} listed of {len(PJ['products'])} in products.json){' [PREVIEW incl. drafts]' if preview else ''} -> {out/'shop'}")
    return urls()

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--preview"]:
        if len(a) < 2 or pathlib.Path(a[1]).resolve() == ROOT or ROOT in pathlib.Path(a[1]).resolve().parents: raise SystemExit("--preview needs a directory OUTSIDE the repo")
        build(a[1], preview=True)
    else: build()
