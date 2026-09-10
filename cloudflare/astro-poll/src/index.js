// mimic-poll (worker name astro-poll): 1-min cron, per-handle cadence.
// astro every tick (~1440 calls/day), other 9 every 5th tick (~2592/day).
// Total ~4032 calls/day ≈ $4.03/day. KV keys per handle:
//   {handle}/last_seen_id  {handle}/inbox  + global heartbeat mimic/last_tick.
// Writes only on new posts (+ hourly heartbeat).

const API = "https://api.getxapi.com/twitter/user/tweets";

// Recon 2026-09-10 (user_info, all public). Matches astronomer/mimic/handles.json.
const HANDLES = [
  { handle: "astronomer_zero", author_id: "1390948342021120000", cadence_min: 1 },
  { handle: "Timeless_Crypto", author_id: "952109977157668864", cadence_min: 5 },
  { handle: "Trader_XO", author_id: "1381341090", cadence_min: 5 },
  { handle: "CryptoBheem", author_id: "1399033636691849222", cadence_min: 5 },
  { handle: "eliz883", author_id: "993962483332329472", cadence_min: 5 },
  { handle: "lookonchain", author_id: "1462727797135216641", cadence_min: 5 },
  { handle: "laevitas1", author_id: "1306192341682786306", cadence_min: 5 },
  { handle: "hyblockcapital", author_id: "1185049143703724033", cadence_min: 5 },
  { handle: "52kskew", author_id: "723345972", cadence_min: 5 },
  { handle: "exitpumpBTC", author_id: "1373615088532328449", cadence_min: 5 },
];

async function pollOne(env, h) {
  const keyBase = `${h.handle}/`;
  const [lastSeen, inboxRaw] = await Promise.all([
    env.MIMIC_STATE.get(keyBase + "last_seen_id"),
    env.MIMIC_STATE.get(keyBase + "inbox"),
  ]);
  const floor = lastSeen || "0";
  const inbox = inboxRaw ? JSON.parse(inboxRaw) : [];
  const cap = parseInt(env.INBOX_CAP || "200", 10);

  const res = await fetch(`${API}?userId=${h.author_id}`, {
    headers: { Authorization: `Bearer ${env.GETXAPI_KEY}` },
  });
  if (!res.ok) return { handle: h.handle, ok: false, error: `getxapi ${res.status}` };
  const data = await res.json();
  const fresh = (data.tweets || [])
    .filter((t) => typeof t.id === "string" && t.id > floor)
    .sort((a, b) => (a.id < b.id ? -1 : 1));
  if (fresh.length) {
    await Promise.all([
      env.MIMIC_STATE.put(keyBase + "inbox", JSON.stringify(inbox.concat(fresh).slice(-cap))),
      env.MIMIC_STATE.put(keyBase + "last_seen_id", fresh[fresh.length - 1].id),
    ]);
  }
  return { handle: h.handle, ok: true, new: fresh.length };
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(this.run(env));
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/tick") return Response.json(await this.run(env, true));
    return Response.json({ ok: true, handles: HANDLES.length, usage: "cron * * * * *" });
  },

  async run(env, forceAll = false) {
    if (env.PAUSED === "1" && !forceAll) {
      return { ok: true, paused: true, polled: 0, new: 0, results: [] };
    }
    const minute = new Date().getUTCMinutes();
    const due = HANDLES.filter((h) => forceAll || minute % h.cadence_min === 0);
    const results = [];
    for (const h of due) {
      try {
        results.push(await pollOne(env, h));
      } catch (e) {
        results.push({ handle: h.handle, ok: false, error: String(e).slice(0, 120) });
      }
    }
    const lastTick = await env.MIMIC_STATE.get("mimic/last_tick");
    if (!lastTick || Date.now() - parseInt(lastTick, 10) > 3600_000) {
      await env.MIMIC_STATE.put("mimic/last_tick", String(Date.now()));
    }
    const fresh = results.reduce((n, r) => n + (r.new || 0), 0);
    return { ok: true, polled: due.length, new: fresh, results };
  },
};
