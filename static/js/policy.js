/* Policy editor: list every unsaved change (old → new) and flag the ones drawn on the Claim Summary Card. */
(() => {
  "use strict";
  const { $, $$ } = window.AX;
  const form = $("[data-policy-form]");
  if (!form) return;
  const list = $("[data-diff]"), count = $("[data-diff-count]"), card = $("[data-diff-card]"), save = $("[data-diff-save]");
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const groupValue = (g) => $$("input:checked", g).map((i) => i.value).sort().join("|");

  const diff = () => {
    const changes = [];
    $$("[data-track]", form).forEach((f) => {
      const now = f.tagName === "SELECT" ? f.value : String(Number(f.value));
      const was = f.tagName === "SELECT" ? f.dataset.initial : String(Number(f.dataset.initial));
      if (now !== was) changes.push({ label: f.dataset.label, from: f.tagName === "SELECT" ? f.selectedOptions[0] && [...f.options].find((o) => o.value === was).text : was,
        to: f.tagName === "SELECT" ? f.selectedOptions[0].text : now, card: "card" in f.dataset });
    });
    $$("[data-track-group]", form).forEach((g) => {
      const now = groupValue(g), was = g.dataset.initial;
      if (now !== was) changes.push({ label: g.dataset.label, from: was.split("|").filter(Boolean).join(", ") || "none", to: now.split("|").filter(Boolean).join(", ") || "none", card: true });
    });
    list.replaceChildren(...(changes.length ? changes.map((c) => {
      const li = el("li");
      li.append(el("span", "mono", c.label), ": ", el("del", "", c.from), " → ", el("ins", "", c.to));
      if (c.card) li.append(" ", el("span", "chip", "on the card"));
      return li;
    }) : [el("li", "small muted", "No unsaved changes.")]));
    count.textContent = changes.length ? `${changes.length} unsaved` : "None yet";
    card.classList.toggle("hidden", !changes.some((c) => c.card));
    save.disabled = !changes.length;
  };
  form.addEventListener("input", diff);
  form.addEventListener("change", diff);
  form.addEventListener("reset", () => setTimeout(diff, 0));
})();
