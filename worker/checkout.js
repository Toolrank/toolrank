// ToolRank checkout Worker. POST /checkout {items:[{id, qty}]} -> {url} (hosted redirect, default)
// POST /checkout {items, ui:"embedded"} -> {client_secret} (Stripe Embedded Checkout on toolrank.io/shop/checkout/)
// Prices and titles come only from the published price files on toolrank.io (never from the request).
// Secret: STRIPE_SECRET_KEY (restricted key, Checkout Sessions: Write only).
const SITE = "https://toolrank.io";
const ORIGINS = new Set(["https://toolrank.io", "https://www.toolrank.io"]);
const MAX_QTY = 10, MAX_LINES = 20;
const EMBED_UI = "embedded_page";  // Stripe ui_mode for embedded checkout (the old value "embedded" is rejected by Stripe)

function cors(origin) {
  return ORIGINS.has(origin)
    ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400", "Vary": "Origin" }
    : { "Vary": "Origin" };
}
function json(obj, status, origin) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...cors(origin) } });
}
function sydneyToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Australia/Sydney", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}
async function getJSON(path) {
  const r = await fetch(SITE + path, { cf: { cacheTtlByStatus: { "200-299": 300, "404": 1, "500-599": 0 }, cacheEverything: true } });
  if (r.status === 404) return {};
  if (!r.ok) throw new Error("price data " + r.status);
  return r.json();
}
// -> {id, name, cents} or null (unknown / not for sale)
async function lookup(id, cache) {
  const dz = /^TR-DZ-(\d{6})$/i.exec(id);
  if (dz) {
    const n = parseInt(dz[1], 10), k = "/shop-data/pr/" + Math.floor(n / 1000) + ".json";
    const t = cache[k] || (cache[k] = await getJSON(k));
    const row = t[String(n)];
    return row ? { id: "TR-DZ-" + dz[1], name: row[1], cents: row[0] } : null;
  }
  if (!/^[a-z0-9][a-z0-9-]{0,99}$/.test(id)) return null;
  const k = "/shop-data/pr/h.json";
  const t = cache[k] || (cache[k] = await getJSON(k));
  const row = t[id];
  if (!row) return null;
  let [cents, name, reg, ends] = row;  // launch price only while sale_ends (Sydney date) has not passed
  if (Number.isInteger(reg) && ends && sydneyToday() > ends) cents = reg;
  return { id, name, cents };
}
function form(obj, prefix = "", out = new URLSearchParams()) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}[${k}]` : k;
    if (v !== null && typeof v === "object") form(v, key, out);
    else if (v !== undefined) out.append(key, String(v));
  }
  return out;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url), origin = req.headers.get("Origin") || "";
    if (url.pathname !== "/checkout") return json({ error: "Not found" }, 404, origin);
    if (!ORIGINS.has(origin)) return json({ error: "Origin not allowed" }, 403, origin);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (req.method !== "POST") return json({ error: "Method not allowed" }, 405, origin);

    let body;
    try { body = await req.json(); } catch { return json({ error: "Bad request" }, 400, origin); }
    const raw = Array.isArray(body && body.items) ? body.items : [];
    if (!raw.length) return json({ error: "Your cart is empty" }, 400, origin);
    if (raw.length > MAX_LINES) return json({ error: `Max ${MAX_LINES} different items per order` }, 400, origin);

    const merged = new Map();  // only id + qty are read from the request
    for (const it of raw) {
      let id = String((it && it.id) || "").trim();
      if (/^tr-dz-\d{6}$/i.test(id)) id = id.toUpperCase();
      const q = Math.floor(Number(it && it.qty));
      if (!id || !Number.isFinite(q) || q < 1) return json({ error: "Bad item" }, 400, origin);
      merged.set(id, Math.min(MAX_QTY, (merged.get(id) || 0) + q));
    }
    const cache = {}, lines = [];
    try {
      for (const [id, qty] of merged) {
        const p = await lookup(id, cache);
        if (!p || !Number.isInteger(p.cents) || p.cents < 50) return json({ error: "Item not available: " + id.slice(0, 40), id }, 400, origin);
        lines.push({ ...p, qty });
      }
    } catch (e) { return json({ error: "Prices unavailable, try again shortly" }, 503, origin); }

    const ref = lines.map(l => `${l.id}x${l.qty}`).join(",").slice(0, 500);
    const meta = { business: "toolrank", items: ref };
    const embedded = body.ui === "embedded" || body.ui === "embedded_page";  // anything else keeps the hosted redirect flow
    const params = {
      mode: "payment",
      ...(embedded
        ? { ui_mode: EMBED_UI, return_url: SITE + "/shop/thanks/?s={CHECKOUT_SESSION_ID}" }
        : { success_url: SITE + "/shop/thanks/?s={CHECKOUT_SESSION_ID}", cancel_url: SITE + "/shop/cart/" }),
      shipping_address_collection: { allowed_countries: ["AU"] },
      phone_number_collection: { enabled: true },
      billing_address_collection: "auto",
      metadata: meta,
      payment_intent_data: { metadata: meta, description: "ToolRank order" },
      line_items: lines.map(l => ({
        quantity: l.qty,
        price_data: { currency: "aud", unit_amount: l.cents, product_data: { name: l.name.slice(0, 250), metadata: { id: l.id } } },
      })),
    };
    const r = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: { Authorization: "Bearer " + env.STRIPE_SECRET_KEY, "Content-Type": "application/x-www-form-urlencoded" },
      body: form(params),
    });
    const s = await r.json().catch(() => ({}));
    if (!r.ok || !(embedded ? s.client_secret : s.url)) {
      console.log("stripe error", r.status, s.error && s.error.type, s.error && s.error.code, s.error && s.error.message);
      return json({ error: "Checkout unavailable, please order by email", stripe: s.error ? { type: s.error.type, code: s.error.code, message: s.error.message } : { status: r.status } }, 502, origin);
    }
    return json({ ...(embedded ? { client_secret: s.client_secret, ui_mode: s.ui_mode } : { url: s.url }), id: s.id, amount_total: s.amount_total, currency: s.currency, metadata: s.metadata,
                  lines: lines.map(l => ({ id: l.id, name: l.name, unit_amount: l.cents, qty: l.qty })) }, 200, origin);
  },
};
