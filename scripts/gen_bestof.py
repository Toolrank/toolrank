#!/usr/bin/env python3
"""Generate data-driven /best-of/ guide pages from verified facts in data/tools.json.
Every page: >=4 vendor-verified tools, a distinct filter (angle), and copy assembled only from
verified fields (pricing_detail, platforms, integrations, best_for, main_limitation, why_rank).
Writes data/best-of.json (keeps hand-written pages n<=50) and monetisation/guide-plan-500.md.
Usage: python3 scripts/gen_bestof.py [--limit N]"""
import json, re, sys, pathlib, html
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.loads((ROOT/"data/tools.json").read_text()); BO = json.loads((ROOT/"data/best-of.json").read_text())
import datetime as dt
def hday(d): return dt.date.fromisoformat(d).strftime("%-d %b %Y")
def span(ds):
    """Human date or date range for the check dates of the tools on a page, e.g. 16 Oct 2026 or 16–17 Oct 2026."""
    ds = sorted(set(ds)); a, b = dt.date.fromisoformat(ds[0]), dt.date.fromisoformat(ds[-1])
    if a == b: return hday(ds[0])
    if (a.year, a.month) == (b.year, b.month): return f"{a.day}\u2013{b.day} {b.strftime('%b %Y')}"
    return f"{hday(ds[0])} \u2013 {hday(ds[-1])}"
def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
CAT = {c["id"]: c for c in D["categories"]}
NOUN = {"ai-assistants": "AI assistants", "coding": "AI coding tools", "image": "AI image tools", "video": "AI video tools", "writing": "AI writing tools",
        "voice-audio": "AI voice and audio tools", "automation": "AI automation tools", "research": "AI research and productivity tools", "marketing": "AI marketing tools",
        "business": "AI business tools", "restaurants": "AI tools for restaurants", "hospitality": "AI hospitality tools", "crypto": "AI crypto tools",
        "education": "AI education tools", "health": "AI health and fitness tools", "gaming": "AI game development tools"}
SHORT = {"ai-assistants": "AI Assistants", "coding": "AI Coding Tools", "image": "AI Image Tools", "video": "AI Video Tools", "writing": "AI Writing Tools",
         "voice-audio": "AI Voice & Audio Tools", "automation": "AI Automation Tools", "research": "AI Research Tools", "marketing": "AI Marketing Tools",
         "business": "AI Business Tools", "restaurants": "AI Restaurant Tools", "hospitality": "AI Hospitality Tools", "crypto": "AI Crypto Tools",
         "education": "AI Education Tools", "health": "AI Health Tools", "gaming": "AI Game Dev Tools"}
FREE_OVERRIDE = {"qodo": "trial", "oura": "trial", "deepl-write": "yes"}
def usd(t):
    best = None
    for x in (t.get("pricing_detail") or {}).get("tiers", []):
        p = x["price"]
        if "not shown" in p.lower(): continue
        for m in re.finditer(r'\$(\d[\d,]*(?:\.\d+)?)\s*(?:/|per\s)\s*(?:user/|seat/|member/|location/|seat |user |member )?(mo\b|month)', p):
            v = float(m.group(1).replace(",", ""))
            if v > 0 and (best is None or v < best[0]): best = (v, x["name"])
    return best
def freeness(i, t):
    if i in FREE_OVERRIDE: return FREE_OVERRIDE[i]
    pd = t.get("pricing_detail") or {}; f = (pd.get("free_tier") or "").lower()
    if pd.get("free_tier_unverified") and not f and pd.get("model") != "free": return "unknown"  # vendor page did not show whether a free plan exists
    if pd.get("model") == "free" or t["pricing"] == "free": return "free"
    if ("trial" in f or "first month free" in f) and not re.search(r"free plan|free forever|free:|basic|starter|lite|hobby|personal|sandbox|\$0|free tier|free for|open source|free to|free version", f): return "trial"
    if f or any(re.match(r"\$?0\b|free", x["price"].lower()) for x in pd.get("tiers", [])): return "yes"
    return "no"
ALL = []
for c in D["categories"]:
    for k, t in enumerate(c["tools"]):
        if not t.get("last_verified"): continue
        i = slug(t["name"]); pd = t.get("pricing_detail") or {}
        blob = " ".join([*(t.get("platforms") or []), *(t.get("integrations") or [])]).lower()
        tiers = pd.get("tiers", []); tn = " ".join(x["name"] + " " + x["price"] + " " + x.get("notes", "") for x in tiers).lower()
        ALL.append(dict(id=i, cat=c["id"], rank=k, t=t, usd=usd(t), free=freeness(i, t), blob=blob, tiers=tiers, tn=tn))
BYID = {a["id"]: a for a in ALL}
def andl(xs): return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
def low(s):
    s = (s or "").strip().rstrip("."); w = s.split(" ")[0] if s else ""
    return s if (len(w) > 1 and (w.isupper() or any(ch.isupper() for ch in w[1:]))) else s[:1].lower() + s[1:]
def tier_named(a, pred):
    for x in a["tiers"]:
        if pred(x): return x["name"]
    return ""
def free_tier_name(a): return tier_named(a, lambda x: re.match(r"\$?0\b|free", x["price"].lower()) or x["name"].lower() in ("free", "hobby", "basic", "personal", "lite", "sandbox"))
def cheap_tier_name(a): return a["usd"][1] if a["usd"] else ""
def money(v): return f"${v:,.2f}".replace(".00", "")
def plan_txt(a, tn):
    x = next((x for x in a["tiers"] if x["name"] == tn), None)
    if x: return f'{x["name"]} ({x["price"]})'
    pd = a["t"]["pricing_detail"]
    return pd.get("starting_price") or (f'free plan: {pd["free_tier"]}' if pd.get("free_tier") and a["free"] in ("yes", "free") else "price not yet verified")

# ---------- topic definitions ----------
# Each topic: slug, cat (breadcrumb category), h1, title, ids (ordered), tierfn, angle(intro sentence), crit(how chosen), kind, order_note
TOPICS = []; PLAN = []
def plan(cat, topic, needs, slug_=None, status=None, reason=""):
    PLAN.append(dict(cat=cat, topic=topic, needs=needs, slug=slug_, status=status, reason=reason))
def add(cat, slug_, h1, title, sel, tierfn, angle, crit, needs, order="rank", order_note=None):
    ids = [a["id"] for a in sorted(sel, key=(lambda a: (a["usd"][0] if a["usd"] else 9e9, a["rank"])) if order == "price" else (lambda a: (list(CAT).index(a["cat"]), a["rank"])))]
    TOPICS.append(dict(cat=cat, slug=slug_, h1=h1, title=title, ids=ids[:10], tierfn=tierfn, angle=angle, crit=crit, needs=needs, order_note=order_note))
def incat(c): return [a for a in ALL if a["cat"] == c]
has = lambda a, *ws: any(w in a["blob"] for w in ws)
def offers_api(a):
    """The vendor offers its own API (not just 'works with LLM APIs', an 'API connector' to other services, or a model provider's API key)."""
    b = re.sub(r"(most |any )?(llm|model|provider) apis?|api connector|gemini api|api keys?|openapi", " ", a["blob"])
    return bool(re.search(r"\bapi\b", b))

for c in CAT:
    N = NOUN[c]; S = SHORT[c]; pool = incat(c)
    add(c, f"free-{slug(N)}" if not N.startswith("AI tools") else f"free-{slug(N)}", f"Best free {N} (with a real free plan)", f"Best Free {S} in 2026", [a for a in pool if a["free"] in ("yes", "free")], free_tier_name,
        f"These {N} have a free plan or are free to use, and we confirmed it on each vendor's own pricing page", "a free plan or free use (not just a trial)", "free_tier verified")
    for cap in (10, 15, 20, 30, 50, 100):
        add(c, f"{slug(N)}-under-{cap}-a-month", f"Best {N} for ${cap} a month or less", f"Best {S} Under ${cap}/Month (2026)", [a for a in pool if a["usd"] and a["usd"][0] <= cap], cheap_tier_name,
            f"Every tool here has a paid plan listed at ${cap} a month or less on its vendor's pricing page", f"a verified paid plan at or below ${cap}/month (USD)", "tier prices in USD")
    add(c, f"cheapest-{slug(N)}", f"Cheapest {N}: lowest verified paid plans", f"Cheapest {S}: Paid Plans Compared", [a for a in pool if a["usd"]], cheap_tier_name,
        f"This list ranks {N} purely by their cheapest verified paid plan", "a paid plan price we could read on the vendor page", "tier prices in USD", order="price",
        order_note="Ordered strictly by lowest verified monthly price, cheapest first. Rank in the category ranking is shown on each profile.")
    add(c, f"{slug(N)}-with-free-trial-no-free-plan", f"{N[:1].upper()+N[1:]} with a free trial (paid plans only)", f"{S} With a Free Trial (2026)", [a for a in pool if a["free"] == "trial"], cheap_tier_name,
        f"None of these {N} has a permanent free plan, but each offers a trial confirmed on its pricing page", "a trial but no permanent free plan", "free_tier text mentions a trial")
    add(c, f"paid-{slug(N)}-no-free-plan", f"Best paid {N} (no free plan)", f"Best Paid {S}: No Free Plan (2026)", [a for a in pool if a["free"] in ("no", "trial")], cheap_tier_name,
        f"These {N} are paid products: no permanent free plan is listed on their pricing pages", "no permanent free plan on the vendor page", "free_tier verified absent")
    add(c, f"{slug(N)}-with-mobile-apps", f"Best {N} with mobile apps", f"Best {S} With Mobile Apps (2026)", [a for a in pool if has(a, "ios", "android", "iphone", "mobile")], cheap_tier_name,
        f"Each of these {N} lists an iOS, Android or mobile app among its platforms", "a mobile app listed on the vendor site", "platforms verified")
    add(c, f"{slug(N)}-with-an-api", f"Best {N} with an API", f"Best {S} With an API (2026)", [a for a in pool if offers_api(a)], cheap_tier_name,
        f"Each of these {N} offers an API, so you can build it into your own product or workflow", "an API listed by the vendor", "platforms/integrations verified")
    add(c, f"{slug(N)}-for-desktop", f"Best {N} with desktop apps", f"Best {S} With Desktop Apps (2026)", [a for a in pool if has(a, "desktop", "mac", "windows", "linux")], cheap_tier_name,
        f"Each of these {N} runs as a desktop app (Mac, Windows or Linux) rather than only in a browser", "a desktop app listed by the vendor", "platforms verified")
    add(c, f"{slug(N)}-for-teams", f"Best {N} for teams (per-seat plans)", f"Best {S} for Teams (2026)", [a for a in pool if re.search(r"/user|/seat|/member|per user|per seat|per member|team", a["tn"])], lambda a: tier_named(a, lambda x: re.search(r"team|business|/user|/seat|/member", (x["name"] + x["price"]).lower())) or cheap_tier_name(a),
        f"Each of these {N} sells a team, business or per-seat plan, so you can put several people on one bill", "a team, business or per-seat plan on the pricing page", "tier names/units verified")
    add(c, f"{slug(N)}-for-enterprise", f"Best {N} for enterprise buyers", f"Best {S} for Enterprise (2026)", [a for a in pool if re.search(r"enterprise|custom|contact sales", a["tn"])], lambda a: tier_named(a, lambda x: re.search(r"enterprise|custom|contact", (x["name"] + x["price"]).lower())),
        f"Each of these {N} lists an Enterprise or custom-priced plan, the usual route to SSO, contracts and volume pricing", "an Enterprise or custom plan on the pricing page", "tier names verified")
    add(c, f"{slug(N)}-with-annual-discount", f"{N[:1].upper()+N[1:]} that are cheaper billed yearly", f"{S} With Annual Discounts (2026)", [a for a in pool if re.search(r"annual|yearly|billed annually", a["tn"]) and re.search(r"monthly|/month", a["tn"])], lambda a: tier_named(a, lambda x: re.search(r"annual|yearly", x["price"].lower())) or cheap_tier_name(a),
        f"Each of these {N} shows both a yearly and a monthly price, so you can see what committing for a year saves", "both annual and monthly prices on the vendor page", "annual + monthly prices verified")
    add(c, f"{slug(N)}-with-mcp", f"Best {N} with MCP support", f"Best {S} With MCP Support (2026)", [a for a in pool if has(a, "mcp")], cheap_tier_name,
        f"Each of these {N} supports the Model Context Protocol (MCP), so AI agents can connect to it", "MCP support listed by the vendor", "integrations verified")
    add(c, f"self-hosted-{slug(N)}", f"Best self-hosted and open-source {N}", f"Best Self-Hosted {S} (2026)", [a for a in pool if has(a, "self-hosted", "open source", "local") or "open source" in (a["t"]["pricing_detail"].get("free_tier") or "").lower()], free_tier_name,
        f"Each of these {N} can run on your own machine or servers, or is open source", "self-hosting, local use or an open-source licence stated by the vendor", "platforms/free_tier verified")

# Cross-category, curated by verified job/integration fields
def pick(*ids): return [BYID[i] for i in ids if i in BYID]
X = [
 ("business", "ai-meeting-note-takers", "Best AI meeting note takers", "Best AI Meeting Note Takers (2026)", pick("otter-ai", "fathom", "fireflies-ai", "granola", "krisp"), cheap_tier_name, "These tools record or transcribe meetings and write the notes for you", "AI meeting notes listed as a core feature on the vendor page"),
 ("business", "free-ai-meeting-note-takers", "Best free AI meeting note takers", "Best Free AI Meeting Note Takers (2026)", [a for a in pick("otter-ai", "fathom", "fireflies-ai", "granola", "krisp") if a["free"] in ("yes", "free")], free_tier_name, "Each of these meeting note takers has a free plan we confirmed on its pricing page", "a free plan and AI meeting notes"),
 ("business", "ai-tools-for-zoom-meetings", "Best AI tools for Zoom meetings", "Best AI Tools for Zoom Meetings (2026)", [a for a in ALL if "zoom" in a["blob"]], cheap_tier_name, "Each of these tools lists a Zoom integration", "Zoom listed as an integration"),
 ("business", "ai-tools-for-microsoft-teams", "Best AI tools for Microsoft Teams users", "Best AI Tools for Microsoft Teams Users", [a for a in ALL if "teams" in a["blob"] and ("microsoft" in a["blob"] or "teams" in a["blob"].split(", "))], cheap_tier_name, "Each of these tools lists Microsoft Teams among its integrations or platforms", "Microsoft Teams listed by the vendor"),
 ("business", "ai-tools-for-google-workspace", "Best AI tools for Google Workspace users", "Best AI Tools for Google Workspace Users (2026)", [a for a in ALL if re.search(r"gmail|google meet|google drive|google calendar|google workspace|\bdocs\b|sheets", a["blob"]) and a["id"] != "superhuman"], cheap_tier_name, "Each of these tools connects to Gmail, Drive, Docs, Sheets, Meet or Google Calendar", "a Google Workspace app listed as an integration"),
 ("video", "ai-avatar-video-generators", "Best AI avatar video generators", "Best AI Avatar Video Generators (2026)", pick("synthesia", "heygen", "colossyan", "descript-video"), cheap_tier_name, "These tools turn a script into a video presented by an AI avatar", "AI avatars listed in the vendor's plans"),
 ("video", "ai-text-to-video-generators", "Best AI text-to-video generators", "Best AI Text-to-Video Generators (2026)", pick("runway", "luma-ai", "pika", "invideo-ai"), cheap_tier_name, "These tools generate video clips from a prompt using video models", "generative video models listed in the vendor's plans"),
 ("voice-audio", "voice-ai-apis-for-developers", "Best voice AI APIs for developers", "Best Voice AI APIs for Developers (2026)", pick("deepgram", "assemblyai", "elevenlabs", "vapi", "inworld-ai"), cheap_tier_name, "Each of these is a developer API for speech-to-text, text-to-speech or voice agents", "an API product with published pricing"),
 ("research", "ai-search-engines", "Best AI search engines", "Best AI Search Engines (2026)", pick("perplexity", "kagi", "liner", "you-com"), cheap_tier_name, "These tools answer questions by searching the web and citing sources", "AI search listed as the core product"),
 ("research", "ai-tools-for-academic-research", "Best AI tools for academic research", "Best AI Tools for Academic Research (2026)", pick("elicit", "consensus", "scite", "notebooklm", "liner"), cheap_tier_name, "These tools search, summarise or check scientific papers and sources", "paper search, citation analysis or source-grounded notes on the vendor page"),
 ("automation", "no-code-ai-agent-builders", "Best no-code AI agent builders", "Best No-Code AI Agent Builders (2026)", pick("zapier-agents", "lindy", "gumloop", "botpress", "make"), cheap_tier_name, "These tools let you build AI agents or AI workflows without writing code", "a no-code builder on the vendor page"),
 ("automation", "open-source-ai-agent-platforms", "Best open-source AI agent and workflow platforms", "Best Open-Source AI Agent Platforms (2026)", pick("n8n", "dify", "flowise", "langflow", "crewai"), free_tier_name, "These platforms publish open-source code you can self-host, with optional paid cloud plans", "open-source or self-hosted edition stated by the vendor"),
 ("coding", "ai-website-builders", "Best AI website and app builders", "Best AI Website Builders (2026)", pick("lovable", "bolt-new", "v0", "replit", "base44", "webflow", "framer"), cheap_tier_name, "These tools build and publish websites or web apps in the browser", "browser-based site or app building with publishing"),
 ("coding", "ai-tools-for-terminal-users", "Best AI coding tools for terminal users", "Best AI Coding Tools for the Terminal (2026)", [a for a in incat("coding") if re.search(r"\bcli\b|terminal", a["blob"])], cheap_tier_name, "Each of these coding tools runs in the terminal (CLI)", "a CLI or terminal product listed by the vendor"),
 ("coding", "ai-coding-tools-for-jetbrains", "Best AI coding tools for JetBrains IDEs", "Best AI Coding Tools for JetBrains IDEs (2026)", [a for a in incat("coding") if "jetbrains" in a["blob"]], cheap_tier_name, "Each of these tools lists JetBrains IDE support", "JetBrains listed as a supported platform"),
 ("coding", "ai-coding-tools-for-vs-code", "Best AI coding tools for VS Code", "Best AI Coding Tools for VS Code (2026)", [a for a in incat("coding") if "vs code" in a["blob"]], cheap_tier_name, "Each of these tools runs in VS Code or is built on it", "VS Code listed as a supported platform"),
 ("coding", "ai-coding-tools-bring-your-own-key", "Best AI coding tools that use your own API keys", "Best BYOK AI Coding Tools (2026)", [a for a in incat("coding") if re.search(r"byok|bring your own|own api|own model keys|most llm apis|openrouter", a["blob"] + " " + (a["t"]["pricing_detail"].get("free_tier") or "").lower())], free_tier_name, "Each of these tools lets you bring your own model API keys", "bring-your-own-key support stated by the vendor"),
 ("coding", "ai-coding-tools-with-local-models", "Best AI coding tools that work with local models", "Best AI Coding Tools for Local Models (2026)", [a for a in incat("coding") if re.search(r"local models|ollama", a["blob"])], free_tier_name, "Each of these tools can use locally run models", "local models or Ollama listed by the vendor"),
 ("coding", "ai-coding-tools-for-github", "Best AI coding tools that work with GitHub", "Best AI Coding Tools for GitHub (2026)", [a for a in incat("coding") if "github" in a["blob"]], cheap_tier_name, "Each of these tools lists a GitHub integration", "GitHub listed as an integration"),
 ("coding", "ai-coding-agents-in-slack", "Best AI coding agents you can use from Slack", "Best AI Coding Agents for Slack (2026)", [a for a in incat("coding") if "slack" in a["blob"]], cheap_tier_name, "Each of these coding tools lists Slack among its integrations", "Slack listed by the vendor"),
 ("automation", "python-ai-agent-frameworks", "Best open-source Python AI agent frameworks", "Best Python AI Agent Frameworks (2026)", [a for a in incat("automation") if "python framework" in a["blob"] and a["free"] in ("yes", "free")], free_tier_name, "Each of these is a code-first agent framework you can install in Python, with a free open-source or free tier to start", "a Python framework listed on the vendor's site or repository"),
 ("ai-assistants", "free-ai-chatbots", "Best free AI chatbots", "Best Free AI Chatbots (2026)", [a for a in incat("ai-assistants") if a["free"] in ("yes", "free")], free_tier_name, "These general assistants have a free plan we confirmed on each vendor's page", "a free plan for a general AI assistant"),
 ("business", "ai-assistants-for-office-suites", "Best AI assistants built into office suites", "Best AI Assistants for Office Suites (2026)", pick("microsoft-365-copilot", "gemini-for-google-workspace", "notion-ai", "clickup"), cheap_tier_name, "These AI assistants live inside a suite of documents, mail or work apps", "AI bundled into a productivity suite plan"),
 ("image", "ai-image-generators-with-api", "Best AI image generators with an API", "Best AI Image Generator APIs (2026)", [a for a in incat("image") if "api" in a["blob"]], cheap_tier_name, "Each of these image generators offers an API", "an API listed by the vendor"),
 ("gaming", "ai-game-asset-generators", "Best AI game asset generators", "Best AI Game Asset Generators (2026)", pick("scenario", "meshy", "ludo-ai", "rosebud-ai"), cheap_tier_name, "These tools generate art, 3D models or game content for game developers", "game asset generation as the vendor's core product"),
 ("restaurants", "ai-tools-for-restaurants", "Best AI tools for restaurants", "Best AI Tools for Restaurants (2026)", incat("restaurants"), cheap_tier_name, "These tools handle restaurant phone calls, ordering or marketing with AI", "restaurant-specific products with vendor pages we checked"),
 ("research", "ai-tools-with-mcp-support", "Best AI tools with MCP support (all categories)", "Best AI Tools With MCP Support (2026)", [a for a in ALL if "mcp" in a["blob"]], cheap_tier_name, "Each of these tools, across all categories, supports the Model Context Protocol", "MCP support listed by the vendor"),
 ("research", "ai-tools-under-10-dollars-a-month", "Best AI tools under $10 a month (all categories)", "Best AI Tools Under $10/Month (2026)", [a for a in ALL if a["usd"] and a["usd"][0] <= 10], cheap_tier_name, "Every tool here, from any category, has a paid plan listed at $10 a month or less", "a verified paid plan at or below $10/month"),
 ("crypto", "free-crypto-analytics-and-portfolio-tools", "Best free crypto analytics and portfolio tools", "Best Free Crypto Analytics Tools (2026)", [a for a in incat("crypto") if a["free"] in ("yes", "free")], free_tier_name, "These crypto tools have a free plan confirmed on their vendor pages", "a free plan"),
 ("crypto", "crypto-analytics-tools-with-api", "Best crypto analytics tools with an API", "Best Crypto Analytics Tools With an API (2026)", pick("dune", "santiment", "nansen", "elfa-ai"), cheap_tier_name, "Each of these crypto data tools offers an API for pulling on-chain or market data into your own code", "an API listed on the vendor pricing page"),
 ("research", "free-ai-tools-for-finding-research-papers", "Best free AI tools for finding research papers", "Best Free AI Tools for Research Papers (2026)", [a for a in pick("semantic-scholar", "research-rabbit", "undermind", "elicit", "consensus") if a["free"] in ("yes", "free")], free_tier_name, "Each of these paper-discovery tools can be used free, confirmed on the vendor's site", "a free plan for paper search or discovery"),
 ("automation", "ai-agent-frameworks-for-developers", "Best AI agent frameworks for developers", "Best AI Agent Frameworks for Developers (2026)", pick("crewai", "mastra", "agno", "llamaindex", "langflow"), free_tier_name, "These are code-first frameworks or platforms for building AI agents, each with a free way to start", "a developer framework with a free tier or open-source edition"),
 ("voice-audio", "ai-text-to-speech-tools", "Best AI text-to-speech tools", "Best AI Text-to-Speech Tools (2026)", pick("elevenlabs", "speechify", "murf", "cartesia"), cheap_tier_name, "These tools turn written text into natural-sounding speech", "text-to-speech as a core product on the vendor page"),
 ("coding", "ai-app-builders-for-non-coders", "Best AI app builders for non-coders", "Best AI App Builders for Non-Coders (2026)", pick("lovable", "bolt-new", "base44", "create-xyz-anything", "macaly", "glide"), free_tier_name, "These tools build working apps from a prompt or a spreadsheet, without writing code", "prompt-to-app or no-code app building on the vendor page"),
 ("research", "ai-note-taking-apps", "Best AI note-taking apps", "Best AI Note-Taking Apps (2026)", pick("notion-ai", "notebooklm", "mem", "granola"), cheap_tier_name, "These apps capture and organise notes with AI built in", "AI note-taking as a core feature on the vendor page"),
 ("video", "ai-video-generators-with-free-plans", "Best AI video generators with a free plan", "Best Free AI Video Generators (2026)", [a for a in pick("runway", "pika", "ltx-studio", "luma-ai", "leonardo-ai") if a["free"] in ("yes", "free")], free_tier_name, "Each of these generative video tools has a free plan we confirmed on its pricing page", "a free plan for generative video"),
 ("crypto", "crypto-trading-bots", "Best crypto trading bots", "Best Crypto Trading Bots (2026)", pick("3commas", "cryptohopper"), cheap_tier_name, "Automated crypto trading bot platforms", "trading-bot products"),
 ("writing", "ai-grammar-checkers", "Best AI grammar checkers and editors", "Best AI Grammar Checkers (2026)", pick("grammarly", "quillbot", "prowritingaid", "wordtune", "deepl-write"), cheap_tier_name, "These tools correct grammar and suggest edits to your writing", "grammar or editing as a core feature"),
 ("education", "ai-tools-for-teachers", "Best AI tools for teachers", "Best AI Tools for Teachers (2026)", pick("khanmigo", "magicschool", "brisk-teaching", "quizlet"), free_tier_name, "These tools give teachers AI help with lessons, feedback or practice sets, with free teacher access or a teacher plan confirmed on each vendor&rsquo;s site", "a teacher plan or free teacher access on the vendor site"),
 ("health", "ai-fitness-trackers", "Best AI fitness wearables", "Best AI Fitness Wearables (2026)", pick("oura", "whoop"), cheap_tier_name, "Wearables with AI coaching", "membership pricing"),
 ("hospitality", "ai-tools-for-hotels", "Best AI tools for hotels", "Best AI Tools for Hotels (2026)", pick("hijiffy", "canary-technologies", "asksuite", "duetto"), lambda a: a["tiers"][0]["name"] if a["tiers"] else "", "These tools use AI for hotel guest messaging, reservations or room pricing", "hotel-specific AI products with vendor pages we checked"),
 ("voice-audio", "ai-music-generators", "Best AI music generators", "Best AI Music Generators (2026)", pick("suno", "udio", "aiva", "elevenlabs"), cheap_tier_name, "These tools compose original songs or instrumental music from a prompt or style settings", "AI music generation offered on the vendor's own site"),
 ("voice-audio", "ai-dictation-apps", "Best AI dictation apps", "Best AI Dictation Apps (2026)", pick("wispr-flow", "superwhisper"), free_tier_name, "AI dictation", "vendor pricing"),
 ("coding", "ai-code-review-tools", "Best AI code review tools", "Best AI Code Review Tools (2026)", pick("coderabbit", "qodo"), cheap_tier_name, "AI pull-request review", "vendor pricing"),
]
_gen = TOPICS[:]; TOPICS.clear()
for c, s_, h1, ti, sel, tf, ang, crit in X:
    multi = len({a["cat"] for a in sel}) > 1
    add(c, s_, h1, ti, sel, tf, ang, crit, "curated by verified job/integration fields", order_note="Tools come from several ToolRank categories, so they are grouped by category and then by each category&rsquo;s editorial rank." if multi else None)
TOPICS.extend(_gen)
# Plan-only topics: need evidence we do not hold yet (hands-on tests, compliance docs, audience-specific features)
NEEDS = [("for beginners", "hands-on onboarding tests"), ("for students", "verified student/education pricing"), ("for small businesses", "verified SMB plans + use-case evidence"),
         ("for agencies and freelancers", "verified multi-client/brand features"), ("for nonprofits", "verified nonprofit discounts"), ("with the best output quality", "our own side-by-side output tests"),
         ("that don't train on your data", "vendor privacy/training policy pages"), ("with EU data residency (GDPR)", "vendor data-residency documentation"),
         ("with SOC 2 compliance", "vendor trust-centre/SOC 2 reports"), ("priced in Australian dollars", "AUD pricing pages"), ("with the best customer support", "support SLAs + user review data")]
for c in CAT:
    for a, need in NEEDS: plan(c, f"Best {NOUN[c]} {a}", need, None, "not started", f"needs {need}; not held yet, so not publishable without inventing claims")

# ---------- build pages ----------
existing = {p["slug"]: p for p in BO["pages"] if p.get("n", 0) <= 50 and not p.get("generated")}
LIVE = [p["slug"] for p in json.loads((ROOT/"data/best-of.live.json").read_text())] if (ROOT/"data/best-of.live.json").exists() else []
TOPICS.sort(key=lambda T: (LIVE.index(T["slug"]) if T["slug"] in LIVE else len(LIVE)))  # published pages keep their URL and priority
used_sets = [set(i for i, _ in p["items"]) for p in existing.values()]
pages, skipped = [], []
def jacc(a, b): return len(a & b) / max(1, len(a | b))
def fit_desc(*parts):
    s = ""
    for p in parts:
        if len(s + p) <= 160: s += p
    return s.strip()
for T in TOPICS:
    ids = T["ids"]; topic = T["h1"]
    if T["slug"] in existing: plan(T["cat"], topic, T["needs"], T["slug"], "live (hand-written)"); continue
    if len(ids) < 4:
        skipped.append((T, f"only {len(ids)} vendor-verified tool(s) match ({', '.join(BYID[i]['t']['name'] for i in ids) or 'none'}); 4 needed")); continue
    s = set(ids); dup = next((p for p in pages + [{"slug": k, "set": v} for k, v in zip(existing, used_sets)] if jacc(s, p["set"]) >= 0.8), None)
    if dup:
        skipped.append((T, f"near-duplicate of /best-of/{dup['slug']}/ (same or almost the same verified tools)")); continue
    A = [BYID[i] for i in ids]; noun = NOUN.get(T["cat"], "AI tools")
    items = [[a["id"], (T["tierfn"](a) or "")] for a in A]
    priced = [a for a in A if a["usd"]]; ch = min(priced, key=lambda a: a["usd"][0]) if priced else None
    frees = [a for a in A if a["free"] in ("yes", "free")]
    top = A[0]; tt = top["t"]; DAYH = span(a["t"]["last_verified"] for a in A)
    summ = f'{T["angle"]}. ' + f'<b>{html.escape(tt["name"])}</b> comes first: {html.escape(low(tt.get("why_rank") or tt["verdict"]))}. '
    if ch: summ += f'The cheapest verified paid plan here is <b>{html.escape(ch["t"]["name"])}</b> {html.escape(plan_txt(ch, ch["usd"][1]))}. '
    summ += (f'{len(frees)} of the {len(A)} have a free plan we could confirm. ' if frees else f'None of the {len(A)} has a free plan we could confirm. ')
    summ += f'Every price below is from the vendor&rsquo;s own page, checked {DAYH}.'
    picks = []
    for a in A[:7]:
        t = a["t"]; bf = t.get("best_for"); lim = t.get("avoid_if") or t.get("main_limitation"); tn = dict(items)[a["id"]]
        pt = (plan_txt(a, tn).replace(" (", ": ", 1)[:-1] if tn and plan_txt(a, tn).endswith(")") else plan_txt(a, tn))
        if not bf:
            line = f'<b>{html.escape(t["name"])}</b> ({html.escape(pt)}): {html.escape(t["verdict"].rstrip("."))}'
            if lim: line += f'. Watch out: {html.escape(low(lim))}'
            picks.append(line + "."); continue
        line = f'Pick <b>{html.escape(t["name"])}</b> for {html.escape(low(bf))}'
        line += f' ({html.escape((plan_txt(a, tn).replace(" (", ": ", 1)[:-1] if tn and plan_txt(a, tn).endswith(")") else plan_txt(a, tn)))})'
        if lim: line += f'; think twice if {html.escape(low(lim))}' if t.get("avoid_if") else f'. Watch out: {html.escape(low(lim))}'
        picks.append(line + ".")
    pick_txt = " ".join(picks)
    faq = []
    if ch:
        faq.append((f"Which of these is cheapest?", f'{ch["t"]["name"]} {plan_txt(ch, ch["usd"][1])} is the lowest paid price we verified on this list ({ch["t"]["sources"][0]["url"]}, checked {hday(ch["t"]["last_verified"])}). Check the vendor page for tax, billing period and usage limits.'))
    faq.append(("Which of these have a free plan?", ("; ".join(f'{a["t"]["name"]}: {a["t"]["pricing_detail"].get("free_tier") or "free plan listed"}' for a in frees) + ".") if frees else ("None of these has a free plan we could confirm. " + (f'For {andl([a["t"]["name"] for a in A if a["free"] == "unknown"])} the vendor pages we checked do not say either way, so this is marked Not yet verified; check before you sign up.' if any(a["free"] == "unknown" for a in A) else "None lists a permanent free plan on its pricing page. Some offer a trial; see the table."))))
    faq.append(("How were these tools chosen?", f'They are the tools in ToolRank\'s rankings with {T["crit"]}, confirmed on the vendor\'s own website on {DAYH}. Tools we could not verify are left out rather than guessed, and anything unconfirmed is marked Not yet verified.'))
    names = [a["t"]["name"] for a in A]
    title = T["title"] if len(T["title"]) <= 60 else T["title"].replace(" (2026)", "")
    desc = fit_desc(f'{topic}: {len(A)} picks with vendor-verified prices checked {DAYH}, ', f'including {", ".join(names[:2])} and {names[2]}.' if len(", ".join(names[:2]) + names[2]) < 70 else f'led by {names[0]}.')
    if desc.endswith(","): desc = desc[:-1] + "."
    if len(desc) < 70: desc = fit_desc(desc, " Free plans, limits and who should pick which.")
    assert len(title) <= 60 and 70 <= len(desc) <= 160, (T["slug"], title, desc)
    p = dict(slug=T["slug"], n=1000 + len(pages), generated=True, cat=T["cat"], h1=topic, title=title, desc=desc, summary=summ, items=items, pick=pick_txt, faq=faq)
    if T["order_note"]: p["order_note"] = T["order_note"]
    pages.append(dict(slug=T["slug"], set=s, page=p, T=T))
lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
live = pages[:lim]
for x in live: plan(x["T"]["cat"], x["T"]["h1"], x["T"]["needs"], x["slug"], "live")
for x in pages[lim:]: plan(x["T"]["cat"], x["T"]["h1"], x["T"]["needs"], x["slug"], "ready (next batch)")
for T, r in skipped: plan(T["cat"], T["h1"], T["needs"], None, "skipped", r)
BO["pages"] = list(existing.values()) + [x["page"] for x in live]
BO["checked"] = max(a["t"]["last_verified"] for a in ALL)
# previously published pages that are now near-duplicates: redirect to the page that covers them
red = dict(BO.get("redirects", {})); now = {p["slug"] for p in BO["pages"]}
for T, r in skipped:
    if T["slug"] in LIVE and "near-duplicate of /best-of/" in r: red[T["slug"]] = r.split("/best-of/")[1].split("/")[0]
BO["redirects"] = {k: v for k, v in red.items() if k not in now and v in now}
BO["skipped_generated"] = [dict(slug=T["slug"], topic=T["h1"], reason=r) for T, r in skipped]
(ROOT/"data/best-of.json").write_text(json.dumps(BO, indent=1, ensure_ascii=False) + "\n")
extra = len(PLAN) - 500
if extra > 0:
    drop = [k for k, x in enumerate(PLAN) if x["status"] == "not started"][-extra:]
    PLAN = [x for k, x in enumerate(PLAN) if k not in set(drop)]
(ROOT/"data/best-of.live.json").write_text(json.dumps([{"slug": x} for x in dict.fromkeys(LIVE + [x["slug"] for x in live])], indent=0) + "\n")
json.dump(PLAN, open(ROOT/"scripts/tmp/plan_status.json", "w"), indent=1)
print(f"topics {len(TOPICS)}, buildable {len(pages)}, live now {len(live)}, skipped {len(skipped)}")
