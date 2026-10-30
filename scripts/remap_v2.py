#!/usr/bin/env python3
"""One-off: remap tools.json into the 16 v2 categories and add verified new tools (2026-10-15)."""
import json, pathlib
R = pathlib.Path(__file__).resolve().parent.parent; P = R/"data/tools.json"
d = json.loads(P.read_text()); old = {c["id"]: c["tools"] for c in d["categories"]}
by = {t["name"]: t for ts in old.values() for t in ts}
def take(names): return [by.pop(n) for n in names]
def V(n,u,v,p,a,ok=True): return {"name":n,"url":u,"verdict":v,"pricing":p,"affiliate_url":"","featured":False,
  "url_check":"200 verified 2026-10-15" if ok else "bot-blocked (403/429), known official domain, verified 2026-10-15","audience":a}
CATS = [
 ("ai-assistants","AI Assistants","General-purpose AI chat assistants for everyday questions, writing and thinking."),
 ("coding","Coding & App Building","Build apps from a prompt, or code faster with AI pair programmers and agents."),
 ("image","Image & Design","Create and edit images, graphics and designs from prompts."),
 ("video","Video & Animation","Generate, edit, caption and translate video with AI."),
 ("writing","Writing & Content","Drafting, editing, rewriting and long-form writing."),
 ("voice-audio","Voice & Audio","Speech, voice cloning, dictation, music and audio editing."),
 ("automation","Automation & Agents","Automate workflows and build AI agents, no-code or in code."),
 ("research","Research & Productivity","Answer engines, research assistants, notes, meetings and planning."),
 ("marketing","Marketing & Sales","Marketing copy, social content, prospecting and CRM AI."),
 ("business","Business & Data","AI for workplace suites, databases, meetings and enterprise teams."),
 ("restaurants","Restaurants & Bars","AI phone hosts, voice ordering, marketing and kitchen waste tracking for venues."),
 ("hospitality","Hospitality & Travel","AI trip planners for travellers and guest-messaging and revenue AI for hotels."),
 ("crypto","Crypto & Web3","On-chain research, AI trading assistants, wallet security, portfolio and tax tools."),
 ("education","Education & Learning","AI tutors, language learning and classroom tools for teachers."),
 ("health","Health & Fitness","AI workout coaching, sleep and recovery insights, symptom checks and wellbeing."),
 ("gaming","Gaming","Make games and game assets with AI, or play AI-driven stories."),
]
T = {}
T["ai-assistants"] = take(["ChatGPT","Claude","Google Gemini","Microsoft Copilot","Grok"]) + [
  V("Le Chat (Mistral)","https://chat.mistral.ai","Mistral AI's assistant with web search, documents and fast answers.","freemium","both",False)]
T["marketing"] = take(["Jasper","Copy.ai","Typefully","Easel"]) + [
  V("HubSpot Breeze","https://www.hubspot.com/products/artificial-intelligence","HubSpot's AI agents and assistants built into its CRM and marketing hub.","freemium","business"),
  V("Clay","https://www.clay.com","Data enrichment and AI research agents for building prospect lists.","freemium","business"),
  V("Apollo.io","https://www.apollo.io","B2B contact database and sales engagement with AI-written outreach.","freemium","business")]
T["business"] = take(["Microsoft 365 Copilot","Gemini for Google Workspace","Airtable","ClickUp","Fireflies.ai","Fathom","Writer","Superhuman","Glide"])
T["automation"] = take(["Zapier","n8n","Make","Zapier Agents","Manus","ChatGPT Agent"]) + [by.pop(t["name"]) for t in old["agent-builders"] if t["name"] in by] + take(["Perplexity Comet"])
T["research"] = [by.pop(t["name"]) for t in old["research"][:4]] + take(["Notion AI","Gamma","Granola"]) + [by.pop(t["name"]) for t in old["research"][4:]] + take(["Motion","Reclaim.ai","Raycast","Mem","Beautiful.ai"])
vc = [t for t in old["vibe-coding"] if t["name"] in by]; ca = [t for t in old["coding-assistants"] if t["name"] in by]
mix = []
for i in range(max(len(vc), len(ca))):
    if i < len(ca): mix.append(ca[i])
    if i < len(vc): mix.append(vc[i])
T["coding"] = [by.pop(t["name"]) for t in mix] + take(["coucou"])
for k in ("image","video","writing","voice-audio","crypto"): T[k] = [by.pop(t["name"]) for t in old[k] if t["name"] in by]
T["restaurants"] = [
  V("Slang.ai","https://www.slang.ai","AI phone host that answers restaurant calls, takes reservations and answers FAQs.","paid","business"),
  V("Loman","https://loman.ai","24/7 AI phone answering for restaurants: orders, reservations and questions.","paid","business"),
  V("ConverseNow","https://conversenow.ai","Voice AI that takes phone and drive-thru orders for restaurant chains.","paid","business"),
  V("Owner.com","https://www.owner.com","Online ordering, website and automated marketing for independent restaurants.","paid","business"),
  V("Popmenu","https://get.popmenu.com","Restaurant website, marketing and AI phone answering platform.","paid","business",False),
  V("Toast (ToastIQ)","https://pos.toasttab.com","Restaurant POS whose ToastIQ AI surfaces insights and helps run service.","paid","business",False),
  V("Winnow","https://www.winnowsolutions.com","Camera-based AI that tracks and cuts food waste in commercial kitchens.","paid","business")]
T["hospitality"] = [
  V("Mindtrip","https://mindtrip.ai","AI travel planner that builds itineraries on a map and helps you book.","free","consumer"),
  V("Layla","https://layla.ai","Chat-based AI trip planner for itineraries, flights and hotels.","freemium","consumer",False),
  V("Wonderplan","https://wonderplan.ai","Free AI trip planner that generates day-by-day itineraries.","free","consumer"),
  V("Canary Technologies","https://www.canarytechnologies.com","Hotel guest management: check-in, upsells, payments and AI messaging.","paid","business"),
  V("HiJiffy","https://www.hijiffy.com","AI chatbot and guest communications hub for hotels.","paid","business"),
  V("Asksuite","https://asksuite.com","AI agent for hotels that answers guests and drives direct bookings.","paid","business"),
  V("Duetto","https://www.duettocloud.com","Hotel revenue management and pricing software.","paid","business")]
T["education"] = [
  V("Khanmigo","https://www.khanmigo.ai","Khan Academy's AI tutor for students and teaching assistant for teachers.","freemium","both"),
  V("Duolingo","https://www.duolingo.com","Gamified language learning; Max tier adds AI roleplay and explanations.","freemium","consumer"),
  V("Speak","https://www.speak.com","Language app focused on speaking practice with an AI tutor.","freemium","consumer"),
  V("Quizlet","https://quizlet.com","Flashcards and study sets with AI-generated practice.","freemium","consumer",False),
  V("MagicSchool","https://www.magicschool.ai","AI toolkit for teachers and school districts: lesson plans, rubrics, feedback.","freemium","business"),
  V("Brisk Teaching","https://www.briskteaching.com","Chrome extension that helps teachers create, give feedback and differentiate.","freemium","business")]
T["health"] = [
  V("Fitbod","https://fitbod.me","Strength-training app that adapts each workout to your history and recovery.","paid","consumer",False),
  V("Freeletics","https://www.freeletics.com","AI coach that builds personalised bodyweight and gym training plans.","freemium","consumer"),
  V("Oura","https://ouraring.com","Smart ring tracking sleep, readiness and activity, with an AI advisor.","paid","consumer"),
  V("WHOOP","https://www.whoop.com","Wearable for strain, recovery and sleep, with a GPT-powered coach.","paid","consumer",False),
  V("Ada","https://ada.com","AI symptom checker that suggests possible causes and next steps.","free","consumer"),
  V("Wysa","https://www.wysa.com","AI mental wellbeing chatbot based on CBT techniques, with human coaching option.","freemium","both")]
T["gaming"] = [
  V("Rosebud AI","https://rosebud.ai","Make and share browser games by describing them in plain English.","freemium","consumer"),
  V("Scenario","https://www.scenario.com","Generate consistent game art and assets with custom-trained models.","freemium","business"),
  V("Ludo.ai","https://ludo.ai","Game ideation, market research and sprite and asset generation.","freemium","business"),
  V("Meshy","https://www.meshy.ai","Text- and image-to-3D model generator for games and 3D printing.","freemium","both"),
  V("Inworld AI","https://inworld.ai","Real-time AI voice and character engine for games and apps.","freemium","business"),
  V("Layer","https://www.layer.ai","AI creative platform for game studios to produce art at scale.","paid","business"),
  V("AI Dungeon","https://aidungeon.com","Free AI text adventure game where the story responds to anything you type.","freemium","consumer")]
assert not by, by.keys()
d["categories"] = [{"id": i, "title": t, "blurb": b, "tools": T[i]} for i, t, b in CATS]
for c in d["categories"]: assert len(c["tools"]) >= 6, c["id"]
P.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print({c["id"]: len(c["tools"]) for c in d["categories"]}, sum(len(c["tools"]) for c in d["categories"]))
