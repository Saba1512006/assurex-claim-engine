/* Batch evaluator: upload, then call the step endpoint until the batch is done (one chunk per call). */
(() => {
  "use strict";
  const { $, api } = window.AX;
  const form = $("[data-batch-form]");
  if (!form) return;
  const box = $("[data-batch-progress]"), meter = $("[data-batch-meter]"), count = $("[data-batch-count]");
  const errBox = $("[data-batch-error]");
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const pct = (v) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);

  const metric = (v, l) => { const m = el("div", "metric"); m.append(el("div", "v mono", v), el("div", "l", l)); return m; };
  const draw = (s) => {
    const p = s.total ? Math.round((s.processed / s.total) * 100) : 0;
    meter.style.setProperty("--p", p / 100);
    meter.setAttribute("aria-valuenow", String(p));
    count.textContent = `${s.processed} / ${s.total}`;
    const tiles = [metric(String(s.decisions["Likely Valid"]), "Likely Valid"), metric(String(s.decisions["Likely Invalid"]), "Likely Invalid"),
      metric(String(s.decisions["Manual Review Required"]), "Manual review"), metric(pct(s.agreement), "Models agree on the class")];
    if (s.labelled) tiles.push(metric(pct(s.python_accuracy), "Python accuracy"), metric(pct(s.gtm_accuracy), "Teachable Machine accuracy"),
      metric(pct(s.decision_accuracy), "Final decision matches the label"));
    $("[data-batch-summary]").replaceChildren(...tiles);
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const btn = $("button[type=submit]", form);
    btn.disabled = true;
    errBox.classList.add("hidden");
    const r = await api(form.dataset.url, { method: "POST", form: new FormData(form) });
    if (!r.success) {
      btn.disabled = false;
      $("[data-batch-error-msg]").textContent = r.error.message;
      $("[data-batch-error-rows]").replaceChildren(...((r.error.fields && r.error.fields.rows) || []).map((t) => el("li", "", t)));
      errBox.classList.remove("hidden");
      return;
    }
    form.classList.add("hidden");
    box.classList.remove("hidden");
    $("[data-batch-id]").textContent = r.data.batch_id;
    let s = r.data;
    draw(s);
    while (s.status === "queued" || s.status === "running") {
      const next = await api(s.step_url, { method: "POST", body: {} });
      if (!next.success) { window.AX.toast(next.error.message, "danger"); break; }
      s = next.data;
      draw(s);
    }
    if (s.status === "done") {
      $("[data-batch-csv]").href = s.csv_url;
      $("[data-batch-done]").classList.remove("hidden");
      $("#pr-h").firstChild.textContent = "Finished ";
    } else if (s.status === "failed") {
      window.AX.toast(`The batch stopped: ${s.error}`, "danger");
    }
  });
})();
