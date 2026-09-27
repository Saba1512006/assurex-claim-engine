/* Product registration: two steps (receipt, details); the receipt is read by OCR and prefills the empty fields. */
(() => {
  "use strict";
  const { $, $$, api } = window.AX;
  const form = $("[data-product-form]");
  if (!form) return;
  const steps = $$("[data-pstep]", form);
  const tabs = $$("[data-pstep-btn]", form);
  const status = $("[data-scan-status]", form);

  const show = (n) => {
    steps.forEach((s) => { s.hidden = s.dataset.pstep !== String(n); });
    tabs.forEach((b) => {
      const k = Number(b.dataset.pstepBtn);
      if (k === n) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
      b.classList.toggle("done", k < n);
    });
    const first = steps.find((s) => !s.hidden);
    const target = first && $("input:not([type=hidden]):not([type=radio]), select", first);
    if (target && n === 2) target.focus({ preventScroll: true });
  };
  form.dataset.stepsReady = "1";
  show(Number(form.dataset.start || 1));
  tabs.forEach((b) => b.addEventListener("click", () => show(Number(b.dataset.pstepBtn))));
  $$("[data-pstep-go]", form).forEach((b) => b.addEventListener("click", () => show(Number(b.dataset.pstepGo))));

  /* a server-side error re-renders on step 2; the browser still validates step 2 fields on submit */
  form.addEventListener("invalid", () => show(2), true);

  /* category -> default warranty length, and highlight that category's policy */
  const cat = $("[data-category]", form);
  const months = $("input[data-months]", form);
  const syncCategory = () => {
    const opt = cat.selectedOptions[0];
    if (opt && opt.dataset.months && !months.value) months.value = opt.dataset.months;
    $$("[data-policy]").forEach((li) => li.classList.toggle("current", li.dataset.policy === cat.value));
  };
  cat.addEventListener("change", syncCategory);
  syncCategory();

  const say = (text, kind) => { status.textContent = text; status.className = `small mb-0 ${kind || ""}`; };
  const input = $("[data-scan-input]", form);
  input.addEventListener("change", async () => {
    $$(".prefilled", form).forEach((el) => el.classList.remove("prefilled"));
    if (!input.files.length) { say(""); return; }
    say("Reading your receipt…", "muted");
    const fd = new FormData();
    fd.append("receipt", input.files[0]);
    const r = await api(form.dataset.scanUrl, { method: "POST", form: fd });
    if (!r.success) { say(r.error.message, "warn-text"); return; }
    let filled = 0;
    $$("[data-fill]", form).forEach((el) => {
      const v = r.data.entities[el.dataset.fill];
      if (v === undefined || v === null || v === "" || el.value) return;
      el.value = v;
      el.classList.add("prefilled");
      filled++;
    });
    $("[data-prefill-note]", form).classList.toggle("hidden", !filled);
    if (filled) {
      say(`Read ${filled} detail${filled === 1 ? "" : "s"} from the receipt. Check them on the next step.`, "ok-text");
      setTimeout(() => show(2), 600);
    } else {
      say("The receipt was read but had nothing new for the empty fields. Continue and type the details.", "muted");
    }
  });
  form.addEventListener("input", (e) => e.target.classList && e.target.classList.remove("prefilled"));
})();
