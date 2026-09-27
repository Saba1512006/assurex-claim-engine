/* Reviewer workbench: evidence viewer, column tabs below 1280 px, keyboard shortcuts and the help dialog. */
(() => {
  "use strict";
  const { $, $$ } = window.AX;
  const bench = $("[data-workbench]");
  if (!bench) return;

  /* evidence viewer: thumbnails swap the large frame */
  const frame = $("[data-frame]"), label = $("[data-frame-label]");
  $$("[data-thumb]").forEach((b) => b.addEventListener("click", () => {
    $$("[data-thumb]").forEach((t) => t.setAttribute("aria-pressed", String(t === b)));
    const img = document.createElement("img");
    img.src = b.dataset.src; img.alt = b.dataset.label;
    frame.replaceChildren(img);
    label.textContent = b.dataset.label;
  }));

  /* column tabs (narrow screens) */
  const tabs = $$("[data-col-tab]");
  const showCol = (name) => {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.colTab === name)));
    $$("[data-col]", bench).forEach((c) => c.classList.toggle("active", c.dataset.col === name));
  };
  tabs.forEach((t) => t.addEventListener("click", () => showCol(t.dataset.colTab)));

  /* help dialog */
  const help = $("[data-help]");
  const openHelp = () => { if (help && !help.open) help.showModal(); };
  $("[data-help-open]")?.addEventListener("click", openHelp);
  $("[data-help-close]")?.addEventListener("click", () => help.close());

  /* shortcuts: never while typing */
  const form = $("[data-decision-bar]");
  const comment = form && $("textarea[name=comments]", form);
  const choose = (key) => {
    const radio = form && $(`input[name=action][data-key="${key}"]`, form);
    if (!radio) return false;
    radio.checked = true;
    radio.dispatchEvent(new Event("change", { bubbles: true }));
    comment.focus();
    return true;
  };
  document.addEventListener("keydown", (e) => {
    const t = e.target;
    const typing = t.closest && t.closest("input, textarea, select, [contenteditable]");
    if (e.key === "Escape" && typing && t.blur) { t.blur(); return; }
    if (typing || e.ctrlKey || e.metaKey || e.altKey || (help && help.open)) return;
    const k = e.key.toLowerCase();
    if (["a", "r", "i"].includes(k) && choose(k)) e.preventDefault();
    else if (e.key === "/" && comment) { e.preventDefault(); comment.focus(); }
    else if (e.key === "?") { e.preventDefault(); openHelp(); }
    else if (k === "n") { const n = $("[data-next-claim]"); if (n) { e.preventDefault(); n.click(); } }
    else if (["1", "2", "3"].includes(e.key) && tabs.length) showCol(["evidence", "verdict", "facts"][Number(e.key) - 1]);
  });
})();
