/* Claim wizard: steps, live readiness (debounced 400 ms), server draft autosave, receipt OCR split view, review. */
(() => {
  "use strict";
  const { $, $$, api, debounce } = window.AX;
  const wiz = $("[data-wizard]");
  if (!wiz) return;
  const data = JSON.parse($("#wizard-data").textContent);
  const byId = Object.fromEntries(data.products.map((p) => [p.id, p]));
  const steps = $$("[data-step]", wiz);
  const tabs = $$("[data-step-btn]", wiz);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const product = () => byId[($("input[name=product_id]:checked", wiz) || {}).value];
  const norm = (v) => String(v || "").replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  let current = 0;

  /* ------------------------------------------------------------ steps */
  wiz.dataset.stepsReady = "1";
  const valid = (i) => {
    const bad = $$("input, select, textarea", steps[i]).filter((f) => f.willValidate && !window.AX.check(f));
    if (bad.length) { bad[0].focus(); return false; }
    return true;
  };
  const show = (i, focus = true) => {
    current = Math.max(0, Math.min(steps.length - 1, i));
    steps.forEach((s, k) => { s.hidden = k !== current; });
    tabs.forEach((b, k) => {
      if (k === current) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
      b.classList.toggle("done", k < current);
    });
    if (current === 3) review();
    if (focus) { const h = $("h2", steps[current]); h.tabIndex = -1; h.focus({ preventScroll: true }); wiz.scrollIntoView({ block: "start", behavior: window.AX.reduced() ? "auto" : "smooth" }); }
  };
  const go = (to) => {
    for (let i = current; i < to; i++) if (!valid(i)) { show(i); return; }
    if (current <= 1 && to >= 2) saveDraft();                 // "What happened" complete: keep a server draft from here on
    show(to);
  };
  $$("[data-next]", wiz).forEach((b) => b.addEventListener("click", () => go(current + 1)));
  $$("[data-prev]", wiz).forEach((b) => b.addEventListener("click", () => show(current - 1)));
  tabs.forEach((b, k) => b.addEventListener("click", () => (k > current ? go(k) : show(k))));
  wiz.addEventListener("invalid", (e) => { const s = e.target.closest("[data-step]"); if (s) show(Number(s.dataset.step), false); }, true);

  /* ------------------------------------------------------------ product -> faults, policy, hints */
  const faultSel = $("[data-fault-select]", wiz);
  const syncProduct = () => {
    const p = product();
    $("[data-policy-card]").classList.toggle("hidden", !p);
    if (!p) return;
    $$("optgroup", faultSel).forEach((g) => {
      const mine = g.dataset.cat === p.category;
      g.hidden = !mine; g.disabled = !mine;
    });
    if (faultSel.selectedOptions[0] && faultSel.selectedOptions[0].parentElement.disabled) faultSel.value = "";
    const pol = data.policies[p.category];
    $("[data-policy-name]").textContent = pol.policy_name;
    $("[data-policy-reporting]").textContent = `Report within ${pol.claim_reporting_period_days} days`;
    $("[data-policy-grace]").textContent = `${pol.grace_period_days}-day grace period`;
    $("[data-policy-excluded]").textContent = pol.excluded_damage_types.join(", ").toLowerCase();
    $("[data-receipt-on-file]").classList.toggle("hidden", !p.docs.includes("receipt"));
    hints();
  };
  const hints = () => {
    const p = product(); if (!p) return;
    const pol = data.policies[p.category];
    const dmg = wiz.elements.damage_type.value;
    const ex = $("[data-exclusion-hint]");
    if (ex.className !== "err") ex.textContent = pol.excluded_damage_types.includes(dmg)
      ? `${dmg} is not covered for ${p.category} unless a diagnosis says otherwise.` : "If you are not sure, choose Unknown.";
    const fd = wiz.elements.fault_occurrence_date.value;
    const dl = $("[data-deadline-hint]");
    if (fd && dl.className !== "err") {
      const days = Math.floor((Date.now() - new Date(`${fd}T00:00:00`).getTime()) / 864e5);
      const left = pol.claim_reporting_period_days - days;
      dl.textContent = left >= 0 ? `${left} day${left === 1 ? "" : "s"} left in the ${pol.claim_reporting_period_days}-day reporting window.`
        : `${-left} day${left === -1 ? "" : "s"} past the ${pol.claim_reporting_period_days}-day reporting window. A reviewer will decide.`;
    }
  };
  $$("input[name=product_id]", wiz).forEach((r) => r.addEventListener("change", () => { syncProduct(); prep(); wiz.elements.draft_id.value = ""; }));
  wiz.elements.damage_type.addEventListener("change", hints);
  wiz.elements.fault_occurrence_date.addEventListener("change", hints);

  /* ------------------------------------------------------------ readiness (SRS xxxiii) */
  const readyFields = ["product_id", "fault_category", "damage_type", "fault_occurrence_date", "fault_description", "diagnostic_confidence"];
  const formData = (keys) => {
    const fd = new FormData();
    keys.forEach((k) => { const f = wiz.elements[k]; if (f) fd.append(k, f.value || ""); });
    return fd;
  };
  const LEVEL = { error: ["no", "bi-x-lg"], warning: ["warn", "bi-exclamation"], info: ["", "bi-info"] };
  const prep = debounce(async () => {
    if (!product()) return;
    const fd = formData(readyFields);
    $$("[data-doc-input]", wiz).forEach((i) => { if (i.files.length) fd.append(`has_${i.dataset.docInput}`, "1"); });
    const r = await api(wiz.dataset.prepUrl, { method: "POST", form: fd });
    if (!r.success) return;                                   // keep the last checklist
    const { items, score, ready } = r.data;
    const list = $("[data-ready-list]");
    list.replaceChildren(...(items.length ? items : [{ level: "ok", title: "Ready to submit", detail: "Nothing is missing." }]).map((it) => {
      const li = el("li");
      const [cls, icon] = it.level === "ok" ? ["ok", "bi-check-lg"] : LEVEL[it.level];
      const i = el("i", `bi ${icon} ${cls}`); i.setAttribute("aria-hidden", "true");
      const body = el("div"); body.append(el("b", "small", it.title), el("div", "tiny muted", it.detail));
      li.append(i, body);
      return li;
    }));
    const meter = $("[data-ready-meter]");
    meter.className = `meter ${score >= 80 ? "good" : score >= 50 ? "warn" : "bad"}`;
    meter.style.setProperty("--p", score / 100);
    meter.setAttribute("aria-label", `Readiness ${score} percent`);
    $("[data-ready-tag]").className = `tag ${ready ? "valid" : "review"}`;
    $("[data-ready-word]").textContent = ready ? `${score}% ready` : "Needs attention";
  }, 400);
  wiz.addEventListener("input", prep);
  wiz.addEventListener("change", prep);

  /* ------------------------------------------------------------ server draft autosave */
  const status = $("[data-draft-status]");
  let saving = false;
  const saveDraft = async () => {
    if (saving || !product()) return;
    if (!$$("input, select, textarea", steps[1]).every((f) => !f.willValidate || f.checkValidity())) return;
    saving = true;
    const fd = formData([...readyFields, "previous_replacement_details", "draft_id"]);
    const r = await api(wiz.dataset.draftUrl, { method: "POST", form: fd });
    saving = false;
    if (r.success) {
      wiz.elements.draft_id.value = r.data.claim_id;
      status.replaceChildren("Draft ", el("span", "id", r.data.claim_id), ` saved at ${r.data.saved_at}`);
    } else if (r.status !== 400) {
      status.textContent = "Not saved yet. Your answers are still here.";
    }
  };
  const autosave = debounce(() => { if (wiz.elements.draft_id.value) saveDraft(); }, 1500);
  $$("input, select, textarea", steps[1]).forEach((f) => f.addEventListener("input", autosave));

  /* ------------------------------------------------------------ receipt OCR split view (SRS vi, vii) */
  const ocrInput = $("[data-ocr-input]", wiz);
  const panel = $("[data-ocr-panel]", wiz);
  const ocrStatus = $("[data-ocr-status]", panel);
  const REGISTERED = { serial_number: "serial", invoice_number: "invoice", model_number: "model", purchase_date: "purchase", retailer: "retailer" };
  const compare = () => {
    const p = product();
    $$("[data-ocr-field]", panel).forEach((input) => {
      const key = input.dataset.ocrField;
      const note = $(`[data-ocr-note="${key}"]`, panel);
      const reg = p && REGISTERED[key] ? p[REGISTERED[key]] : "";
      const differs = !!(input.value && reg && norm(input.value) !== norm(reg));
      input.classList.toggle("mismatch", differs);
      note.className = differs ? "help warn-text" : "help";
      note.textContent = differs ? `Differs from the registered value ${reg}. A mismatch sends the claim to a reviewer.`
        : (input.value && reg ? "Matches the registered product." : "");
    });
  };
  const renderText = (text, entities) => {
    const values = Object.values(entities).filter((v) => v && String(v).length > 2).map(String);
    const list = $("[data-ocr-text]", panel);
    const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).slice(0, 40);
    list.replaceChildren(...lines.map((line) => {
      const li = el("li");
      const hit = values.find((v) => line.toUpperCase().includes(v.toUpperCase()));
      if (!hit) { li.textContent = line; return li; }
      const at = line.toUpperCase().indexOf(hit.toUpperCase());
      li.append(line.slice(0, at), el("mark", "", line.slice(at, at + hit.length)), line.slice(at + hit.length));
      return li;
    }));
    if (!lines.length) list.replaceChildren(el("li", "muted", "No text lines to show for this file."));
  };
  ocrInput.addEventListener("change", async () => {
    if (!ocrInput.files.length) { panel.classList.add("hidden"); return; }
    panel.classList.remove("hidden");
    ocrStatus.textContent = "Reading the receipt…";
    const fd = new FormData();
    fd.append("receipt", ocrInput.files[0]);
    const r = await api(wiz.dataset.ocrUrl, { method: "POST", form: fd });
    $$("[data-ocr-field]", panel).forEach((f) => { f.value = r.success ? (r.data.entities[f.dataset.ocrField] ?? "") : ""; });
    if (r.success) {
      ocrStatus.textContent = "Read. Check each value against the receipt.";
      renderText(r.data.text || "", r.data.entities);
    } else {
      ocrStatus.textContent = r.error.message;
      $("[data-ocr-text]", panel).replaceChildren(el("li", "muted", "Nothing could be read. Type the values from the receipt instead."));
    }
    compare();
  });
  panel.addEventListener("input", compare);

  /* ------------------------------------------------------------ review */
  const review = () => {
    const p = product();
    const docs = $$("[data-doc-input]", wiz).filter((i) => i.files.length).map((i) => i.closest("label").querySelector("b").textContent);
    const opt = (name) => { const f = wiz.elements[name]; return f && f.value ? f.value : "Not given"; };
    const rows = [
      ["Product", p ? `${p.name} (${p.serial})` : "Not chosen"],
      ["Fault", opt("fault_category")], ["Cause", opt("damage_type")], ["Started", opt("fault_occurrence_date")],
      ["Description", opt("fault_description")],
      ["Evidence", docs.length ? docs.join(", ") : (p && p.docs.length ? "Uses the files already on the product" : "None attached")],
      ["Draft", wiz.elements.draft_id.value || "Not saved yet"],
    ];
    $("[data-review]").replaceChildren(...rows.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)]));
  };

  show(Number(wiz.dataset.start || 0), false);
  if (product()) { syncProduct(); prep(); }
})();
