/* Model card: highlight the section in view in the table of contents, and open misclassified cards full size. */
(() => {
  "use strict";
  const links = Array.from(document.querySelectorAll("[data-toc-link]"));
  const sections = links.map((a) => document.getElementById(a.dataset.tocLink)).filter(Boolean);
  if (links.length && "IntersectionObserver" in window) {
    const visible = new Map();
    const mark = () => {
      const current = sections.find((s) => visible.get(s.id));
      if (!current) return;
      links.forEach((a) => {
        const on = a.dataset.tocLink === current.id;
        if (on) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
        if (on && a.scrollIntoView && getComputedStyle(a.closest("ol")).overflowX === "auto") {
          a.scrollIntoView({ block: "nearest", inline: "center", behavior: window.AX && window.AX.reduced() ? "auto" : "smooth" });
        }
      });
    };
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => visible.set(e.target.id, e.isIntersecting));
      mark();
    }, { rootMargin: "-96px 0px -55% 0px" });
    sections.forEach((s) => io.observe(s));
  }

  /* lightbox: native <dialog> (Escape closes); focus goes back to the card that opened it */
  const box = document.querySelector("[data-lightbox]");
  if (!box || typeof box.showModal !== "function") return;
  const img = box.querySelector("[data-lightbox-img]");
  let opener = null;
  document.querySelectorAll("[data-lightbox-open]").forEach((b) => b.addEventListener("click", () => {
    opener = b;
    img.src = b.dataset.src;
    img.alt = b.dataset.alt;
    box.showModal();
  }));
  box.querySelector("[data-lightbox-close]").addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => { if (e.target === box) box.close(); });   // a click on the backdrop
  box.addEventListener("close", () => { if (opener) opener.focus(); });
})();
