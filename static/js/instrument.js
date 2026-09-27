/* Landing instrument: draws a sample claim's decision into the server-rendered markup.
   Choosing a sample swaps in its cached result (no request); "Run the checks again" calls /api/demo/evaluate
   and draws the fresh result. Each draw replays the reveal unless the reader prefers reduced motion. */
(() => {
  "use strict";
  const root = document.querySelector("[data-instrument]");
  const dataEl = document.getElementById("bench-data");
  if (!root || !dataEl || !window.AX) return;
  const { views, icons } = JSON.parse(dataEl.textContent);
  const $ = (s) => root.querySelector(s);
  const two = (x) => (x === null || x === undefined ? "—" : Number(x).toFixed(2));
  const sprite = (() => { const u = root.querySelector("[data-im-stamp-icon] use"); return u ? u.getAttribute("href").split("#")[0] : ""; })();
  const run = $("[data-im-run]");
  const runLabel = run.querySelector("span");
  let token = 0;

  function reveal() {
    root.classList.remove("reveal");
    if (window.AX.reduced()) return;
    void root.offsetWidth;                                   // restart the CSS animations
    root.classList.add("reveal");
  }

  function countUp(el, to) {
    if (to === null || to === undefined || window.AX.reduced()) { el.textContent = two(to); return; }
    const start = performance.now(), dur = 300, delay = 570, mine = ++token;
    const step = (t) => {
      if (mine !== token) return;
      const k = Math.min(1, Math.max(0, (t - start - delay) / dur));
      el.textContent = two(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    };
    el.textContent = two(0);
    requestAnimationFrame(step);
  }

  function draw(v) {
    $("[data-im-total]").textContent = `${(v.total_ms / 1000).toFixed(2)} s`;
    $("[data-im-desc]").textContent = v.desc;
    ["python", "gtm"].forEach((k) => {
      const m = v[k], box = $(`[data-im-model=${k}]`);
      box.querySelector("[data-im-top]").textContent = m.available ? two(m.top) : "—";
      box.querySelector("[data-im-bar]").style.setProperty("--p", (m.top || 0).toFixed(3));
      box.querySelector("[data-im-class]").textContent = m.available ? m.predicted : "Unavailable";
    });
    const svg = $("[data-im-meter]");
    svg.setAttribute("aria-label", v.meter.label);
    const arc = $("[data-im-arc]");
    arc.setAttribute("d", v.meter.arc || "");
    arc.setAttribute("class", `im-arc tone-${v.consistency.tone}`);
    ["py", "gtm"].forEach((cls) => {
      const g = $(`[data-im-needle=${cls}]`), n = v.meter.needles.find((x) => x.cls === cls);
      g.hidden = !n;
      if (!n) return;
      g.style.setProperty("--a", `${n.angle}deg`);
      const line = g.querySelector("line");
      if (n.dashed) line.setAttribute("stroke-dasharray", "7 5"); else line.removeAttribute("stroke-dasharray");
    });
    countUp($("[data-im-delta]"), v.consistency.difference);
    const status = $("[data-im-status]");
    status.textContent = v.consistency.status;
    status.className = `im-status tone-${v.consistency.tone}`;
    const stamp = $("[data-im-stamp]");
    stamp.className = `stamp ${v.tone}`;
    $("[data-im-stamp-text]").textContent = v.decision.value;
    const use = root.querySelector("[data-im-stamp-icon] use");
    if (use && sprite) use.setAttribute("href", `${sprite}#i-${icons[v.tone] || "minus"}`);
    $("[data-im-rule]").innerHTML = "";
    $("[data-im-rule]").append("Rule ", Object.assign(document.createElement("span"), { className: "mono", textContent: v.decision.rule_id }),
      `: ${v.decision.reason}.`);
    $("[data-im-times]").textContent = v.stages.map((s) => `${s.name} ${s.ms}`).join(" · ");
    $("[data-im-live]").textContent = `${v.short}: ${v.decision.value}. ${v.consistency.status}.`;
    reveal();
  }

  const current = () => (root.querySelector("input[name=im-case]:checked") || {}).value || "valid";

  root.addEventListener("change", (e) => {
    if (e.target.name === "im-case" && views[e.target.value]) draw(views[e.target.value]);
  });

  run.addEventListener("click", async () => {
    const was = runLabel.textContent;
    run.disabled = true;
    run.setAttribute("aria-busy", "true");
    runLabel.textContent = "Running the checks";
    const res = await window.AX.api(root.dataset.url, { method: "POST", body: { case: current() } });
    run.disabled = false;
    run.removeAttribute("aria-busy");
    runLabel.textContent = was;
    if (!res.success) { window.AX.toast(res.error.message, "danger"); return; }
    views[res.data.view.case] = res.data.view;
    draw(res.data.view);
  });

  /* first paint is already drawn by the server; play the reveal once when it scrolls into view */
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((es) => { if (es.some((x) => x.isIntersecting)) { reveal(); io.disconnect(); } }, { threshold: 0.3 });
    io.observe(root);
  }
})();
