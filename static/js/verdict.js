/* Verdict screen: drops ?fresh=1 after the one-time reveal, and polls the pipeline stages while a claim is evaluated. */
(() => {
  "use strict";
  const url = new URL(location.href);
  if (url.searchParams.has("fresh")) {           // reloading must show the final state without animation
    url.searchParams.delete("fresh");
    history.replaceState(null, "", url.pathname + (url.search || "") + url.hash);
  }

  document.addEventListener("alpine:init", () => {
    window.Alpine.data("pendingVerdict", () => ({
      elapsed: "", failed: false, started: 0, timer: null,
      init() { this.start(); },
      start() {
        this.failed = false;
        this.started = Date.now();
        clearInterval(this.timer);
        this.timer = setInterval(() => this.poll(), 500);
        this.poll();
      },
      retry() { this.start(); },
      async poll() {
        const secs = (Date.now() - this.started) / 1000;
        this.elapsed = `${secs.toFixed(1)} s`;
        if (secs > 20) { clearInterval(this.timer); this.failed = true; return; }
        const res = await window.AX.api(this.$el.dataset.url);
        if (!res.success) return;
        const items = this.$el.querySelectorAll(".stages-live li");
        (res.data.stages || []).forEach((s, i) => {
          const li = items[i]; if (!li) return;
          li.querySelector("i").className = `bi ${s.status === "done" ? "bi-check-lg" : "bi-circle"}`;
          li.querySelector(".ms").textContent = s.status === "done" ? `${s.ms} ms` : s.status;
        });
        if (res.data.state === "decided") { clearInterval(this.timer); location.assign(this.$el.dataset.doneUrl); }
      },
    }));
  });
})();
