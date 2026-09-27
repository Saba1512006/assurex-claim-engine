/* Reviewer decision form: shows the override reason when the choice contradicts the recommendation and keeps submit disabled until it is long enough. */
(() => {
  "use strict";
  document.querySelectorAll("[data-review-form]").forEach((f) => {
    const pairs = JSON.parse(f.dataset.overrides || "[]");
    const targets = JSON.parse(f.dataset.targets || "{}");
    const rec = f.dataset.recommendation;
    const min = Number(f.dataset.min || 20);
    const field = f.querySelector("[data-override-field]");
    const reason = field.querySelector("textarea");
    const submit = f.querySelector("[data-review-submit]");
    const sync = () => {
      const chosen = f.querySelector("input[name=action]:checked");
      const needed = !!chosen && pairs.some(([d, s]) => d === rec && s === targets[chosen.value]);
      field.hidden = !needed;
      reason.required = needed;
      reason.minLength = needed ? min : 0;
      submit.disabled = needed && reason.value.trim().length < min;
    };
    f.querySelectorAll("input[name=action]").forEach((r) => r.addEventListener("change", sync));
    reason.addEventListener("input", sync);
    sync();
  });
})();
