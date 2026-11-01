#!/usr/bin/env python3
"""Reprice hand-built FactoryFast / ZNTS products with the store's standard formula (same as the bulk import):
regular price = (cost incl. Sydney metro delivery x 1.10 + A$0.30) / (1 - 1.65%), rounded UP to .95; never below a 5% margin after Stripe fees.
Launch-sale items keep their sale price (or the new regular price if that is lower) until sale_ends.
Costs are PRIVATE (TOOLRANK_PRIVATE, default /workspace/toolrank-private/costs.json); without that file this does nothing.
Run: python3 scripts/reprice.py [--dry-run]"""
import json, sys, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ff_sync import F, PRIV, fee, private
import dsz_rules as R
def main():
    pv = private()
    if not pv: print("reprice: no private cost file; skipping"); return
    d = json.loads(F.read_text()); today = datetime.date.today().isoformat(); rows = []
    for p in d["products"]:
        c = pv.get(p["id"])
        if not c or c.get("supplier") not in ("FactoryFast", "ZNTS Wholesale") or not isinstance(c.get("cost_total"), (int, float)) or not isinstance(p.get("our_price"), (int, float)): continue
        old = p["our_price"]; old_reg = p.get("regular_price")
        new, _ = R.sell_price(c["cost_total"])
        on_sale = p.get("sale_ends") and today <= p["sale_ends"] and isinstance(old_reg, (int, float))
        if on_sale and old < new:
            p["regular_price"] = new  # sale price stays until sale_ends; the (lower) new regular price applies after
        else:
            p["our_price"] = new
            for k in ("regular_price", "sale_label", "sale_ends"): p.pop(k, None)
        c["margin_aud"] = round(p["our_price"] - fee(p["our_price"]) - c["cost_total"], 2); c["margin_pct"] = round(c["margin_aud"] / c["cost_total"] * 100, 1)
        if p.get("regular_price"):
            c["regular_margin_aud"] = round(p["regular_price"] - fee(p["regular_price"]) - c["cost_total"], 2); c["regular_margin_pct"] = round(c["regular_margin_aud"] / c["cost_total"] * 100, 1)
        else: c.pop("regular_margin_aud", None); c.pop("regular_margin_pct", None)
        assert c["margin_pct"] >= 5, p["id"]
        rows.append((p["id"], old, old_reg, p["our_price"], p.get("regular_price")))
    for r in rows: print(f"{r[0][:40]:40} {r[1]:8.2f} {r[2] or '':>8} -> {r[3]:8.2f} {r[4] or ''}")
    if "--dry-run" in sys.argv: return rows
    F.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    PRIV.write_text(json.dumps({**json.loads(PRIV.read_text()), "products": pv}, indent=1, ensure_ascii=False))
    print(f"reprice: {len(rows)} products")
    return rows
if __name__ == "__main__": main()
