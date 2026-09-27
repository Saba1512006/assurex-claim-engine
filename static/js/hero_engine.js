/* Hero engine: lays the background engine out around the hero's foreground blocks and keeps it in step with the live
   check. The geometry comes from hero_engine_math.js (pure, unit-tested); this file only measures, applies and
   animates. Measuring happens on load and on resize (ResizeObserver, debounced 100 ms), never on scroll.
   Motion: an idle packet every ~5 s; a run fires both models at once, flashes the core and draws the outcome.
   Everything stops when the hero is off screen or the tab is hidden, and never starts under reduced motion. */
(() => {
  "use strict";
  const M = window.AXEngineMath;
  const hero = document.querySelector(".hero");
  const layer = document.querySelector("[data-hero-engine]");
  if (!M || !hero || !layer) return;

  const q = (s, r = layer) => r.querySelector(s);
  const qa = (s, r = layer) => Array.from(r.querySelectorAll(s));
  const SVGNS = "http://www.w3.org/2000/svg";
  const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = () => matchMedia("(pointer: fine)").matches;
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const set = (el, attrs) => { if (el) for (const k in attrs) el.setAttribute(k, attrs[k]); };
  const f1 = (n) => (Math.round(n * 10) / 10).toString();

  let L = null;                       // current layout
  let state = null;                   // {python, vision, pyClass, tmClass, delta, agree, outcome}
  let running = !document.hidden;     // hero on screen and tab visible
  let busy = false;                   // a triggered run is in flight
  let idleTimer = 0, idleSide = "py";
  const packets = new Set();

  /* ---------------------------------------------------------------- measure + apply */
  function measure() {
    const H = hero.getBoundingClientRect();
    const raw = {};
    document.querySelectorAll("[data-engine-avoid]").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (!r.width && !r.height) return;
      raw[el.dataset.engineAvoid] = { l: r.left - H.left, t: r.top - H.top, r: r.right - H.left, b: r.bottom - H.top };
    });
    return { hero: { w: H.width, h: H.height }, raw };
  }

  function apply() {
    const { hero: box, raw } = measure();
    L = M.layout(box, raw);
    layer.dataset.tier = L.tier;
    const s = L.scale;

    qa("[data-he-node]").forEach((g) => {
      const n = L[g.dataset.heNode];
      set(g, { transform: `translate(${f1(n.x)} ${f1(n.y)})` });
      set(q("[data-he-scale]", g), { transform: `scale(${s})` });
      set(q("[data-he-name]", g), { y: f1(n.r + 16) });
      set(q("[data-he-val]", g), { y: f1(n.r + 30) });
      g.classList.toggle("he-hide", L.hidden.includes(g.dataset.heNode));
    });
    const core = q("[data-he-core]");
    set(core, { transform: `translate(${f1(L.core.x)} ${f1(L.core.y)})` });
    set(q("[data-he-scale]", core), { transform: `scale(${s})` });
    core.classList.toggle("he-hide", L.hidden.includes("core"));

    ["py", "tm"].forEach((k) => {
      const p = q(`[data-he-path="${k}"]`), c = L.paths[k];
      p.classList.toggle("he-hide", !c);
      if (!c) return;
      set(p, { d: M.toD(c) });
      set(q(`[data-he-lg="${k}"]`), { x1: f1(c.p0.x), x2: f1(c.p3.x) });
    });
    const feed = q("[data-he-feed]");
    feed.classList.toggle("he-hide", !L.feed);
    if (L.feed) set(feed, { x1: f1(L.feed.x1), y1: f1(L.feed.y1), x2: f1(L.feed.x2), y2: f1(L.feed.y2) });
    set(q("[data-he-trunk]"), { x1: f1(L.core.x), y1: f1(L.core.y + L.core.h), x2: f1(L.policy.x), y2: f1(L.policy.y - 6) });
    set(q("[data-he-policy]"), { transform: `translate(${f1(L.policy.x)} ${f1(L.policy.y)})` });
    Object.entries(L.branches).forEach(([k, c]) => set(q(`[data-he-branch="${k}"]`), { d: M.toD(c) }));
    Object.entries(L.terms).forEach(([k, t]) => set(q(`[data-he-term="${k}"]`), { transform: `translate(${f1(t.x)} ${f1(t.y)})` }));

    Object.entries(L.labels).forEach(([k, lb]) => {
      const el = q(`[data-he-label="${k}"]`);
      if (!el) return;
      el.classList.toggle("he-hide", !lb);
      if (!lb) return;
      set(el, { x: f1(lb.x), y: f1(lb.y), "text-anchor": lb.anchor });
      if (lb.text) el.textContent = lb.text;
    });

    const rings = q("[data-he-rings]");
    rings.classList.toggle("he-hide", !L.rings);
    if (L.rings) qa("circle", rings).forEach((c, i) => set(c, { cx: f1(L.rings.cx), cy: f1(L.rings.cy), r: f1(L.rings.radii[i]) }));
    Object.entries(L.glows).forEach(([k, g]) => set(q(`[data-he-glow="${k}"]`), { cx: f1(g.x), cy: f1(g.y), r: f1(g.r) }));
    set(q("[data-he-dotfade]"), { cx: f1(L.dotFocus.x), cy: f1(L.dotFocus.y), r: f1(L.dotFocus.r) });

    const holes = q("[data-he-holes]");
    holes.replaceChildren(...L.textZones.map((z) => {
      const r = document.createElementNS(SVGNS, "rect");
      set(r, { x: f1(z.l), y: f1(z.t), width: f1(z.r - z.l), height: f1(z.b - z.t), rx: 16 });
      return r;
    }));
    layer.classList.add("is-ready");
  }

  /* ---------------------------------------------------------------- state from the live check */
  function fromView(v) {
    if (!v) return null;
    return {
      python: v.python && v.python.available !== false ? v.python.top : null,
      vision: v.gtm && v.gtm.available !== false ? v.gtm.top : null,
      pyClass: v.python && v.python.predicted, tmClass: v.gtm && v.gtm.predicted,
      delta: v.consistency ? v.consistency.difference : null,
      agree: M.agreeWord(v.consistency && v.consistency.status),
      outcome: M.outcomeFor(v),
    };
  }

  function tweenText(el, from, to, fmt, ms = 400) {
    if (!el) return;
    if (reduced() || from === null || to === null || from === undefined || to === undefined) { el.textContent = fmt(to); return; }
    const t0 = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - t0) / ms);
      el.textContent = fmt(from + (to - from) * easeInOut(k));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function showCaptions(prev, next) {
    const pyVal = q('[data-he-node="py"] [data-he-val]'), tmVal = q('[data-he-node="tm"] [data-he-val]');
    tweenText(pyVal, prev && prev.python, next.python, (p) => M.caption(p, next.pyClass));
    tweenText(tmVal, prev && prev.vision, next.vision, (p) => M.caption(p, next.tmClass));
    [["py", next.python], ["tm", next.vision]].forEach(([k, p]) =>
      set(q(`[data-he-node="${k}"] [data-he-conf]`), { "stroke-dasharray": `${((p || 0) * 100).toFixed(1)} 100` }));
    const d = q('[data-he-label="delta"]');
    tweenText(d, prev && prev.delta, next.delta, (x) => `Δ ${x === null || x === undefined ? "—" : Number(x).toFixed(2)} · ${next.agree}`);
  }

  function showOutcome(outcome, animate) {
    ["invalid", "review", "valid"].forEach((k) => {
      const on = k === outcome;
      const b = q(`[data-he-branch="${k}"]`), t = q(`[data-he-term="${k}"]`);
      b.classList.toggle("is-drawing", on && animate);
      b.classList.toggle("is-on", on);
      t.classList.toggle("is-on", on);
    });
  }

  function flashCore() {
    const c = q("[data-he-core]");
    c.classList.remove("is-flash");
    void c.getBBox();
    c.classList.add("is-flash");
  }

  /* ---------------------------------------------------------------- packets */
  function packet(pathEl, tone, ms, done) {
    if (!running || reduced() || !pathEl || pathEl.classList.contains("he-hide") || packets.size >= 3) { if (done) done(); return; }
    const g = document.createElementNS(SVGNS, "g");
    g.setAttribute("class", `he-packet ${tone}`);
    const trail = document.createElementNS(SVGNS, "polyline");
    const head = document.createElementNS(SVGNS, "circle");
    head.setAttribute("r", "3");
    g.append(trail, head);
    q("[data-he-packets]").append(g);
    const len = pathEl.getTotalLength(), t0 = performance.now();
    const p = { g, raf: 0 };
    packets.add(p);
    const frame = (now) => {
      if (!running) { finish(); return; }
      const k = Math.min(1, (now - t0) / ms), at = len * easeInOut(k);
      const hp = pathEl.getPointAtLength(at);
      head.setAttribute("cx", hp.x.toFixed(1)); head.setAttribute("cy", hp.y.toFixed(1));
      const pts = [];
      for (let i = 0; i <= 4; i++) { const tp = pathEl.getPointAtLength(Math.max(0, at - i * 6)); pts.push(`${tp.x.toFixed(1)},${tp.y.toFixed(1)}`); }
      trail.setAttribute("points", pts.join(" "));
      if (k < 1) p.raf = requestAnimationFrame(frame); else finish();
    };
    function finish() { cancelAnimationFrame(p.raf); g.remove(); packets.delete(p); if (done) done(); }
    p.raf = requestAnimationFrame(frame);
  }

  function scheduleIdle() {
    clearTimeout(idleTimer);
    if (!running || reduced()) return;
    idleTimer = setTimeout(() => {
      if (!busy) {
        const side = idleSide; idleSide = side === "py" ? "tm" : "py";
        packet(q(`[data-he-path="${side}"]`), side, 2800);
      }
      scheduleIdle();
    }, 5000);
  }

  function run(next) {
    const prev = state;
    state = next;
    showCaptions(prev, next);
    if (reduced() || !running) { showOutcome(next.outcome, false); return; }
    busy = true;
    showOutcome(null, false);
    let arrived = 0;
    const land = () => {
      if (++arrived < 2) return;
      flashCore();
      showOutcome(next.outcome, true);
      const b = next.outcome && q(`[data-he-branch="${next.outcome}"]`);
      packet(b, next.outcome || "py", 900, () => { busy = false; });
      if (!b) busy = false;
    };
    packet(q('[data-he-path="py"]'), "py", 2600, land);
    packet(q('[data-he-path="tm"]'), "tm", 2600, land);
  }

  /* ---------------------------------------------------------------- parallax (fine pointers, two-column layouts) */
  const par = { a: q('[data-he-par="a"]'), b: q('[data-he-par="b"]'), tx: 0, ty: 0, x: 0, y: 0, raf: 0 };
  function parallaxTick() {
    par.x += (par.tx - par.x) * 0.12; par.y += (par.ty - par.y) * 0.12;
    set(par.a, { transform: `translate(${(par.x * 6).toFixed(2)} ${(par.y * 6).toFixed(2)})` });
    set(par.b, { transform: `translate(${(par.x * 3).toFixed(2)} ${(par.y * 3).toFixed(2)})` });
    par.raf = Math.abs(par.tx - par.x) + Math.abs(par.ty - par.y) > 0.002 ? requestAnimationFrame(parallaxTick) : 0;
  }
  hero.addEventListener("pointermove", (e) => {
    if (!running || reduced() || !finePointer() || !L || (L.tier !== "full" && L.tier !== "compact")) return;
    const r = hero.getBoundingClientRect();
    par.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    par.ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
    if (!par.raf) par.raf = requestAnimationFrame(parallaxTick);
  });
  hero.addEventListener("pointerleave", () => { par.tx = 0; par.ty = 0; if (!par.raf && running) par.raf = requestAnimationFrame(parallaxTick); });

  /* ---------------------------------------------------------------- lifecycle */
  function setRunning(on) {
    running = on && !document.hidden;
    layer.classList.toggle("is-paused", !running);
    if (running) scheduleIdle();
    else { clearTimeout(idleTimer); packets.forEach((p) => { cancelAnimationFrame(p.raf); p.g.remove(); }); packets.clear(); busy = false; }
  }
  let onScreen = true;
  if ("IntersectionObserver" in window) new IntersectionObserver((es) => { onScreen = es.some((x) => x.isIntersecting); setRunning(onScreen); }).observe(hero);
  document.addEventListener("visibilitychange", () => setRunning(onScreen));

  const relayout = window.AX && window.AX.debounce ? window.AX.debounce(apply, 100) : apply;
  if ("ResizeObserver" in window) {
    const ro = new ResizeObserver(relayout);
    ro.observe(hero);
    document.querySelectorAll("[data-engine-avoid]").forEach((el) => ro.observe(el));
  } else window.addEventListener("resize", relayout);

  if (window.AX && window.AX.bus) window.AX.bus.on("engine:run", (d) => run(fromView(d.view)));

  /* first state: the sample the card shows */
  try {
    const data = JSON.parse(document.getElementById("bench-data").textContent);
    const pick = (document.querySelector("input[name=im-case]:checked") || {}).value;
    state = fromView(data.views[pick] || Object.values(data.views)[0]);
  } catch { state = null; }
  apply();
  if (state) { showCaptions(null, state); showOutcome(state.outcome, false); }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(apply);
  scheduleIdle();

  window.AXEngine = { layout: () => L, state: () => state, relayout: apply };
})();
