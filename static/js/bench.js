/* Landing-page live bench: POSTs a sample-claim choice to /api/demo/evaluate and draws the compact verdict. */
document.addEventListener("alpine:init", () => {
  "use strict";
  const tone = { "Likely Valid": "valid", "Likely Invalid": "invalid", "Manual Review Required": "review" };
  window.Alpine.data("bench", () => ({
    busy: false, done: false, error: "", pyText: "", gtmText: "", consistencyText: "", stampText: "", stampClass: "", timingText: "",
    get buttonLabel() { return this.busy ? "Running the checks" : "Run the checks"; },
    async run() {
      const form = this.$el;
      const choice = form.querySelector("input[name=case]:checked");
      this.busy = true; this.error = "";
      const res = await window.AX.api(this.$root.dataset.url, { method: "POST", body: { case: choice.value } });
      this.busy = false;
      if (!res.success) { this.error = res.error.message; this.done = false; return; }
      const { payload: p, meter: m } = res.data;
      const svg = this.$root.querySelector("[data-bench-meter]");
      svg.setAttribute("aria-label", m.label);
      svg.querySelector("[data-track]").setAttribute("d", m.track);
      const arc = svg.querySelector("[data-arc]");
      if (m.arc) { arc.setAttribute("d", m.arc); arc.setAttribute("fill", `var(${m.tone_var})`); arc.setAttribute("stroke", `var(${m.tone_var})`); }
      else arc.removeAttribute("d");
      ["python", "gtm"].forEach((k) => {
        const g = svg.querySelector(`[data-needle=${k}]`);
        const n = m.needles.find((x) => x.cls === (k === "python" ? "py" : "gtm"));
        g.style.display = n ? "" : "none";
        if (!n) return;
        g.style.setProperty("--a", `${n.angle}deg`);
        g.querySelector("line").setAttribute("stroke-dasharray", n.dashed ? "7 5" : "");
      });
      svg.classList.remove("swept");
      if (!window.AX.reduced()) { void svg.getBoundingClientRect(); svg.classList.add("swept"); }
      const fmt = (x) => (x.available ? `${x.predicted} ${window.AX.fmt(x.top)}` : "Unavailable");
      this.pyText = `Python: ${fmt(p.python)}`;
      this.gtmText = `Teachable Machine: ${fmt(p.gtm)}`;
      const d = p.consistency.difference;
      this.consistencyText = `${p.consistency.status}${d === null ? "" : `, difference ${window.AX.fmt(d)}`}. Rule ${p.decision.rule_id}: ${p.decision.reason}.`;
      this.stampText = p.decision.value;
      this.stampClass = tone[p.decision.value] || "none";
      this.timingText = `Decided in ${(p.total_ms / 1000).toFixed(2)} s`;
      this.done = true;
    },
  }));
});
