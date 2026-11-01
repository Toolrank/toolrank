#!/usr/bin/env python3
"""Re-check ZNTS Wholesale stock and price (same rules as ff_sync.py).
ZNTS blocks plain requests, so this uses headless Chrome via Playwright to load each product's Shopify .js JSON.
Private costs stay in TOOLRANK_PRIVATE; our_price is never changed. Errors leave products untouched.
Run: python3 scripts/znts_sync.py"""
import json, datetime
from ff_sync import F, PRIV, fee, private
from playwright.sync_api import sync_playwright
def sync():
    pv = private()
    if not pv: print(f"znts_sync: no private cost file at {PRIV}; skipping"); return
    d = json.loads(F.read_text()); changed = ok = 0
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=11))).isoformat(timespec="minutes")
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, channel="chrome")
        pg = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36").new_page()
        for p in d["products"]:
            c = pv.get(p["id"])
            if not c or c.get("supplier") != "ZNTS Wholesale" or not c.get("supplier_url") or p.get("status") == "draft": continue
            try:
                r = pg.goto(c["supplier_url"].split("?")[0] + ".js", timeout=30000)
                j = json.loads(pg.evaluate("document.body.innerText"))
            except Exception as e:
                print("znts_sync: skip", p.get("sku"), str(e)[:80]); continue
            ok += 1
            v = next((x for x in j["variants"] if x["id"] == c.get("supplier_variant_id")), None) or j["variants"][0]
            before = json.dumps([p, c], sort_keys=True)
            price = v["price"]/100
            if price != c.get("supplier_cost"):
                c["supplier_cost"] = price; c["cost_total"] = round(price + float(c.get("supplier_shipping_nsw2131") or 0), 2)
            c["margin_aud"] = round(p["our_price"] - fee(p["our_price"]) - c["cost_total"], 2); c["margin_pct"] = round(c["margin_aud"]/c["cost_total"]*100, 1)
            if not v.get("available"):
                p.update(stock="out", status="paused", paused_reason="out_of_stock")
            elif c["margin_pct"] < 5:
                p.update(stock="in_stock", status="paused", paused_reason="low_margin")
            else:
                p["stock"] = "in_stock"
                if p.get("status") == "paused" and p.get("paused_reason") in ("out_of_stock", "low_margin"): p["status"] = "active"; p.pop("paused_reason", None)
            if json.dumps([p, c], sort_keys=True) != before:
                changed += 1; p["stock_checked"] = now; print("znts_sync: changed", p.get("sku"), p["status"], p["stock"])
        b.close()
    if changed:
        F.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        PRIV.write_text(json.dumps({**json.loads(PRIV.read_text()), "products": pv}, indent=1, ensure_ascii=False))
    print(f"znts_sync: checked {ok}, {changed} product(s) changed")
if __name__ == "__main__": sync()
