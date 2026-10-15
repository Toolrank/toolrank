#!/usr/bin/env python3
"""Rebuild static SEO pages from data/*.json.
Outputs: best/<category>/index.html, sitemap.xml, robots.txt, llms.txt, llms-full.txt,
and refreshes the <!--SEO--> head block + pre-rendered directory in index.html / featured.html.
BASE is a PLACEHOLDER until the live domain is chosen: change it and rerun."""
import json, re, html, pathlib
BASE = "https://toolrank.io"  # PLACEHOLDER base URL
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.loads((ROOT/"data/tools.json").read_text())
N = json.loads((ROOT/"data/new-this-week.json").read_text())
UPD = D["updated"]; E = html.escape
LOGO = '<a class="logo" href="/"><span class="mark">T</span>Tool<b>Rank</b></a>'
ORG = {"@type": "Organization", "@id": BASE+"/#org", "name": "ToolRank", "url": BASE+"/"}
SITE = {"@type": "WebSite", "@id": BASE+"/#website", "name": "ToolRank", "url": BASE+"/", "publisher": {"@id": BASE+"/#org"},
        "potentialAction": {"@type": "SearchAction", "target": {"@type": "EntryPoint", "urlTemplate": BASE+"/?q={search_term_string}"},
                            "query-input": "required name=search_term_string"}}
def short(c): return re.sub(r"^Best (for )?", "", c["title"])
def link(t): return t.get("affiliate_url") or t["url"]
def rel(t): return "noopener" + (" sponsored" if t.get("affiliate_url") else "")

def head(title, desc, path, ld, otype="website"):
    url = BASE + path
    return f"""<!--SEO--><title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}"><meta name="robots" content="index,follow,max-snippet:-1">
<meta property="og:type" content="{otype}"><meta property="og:site_name" content="ToolRank"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script><!--/SEO-->"""

def tool_ld(t, c, i):
    # Only facts present in data: name, url, category, and free tier yes/no from pricing field. No ratings invented.
    o = {"@type": "SoftwareApplication", "name": t["name"], "url": t["url"], "description": t["verdict"],
         "applicationCategory": "AI tool: " + short(c)}
    if t["pricing"] in ("free", "freemium"):
        o["offers"] = {"@type": "Offer", "price": "0", "priceCurrency": "USD", "description": t["pricing"] + " (free tier available)"}
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
                   f'<span class="tag {t["pricing"]}">{t["pricing"]}</span><a class="go" href="{E(link(t))}" target="_blank" rel="{rel(t)}">Visit {E(t["name"])} →</a></article>')
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
<header class="top">{LOGO}<nav><a href="/">Directory</a><a href="/submit.html">Submit a tool</a><a href="/featured.html">Get featured</a></nav></header>
<nav class="wrap muted" aria-label="Breadcrumb"><a href="/">ToolRank</a> › {E(c['title'])}</nav>
<main><article><section class="hero"><h1>{E(c['title'])}</h1><p>{E(c['blurb'])}</p><p class="muted">Last updated <time datetime="{UPD}">{UPD}</time>. Editorial ranking.</p></section>
<section class="wrap"><h2>The ranking</h2><ol class="muted">{''.join(f'<li><strong>{E(t["name"])}</strong> ({t["pricing"]}): {E(t["verdict"])}</li>' for t in c["tools"])}</ol><div class="grid">{cards(c)}</div></section>
<section class="wrap faq"><h2>FAQ</h2>{''.join(f'<details open><summary><h3 style="display:inline">{E(a)}</h3></summary><p>{E(b)}</p></details>' for a, b in fq)}</section>
</article><section class="wrap"><h2>More categories</h2><ul>{others}</ul></section></main>
<footer class="wrap muted">© {UPD[:4]} ToolRank. Some links may become affiliate links; featured placements are labelled.</footer></body></html>
"""

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
    ild = [ORG, SITE] + [{"@type": "ItemList", "name": c["title"], "url": f"{BASE}/best/{c['id']}/",
                           "itemListElement": [{"@type": "ListItem", "position": i, "name": t["name"], "url": t["url"]} for i, t in enumerate(c["tools"], 1)]} for c in cats]
    pre = "<!--PRE-->" + "".join(f'<section id="{c["id"]}"><h2><a href="/best/{c["id"]}/">{E(c["title"])}</a></h2><p class="muted">{E(c["blurb"])}</p><div class="grid">{cards(c)}</div></section>' for c in cats) + "<!--/PRE-->"
    def idx(s):
        s = re.sub(r'<main id="cats">.*?</main>', lambda m: f'<main id="cats">{pre}</main>', s, flags=re.S)
        s = s.replace('<a href="index.html"', '<a href="/"')
        return s
    patch("index.html", head("ToolRank: the best AI tools ranked by use case (" + UPD[:4] + ")",
          f"Editorial rankings of AI tools across {len(cats)} use cases: " + ", ".join(short(c) for c in cats) + f". Updated {UPD}.", "/", ild), idx)
    patch("featured.html", head("Get your AI tool featured | ToolRank", "Featured placements and newsletter sponsorship on ToolRank. Featured spots are clearly labelled; rankings stay editorial.", "/featured.html", [ORG, SITE]))
    patch("submit.html", head("Submit your AI tool for free | ToolRank", "Submit your AI tool to ToolRank for free. Every submission gets an editorial review; approved tools are listed in the right category.", "/submit.html", [ORG, SITE]))
    urls = ["/", "/submit.html", "/featured.html"] + [f"/best/{c['id']}/" for c in cats]
    (ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{UPD}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot", "PerplexityBot", "Perplexity-User", "Google-Extended", "Googlebot", "Bingbot", "Applebot", "Applebot-Extended"]
    (ROOT/"robots.txt").write_text("# ToolRank: search engines and AI crawlers are welcome.\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) +
                                   f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
    L = [f"# ToolRank\n\n> Editorial rankings of AI tools by use case. Last updated {UPD}. Rankings are editorial; featured placements are labelled and paid.\n\n## Categories\n"]
    L += [f"- [{c['title']}]({BASE}/best/{c['id']}/): {c['blurb']} #1: {c['tools'][0]['name']}." for c in cats]
    L += [f"\n## Optional\n\n- [Full rankings]({BASE}/llms-full.txt)\n- [Submit a tool (free)]({BASE}/submit.html)\n- [Get featured]({BASE}/featured.html)\n"]
    (ROOT/"llms.txt").write_text("\n".join(L))
    F = [f"# ToolRank: full rankings\n\nLast updated {UPD}. Source: {BASE}/. Editorial ranking; position 1 = top pick. Pricing labels: free / freemium / paid (as listed; verify with vendor).\n"]
    for c in cats:
        F.append(f"\n## {c['title']}\n\n{c['blurb']}\nPage: {BASE}/best/{c['id']}/\n")
        F += [f"{i}. {t['name']} ({t['pricing']}){' [Featured]' if t.get('featured') else ''}: {t['verdict']} {t['url']}" for i, t in enumerate(c["tools"], 1)]
    F.append(f"\n## New this week (as of {N['updated']})\n")
    F += [f"- {n['date']} {n['title']} ({n['type']}): {n['summary']} {n['url']}" for n in sorted(N["items"], key=lambda n: n["date"], reverse=True)]
    (ROOT/"llms-full.txt").write_text("\n".join(F) + "\n")
    print(f"built {len(cats)} category pages, sitemap ({len(urls)} urls), robots, llms.txt, llms-full.txt")
if __name__ == "__main__": main()
