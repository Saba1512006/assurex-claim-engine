/* AssureX front-end. No inline scripts anywhere (strict CSP): every behaviour hangs off data-* attributes. */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------------------------------------------------------------- theme */
  const saved = store.get("assurex-theme");
  if (saved) document.documentElement.dataset.theme = saved;
  $$("[data-theme-toggle]").forEach((b) => b.addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    store.set("assurex-theme", next);
    document.dispatchEvent(new CustomEvent("themechange"));
  }));

  /* ---------------------------------------------------------------- chrome */
  $$("[data-nav-toggle]").forEach((b) => b.addEventListener("click", () => {
    const nav = document.getElementById(b.getAttribute("aria-controls"));
    const open = nav.classList.toggle("open");
    b.setAttribute("aria-expanded", String(open));
  }));
  document.addEventListener("click", (e) => {
    $$("details.menu[open]").forEach((d) => { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $$("details.menu[open]").forEach((d) => d.removeAttribute("open"));
  });
  $$("[data-dismiss]").forEach((b) => b.addEventListener("click", () => b.closest("[data-dismissable]").remove()));
  $$("[data-history-back]").forEach((b) => b.addEventListener("click", () => history.back()));

  /* forms: confirmation, auto-submit, double-submit guard */
  $$("form[data-confirm]").forEach((f) => f.addEventListener("submit", (e) => {
    if (!confirm(f.dataset.confirm)) e.preventDefault();
  }));
  $$("[data-autosubmit]").forEach((el) => {
    const initial = el.value;
    el.addEventListener("change", () => {
      const f = el.form;
      if (el.hasAttribute("data-confirm-change") && f.dataset.confirm && !confirm(f.dataset.confirm)) { el.value = initial; return; }
      f.requestSubmit ? f.requestSubmit() : f.submit();
    });
  });
  document.addEventListener("submit", (e) => {
    const f = e.target;
    if (e.defaultPrevented || f.method.toLowerCase() !== "post") return;
    const btn = e.submitter;
    if (btn && btn.tagName === "BUTTON") setTimeout(() => { btn.disabled = true; btn.dataset.busy = "1"; }, 0);
  });
  window.addEventListener("pageshow", () => $$("button[data-busy]").forEach((b) => { b.disabled = false; delete b.dataset.busy; }));

  /* file inputs inside drop zones */
  $$("[data-dropzone]").forEach((z) => {
    const input = $("input[type=file]", z);
    if (!input) return;
    const update = () => z.classList.toggle("done", input.files.length > 0);
    input.addEventListener("change", update);
    ["dragenter", "dragover"].forEach((ev) => z.addEventListener(ev, (e) => { e.preventDefault(); z.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) => z.addEventListener(ev, () => z.classList.remove("drag")));
    z.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; input.dispatchEvent(new Event("change", { bubbles: true })); }
    });
  });

  /* login: fill an evaluator account */
  $$("[data-fill-login]").forEach((b) => b.addEventListener("click", () => {
    const [email, pw] = b.dataset.fillLogin.split("|");
    $("input[name=email]").value = email;
    $("input[name=password]").value = pw;
    $("input[name=password]").form.requestSubmit();
  }));

  /* access control: service center only for staff */
  const inviteRole = $("[data-invite-role]");
  if (inviteRole) {
    const field = $("[data-center-field]");
    const sync = () => { field.hidden = inviteRole.value !== "service_center_staff"; };
    inviteRole.addEventListener("change", sync); sync();
  }

  /* reviewer: override reason appears only when the decision contradicts the recommendation */
  $$("[data-review-form]").forEach((f) => {
    const pairs = JSON.parse(f.dataset.overrides || "[]");
    const targets = JSON.parse(f.dataset.targets || "{}");
    const rec = f.dataset.recommendation;
    const field = $("[data-override-field]", f);
    const area = $("textarea", field);
    const sync = () => {
      const chosen = $("input[name=action]:checked", f);
      const target = chosen ? targets[chosen.value] : null;
      const needed = pairs.some(([d, s]) => d === rec && s === target);
      field.classList.toggle("hidden", !needed);
      area.required = needed;
    };
    $$("input[name=action]", f).forEach((r) => r.addEventListener("change", sync));
    sync();
  });

  /* ---------------------------------------------------------------- receipt reading (product form) */
  const productForm = $("[data-product-form]");
  if (productForm) {
    const input = $("[data-scan-input]", productForm);
    const status = $("[data-scan-status]", productForm);
    const cat = $("[data-category]", productForm);
    const months = $("[data-months]", productForm);
    cat.addEventListener("change", () => {
      const opt = cat.selectedOptions[0];
      if (opt && opt.dataset.months && !months.value) months.value = opt.dataset.months;
    });
    input.addEventListener("change", async () => {
      if (!input.files.length) return;
      status.innerHTML = '<span class="muted"><i class="bi bi-hourglass-split"></i> Reading your receipt…</span>';
      const fd = new FormData();
      fd.append("receipt", input.files[0]);
      fd.append("csrf_token", $("input[name=csrf_token]", productForm).value);
      try {
        const res = await fetch(productForm.dataset.scanUrl, { method: "POST", body: fd, credentials: "same-origin" });
        const data = await res.json();
        if (!data.ok) { status.innerHTML = `<span style="color:var(--warn)"><i class="bi bi-info-circle"></i> ${esc(data.error)}</span>`; return; }
        let filled = 0;
        $$("[data-fill]", productForm).forEach((el) => {
          const v = data.entities[el.dataset.fill];
          if (v !== undefined && v !== null && v !== "" && !el.value) { el.value = v; el.style.boxShadow = "0 0 0 3px var(--good-soft)"; filled++; }
        });
        status.innerHTML = `<span style="color:var(--good)"><i class="bi bi-magic"></i> Filled ${filled} field${filled === 1 ? "" : "s"} from the receipt — please check them.</span>`;
      } catch {
        status.innerHTML = '<span style="color:var(--warn)">Couldn\'t read the receipt right now. Type the details instead.</span>';
      }
    });
  }

  /* ---------------------------------------------------------------- claim wizard */
  const wiz = $("[data-wizard]");
  if (wiz) {
    const data = JSON.parse($("#wizard-data").textContent);
    const steps = $$("[data-step]", wiz);
    const btns = $$("[data-step-btn]", wiz);
    let current = 0;
    const byId = Object.fromEntries(data.products.map((p) => [p.id, p]));
    const product = () => byId[($("input[name=product_id]:checked", wiz) || {}).value];
    const faultSel = $("[data-fault-select]", wiz);

    const show = (i) => {
      current = Math.max(0, Math.min(steps.length - 1, i));
      steps.forEach((s, k) => s.classList.toggle("active", k === current));
      btns.forEach((b, k) => {
        if (k === current) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
        b.classList.toggle("done", k < current);
      });
      if (current === 3) renderReview();
      wiz.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    const validStep = (i) => {
      const fields = $$("input, select, textarea", steps[i]).filter((el) => el.willValidate);
      for (const el of fields) {
        if (!el.checkValidity()) { el.reportValidity(); return false; }
      }
      return true;
    };
    $$("[data-next]", wiz).forEach((b) => b.addEventListener("click", () => { if (validStep(current)) show(current + 1); }));
    $$("[data-prev]", wiz).forEach((b) => b.addEventListener("click", () => show(current - 1)));
    btns.forEach((b, k) => b.addEventListener("click", () => {
      for (let i = current; i < k; i++) if (!validStep(i)) return show(i);
      show(k);
    }));

    const syncProduct = () => {
      const p = product();
      const card = $("[data-policy-card]");
      if (!p) { card.hidden = true; return; }
      const faults = data.faults[p.category] || [];
      const keep = faultSel.value || data.initialFault;
      faultSel.innerHTML = '<option value="">Choose the fault…</option>' +
        faults.map((f) => `<option ${f === keep ? "selected" : ""}>${esc(f)}</option>`).join("");
      const pol = data.policies[p.category];
      card.hidden = false;
      $("[data-policy-name]").textContent = pol.policy_name;
      $("[data-policy-reporting]").textContent = `Report within ${pol.claim_reporting_period_days} days`;
      $("[data-policy-grace]").textContent = `${pol.grace_period_days}-day grace`;
      $("[data-policy-excluded]").textContent = pol.excluded_damage_types.join(", ").toLowerCase();
      $("[data-receipt-on-file]").classList.toggle("hidden", !p.docs.includes("receipt"));
      hints();
    };
    const hints = () => {
      const p = product(); if (!p) return;
      const pol = data.policies[p.category];
      const dmg = $("select[name=damage_type]", wiz).value;
      $("[data-exclusion-hint]").textContent = pol.excluded_damage_types.includes(dmg)
        ? `“${dmg}” is not covered for ${p.category} unless a diagnosis shows otherwise.` : "";
      const fd = $("input[name=fault_occurrence_date]", wiz).value;
      if (fd) {
        const days = Math.floor((Date.now() - new Date(fd + "T00:00:00").getTime()) / 864e5);
        const left = pol.claim_reporting_period_days - days;
        $("[data-deadline-hint]").textContent = left >= 0 ? `${left} day${left === 1 ? "" : "s"} left in the ${pol.claim_reporting_period_days}-day reporting window.`
          : `This is ${-left} day(s) past the ${pol.claim_reporting_period_days}-day reporting window.`;
      }
    };
    $$("input[name=product_id]", wiz).forEach((r) => r.addEventListener("change", () => { syncProduct(); prep(); }));
    ["damage_type", "fault_occurrence_date"].forEach((n) => wiz.elements[n].addEventListener("change", hints));

    /* live readiness checklist (SRS xxxiii) */
    let timer = null;
    const prep = () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        if (!product()) return;
        const fd = new FormData();
        ["csrf_token", "product_id", "fault_category", "damage_type", "fault_occurrence_date", "fault_description", "diagnostic_confidence"]
          .forEach((k) => { const el = wiz.elements[k]; if (el) fd.append(k, el.value || (el.length ? (($("input[name=" + k + "]:checked", wiz) || {}).value || "") : "")); });
        $$("[data-doc-input]", wiz).forEach((i) => { if (i.files.length) fd.append(`has_${i.dataset.docInput}`, "1"); });
        try {
          const res = await fetch(wiz.dataset.prepUrl, { method: "POST", body: fd, credentials: "same-origin" });
          const r = await res.json();
          const icon = { error: ["bad", "bi-x-lg"], warning: ["warn", "bi-exclamation"], info: ["info", "bi-info"] };
          $("[data-ready-list]").innerHTML = r.items.length ? r.items.map((it) =>
            `<li><span class="ico ${icon[it.level][0]}"><i class="bi ${icon[it.level][1]}"></i></span><div class="grow"><div class="ttl small">${esc(it.title)}</div><div class="sub">${esc(it.detail)}</div></div></li>`).join("")
            : '<li><span class="ico good"><i class="bi bi-check-lg"></i></span><div class="grow"><div class="ttl small">Ready to submit</div><div class="sub">Nothing is missing.</div></div></li>';
          const bar = $("[data-ready-bar]"); bar.style.width = `${r.score}%`;
          bar.parentElement.className = "meter " + (r.score >= 80 ? "good" : r.score >= 50 ? "warn" : "bad");
          const badge = $("[data-ready-badge]");
          badge.className = "badge " + (r.ready ? "good" : "bad");
          badge.textContent = r.ready ? `${r.score}% ready` : "Needs attention";
        } catch { /* keep the last checklist */ }
      }, 350);
    };
    wiz.addEventListener("input", prep);
    wiz.addEventListener("change", prep);

    /* receipt OCR -> editable verification fields (SRS vi, vii) */
    const ocrInput = $("[data-ocr-input]", wiz);
    ocrInput.addEventListener("change", async () => {
      const panel = $("[data-ocr-panel]", wiz);
      const st = $("[data-ocr-status]", wiz);
      if (!ocrInput.files.length) { panel.classList.add("hidden"); return; }
      panel.classList.remove("hidden");
      st.textContent = "Reading…";
      const fd = new FormData();
      fd.append("receipt", ocrInput.files[0]);
      fd.append("csrf_token", wiz.elements.csrf_token.value);
      try {
        const res = await fetch(wiz.dataset.ocrUrl, { method: "POST", body: fd, credentials: "same-origin" });
        const r = await res.json();
        $$("[data-ocr-field]", wiz).forEach((el) => { el.value = r.ok ? (r.entities[el.dataset.ocrField] ?? "") : ""; });
        st.innerHTML = r.ok ? '<span style="color:var(--good)">Read successfully</span>' : `<span style="color:var(--warn)">${esc(r.error)}</span>`;
        const p = product();
        const sn = $("[data-ocr-field=serial_number]", wiz).value;
        if (r.ok && p && sn && sn.replace(/[^A-Z0-9]/gi, "").toUpperCase() !== p.serial.replace(/[^A-Z0-9]/gi, "").toUpperCase()) {
          st.innerHTML += ` · <span style="color:var(--bad)">serial differs from the registered ${esc(p.serial)}</span>`;
        }
      } catch { st.textContent = "Couldn't read the file. Enter the details yourself."; }
    });

    const renderReview = () => {
      const p = product();
      const docs = $$("[data-doc-input]", wiz).filter((i) => i.files.length).map((i) => i.closest("label").querySelector("b").textContent);
      const rows = [
        ["Product", p ? `${p.name} (${p.serial})` : "—"],
        ["Fault", faultSel.value || "—"],
        ["Cause", wiz.elements.damage_type.value || "—"],
        ["Started", wiz.elements.fault_occurrence_date.value || "—"],
        ["Description", wiz.elements.fault_description.value || "—"],
        ["Evidence", docs.length ? docs.join(", ") : (p && p.docs.length ? "Using files already on the product" : "None attached")],
      ];
      $("[data-review]").innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
    };

    if (product()) { syncProduct(); prep(); }
  }

  /* ---------------------------------------------------------------- charts */
  const chartData = $("#chart-data");
  if (chartData) {
    const specs = JSON.parse(chartData.textContent);
    const charts = [];
    // categorical slots 1-2 (validated reference palette), status tones for decision states
    const series = { light: ["#2a78d6", "#eb6834", "#1baf7a"], dark: ["#3987e5", "#d95926", "#199e70"] };
    const toneVar = { good: "--good", bad: "--bad", warn: "--warn", info: "--info" };
    const decisionTone = { "Likely Valid": "good", "Likely Invalid": "bad", "Manual Review Required": "warn" };
    const isDark = () => css("color-scheme") === "dark";

    const build = () => {
      if (!window.Chart) return;
      charts.splice(0).forEach((c) => c.destroy());
      const ink = css("--muted"), grid = css("--line"), surface = css("--surface");
      const palette = series[isDark() ? "dark" : "light"];
      Chart.defaults.font.family = css("--font") || "Inter, sans-serif";
      Chart.defaults.color = ink;
      $$("canvas[data-chart]").forEach((cv) => {
        const s = specs[cv.dataset.chart];
        if (!s) return;
        const horizontal = s.type === "hbar";
        const fmt = (v) => s.percent ? `${(v * 100).toFixed(1)}%` : (s.decimals ? Number(v).toFixed(s.decimals) : v);
        let datasets;
        if (s.series) {
          datasets = (Array.isArray(s.series) ? s.series : Object.entries(s.series)).map(([name, values], i) => ({
            label: name, data: values,
            backgroundColor: decisionTone[name] ? css(toneVar[decisionTone[name]]) : palette[i % palette.length],
            borderColor: surface, borderWidth: s.stacked ? { top: 2 } : 0, borderRadius: 4, borderSkipped: "bottom",
            maxBarThickness: 36,
          }));
        } else {
          const colors = s.tones ? s.tones.map((t) => css(toneVar[t])) : palette[0];
          datasets = [{ label: "Count", data: s.values, backgroundColor: colors, borderRadius: 4, maxBarThickness: 22,
            borderSkipped: horizontal ? "left" : "bottom" }];
        }
        const valueAxis = { beginAtZero: true, grid: { color: grid }, border: { display: false },
          ticks: { precision: s.decimals || s.percent ? undefined : 0, callback: (v) => fmt(v) } };
        const catAxis = { grid: { display: false }, border: { color: grid }, stacked: !!s.stacked,
          ticks: { autoSkip: !horizontal, callback(v) { const l = this.getLabelForValue(v); return l.length > 26 ? l.slice(0, 24) + "…" : l; } } };
        if (s.stacked) valueAxis.stacked = true;
        charts.push(new Chart(cv, {
          type: "bar",
          data: { labels: s.labels, datasets },
          options: {
            indexAxis: horizontal ? "y" : "x", maintainAspectRatio: false, animation: { duration: 250 },
            interaction: { mode: "index", intersect: false },
            plugins: {
              legend: { display: datasets.length > 1, position: "top", align: "start", labels: { boxWidth: 10, boxHeight: 10, useBorderRadius: true, borderRadius: 3 } },
              tooltip: { callbacks: { label: (c) => `${c.dataset.label === "Count" ? "" : c.dataset.label + ": "}${fmt(c.raw)}` } },
            },
            scales: horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
          },
        }));
      });
    };
    const start = () => (window.Chart ? build() : setTimeout(start, 60));
    start();
    document.addEventListener("themechange", build);
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", build);
  }
})();
