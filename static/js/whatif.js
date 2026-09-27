/* What-if simulator: every slider move re-runs the read-only simulation (debounced) and redraws the results. */
(() => {
  "use strict";
  const { $, $$, api, debounce } = window.AX;
  const form = $("[data-whatif]");
  if (!form) return;
  const sliders = $$("input[type=range]", form);
  const status = $("[data-wi-status]"), err = $("[data-wi-error]"), apply = $("[data-wi-apply]");
  const LABELS = ["Likely Valid", "Likely Invalid", "Manual Review Required"];
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const fmt = (v, kind) => (v === null || v === undefined ? "—" : kind === "pct" ? `${(v * 100).toFixed(1)}%` : String(v));
  const delta = (a, b, kind) => {
    if (a === null || b === null) return "—";
    const d = kind === "pct" ? (b - a) * 100 : b - a;
    if (Math.abs(d) < 0.05) return "±0";
    return `${d > 0 ? "+" : "−"}${Math.abs(d).toFixed(kind === "pct" ? 1 : 0)}${kind === "pct" ? " pts" : ""}`;
  };

  const render = (sim) => {
    const t = sim.test;
    $$("[data-wi-row]").forEach((row) => {
      const k = row.dataset.wiRow, kind = row.dataset.kind;
      $("[data-wi-new]", row).textContent = fmt(t.proposed[k], kind);
      $("[data-wi-delta]", row).textContent = delta(t.current[k], t.proposed[k], kind);
    });
    $("[data-wi-changed]").textContent = t.changed;
    t.transitions.forEach((r, i) => r.forEach((n, j) => { $(`[data-cell="${i}${j}"]`).textContent = n; }));
    $("[data-wi-live-count]").textContent = sim.live.changed_count;
    const list = $("[data-wi-live]");
    list.replaceChildren(...(sim.live.changed.length ? sim.live.changed.map((c) => {
      const li = el("li");
      const a = el("a", "id", c.claim_id); a.href = `/claims/${encodeURIComponent(c.claim_id)}`;
      const body = el("div", "grow"); body.append(a, " ", el("span", "small", c.product));
      li.append(body, el("span", "small mono", `${c.from} → ${c.to}`));
      return li;
    }) : [el("li", "small muted", "No live claim would get a different recommendation.")]));
  };

  const values = () => Object.fromEntries(sliders.map((s) => [s.name, Number(s.value)]));
  const run = debounce(async () => {
    const v = values();
    const same = sliders.every((s) => Math.abs(Number(s.value) - Number(s.dataset.current)) < 1e-9);
    status.textContent = "Simulating…";
    const r = await api(form.dataset.url, { method: "POST", body: v });
    if (!r.success) {
      err.textContent = r.error.message; err.classList.remove("hidden"); apply.disabled = true;
      status.textContent = "Not simulated"; return;
    }
    err.classList.add("hidden");
    render(r.data);
    apply.disabled = same;
    status.textContent = same ? "Current thresholds" : "Proposed thresholds (not saved)";
  }, 250);

  sliders.forEach((s) => s.addEventListener("input", () => {
    $(`[data-out="${s.name}"]`).textContent = Number(s.value).toFixed(2);
    run();
  }));
  $("[data-wi-reset]").addEventListener("click", () => {
    sliders.forEach((s) => { s.value = s.dataset.current; $(`[data-out="${s.name}"]`).textContent = Number(s.value).toFixed(2); });
    run();
  });
  run();
})();
