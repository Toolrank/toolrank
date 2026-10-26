#!/usr/bin/env python3
"""ToolRank Shop: static store pages from data/shop.json + data/products.json.
Outputs: shop/index.html, shop/<category>/index.html, shop/p/<product>/index.html (only for sellable products),
shop/{shipping,returns,terms,privacy}/index.html and assets/shop/<category>.svg.
A product is sellable (shown anywhere on the site) only when status == "active" AND our_price is a number AND stripe_link is set.
Page chrome (head assets, nav, footer) is copied from about/index.html so the shop always matches the rest of the site.
Run standalone:  python3 scripts/shop.py
Layout preview with draft products (written OUTSIDE the repo, never deploy it):  python3 scripts/shop.py --preview /workspace/store-preview
scripts/build.py calls build() too, so a full site build regenerates the shop and adds its URLs to sitemap.xml."""
import json, re, html, pathlib, shutil, sys, hashlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://toolrank.io"; E = html.escape
CFG = json.loads((ROOT/"data/shop.json").read_text())
PJ = json.loads((ROOT/"data/products.json").read_text())
CATS = CFG["categories"]; CAT = {c["id"]: c for c in CATS}
MAIL = CFG["contact_email"]
POLICIES = [("shipping", "Shipping"), ("returns", "Returns & refunds"), ("terms", "Terms of sale"), ("privacy", "Privacy")]

def seller_line():
    """Single switch: data/shop.json show_seller. When false, no personal name or ABN is printed anywhere in the shop."""
    return f'{E(CFG["seller"])}, ABN {E(CFG["abn"])}' if CFG.get("show_seller") else ""
def operator():
    return f'ToolRank Shop is operated by {E(CFG["seller"])}, ABN {E(CFG["abn"])}, Sydney NSW.' if CFG.get("show_seller") else "ToolRank Shop is operated from Sydney NSW."
def sellable(p):
    return p.get("status") == "active" and isinstance(p.get("our_price"), (int, float)) and p["our_price"] > 0 and bool(p.get("stripe_link"))
def money(v): return f"A${v:,.2f}".replace(".00", "") if float(v).is_integer() else f"A${v:,.2f}"
def img(p): return p.get("image") or f"/assets/shop/{p['category']}.svg"

# ---------- category artwork (generic, no product photos) ----------
GLYPH = {
 "building": '<path d="M62 162 132 92" stroke-width="14"/><g transform="rotate(45 136 86)"><rect x="98" y="72" width="76" height="28" rx="5"/></g>',
 "automotive": '<path d="M150 50a30 30 0 0 0-38 38L56 144a12 12 0 0 0 17 17l56-56a30 30 0 0 0 38-38l-18 18-18-4-4-18z"/>',
 "garden": '<path d="M110 170V100"/><path d="M110 110c-40 0-56-30-56-56 30 0 56 16 56 56zM110 96c0-34 20-52 54-52 0 30-20 52-54 52z"/>',
 "cleaning": '<path d="M100 40c22 32 38 52 38 72a38 38 0 0 1-76 0c0-20 16-40 38-72z"/><path d="M160 96c10 14 16 24 16 32a16 16 0 0 1-32 0c0-8 6-18 16-32z"/>',
 "workshop-storage": '<rect x="54" y="52" width="112" height="116" rx="10"/><path d="M54 90h112M54 128h112M96 71h28M96 109h28M96 147h28"/>',
 "hand-tools": '<path d="M60 160l46-46"/><path d="M100 120l14-14 50-50 10 10-50 50-14 14z"/><path d="M52 168l14-14 8 8-14 14z"/>',
}
PAL = {"building": ("#2563eb", "#60a5fa"), "automotive": ("#1e40af", "#38bdf8"), "garden": ("#0f766e", "#60a5fa"),
       "cleaning": ("#0369a1", "#7dd3fc"), "workshop-storage": ("#3730a3", "#60a5fa"), "hand-tools": ("#1d4ed8", "#8b7cf6")}
def art(cid):
    a, b = PAL.get(cid, ("#2563eb", "#60a5fa"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 176" width="660" height="528"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs><rect width="220" height="176" fill="#0f172a"/>'
            f'<rect width="220" height="176" fill="url(#g)" opacity=".55"/><path d="M0 132 220 60v116H0z" fill="#0b1220" opacity=".35"/>'
            f'<g transform="translate(10 -12)" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity=".92">{GLYPH.get(cid, "")}</g></svg>\n')

# ---------- page chrome ----------
def chrome():
    s = (ROOT/"about/index.html").read_text()
    pre, rest = s.split("<!--SEO-->", 1); _, rest = rest.split("<!--/SEO-->", 1)
    h, rest = rest.split("<main", 1); _, foot = rest.split("</main>", 1)
    v = hashlib.sha1((ROOT/"assets/shop.css").read_bytes()).hexdigest()[:8]
    h = h.replace("</head>", f'<link rel="stylesheet" href="/assets/shop.css?v={v}"></head>', 1)
    sl = seller_line()
    block = ('<div class="shopfoot"><nav aria-label="Shop"><p class="fh">Shop</p><a href="/shop/">All categories</a>' + "".join(f'<a href="/shop/{c["id"]}/">{E(c["title"])}</a>' for c in CATS) +
             '</nav><nav aria-label="Shop policies"><p class="fh">Help</p>' + "".join(f'<a href="/shop/{k}/">{t}</a>' for k, t in POLICIES) + f'<a href="mailto:{MAIL}">{MAIL}</a></nav></div>'
             + (f'<p class="small muted shop-seller">Shop seller: {sl}. Contact <a href="mailto:{MAIL}">{MAIL}</a>.</p>' if sl else f'<p class="small muted shop-seller">Shop contact: <a href="mailto:{MAIL}">{MAIL}</a>.</p>'))
    foot = foot.replace('<p class="si-tag small">', block + '<p class="si-tag small">', 1) if '<p class="si-tag small">' in foot else foot.replace('<p class="muted small">©', block + '<p class="muted small">©', 1)
    return pre, h, foot

def head(title, desc, path, ld, robots="index,follow,max-snippet:-1"):
    url = BASE + path
    if len(title) > 60: title = title[:59].rsplit(" ", 1)[0] + "…"
    if len(desc) > 160: desc = desc[:159].rsplit(" ", 1)[0] + "…"
    org = {"@type": "Organization", "@id": BASE + "/#org", "name": "ToolRank", "url": BASE + "/"}
    return (f'<!--SEO--><title>{E(title)}</title><meta name="description" content="{E(desc)}">\n<link rel="canonical" href="{url}"><meta name="robots" content="{robots}">'
            f'<meta name="theme-color" content="#0b1220"><meta name="color-scheme" content="dark"><meta property="og:type" content="website"><meta property="og:site_name" content="ToolRank">'
            f'<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/assets/og.png">'
            f'<meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png">'
            f'<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png"><link rel="manifest" href="/manifest.webmanifest">\n'
            f'<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": [org] + ld}, ensure_ascii=False)}</script><!--/SEO-->')

def doc(C, headblock, main, preview=False):
    pre, h, foot = C
    banner = '<div class="pvbar" role="note">PREVIEW BUILD: draft products shown for layout only. Not for publishing.</div>' if preview else ""
    return pre + headblock + h + '<main id="main" class="shop">' + banner + main + "</main>" + foot

def crumbs(*items):
    parts = ['<a href="/shop/">Shop</a>'] + [f'<a href="{u}">{E(t)}</a>' if u else f'<span aria-current="page">{E(t)}</span>' for t, u in items]
    return '<nav class="crumb" aria-label="Breadcrumb"><a href="/">ToolRank</a> › ' + " › ".join(parts) + "</nav>"
def crumb_ld(*items):
    li = [("ToolRank", BASE + "/"), ("Shop", BASE + "/shop/")] + list(items)
    return {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(li, 1)]}

def subnav(active=""):
    return ('<nav class="catnav" aria-label="Shop categories"><div class="wrap">' + f'<a href="/shop/"{" aria-current=page" if active == "" else ""}>All</a>' +
            "".join(f'<a href="/shop/{c["id"]}/"{" aria-current=page" if active == c["id"] else ""}>{E(c["title"])}</a>' for c in CATS) + "</div></nav>")

def card(p, preview):
    if sellable(p):
        price = f'<p class="pprice">{money(p["our_price"])}</p>'
    else:
        price = '<p class="pprice tbc">Price to be confirmed <span class="tag">draft</span></p>'
    href = f'/shop/p/{p["id"]}/'
    return (f'<article class="pcard"><a class="pimg" href="{href}"><img src="{E(img(p))}" alt="{E(p["name"])}" width="660" height="528" loading="lazy"></a>'
            f'<div class="pbody"><p class="pcat">{E(CAT[p["category"]]["title"])}</p><h3><a href="{href}">{E(p["name"])}</a></h3>{price}</div></article>')

def empty(msg):
    return (f'<div class="empty"><h3>Products are on the way</h3><p>{msg}</p>'
            f'<p class="small muted">Looking for something specific? Email <a href="mailto:{MAIL}">{MAIL}</a>.</p></div>')

def tiles(prods):
    out = []
    for c in CATS:
        n = sum(1 for p in prods if p["category"] == c["id"])
        out.append(f'<a class="tile" href="/shop/{c["id"]}/"><img class="art" src="/assets/shop/{c["id"]}.svg" alt="" width="660" height="528" loading="lazy">'
                   f'<span class="tn">{E(c["title"])}</span><span class="tc">{f"{n} product" + ("s" if n != 1 else "") if n else "Coming soon"}</span></a>')
    return '<div class="tiles shoptiles">' + "".join(out) + "</div>"

TRUST = ('<dl class="kpis"><div><dt>Ships from</dt><dd>Australian suppliers</dd></div><div><dt>Dispatch</dt><dd>Usually 1&ndash;2 business days</dd></div>'
         '<div><dt>Checkout</dt><dd>Secure, by Stripe</dd></div><div><dt>Returns</dt><dd>Consumer-law guaranteed</dd></div></dl>')

def home_page(C, prods, preview):
    grid = ('<div class="pgrid">' + "".join(card(p, preview) for p in prods) + "</div>") if prods else empty("We&rsquo;re lining up the first range of tools now. Check back soon.")
    main = (f'<section class="hero home studio-hero shophero"><div class="wrap hw"><p class="si-eyebrow"><span>ToolRank Shop</span></p>'
            f'<h1>Tools for every trade, <span class="gt">delivered.</span></h1>'
            f'<p class="lead">Building, automotive, garden, cleaning and workshop gear, shipped from Australian suppliers.</p>'
            f'<p class="hcta"><a class="btn xl" href="#cats">Shop by category</a> <a class="btn ghost xl" href="/shop/shipping/">Shipping &amp; returns</a></p>{TRUST}</div></section>'
            f'{subnav()}'
            f'<section class="sec" id="cats"><div class="wrap"><div class="sh"><p class="eyebrow">Categories</p><h2 class="big">Find the right gear.</h2></div>{tiles(prods)}</div></section>'
            f'<section class="sec" id="products"><div class="wrap"><div class="sh"><p class="eyebrow">Products</p><h2 class="big">In the shop.</h2></div>{grid}</div></section>'
            f'{info_band()}')
    ld = [{"@type": "CollectionPage", "name": "ToolRank Shop", "url": BASE + "/shop/"},
          {"@type": "ItemList", "name": "Shop categories", "itemListElement": [{"@type": "ListItem", "position": i, "name": c["title"], "url": f'{BASE}/shop/{c["id"]}/'} for i, c in enumerate(CATS, 1)]}]
    return doc(C, head("ToolRank Shop: tools for every trade", "Tools for building, automotive, garden, cleaning and workshop storage, shipped from Australian suppliers. Secure Stripe checkout.", "/shop/", ld), main, preview)

def info_band():
    return ('<section class="sec"><div class="wrap"><div class="feats f3">'
            '<article class="feat"><span class="fn">01</span><h3>Ships from Australia</h3><p>Orders ship from Australian supplier warehouses, usually dispatched in 1&ndash;2 business days. Delivery times vary by location. <a href="/shop/shipping/">Shipping</a></p></article>'
            '<article class="feat"><span class="fn">02</span><h3>Your consumer rights</h3><p>Refund or replacement for major failures, repair or replacement for minor ones. We handle every claim. <a href="/shop/returns/">Returns</a></p></article>'
            f'<article class="feat"><span class="fn">03</span><h3>Real people</h3><p>Questions before or after you buy? Email <a href="mailto:{MAIL}">{MAIL}</a>.</p></article>'
            '</div></div></section>')

def cat_page(C, c, prods, preview):
    items = [p for p in prods if p["category"] == c["id"]]
    others = "".join(f'<a class="chip" href="/shop/{o["id"]}/">{E(o["title"])}</a>' for o in CATS if o["id"] != c["id"])
    grid = ('<div class="pgrid">' + "".join(card(p, preview) for p in items) + "</div>") if items else empty(f"We&rsquo;re adding {E(c['title'].lower())} products now. Check back soon.")
    main = (f'<section class="hero sub shopsub"><div class="wrap">{crumbs((c["title"], None))}<h1>{E(c["title"])}</h1><p class="lead">{E(c["blurb"])}</p></div></section>{subnav(c["id"])}'
            f'<section class="sec tight"><div class="wrap">{grid}<p class="small muted pnote">Prices in Australian dollars. Usually dispatched in 1&ndash;2 business days; delivery times vary by location. <a href="/shop/shipping/">Shipping</a> &middot; <a href="/shop/returns/">Returns</a></p>'
            f'<div class="chips">{others}</div></div></section>')
    ld = [{"@type": "CollectionPage", "name": c["title"], "url": f'{BASE}/shop/{c["id"]}/'}, crumb_ld((c["title"], f'{BASE}/shop/{c["id"]}/'))]
    if items: ld.append({"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i, "name": p["name"], "url": f'{BASE}/shop/p/{p["id"]}/'} for i, p in enumerate(items, 1)]})
    return doc(C, head(f'{c["title"]} tools | ToolRank Shop', f'{c["blurb"]} Shipped from Australian suppliers, secure Stripe checkout.', f'/shop/{c["id"]}/', ld), main, preview)

def product_page(C, p, preview):
    c = CAT[p["category"]]; ok = sellable(p)
    buy = (f'<p class="buy"><a class="btn xl" href="{E(p["stripe_link"])}" rel="noopener">Buy now</a></p><p class="small muted">Secure checkout by Stripe. You&rsquo;ll enter your delivery address at checkout.</p>'
           if p.get("stripe_link") and ok else '<p class="muted">Not available to buy yet.</p>')
    price = f'<p class="pprice big">{money(p["our_price"])} <span class="small muted">AUD</span></p>' if ok else '<p class="pprice big tbc">Price to be confirmed <span class="tag">draft</span></p>'
    desc = "".join(f"<p>{E(x)}</p>" for x in str(p.get("description") or "").split("\n\n") if x.strip())
    main = (f'<section class="hero sub shopsub"><div class="wrap">{crumbs((c["title"], f"/shop/{c["id"]}/"), (p["name"], None))}</div></section>'
            f'<section class="sec tight"><div class="wrap pp"><figure class="ppimg"><img src="{E(img(p))}" alt="{E(p["name"])}" width="660" height="528"></figure>'
            f'<div class="ppinfo"><p class="pcat">{E(c["title"])}</p><h1>{E(p["name"])}</h1>{price}{buy}'
            f'<ul class="pfacts"><li>Ships from an Australian supplier. Usually dispatched in 1&ndash;2 business days; delivery times vary by location.</li>'
            f'<li>Covered by the Australian Consumer Law guarantees. <a href="/shop/returns/">Returns &amp; refunds</a></li>'
            f'<li>Questions? <a href="mailto:{MAIL}?subject={E("Question: " + p["name"])}">{MAIL}</a></li></ul></div></div>'
            f'<div class="wrap prose pdesc"><h2>Details</h2>{desc}</div></section>')
    ld = [crumb_ld((c["title"], f'{BASE}/shop/{c["id"]}/'), (p["name"], f'{BASE}/shop/p/{p["id"]}/'))]
    prod = {"@type": "Product", "name": p["name"], "description": re.sub(r"\s+", " ", str(p.get("description") or "")), "image": img(p) if img(p).startswith("http") else BASE + img(p), "category": c["title"]}
    if ok: prod["offers"] = {"@type": "Offer", "price": f'{p["our_price"]:.2f}', "priceCurrency": "AUD", "url": f'{BASE}/shop/p/{p["id"]}/'}
    ld.append(prod)
    return doc(C, head(f'{p["name"]} | ToolRank Shop', f'{p["name"]}: {re.sub(r"\s+", " ", str(p.get("description") or ""))}', f'/shop/p/{p["id"]}/', ld), main, preview)

# ---------- policy pages (Australian Consumer Law) ----------
def policy(C, key, title, lead, body, preview):
    upd = CFG.get("policies_updated", "")
    main = (f'<section class="hero sub shopsub"><div class="wrap">{crumbs((title, None))}<h1>{E(title)}</h1><p class="lead">{lead}</p></div></section>{subnav("-")}'
            f'<section class="sec tight"><div class="wrap prose policy">{body}<p class="small muted">{operator()} Contact: <a href="mailto:{MAIL}">{MAIL}</a>. Last updated <time datetime="{upd}">{upd}</time>.</p></div></section>')
    return doc(C, head(f"{title} | ToolRank Shop", f"{title} for ToolRank Shop: {re.sub('<[^>]+>', '', lead)}", f"/shop/{key}/", [crumb_ld((title, f"{BASE}/shop/{key}/"))]), main, preview)

ACL = ("Our goods come with guarantees that cannot be excluded under the Australian Consumer Law. You are entitled to a replacement or refund for a major failure and "
       "compensation for any other reasonably foreseeable loss or damage. You are also entitled to have the goods repaired or replaced if the goods fail to be of acceptable "
       "quality and the failure does not amount to a major failure.")
def policies(C, preview):
    com = CFG.get("change_of_mind_days")
    com_txt = (f"<p>If you change your mind, you can return an unused item in its original packaging within {int(com)} days of delivery for a refund of the item price. Return postage for change-of-mind returns is paid by you.</p>"
               if com else "<p>We don&rsquo;t offer refunds or exchanges for change of mind (for example, if you ordered the wrong size or no longer need the item), unless a product page says otherwise. This doesn&rsquo;t affect your rights under the Australian Consumer Law if an item is faulty, not as described or doesn&rsquo;t match a sample.</p>")
    shipping = f"""<h2>Where we ship</h2><p>We deliver to addresses within Australia. Products are shipped directly from our Australian suppliers&rsquo; warehouses, so items in one order may arrive in separate parcels.</p>
<h2>Delivery times</h2><p>Orders are usually dispatched in 1&ndash;2 business days. Delivery times vary by location. We&rsquo;ll email tracking details once your order has been dispatched.</p>
<h2>Delivery cost</h2><p>Any delivery charge is shown before you pay. You won&rsquo;t be charged anything extra after checkout.</p>
<h2>Addresses we can&rsquo;t deliver to</h2><p>Some large or heavy items can&rsquo;t be delivered to every location (for example some remote areas, PO boxes or parcel lockers). If we can&rsquo;t deliver your order, we&rsquo;ll contact you and give you a full refund.</p>
<h2>Damaged, lost or late parcels</h2><p>If your order arrives damaged, doesn&rsquo;t arrive, or the wrong item turns up, email <a href="mailto:{MAIL}">{MAIL}</a> with your order number (and photos for damage). We deal with the supplier and courier for you; you don&rsquo;t need to contact them.</p>
<h2>Changing or cancelling an order</h2><p>Email us as soon as possible. If your order hasn&rsquo;t been dispatched yet, we can change it or cancel it with a full refund.</p>"""
    returns = f"""<h2>Your rights under the Australian Consumer Law</h2><p class="acl">{ACL}</p>
<h2>Major failures: refund or replacement</h2><p>If an item has a major failure (for example it&rsquo;s unsafe, significantly different from its description, or has a problem that would have stopped you buying it if you&rsquo;d known about it), you can choose a refund or a replacement.</p>
<h2>Minor failures: repair or replacement</h2><p>If the problem is minor, we&rsquo;ll repair or replace the item within a reasonable time. If we can&rsquo;t or don&rsquo;t, you can choose a refund or replacement instead.</p>
<h2>We handle your claim</h2><p>As the seller, we handle all returns and consumer-guarantee claims. You don&rsquo;t need to contact the supplier or manufacturer (though any manufacturer warranty is in addition to your rights).</p>
<h2>How to make a claim</h2><ol><li>Email <a href="mailto:{MAIL}">{MAIL}</a> with your order number, what&rsquo;s wrong, and photos if you can.</li><li>We&rsquo;ll reply, usually within 1&ndash;2 business days, and tell you what happens next. If the item needs to come back, we&rsquo;ll arrange the return and cover the cost for faulty or incorrect items.</li><li>Approved refunds go back to your original payment method.</li></ol>
<h2>Change of mind</h2>{com_txt}
<h2>What isn&rsquo;t covered</h2><p>Consumer guarantees don&rsquo;t cover damage caused by misuse, abnormal use, or ignoring the instructions, or normal wear and tear.</p>"""
    who = operator()
    terms = f"""<h2>Who we are</h2><p>{who} &ldquo;We&rdquo;, &ldquo;us&rdquo; and &ldquo;our&rdquo; refer to ToolRank Shop. Contact: <a href="mailto:{MAIL}">{MAIL}</a>.</p>
<h2>Products</h2><p>We try to describe and picture every product accurately. Images may be illustrative; check the product details for specifications. We sell non-electrical tools and equipment.</p>
<h2>Prices and payment</h2><p>Prices are in Australian dollars. Payment is taken at checkout by Stripe, our payment provider. We never see or store your full card details.</p>
<h2>Your order</h2><p>After you pay, you&rsquo;ll receive an order confirmation by email. If an item turns out to be unavailable, or was listed at an obviously wrong price, we&rsquo;ll tell you and give you a full refund for that item.</p>
<h2>Delivery</h2><p>Delivery is covered in our <a href="/shop/shipping/">shipping policy</a>. Risk in the goods passes to you on delivery.</p>
<h2>Returns and your consumer rights</h2><p>{ACL}</p><p>See <a href="/shop/returns/">returns &amp; refunds</a> for how to make a claim. Nothing in these terms excludes, restricts or modifies any right or remedy you have under the Australian Consumer Law.</p>
<h2>Using tools safely</h2><p>Always read and follow the manufacturer&rsquo;s instructions and safety warnings, and use appropriate protective equipment.</p>
<h2>Liability</h2><p>To the extent permitted by law, and except for the guarantees above, our liability is limited to replacing the goods, supplying equivalent goods, or refunding the price you paid.</p>
<h2>Privacy</h2><p>How we handle your details is set out in our <a href="/shop/privacy/">privacy policy</a>.</p>
<h2>Governing law</h2><p>These terms are governed by the laws of New South Wales, Australia.</p>
<h2>Changes</h2><p>We may update these terms. The version published when you place your order applies to that order.</p>"""
    privacy = f"""<h2>What we collect</h2><p>When you order, we collect your name, email address, phone number, delivery address and the details of your order. Payment card details are collected and processed by Stripe; we never see or store them.</p>
<h2>Why we collect it</h2><p>To process and deliver your order, send order and tracking updates, handle returns and questions, prevent fraud, and keep the business records the law requires.</p>
<h2>Who we share it with</h2><ul><li><b>Stripe</b>, to take your payment.</li><li><b>Our supplier and its couriers</b>, who receive your name, delivery address and phone number so they can ship your order directly to you.</li><li>Government or regulators, only where the law requires it.</li></ul><p>We don&rsquo;t sell your personal information, and we don&rsquo;t use it for marketing unless you ask us to.</p>
<h2>Overseas processing</h2><p>Stripe and some of our service providers may store or process information outside Australia, under their own privacy and security commitments.</p>
<h2>Analytics</h2><p>This website uses cookieless, privacy-friendly analytics (GoatCounter) that collect no personal data and don&rsquo;t track you across sites.</p>
<h2>How long we keep it</h2><p>We keep order records for as long as needed for tax and legal requirements (generally five years), then delete them.</p>
<h2>Access, correction and complaints</h2><p>You can ask to see or correct the personal information we hold about you, or make a privacy complaint, by emailing <a href="mailto:{MAIL}">{MAIL}</a>. We&rsquo;ll respond within 30 days. If you&rsquo;re not satisfied with our response, you can contact the Office of the Australian Information Commissioner (oaic.gov.au).</p>"""
    return {"shipping": policy(C, "shipping", "Shipping", "Ships from Australian suppliers. Usually dispatched in 1&ndash;2 business days; delivery times vary by location.", shipping, preview),
            "returns": policy(C, "returns", "Returns & refunds", "Your rights under the Australian Consumer Law, and how we handle faulty or incorrect items.", returns, preview),
            "terms": policy(C, "terms", "Terms of sale", "The terms that apply when you buy from ToolRank Shop.", terms, preview),
            "privacy": policy(C, "privacy", "Privacy", "What we collect when you order, why, and who we share it with.", privacy, preview)}

def urls():
    return ["/shop/"] + [f'/shop/{c["id"]}/' for c in CATS] + [f"/shop/{k}/" for k, _ in POLICIES] + [f'/shop/p/{p["id"]}/' for p in PJ["products"] if sellable(p)]

def build(out=None, preview=False):
    out = pathlib.Path(out) if out else ROOT
    bad = [p["id"] for p in PJ["products"] if p.get("category") not in CAT]
    if bad: raise SystemExit(f"products.json: unknown category for {bad}")
    (ROOT/"assets/shop").mkdir(parents=True, exist_ok=True)
    for c in CATS: (ROOT/f"assets/shop/{c['id']}.svg").write_text(art(c["id"]))
    C = chrome()
    prods = [p for p in PJ["products"] if preview or sellable(p)]
    def w(rel, s): d = out/rel; d.mkdir(parents=True, exist_ok=True); (d/"index.html").write_text(s)
    if (out/"shop/p").exists(): shutil.rmtree(out/"shop/p")  # hidden/removed products must disappear
    w("shop", home_page(C, prods, preview))
    for c in CATS: w(f"shop/{c['id']}", cat_page(C, c, prods, preview))
    for p in prods: w(f"shop/p/{p['id']}", product_page(C, p, preview))
    for k, s in policies(C, preview).items(): w(f"shop/{k}", s)
    if preview:
        for a in ("assets", "manifest.webmanifest"):
            if not (out/a).exists(): (out/a).symlink_to(ROOT/a)
    n = sum(1 for p in PJ["products"] if sellable(p))
    print(f"shop: {len(CATS)} categories, {len(prods)} product page(s) ({n} sellable of {len(PJ['products'])} in products.json){' [PREVIEW incl. drafts]' if preview else ''} -> {out/'shop'}")
    return urls()

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--preview"]:
        if len(a) < 2 or pathlib.Path(a[1]).resolve() == ROOT or ROOT in pathlib.Path(a[1]).resolve().parents: raise SystemExit("--preview needs a directory OUTSIDE the repo")
        build(a[1], preview=True)
    else: build()
