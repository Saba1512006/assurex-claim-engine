// Unit tests for static/js/hero_engine_math.js (run: node --test tests/js). No dependencies beyond Node itself.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const M = require("../../static/js/hero_engine_math.js");

const HERO_1440 = { w: 1440, h: 800 };
const RAW_1440 = {
  badge: { l: 120, t: 120, r: 328, b: 146 }, h1: { l: 120, t: 162, r: 651, b: 279 }, lede: { l: 120, t: 295, r: 576, b: 353 },
  cta: { l: 120, t: 369, r: 525, b: 417 }, stats: { l: 120, t: 445, r: 704, b: 564 }, card: { l: 736, t: 83, r: 1320, b: 601 },
};
const HERO_1280 = { w: 1280, h: 754 };
const RAW_1280 = {
  badge: { l: 40, t: 122, r: 248, b: 148 }, h1: { l: 40, t: 164, r: 512, b: 268 }, lede: { l: 40, t: 284, r: 496, b: 343 },
  cta: { l: 40, t: 359, r: 445, b: 407 }, stats: { l: 40, t: 435, r: 624, b: 549 }, card: { l: 656, t: 76, r: 1240, b: 595 },
};

test("inflate pads every side", () => {
  assert.deepEqual(M.inflate({ l: 10, t: 20, r: 30, b: 40 }, 24), { l: -14, t: -4, r: 54, b: 64 });
  assert.deepEqual(M.inflate({ l: 0, t: 0, r: 1, b: 1 }), { l: -24, t: -24, r: 25, b: 25 });
});

test("rect intersection is strict (touching edges do not intersect)", () => {
  const a = { l: 0, t: 0, r: 10, b: 10 };
  assert.equal(M.intersects(a, { l: 5, t: 5, r: 15, b: 15 }), true);
  assert.equal(M.intersects(a, { l: 10, t: 0, r: 20, b: 10 }), false);
  assert.equal(M.intersects(a, { l: 20, t: 20, r: 30, b: 30 }), false);
});

test("cubic point hits both end points", () => {
  const c = { p0: { x: 0, y: 0 }, p1: { x: 10, y: 0 }, p2: { x: 20, y: 10 }, p3: { x: 30, y: 10 } };
  assert.deepEqual(M.cubicPoint(c, 0), { x: 0, y: 0 });
  assert.deepEqual(M.cubicPoint(c, 1), { x: 30, y: 10 });
});

test("Bezier-rect intersection detects a crossing and clears a miss", () => {
  const c = { p0: { x: 0, y: 50 }, p1: { x: 40, y: 50 }, p2: { x: 60, y: 50 }, p3: { x: 100, y: 50 } };
  assert.equal(M.cubicHitsRects(c, [{ l: 40, t: 40, r: 60, b: 60 }]), true);
  assert.equal(M.cubicHitsRects(c, [{ l: 40, t: 0, r: 60, b: 30 }]), false);
});

test("route sags below an obstacle, and gives up when there is no way round", () => {
  const block = { l: 40, t: 40, r: 60, b: 58 };
  const c = M.route({ x: 0, y: 50 }, { x: 100, y: 50 }, [block]);
  assert.ok(c, "a route exists");
  assert.equal(M.cubicHitsRects(c, [block]), false);
  assert.ok(c.p1.y > 50, "control points moved down");
  assert.equal(M.route({ x: 0, y: 50 }, { x: 100, y: 50 }, [{ l: 40, t: -1000, r: 60, b: 1000 }]), null);
});

test("tiers follow the hero width", () => {
  assert.equal(M.tier(1920), "full");
  assert.equal(M.tier(1280), "full");
  assert.equal(M.tier(1279), "compact");
  assert.equal(M.tier(1081), "compact");
  assert.equal(M.tier(1080), "strip");
  assert.equal(M.tier(768), "strip");
  assert.equal(M.tier(767), "mini");
});

test("outcome mapping reads the real result", () => {
  assert.equal(M.outcomeFor({ tone: "valid" }), "valid");
  assert.equal(M.outcomeFor({ tone: "invalid" }), "invalid");
  assert.equal(M.outcomeFor({ tone: "review" }), "review");
  assert.equal(M.outcomeFor({ tone: "none", decision: { value: "Likely Invalid" } }), "invalid");
  assert.equal(M.outcomeFor({ decision: { value: "Manual Review Required" } }), "review");
  assert.equal(M.outcomeFor({ tone: "none", decision: { value: "Unavailable" } }), null);
  assert.equal(M.outcomeFor(null), null);
});

test("captions and agreement words", () => {
  assert.equal(M.caption(0.8876, "Valid Claim"), "p 0.89 · VALID");
  assert.equal(M.caption(0.9953, "Invalid Claim"), "p 1.00 · INVALID");
  assert.equal(M.caption(null, "Manual Review"), "p — · REVIEW");
  assert.equal(M.agreeWord("Strong Match"), "AGREE");
  assert.equal(M.agreeWord("Uncertain Result"), "SPLIT");
});

for (const [name, hero, raw] of [["1440x800", HERO_1440, RAW_1440], ["1280x754", HERO_1280, RAW_1280]]) {
  test(`layout ${name}: every node, label and primary path clears the zones`, () => {
    const L = M.layout(hero, raw);
    assert.equal(L.ok, true, `hidden: ${L.hidden}`);
    const zones = L.zones, text = L.textZones;
    for (const k of ["py", "core"]) {
      const n = k === "core" ? { x: L.core.x, y: L.core.y, r: L.core.h } : L[k];
      assert.equal(M.hitsAny({ l: n.x - n.r, t: n.y - n.r, r: n.x + n.r, b: n.y + n.r }, zones), false, k);
    }
    // the vision ring may tuck behind the solid card, never behind text
    assert.equal(M.hitsAny({ l: L.tm.x - L.tm.r, t: L.tm.y - L.tm.r, r: L.tm.x + L.tm.r, b: L.tm.y + L.tm.r }, text), false);
    assert.ok(L.tm.y - L.tm.r < raw.card.b && L.tm.y > raw.card.b, "vision ring straddles the card's bottom edge");
    assert.equal(M.cubicHitsRects(L.paths.py, zones), false);
    assert.equal(M.cubicHitsRects(L.paths.tm, zones), false);
    for (const b of Object.values(L.branches)) assert.equal(M.cubicHitsRects(b, zones), false);
    for (const t of Object.values(L.terms)) assert.ok(t.y + 18 <= hero.h, "terminal labels stay inside the hero");
    assert.ok(Math.abs(L.core.x - (raw.stats.r + raw.card.l) / 2) < 1, "core sits under the column gutter");
  });
}

test("layout reports what it could not place instead of overlapping", () => {
  const raw = { ...RAW_1440, stats: { l: 120, t: 445, r: 704, b: 790 } };   // stats reach the bottom: no band left
  const L = M.layout(HERO_1440, raw);
  assert.equal(L.ok, false);
  assert.ok(L.hidden.includes("py"));
});

test("stacked tiers put the band under the card", () => {
  const raw = { h1: { l: 16, t: 100, r: 374, b: 250 }, stats: { l: 16, t: 500, r: 374, b: 600 }, card: { l: 16, t: 650, r: 374, b: 1450 } };
  const L = M.layout({ w: 390, h: 1650 }, raw);
  assert.equal(L.tier, "mini");
  assert.ok(L.core.y - L.core.h > raw.card.b, "core below the card");
  assert.equal(L.rings, null);
  assert.equal(L.labels.path, null);
});
