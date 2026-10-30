#!/usr/bin/env python3
"""Re-check FactoryFast stock and price for listed products.
Supplier URLs, costs and margins are PRIVATE: they live outside the repo in TOOLRANK_PRIVATE
(default /workspace/toolrank-private/costs.json), keyed by product id. Without that file (e.g. on GitHub Actions) this script does nothing.
- Supplier shows sold out  -> public stock "out", status "paused" (pages disappear on the next build).
- Supplier price changed   -> private cost/margin updated; if margin after Stripe fees drops below 5% of cost, status "paused".
- Back in stock / margin OK again (paused_reason set by this script) -> re-activated.
our_price is never changed automatically. Network errors leave the product untouched.
Runs from scripts/build.py when CI or FF_SYNC is set, or standalone: python3 scripts/ff_sync.py"""
import json, os, pathlib, urllib.request, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
F = ROOT/"data/products.json"
PRIV = pathlib.Path(os.environ.get("TOOLRANK_PRIVATE", "/workspace/toolrank-private/costs.json"))
def fee(p): return round(p*0.0165 + 0.30, 2)
def private():
    """Private supplier/cost data keyed by product id, or {} when the file is not available."""
    try: return json.loads(PRIV.read_text())["products"]
    except Exception: return {}
def sync():
    pv = private()
    if not pv: print(f"ff_sync: no private cost file at {PRIV}; skipping"); return
    d = json.loads(F.read_text()); changed = 0
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=11))).isoformat(timespec="minutes")
    for p in d["products"]:
        c = pv.get(p["id"])
        if not c or c.get("supplier") != "FactoryFast" or not c.get("supplier_url") or p.get("status") == "draft": continue
        try:
            rq = urllib.request.Request(c["supplier_url"] + ".js", headers={"User-Agent": "Mozilla/5.0 (ToolRank stock check)"})
            j = json.loads(urllib.request.urlopen(rq, timeout=20).read())
        except Exception as e:
            print("ff_sync: skip", p.get("sku"), str(e)[:60]); continue
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
            changed += 1; p["stock_checked"] = now; print("ff_sync: changed", p.get("sku"), p["status"], p["stock"], c["supplier_cost"])
    if changed:
        F.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        PRIV.write_text(json.dumps({**json.loads(PRIV.read_text()), "products": pv}, indent=1, ensure_ascii=False))
    print(f"ff_sync: {changed} product(s) changed")
if __name__ == "__main__": sync()
