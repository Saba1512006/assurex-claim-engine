/* App shell behaviour: preloader, menus, nav sheet, toasts, form validation, uploads, counters, charts. */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const csrf = () => ($("input[name=csrf_token]") || {}).value || "";

  /* Shared helpers for page scripts (verdict, wizard, workbench, what-if, batch, bench). */
  const AX = window.AX = {
    $, $$, css, reduced, csrf,
    /* fetch that sends the CSRF header and always resolves to the {success, data, error} envelope */
    async api(url, { method = "GET", body = null, form = null } = {}) {
      const headers = { "X-CSRFToken": csrf(), Accept: "application/json" };
      let payload = form;
      if (body !== null) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
      try {
        const res = await fetch(url, { method, headers, body: payload, credentials: "same-origin" });
        const json = await res.json().catch(() => null);
        if (json && typeof json.success === "boolean") return { status: res.status, ...json };
        return { status: res.status, success: false, data: null, error: { code: "BAD_RESPONSE", message: "The server sent an unexpected reply. Try again." } };
      } catch {
        return { status: 0, success: false, data: null, error: { code: "NETWORK", message: "No connection to the server. Check your network and try again." } };
      }
    },
    toast(message, kind = "info") {
      const box = $("[data-toasts]");
      if (!box) return;
      const icon = { success: "bi-check-circle", warning: "bi-exclamation-triangle", danger: "bi-x-circle" }[kind] || "bi-info-circle";
      const t = document.createElement("div");
      t.className = `toast ${kind}`;
      t.setAttribute("role", kind === "danger" ? "alert" : "status");
      t.dataset.toast = "";
      t.dataset.sticky = kind === "danger" ? "1" : "0";
      const i = document.createElement("i"); i.className = `bi ${icon}`; i.setAttribute("aria-hidden", "true");
      const m = document.createElement("div"); m.textContent = message;
      const x = document.createElement("button"); x.className = "x"; x.type = "button"; x.setAttribute("aria-label", "Dismiss message"); x.dataset.toastClose = "";
      const xi = document.createElement("i"); xi.className = "bi bi-x-lg"; xi.setAttribute("aria-hidden", "true"); x.append(xi);
      t.append(i, m, x);
      box.append(t);
      manageToast(t);
    },
    fmt: (v, d = 2) => (v === null || v === undefined || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(d)),
    debounce(fn, ms) { let h; return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); }; },
  };

  /* ---------------------------------------------------------------- preloader (first view of a session only) */
  const pre = $("[data-preloader]");
  const hidePre = () => { if (pre) { pre.classList.add("done"); setTimeout(() => pre.remove(), 200); } };
  try { sessionStorage.setItem("ax-seen", "1"); } catch { /* storage blocked */ }
  if (pre) {
    if (!document.documentElement.classList.contains("first-view")) pre.remove();
    else { hidePre(); setTimeout(hidePre, 600); }
  }

  /* ---------------------------------------------------------------- menus (bell, account) */
  const closeMenus = (except) => $$("[data-menu]").forEach((m) => {
    if (m === except) return;
    const b = $("[data-menu-btn]", m), p = $("[data-menu-panel]", m);
    if (p && !p.hidden) { p.hidden = true; b.setAttribute("aria-expanded", "false"); }
  });
  $$("[data-menu]").forEach((m) => {
    const b = $("[data-menu-btn]", m), p = $("[data-menu-panel]", m);
    b.addEventListener("click", () => {
      const open = p.hidden;
      closeMenus(m);
      p.hidden = !open;
      b.setAttribute("aria-expanded", String(open));
      if (open) { const first = $("a, button:not([disabled])", p); if (first) first.focus(); }
    });
    m.addEventListener("keydown", (e) => { if (e.key === "Escape" && !p.hidden) { p.hidden = true; b.setAttribute("aria-expanded", "false"); b.focus(); } });
  });
  document.addEventListener("click", (e) => { if (!e.target.closest("[data-menu]")) closeMenus(null); });

  /* ---------------------------------------------------------------- navigation sheet (< 992px) */
  const sheet = $("[data-sheet]"), opener = $("[data-sheet-open]"), backdrop = $("[data-sheet-backdrop]");
  if (sheet && opener) {
    const focusables = () => $$("a, button", sheet).filter((el) => el.offsetParent !== null);
    const close = () => {
      sheet.classList.remove("open"); backdrop.classList.remove("open");
      opener.setAttribute("aria-expanded", "false"); opener.focus();
    };
    opener.addEventListener("click", () => {
      sheet.classList.add("open"); backdrop.classList.add("open");
      opener.setAttribute("aria-expanded", "true");
      const f = focusables(); if (f.length) f[0].focus();
    });
    $("[data-sheet-close]", sheet).addEventListener("click", close);
    backdrop.addEventListener("click", close);
    sheet.addEventListener("keydown", (e) => {
      if (!sheet.classList.contains("open")) return;
      if (e.key === "Escape") return close();
      if (e.key !== "Tab") return;
      const f = focusables(), first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  /* ---------------------------------------------------------------- toasts: max 3, auto-dismiss 6 s except errors */
  function manageToast(t) {
    const close = () => t.remove();
    $("[data-toast-close]", t).addEventListener("click", close);
    if (t.dataset.sticky !== "1") setTimeout(close, 6000);
    const all = $$("[data-toast]");
    if (all.length > 3) all.slice(0, all.length - 3).forEach((x) => x.remove());
  }
  $$("[data-toast]").forEach(manageToast);

  /* ---------------------------------------------------------------- forms */
  const describe = (el, msg) => {
    const hint = el.getAttribute("aria-describedby") && document.getElementById(el.getAttribute("aria-describedby").split(" ")[0]);
    if (!hint) return;
    if (!hint.dataset.hint) hint.dataset.hint = hint.textContent;
    if (msg) { hint.textContent = msg; hint.className = "err"; hint.setAttribute("role", "alert"); }
    else { hint.textContent = hint.dataset.hint; hint.className = "help"; hint.removeAttribute("role"); }
  };
  const check = (el) => {
    if (!el.willValidate) return true;
    const ok = el.checkValidity();
    el.setAttribute("aria-invalid", ok ? "false" : "true");
    describe(el, ok ? "" : el.validationMessage);
    return ok;
  };
  AX.check = check;
  document.addEventListener("focusout", (e) => {
    const el = e.target;
    if (el.matches && el.matches("form:not([data-novalidate-ui]) .input, form:not([data-novalidate-ui]) .select, form:not([data-novalidate-ui]) .textarea") && el.value !== "") check(el);
  });
  /* JS owns validation when it runs: native bubbles off, inline messages on (without JS the browser still validates) */
  $$("form:not([data-novalidate-ui])").forEach((f) => { if (!f.noValidate) { f.noValidate = true; f.dataset.axValidate = "1"; } });
  document.addEventListener("submit", (e) => {
    const f = e.target;
    if (f.dataset.confirm && !e.defaultPrevented && !confirm(f.dataset.confirm)) { e.preventDefault(); return; }
    if (f.dataset.axValidate && !(e.submitter && e.submitter.formNoValidate)) {
      const bad = $$(".input, .select, .textarea", f).filter((el) => !check(el));
      if (bad.length) { e.preventDefault(); bad[0].focus(); return; }
    }
    if (e.defaultPrevented || f.method.toLowerCase() !== "post") return;
    const btn = e.submitter;
    if (btn && btn.tagName === "BUTTON") {
      if (btn.dataset.busy) { e.preventDefault(); return; }       // double-click guard
      btn.dataset.busy = "1";
      setTimeout(() => {
        btn.disabled = true; btn.classList.add("busy");
        const s = document.createElement("span"); s.className = "spin"; s.setAttribute("aria-hidden", "true"); btn.prepend(s);
      }, 0);
    }
  }, true);
  window.addEventListener("pageshow", () => $$("button[data-busy]").forEach((b) => {
    b.disabled = false; b.classList.remove("busy"); delete b.dataset.busy; const s = $(".spin", b); if (s) s.remove();
  }));
  $$("[data-autosubmit]").forEach((el) => el.addEventListener("change", () => (el.form.requestSubmit ? el.form.requestSubmit() : el.form.submit())));

  /* character counters: <textarea data-counter="20:1000"> + <span data-counter-for="id"> */
  $$("[data-counter]").forEach((el) => {
    const [min, max] = el.dataset.counter.split(":").map(Number);
    const out = $(`[data-counter-for="${el.id}"]`);
    if (!out) return;
    const upd = () => {
      const n = el.value.trim().length;
      out.textContent = min ? `${n} / ${min} minimum${max ? ` · ${max} max` : ""}` : `${n} / ${max}`;
      out.classList.toggle("short", min && n < min);
    };
    el.addEventListener("input", upd); upd();
  });

  /* password: show / hide and a strength hint */
  $$("[data-reveal]").forEach((b) => {
    const input = document.getElementById(b.getAttribute("aria-controls"));
    b.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      b.textContent = show ? "Hide" : "Show";
      b.setAttribute("aria-pressed", String(show));
    });
  });
  $$("[data-strength]").forEach((meter) => {
    const input = document.getElementById(meter.dataset.strength);
    const label = $(`[data-strength-label="${meter.dataset.strength}"]`);
    const words = ["Too short", "Weak", "Fair", "Good", "Strong"];
    input.addEventListener("input", () => {
      const v = input.value;
      let s = v.length >= 10 ? 1 : 0;                          // the server's minimum
      if (s && /[A-Za-z]/.test(v) && /\d/.test(v)) s++;
      if (s > 1 && /[a-z]/.test(v) && /[A-Z]/.test(v)) s++;
      if (s > 2 && (/[^A-Za-z0-9]/.test(v) || v.length >= 14)) s++;
      meter.dataset.score = String(s);
      if (label) { label.textContent = v ? words[s] : ""; label.dataset.score = String(s); }
    });
  });
  /* confirmation field: says whether it matches the password as the person types */
  $$("[data-match]").forEach((confirm) => {
    const pw = document.getElementById(confirm.dataset.match);
    const hint = document.getElementById(confirm.getAttribute("aria-describedby"));
    if (!pw || !hint || !hint.hasAttribute("data-match-label")) return;
    const upd = () => {
      const state = !confirm.value ? "" : confirm.value === pw.value ? "ok" : "no";
      confirm.setCustomValidity(state === "no" ? "The two passwords don't match." : "");
      if (confirm.getAttribute("aria-invalid") === "true") check(confirm);   // clear an earlier error once it is fixed
      if (hint.classList.contains("err")) return;                            // an error message is showing; keep it
      hint.dataset.state = state;
      hint.textContent = state === "ok" ? "Passwords match." : state === "no" ? "Doesn't match the password yet." : "";
    };
    confirm.addEventListener("input", upd); pw.addEventListener("input", upd);
  });

  /* navbar: a pill glides behind the link under the pointer (desktop tray only) */
  $$(".nav, .pnav").forEach((nav) => {
    const glide = document.createElement("span");
    glide.className = "nav-glide";
    glide.setAttribute("aria-hidden", "true");
    nav.prepend(glide);
    nav.addEventListener("pointerover", (e) => {
      const a = e.target.closest("a");
      if (!a || !nav.contains(a) || !matchMedia("(min-width: 992px)").matches) return;
      glide.style.setProperty("--gx", `${a.offsetLeft}px`);
      glide.style.setProperty("--gw", `${a.offsetWidth}px`);
      requestAnimationFrame(() => nav.classList.add("gliding"));
    });
    nav.addEventListener("pointerleave", () => nav.classList.remove("gliding"));
  });

  /* 3D tilt: the element leans toward the pointer inside its zone (fine pointers only, never with reduced motion) */
  $$("[data-tilt-zone]").forEach((zone) => {
    const el = $("[data-tilt]", zone);
    if (!el || reduced() || !matchMedia("(pointer: fine)").matches) return;
    let frame = 0;
    zone.addEventListener("pointermove", (e) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const r = zone.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        el.style.setProperty("--ry", `${(x * 16).toFixed(2)}deg`);
        el.style.setProperty("--rx", `${(-y * 12).toFixed(2)}deg`);
        el.style.setProperty("--mx", `${((x + 0.5) * 100).toFixed(1)}%`);
        el.style.setProperty("--my", `${((y + 0.5) * 100).toFixed(1)}%`);
      });
    });
    zone.addEventListener("pointerleave", () => { cancelAnimationFrame(frame); ["--rx", "--ry", "--mx", "--my"].forEach((p) => el.style.removeProperty(p)); });
  });

  /* sign-in persona chips fill the seeded evaluator accounts (password never shown as text) */
  $$("[data-persona]").forEach((b) => b.addEventListener("click", () => {
    const f = b.closest("[data-login]") || document;
    $("input[name=email]", f).value = b.dataset.email;
    $("input[name=password]", f).value = b.dataset.password;
    $("input[name=password]", f).form.requestSubmit();
  }));

  /* ---------------------------------------------------------------- uploads: type + size checked before sending */
  $$("[data-dropzone]").forEach((z) => {
    const input = $("input[type=file]", z);
    if (!input) return;
    const max = Number(z.dataset.max || 16) * 1024 * 1024;
    const allow = (z.dataset.accept || "").split(",").filter(Boolean);
    const meta = $("[data-file-meta]", z);
    const thumb = $("[data-file-thumb]", z);
    const clear = $("[data-file-clear]", z);
    const update = () => {
      const f = input.files[0];
      let problem = "";
      if (f && f.size > max) problem = `${f.name} is larger than ${z.dataset.max || 16} MB.`;
      if (f && allow.length && !allow.some((ext) => f.name.toLowerCase().endsWith(ext))) problem = `${f.name} is not an accepted file type (${allow.join(", ")}).`;
      if (problem) { input.value = ""; AX.toast(problem, "warning"); }
      const file = input.files[0];
      z.classList.toggle("done", !!file);
      if (meta) meta.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : (meta.dataset.empty || "");
      if (thumb) {
        if (thumb.dataset.url) URL.revokeObjectURL(thumb.dataset.url);
        if (file && file.type.startsWith("image/")) { thumb.dataset.url = URL.createObjectURL(file); thumb.src = thumb.dataset.url; thumb.hidden = false; }
        else { thumb.hidden = true; thumb.removeAttribute("src"); }
      }
      if (clear) clear.hidden = !file;
      input.dispatchEvent(new CustomEvent("ax:file", { bubbles: true }));
    };
    if (meta) meta.dataset.empty = meta.textContent;
    input.addEventListener("change", update);
    if (clear) clear.addEventListener("click", () => { input.value = ""; update(); input.focus(); });
    ["dragenter", "dragover"].forEach((ev) => z.addEventListener(ev, (e) => { e.preventDefault(); z.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) => z.addEventListener(ev, () => z.classList.remove("drag")));
    z.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; update(); }
    });
  });

  /* access control: service center field only for staff invitations */
  const inviteRole = $("[data-invite-role]");
  if (inviteRole) {
    const field = $("[data-center-field]");
    const sync = () => { field.hidden = inviteRole.value !== "service_center_staff"; };
    inviteRole.addEventListener("change", sync); sync();
  }

  /* ---------------------------------------------------------------- KPI numbers count up once when first seen
     (the final value is already in the HTML; reduced motion shows it as is) */
  const countUp = (el) => {
    const m = el.textContent.trim().match(/^(\d+(?:\.\d+)?)(.*)$/);
    if (!m) return;
    const to = parseFloat(m[1]), dec = (m[1].split(".")[1] || "").length, rest = m[2], t0 = performance.now(), dur = 700;
    el.closest(".kpi")?.classList.add("is-counting");
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = `${(to * e).toFixed(dec)}${rest}`;
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  const counters = $$("[data-countup]");
  if (counters.length && !reduced() && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { countUp(e.target); io.unobserve(e.target); } }), { threshold: 0.4 });
    counters.forEach((c) => io.observe(c));
  }

  /* ---------------------------------------------------------------- charts (Chart.js, themed from tokens) */
  const chartData = $("#chart-data");
  if (chartData) {
    const specs = JSON.parse(chartData.textContent);
    /* chart marks use the validated --chart-* tokens (never the text colours); status hues stay reserved for decisions */
    const colour = {
      "Likely Valid": "--chart-valid", "Likely Invalid": "--chart-invalid", "Manual Review Required": "--chart-review",
      "Valid Claim": "--chart-valid", "Invalid Claim": "--chart-invalid", "Manual Review": "--chart-review",
      "Python model": "--chart-py", "Teachable Machine": "--chart-gtm",
      "Strong Match": "--chart-valid", "Acceptable Match": "--chart-py", "Weak Match": "--chart-review", "Model Disagreement": "--chart-invalid",
      "Uncertain Result": "--chart-neutral",
    };
    const build = () => {
      if (!window.Chart) return setTimeout(build, 50);
      const paper = css("--paper"), ink = css("--ink"), ink2 = css("--ink-2"), steel = css("--steel");
      Chart.defaults.font.family = css("--font");
      Chart.defaults.font.size = 12;
      Chart.defaults.color = ink2;
      $$("canvas[data-chart]").forEach((cv) => {
        const s = specs[cv.dataset.chart];
        if (!s) return;
        const horizontal = s.type === "hbar";
        const line = s.type === "line";
        const fmt = (v) => (s.percent ? `${(v * 100).toFixed(1)}%` : (s.decimals ? Number(v).toFixed(s.decimals) : v));
        const series = s.series ? (Array.isArray(s.series) ? s.series : Object.entries(s.series)) : [[s.label || "Count", s.values]];
        const last = series.length - 1;
        /* 4px rounded data end, square at the baseline; in a stack only the outermost segment is rounded,
           and a 1px paper edge on each segment leaves a 2px gap between neighbours */
        const radius = (i) => (ctx) => {
          if (s.stacked && i !== last) return 0;
          return horizontal ? { topRight: 4, bottomRight: 4 } : { topLeft: 4, topRight: 4 };
        };
        const datasets = series.map(([name, values], i) => {
          const fill = series.length === 1 && s.labels.every((l) => colour[l])
            ? s.labels.map((l) => css(colour[l]))                          // one bar per category: colour by category
            : css(colour[name] || (i === 0 ? "--chart-count" : i === 1 ? "--chart-py" : "--chart-gtm"));
          return {
            label: name, data: values, type: line ? "line" : "bar",
            backgroundColor: fill, hoverBackgroundColor: fill,
            borderColor: line ? css(colour[name] || "--ink") : paper,
            borderWidth: line ? 2 : (s.stacked ? 1 : 0), borderSkipped: "start",
            borderRadius: radius(i), maxBarThickness: 28, categoryPercentage: 0.72, barPercentage: series.length > 1 && !s.stacked ? 0.86 : 0.9,
            pointRadius: line ? 4 : 0, pointHoverRadius: line ? 6 : 0, pointBackgroundColor: css(colour[name] || "--ink"),
            pointBorderColor: paper, pointBorderWidth: 2, tension: 0,
          };
        });
        const grid = { color: "rgba(21, 32, 43, .07)", drawTicks: false, lineWidth: 1 };
        const valueAxis = { beginAtZero: true, grid, border: { display: false }, stacked: !!s.stacked,
          title: { display: !!s.yTitle, text: s.yTitle, color: steel },
          ticks: { padding: 8, color: steel, precision: s.decimals || s.percent ? undefined : 0, callback: (v) => fmt(v) } };
        const catAxis = { grid: { display: false }, border: { color: "rgba(21, 32, 43, .18)" }, stacked: !!s.stacked,
          title: { display: !!s.xTitle, text: s.xTitle, color: steel }, ticks: { padding: 6, color: ink2 } };
        const annotations = s.marker !== undefined ? { id: "marker", afterDraw(c) {
          const x = c.scales.x.getPixelForValue(s.marker); const { top, bottom } = c.chartArea; const g = c.ctx;
          g.save(); g.setLineDash([4, 4]); g.strokeStyle = css("--steel-line"); g.beginPath(); g.moveTo(x, top); g.lineTo(x, bottom); g.stroke(); g.restore();
        } } : null;
        new Chart(cv, {
          type: line ? "line" : "bar",
          data: { labels: s.labels, datasets },
          options: {
            indexAxis: horizontal ? "y" : "x", maintainAspectRatio: false,
            animation: reduced() ? false : { duration: 600, easing: "easeOutQuart" },
            interaction: { mode: "index", intersect: false },
            layout: { padding: { top: 4, right: 8 } },
            plugins: {
              legend: { display: datasets.length > 1, position: "top", align: "start",
                labels: { usePointStyle: true, pointStyle: "rectRounded", boxWidth: 8, boxHeight: 8, padding: 16, color: ink2,
                  font: { size: 12, weight: "500" } } },
              tooltip: {                                                   // the bench, as a floating readout
                backgroundColor: css("--bench"), titleColor: css("--on-bench"), bodyColor: css("--on-bench-2"),
                borderColor: "rgba(255, 255, 255, .08)", borderWidth: 1, padding: 12, cornerRadius: 10, caretSize: 6,
                boxPadding: 6, usePointStyle: true, titleFont: { weight: "600", size: 12 }, bodyFont: { size: 12 },
                callbacks: { label: (c) => ` ${c.dataset.label}: ${fmt(c.raw)}` } },
            },
            scales: horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
          },
          plugins: annotations ? [annotations] : [],
        });
      });
    };
    build();
  }
  /* "View as table" toggles for charts */
  $$("[data-table-toggle]").forEach((b) => {
    const t = document.getElementById(b.getAttribute("aria-controls"));
    b.addEventListener("click", () => {
      const show = t.hidden;
      t.hidden = !show;
      b.setAttribute("aria-expanded", String(show));
      b.textContent = show ? "Hide table" : "View as table";
    });
  });
})();

/* Adaptive navbar: it always takes the opposite tone of the surface scrolling under it. Over a dark (bench)
   section it turns light; over a light section it turns dark; at the very top of the landing page it is a
   see-through dark glass over the hero. The surface is read at the island's centre on scroll (one check per
   frame), so no section needs to be registered anywhere: dark sections are the ones built on .bench. */
(() => {
  const bar = document.querySelector(".topbar");
  if (!bar) return;
  const overlay = document.body.classList.contains("nav-overlay");
  const island = bar.querySelector(".wrap") || bar;
  let queued = false;
  const surfaceIsDark = () => {
    const r = island.getBoundingClientRect();
    const y = Math.round(r.top + r.height / 2);
    for (const x of [Math.round(r.left + r.width / 2), Math.round(r.left + 12), Math.round(r.right - 12)]) {   // the middle decides
      const under = document.elementsFromPoint(x, y).find((el) => !bar.contains(el) && el !== document.documentElement);
      if (under) return !!under.closest(".bench, .footer");
    }
    return false;                                     // nothing under it yet: the page background is light
  };
  const update = () => {
    queued = false;
    const top = overlay && window.scrollY < 24;
    bar.classList.toggle("is-top", top);
    bar.classList.toggle("scrolled", !top);
    bar.classList.toggle("tone-dark", top || !surfaceIsDark());
  };
  const queue = () => { if (!queued) { queued = true; requestAnimationFrame(update); } };
  window.addEventListener("scroll", queue, { passive: true });
  window.addEventListener("resize", queue);
  update();
})();
