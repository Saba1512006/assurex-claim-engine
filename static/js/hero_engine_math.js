/* Hero engine layout math: pure functions, no DOM. Used by hero_engine.js in the browser and by the Node unit tests
   (tests/js/hero_engine_math.test.mjs). Rects are {l, t, r, b} in hero pixels; points are {x, y}. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.AXEngineMath = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const PAD = 24;                 // exclusion padding around every foreground block
  const NODE_R = 46;              // outer ring radius of a model node at scale 1
  const CORE_H = 26;              // half size of the decision core frame at scale 1
  const LABEL_BELOW = 34;         // node caption block under the ring (name + value)
  const LABEL_HALF_W = 64;        // half width of a node caption block
  const CHAR_W = 6.6;             // mono 10.5px with .12em tracking, per character

  const inflate = (r, pad = PAD) => ({ l: r.l - pad, t: r.t - pad, r: r.r + pad, b: r.b + pad });
  const intersects = (a, b) => a.l < b.r && a.r > b.l && a.t < b.b && a.b > b.t;
  const hitsAny = (rect, rects) => rects.some((z) => intersects(rect, z));
  const circleBox = (c, r) => ({ l: c.x - r, t: c.y - r, r: c.x + r, b: c.y + r });

  function cubicPoint(c, t) {
    const u = 1 - t;
    const a = u * u * u, b = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t;
    return { x: a * c.p0.x + b * c.p1.x + d * c.p2.x + e * c.p3.x, y: a * c.p0.y + b * c.p1.y + d * c.p2.y + e * c.p3.y };
  }

  /* true when any sampled point of the curve falls inside one of the rects */
  function cubicHitsRects(c, rects, samples = 64) {
    for (let i = 0; i <= samples; i++) {
      const p = cubicPoint(c, i / samples);
      if (rects.some((z) => p.x > z.l && p.x < z.r && p.y > z.t && p.y < z.b)) return true;
    }
    return false;
  }

  const toD = (c) => `M${c.p0.x.toFixed(1)} ${c.p0.y.toFixed(1)} C${c.p1.x.toFixed(1)} ${c.p1.y.toFixed(1)} ${c.p2.x.toFixed(1)} ${c.p2.y.toFixed(1)} ${c.p3.x.toFixed(1)} ${c.p3.y.toFixed(1)}`;

  /* A smooth S-curve with horizontal tangents from p0 to p3. When it crosses a zone, the control points sag
     downward step by step (the band is below the content) until it clears; null when no route is found. */
  function route(p0, p3, rects, { pull = 0.45, step = 12, tries = 8 } = {}) {
    const dx = p3.x - p0.x;
    for (let k = 0; k <= tries; k++) {
      const sag = k * step;
      const c = { p0, p1: { x: p0.x + dx * pull, y: p0.y + sag }, p2: { x: p3.x - dx * pull, y: p3.y + sag }, p3 };
      if (!cubicHitsRects(c, rects)) return c;
    }
    return null;
  }

  /* layout tier from the hero width */
  const tier = (w) => (w >= 1280 ? "full" : w >= 1081 ? "compact" : w >= 768 ? "strip" : "mini");

  /* the card's result → the outcome terminal that lights up (read from the real view, never assumed from the tab) */
  function outcomeFor(view) {
    if (!view) return null;
    const tone = view.tone || view.outcome;
    if (tone === "valid" || tone === "invalid" || tone === "review") return tone;
    const d = String((view.decision && view.decision.value) || "").toLowerCase();
    if (d.includes("invalid")) return "invalid";
    if (d.includes("valid")) return "valid";
    if (d.includes("review")) return "review";
    return null;
  }

  function shortClass(predicted) {
    const s = String(predicted || "").toLowerCase();
    if (!s) return "—";
    if (s.includes("invalid")) return "INVALID";
    if (s.includes("valid")) return "VALID";
    if (s.includes("review")) return "REVIEW";
    return s.toUpperCase().slice(0, 10);
  }

  const agreeWord = (status) => (/match/i.test(String(status || "")) ? "AGREE" : "SPLIT");

  const caption = (p, predicted) => `p ${p === null || p === undefined ? "—" : Number(p).toFixed(2)} · ${shortClass(predicted)}`;

  const textBox = (x, y, text, anchor = "middle", size = 10.5) => {
    const w = String(text).length * CHAR_W;
    const l = anchor === "middle" ? x - w / 2 : anchor === "end" ? x - w : x;
    return { l, t: y - size, r: l + w, b: y + 3 };
  };

  /* Place every engine element for a hero of size {w, h} with raw foreground rects {badge, h1, lede, cta, stats, card}.
     Returns coordinates plus `ok` (everything placed clear of the zones) and `hidden` (elements that had no room). */
  function layout(hero, raw, opts = {}) {
    const t = opts.tier || tier(hero.w);
    const text = ["badge", "h1", "lede", "cta", "stats"].filter((k) => raw[k]).map((k) => inflate(raw[k]));
    const card = raw.card ? inflate(raw.card) : null;
    /* short heroes: the band under the content is what is left of the screen, so the engine scales to fit it
       (label above the core + core + policy + terminals + their labels = 38 + 98 * scale) */
    const band = hero.h - 8 - Math.max(card ? card.b : 0, ...text.map((z) => z.b), 0);
    const tierScale = t === "full" ? 1 : t === "compact" ? 0.85 : t === "strip" ? 0.85 : 0.7;
    const s = Math.max(0.5, Math.min(tierScale, (band - 38) / 98));
    const zones = card ? text.concat([card]) : text;
    const hidden = [];
    const R = NODE_R * s, CH = CORE_H * s;
    const floor = hero.h - 8;
    const stacked = t === "strip" || t === "mini";
    const leftBottom = text.reduce((m, z) => Math.max(m, z.b), 0);
    const cardBottom = card ? card.b : leftBottom;
    const out = { tier: t, scale: s, zones, textZones: text, hidden };

    /* decision core: under the column gutter (two columns) or the card's centre (stacked) */
    const gutter = raw.stats && raw.card && !stacked ? (raw.stats.r + raw.card.l) / 2 : hero.w / 2;
    let coreY = Math.max(cardBottom, leftBottom) + 18 + CH;
    const fanDepth = CH + 16 * s + 30 * s + 20;
    if (coreY + fanDepth > floor) coreY = floor - fanDepth;          // squeeze into the band if the hero is short
    out.core = { x: gutter, y: coreY, h: CH };

    /* model nodes */
    const pyX = Math.max(hero.w * (stacked ? 0.14 : 0.12), R + 12);
    let pyY;
    if (stacked) pyY = coreY + 6;
    else {
      const minY = leftBottom + 4 + R, maxY = floor - LABEL_BELOW - R;
      pyY = Math.min(Math.max(coreY + 8, minY), maxY);
    }
    out.py = { x: pyX, y: pyY, r: R };

    let tmX = hero.w * 0.86, tmY;
    if (!stacked && raw.card) {
      tmX = Math.min(Math.max(tmX, raw.card.l + R + 24), raw.card.r - R - 8);
      tmY = raw.card.b + 0.4 * R;                                    // top ~30% of the ring tucks behind the solid card
      if (tmY + R + LABEL_BELOW > floor) tmY = floor - R - LABEL_BELOW;
    } else tmY = coreY + 6;
    out.tm = { x: tmX, y: tmY, r: R };

    /* collision checks: nodes and their captions must clear every zone (the vision ring may tuck behind the card) */
    const captionBox = (n) => ({ l: n.x - LABEL_HALF_W, t: n.y + n.r + 4, r: n.x + LABEL_HALF_W, b: n.y + n.r + LABEL_BELOW });
    if (hitsAny(circleBox(out.py, R), zones) || hitsAny(captionBox(out.py), zones)) hidden.push("py");
    const tmZones = !stacked ? text : zones;
    if (hitsAny(circleBox(out.tm, R), tmZones) || hitsAny(captionBox(out.tm), zones)) hidden.push("tm");
    const coreBox = { l: gutter - CH, t: coreY - CH, r: gutter + CH, b: coreY + CH };
    if (hitsAny(coreBox, zones)) hidden.push("core");

    /* primary paths into the core */
    const pyStart = { x: out.py.x + R, y: out.py.y };
    const pyEnd = { x: gutter - CH - 2, y: coreY };
    out.paths = {};
    out.paths.py = route(pyStart, pyEnd, zones);
    let ang = (20 * Math.PI) / 180, tmStart;
    for (let i = 0; i < 6; i++) {                                     // leave the vision ring below the card's zone
      tmStart = { x: out.tm.x - R * Math.cos(ang), y: out.tm.y + R * Math.sin(ang) };
      if (!card || stacked || tmStart.y > card.b + 2) break;
      ang += (12 * Math.PI) / 180;
    }
    out.paths.tm = route(tmStart, { x: gutter + CH + 2, y: coreY }, zones);
    if (!out.paths.py) hidden.push("path-py");
    if (!out.paths.tm) hidden.push("path-tm");

    /* feed: the live check card is the engine's console */
    if (raw.card) {
      const from = stacked ? { x: (raw.card.l + raw.card.r) / 2, y: raw.card.b } : { x: raw.card.l + 14, y: raw.card.b };
      out.feed = { x1: from.x, y1: from.y, x2: gutter, y2: coreY - CH };
    }

    /* policy junction and the outcome fan */
    const dY = coreY + CH + 16 * s, termY = dY + 30 * s, spread = t === "mini" ? 40 : t === "full" ? 120 : 108;
    out.policy = { x: gutter, y: dY };
    out.terms = {
      invalid: { x: gutter - spread, y: termY },
      review: { x: gutter, y: termY },
      valid: { x: gutter + spread, y: termY },
    };
    const branch = (to) => ({ p0: { x: gutter, y: dY + 6 }, p1: { x: gutter, y: dY + 18 * s }, p2: { x: to.x, y: to.y - 18 * s }, p3: { x: to.x, y: to.y - 4 } });
    out.branches = { invalid: branch(out.terms.invalid), review: branch(out.terms.review), valid: branch(out.terms.valid) };

    /* labels */
    const short = t !== "full";
    out.labels = {
      core: { x: gutter - CH - 8, y: coreY - CH + 4, anchor: "end", text: "DECISION CORE" },
      delta: { x: gutter + CH + 8, y: coreY - CH + 4, anchor: "start" },
      policy: { x: gutter + 12, y: dY + 4, anchor: "start", text: "POLICY · RULES 16" },
    };
    if (t !== "mini" && out.paths.py) {
      const m = cubicPoint(out.paths.py, 0.5);
      const txt = short ? "OCR · SERIAL OK" : "OCR OK · SERIAL VERIFIED";
      let y = m.y - 10;
      if (hitsAny(textBox(m.x, y, txt), zones)) y = m.y + 18;
      out.labels.path = hitsAny(textBox(m.x, y, txt), zones) ? null : { x: m.x, y, anchor: "middle", text: txt };
    } else out.labels.path = null;

    /* ambient layer */
    if (raw.card && t !== "mini") {
      const cx = (raw.card.l + raw.card.r) / 2, cy = (raw.card.t + raw.card.b) / 2;
      const r0 = (Math.max(raw.card.r - raw.card.l, raw.card.b - raw.card.t) / 2) * 1.12;
      out.rings = { cx, cy, radii: [0, 1, 2, 3, 4].map((i) => r0 + i * 70 * (s < 1 ? 0.9 : 1)) };
    } else out.rings = null;
    out.glows = { py: { x: out.py.x, y: out.py.y, r: 150 * s }, tm: { x: out.tm.x, y: out.tm.y, r: 150 * s }, core: { x: gutter, y: coreY, r: 110 * s } };
    out.dotFocus = { x: raw.card ? (raw.card.l + raw.card.r) / 2 : hero.w / 2, y: coreY, r: Math.max(hero.w, hero.h) * 0.7 };

    out.ok = hidden.length === 0;
    return out;
  }

  return { PAD, NODE_R, CORE_H, inflate, intersects, hitsAny, cubicPoint, cubicHitsRects, route, toD, tier, outcomeFor, shortClass, agreeWord, caption, textBox, layout };
});
