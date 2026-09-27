# Hero engine (landing page background)

A decorative, full-bleed layer behind the landing hero that draws the AssureX pipeline running: the Python ML node,
the Teachable Machine vision node, the decision core, the policy junction and the three outcomes. It follows the
Live check card: switching a sample or pressing **Run the checks again** sends packets from both models, flashes the
core and lights the outcome the card actually returned.

## Files

| File | Role |
|---|---|
| `templates/public/_engines.html` | Server-rendered SVG (static fallback laid out for a 1440 x 800 hero) |
| `static/js/hero_engine_math.js` | Pure layout math: zone inflation, Bezier–rect checks, rerouting, tiers, outcome mapping |
| `static/js/hero_engine.js` | Measures the hero, applies the layout, packets, parallax, pause/resume, card sync |
| `static/css/pages/landing.css` | "hero engine" section: band spacing, colours, motion, reduced motion |
| `tests/js/hero_engine_math.test.mjs` | Node unit tests (run by `tests/test_hero_engine_math.py`) |
| `tests/e2e/test_hero_engine.py` | Browser tests: no overlap at 5 widths, full opacity, contrast, identical foreground pixels, card sync, snapshots |

## How it stays out of the way

* Every foreground block carries `data-engine-avoid` (badge, h1, lede, cta, stats, card). The script measures them on
  load and on resize (ResizeObserver, debounced 100 ms, never on scroll) and inflates each by 24 px.
* Nodes, captions, labels and primary paths are placed outside those zones; a path that would cross one sags downward
  until it clears, and anything that still has no room is hidden rather than overlapped. Only the vision ring's top
  may tuck behind the card, which is solid.
* The ambient layer (dots, rings, glows, vignette) is masked out behind every text zone with feathered rectangles, so
  the text renders exactly as it would without the layer. The foreground is never dimmed or made translucent.
* Card sync goes through `AX.bus` (`static/js/app.js`): `instrument.js` emits `engine:run` with the real result.

## Tokens

Teal `#3FB8AE` (Python, valid), indigo `#8EA0E6` / `#6F82D6` (vision), neutral strokes from `--on-bench-2`, outcome
colours from `--valid-bright`, `--review-bright`, `--invalid-bright`, labels in `--mono`. Background is the hero's
`--bench`.

## Tuning density

* Ring count and spacing: `out.rings` in `layout()` (5 rings, 70 px apart).
* Dot grid: the `he-dots` pattern (28 px pitch, 7 % white) and the `he-dotfade` radial mask.
* Node size: `NODE_R` and the per-tier `scale` in `layout()` (it also shrinks to fit a short band, down to 0.5);
  band height: `.hero.hero--engine` padding in landing.css, set per height bracket so the hero stays one screen tall.
* Motion: idle packet every 5 s (`scheduleIdle`), packet travel 2.6–2.8 s, at most 3 packets at once.

## Responsive tiers

`full` >= 1280 px, `compact` 1081–1279 (scale 0.85, short labels), `strip` 768–1080 (band under the card),
`mini` < 768 (row of nodes, no rings or path labels, active outcome by colour). Reduced motion shows a still,
fully drawn diagram with the active outcome lit; everything pauses when the hero is off screen or the tab is hidden.
