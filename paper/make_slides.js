// Builds paper/A7_slides.pptx.
//   npm install pptxgenjs && node paper/make_slides.js
//
// Every figure comes from results/; regenerate those with `python src/train.py`.
//
// Layout rule: slide code never sets a y coordinate. Text height is computed from the
// string, the box width and the point size, and a column cursor advances by that height.
// Overflow and overlap are therefore prevented by construction rather than by inspection.

const pptxgen = require("pptxgenjs");
const path = require("path");

/* ── design system ──────────────────────────────────────────────────────── */

const INK = "12333F";
const SURFACE = "FFFFFF";
const TINT = "EDF4F6";
const BRAND = "0B6E8C";
const SUPPORT = "17A398";
const ALERT = "C25332";
const MUTED = "68808B";
const ON_DARK = "AFC7D0";

const HEAD = "Cambria";
const BODY = "Calibri";

const DISPLAY = 40, TITLE = 30, ACCENT = 24, LEAD = 20, TEXT = 18, MICRO = 14;

const W = 13.333, H = 7.5;
const MARGIN = 0.75;
const CONTENT_W = W - 2 * MARGIN;
const GUTTER = 0.28;
const COLW = (CONTENT_W - 11 * GUTTER) / 12;

const KICKER_Y = 0.75;
const TITLE_Y = 1.12;
const BODY_Y = 2.25;
const FOOT_Y = 6.92;
const CONTENT_BOTTOM = 6.66; // nothing may cross this

const SPLIT_L = 7, SPLIT_R = 5; // the deck's single two-column ratio

const col = (i) => MARGIN + i * (COLW + GUTTER);
const span = (n) => n * COLW + (n - 1) * GUTTER;

const FIGS = path.join(__dirname, "figures");

let SLIDE_NO = 0;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "A7 Water and Supplies";
pres.title = "A7 - Water and Supplies";

/* ── text metrics ───────────────────────────────────────────────────────── */
// Average advance width as a fraction of the em, measured for these two faces.
// Deliberately generous so estimated height is never under the truth.
const EM_FRACTION = { [BODY]: 0.50, [HEAD]: 0.53 };

function lineCount(text, widthIn, size, face, tracking) {
  const em = size / 72;
  const avg = (EM_FRACTION[face] || 0.50) * em + (tracking || 0) / 72;
  const perLine = Math.max(1, Math.floor(widthIn / avg));
  let lines = 0;
  for (const para of String(text).split("\n")) {
    const t = para.trim();
    lines += t.length ? Math.ceil(t.length / perLine) : 1;
  }
  return lines;
}

function blockHeight(text, widthIn, size, face, leading, tracking) {
  const lead = leading || size * 1.35;
  return lineCount(text, widthIn, size, face, tracking) * lead / 72 + 0.06;
}

/* ── slide shells ───────────────────────────────────────────────────────── */

function slideDark(kicker, title) {
  SLIDE_NO += 1;
  const s = pres.addSlide();
  s.background = { color: INK };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: col(0), y: KICKER_Y, w: span(12), h: 0.3,
      fontSize: MICRO, bold: true, color: SUPPORT, fontFace: BODY,
      charSpacing: 2, isTextBox: true, margin: 0, valign: "top",
    });
  }
  if (title) {
    s.addText(title, {
      x: col(0), y: TITLE_Y, w: span(11), h: 0.95,
      fontSize: TITLE, bold: true, color: SURFACE, fontFace: HEAD,
      isTextBox: true, margin: 0, valign: "top",
    });
  }
  return s;
}

function slideLight(kicker, title) {
  SLIDE_NO += 1;
  const s = pres.addSlide();
  s.background = { color: SURFACE };
  s.addText(kicker.toUpperCase(), {
    x: col(0), y: KICKER_Y, w: span(12), h: 0.3,
    fontSize: MICRO, bold: true, color: SUPPORT, fontFace: BODY,
    charSpacing: 2, isTextBox: true, margin: 0, valign: "top",
  });
  s.addText(title, {
    x: col(0), y: TITLE_Y, w: span(12), h: 0.95,
    fontSize: TITLE, bold: true, color: INK, fontFace: HEAD,
    isTextBox: true, margin: 0, valign: "top",
  });
  return s;
}

function footer(s, label) {
  s.addText(label, {
    x: col(0), y: FOOT_Y, w: span(12), h: 0.26,
    fontSize: 11, color: MUTED, fontFace: BODY,
    isTextBox: true, margin: 0, valign: "top",
  });
}

/* ── column flow ────────────────────────────────────────────────────────── */

const CARD_PAD = 0.3;

function flow(slide, startCol, spanCols, yStart) {
  const x = col(startCol);
  const w = span(spanCols);
  let y = yStart === undefined ? BODY_Y : yStart;

  function guard(what) {
    if (process.env.DECK_DEBUG) {
      console.error(`  s${SLIDE_NO} ${spanCols}col ${what.padEnd(6)} -> ${y.toFixed(2)}`);
    }
    if (y > CONTENT_BOTTOM + 0.001) {
      throw new Error(
        `slide ${SLIDE_NO}: ${what} on a ${spanCols}-col flow ends at ${y.toFixed(2)}, ` +
        `limit ${CONTENT_BOTTOM}`);
    }
  }

  const api = {
    get y() { return y; },
    gap(n) { y += n; return api; },

    text(t, o = {}) {
      const size = o.size || TEXT;
      const face = o.face || BODY;
      const lead = o.leading || Math.round(size * 1.38);
      const h = blockHeight(t, w, size, face, lead, o.charSpacing);
      slide.addText(t, {
        x, y, w, h,
        fontSize: size, color: o.color || INK, bold: !!o.bold, italic: !!o.italic,
        fontFace: face, lineSpacing: lead, charSpacing: o.charSpacing,
        isTextBox: true, margin: 0, valign: "top",
      });
      y += h + (o.after === undefined ? 0.16 : o.after);
      guard("text");
      return api;
    },

    // value + caption, one fixed relationship used everywhere
    stat(value, label, o = {}) {
      const size = o.size || 36;
      const vh = blockHeight(value, w, size, HEAD, size * 1.05);
      slide.addText(value, {
        x, y, w, h: vh,
        fontSize: size, bold: true, color: o.color || BRAND, fontFace: HEAD,
        lineSpacing: Math.round(size * 1.05), isTextBox: true, margin: 0, valign: "top",
      });
      y += vh + 0.04;
      const lh = blockHeight(label, w, MICRO, BODY, MICRO * 1.3);
      slide.addText(label, {
        x, y, w, h: lh,
        fontSize: MICRO, color: o.labelColor || MUTED, fontFace: BODY,
        lineSpacing: Math.round(MICRO * 1.3), isTextBox: true, margin: 0, valign: "top",
      });
      y += lh + (o.after === undefined ? 0.2 : o.after);
      guard("stat");
      return api;
    },

    // items: [{ text, size, face, bold, color, charSpacing, after }]
    card(items, o = {}) {
      const innerW = w - 2 * CARD_PAD;
      let inner = CARD_PAD;
      const placed = items.map((it) => {
        const size = it.size || TEXT;
        const face = it.face || BODY;
        const lead = it.leading || Math.round(size * 1.38);
        const h = blockHeight(it.text, innerW, size, face, lead, it.charSpacing);
        const rec = { it, h, dy: inner, size, face, lead };
        inner += h + (it.after === undefined ? 0.14 : it.after);
        return rec;
      });
      const naturalH = inner - (items.length ? (items[items.length - 1].after === undefined ? 0.14 : items[items.length - 1].after) : 0) + CARD_PAD;
      const cardH = Math.max(naturalH, o.minH || 0);
      if (o.measure) return naturalH;

      slide.addShape(pres.ShapeType.roundRect, {
        x, y, w, h: cardH, rectRadius: 0.06,
        fill: { color: o.fill || TINT }, line: { color: o.fill || TINT },
      });
      placed.forEach((p) => {
        slide.addText(p.it.text, {
          x: x + CARD_PAD, y: y + p.dy, w: innerW, h: p.h,
          fontSize: p.size, bold: !!p.it.bold, italic: !!p.it.italic,
          color: p.it.color || INK, fontFace: p.face, lineSpacing: p.lead,
          charSpacing: p.it.charSpacing,
          isTextBox: true, margin: 0, valign: "top",
        });
      });
      y += cardH + (o.after === undefined ? 0.2 : o.after);
      guard("card");
      return api;
    },

    image(file, h, o = {}) {
      slide.addImage({
        path: file, x, y, w, h,
        sizing: { type: "contain", w, h },
      });
      y += h + (o.after === undefined ? 0.16 : o.after);
      guard("image");
      return api;
    },

    chart(data, h, o = {}) {
      slide.addChart(o.type || pres.ChartType.bar, data, {
        x, y, w, h,
        barDir: "col", barGapWidthPct: 55,
        chartColors: o.colors,
        showLegend: false,
        catAxisLabelColor: MUTED, valAxisLabelColor: MUTED,
        catAxisLabelFontSize: MICRO, valAxisLabelFontSize: MICRO,
        catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY,
        valGridLine: { color: "E2EBEF", size: 1 },
        catGridLine: { style: "none" },
        showValue: true, dataLabelPosition: "outEnd",
        dataLabelFontSize: MICRO, dataLabelFontFace: BODY, dataLabelColor: INK,
        chartArea: { fill: { color: SURFACE } },
        plotArea: { fill: { color: SURFACE } },
        ...(o.extra || {}),
      });
      y += h + (o.after === undefined ? 0.16 : o.after);
      guard("chart");
      return api;
    },
  };
  return api;
}

// two cards side by side, levelled to the taller of the two
function cardPair(slide, y, leftItems, rightItems) {
  const probe = (c, n, items) => flow(slide, c, n, y).card(items, { measure: true });
  const h = Math.max(probe(0, 6, leftItems), probe(6, 6, rightItems));
  flow(slide, 0, 6, y).card(leftItems, { minH: h });
  flow(slide, 6, 6, y).card(rightItems, { minH: h });
}

// three stats side by side, each in its own narrow column
function statRow(slide, y, entries, onDark) {
  const each = 4;
  entries.forEach((e, i) => {
    flow(slide, i * each, each - (i === entries.length - 1 ? 0 : 1), y)
      .stat(e.value, e.label, {
        color: e.color,
        labelColor: onDark ? ON_DARK : MUTED,
        size: e.size || 36,
      });
  });
}

/* ── 1 · title ──────────────────────────────────────────────────────────── */
{
  const s = slideDark();
  const f = flow(s, 0, 10, 2.0);
  f.text("MODULE A7", { size: MICRO, bold: true, color: SUPPORT, charSpacing: 2, after: 0.12 });
  f.text("Water and Supplies", { size: DISPLAY, bold: true, color: SURFACE, face: HEAD, after: 0.12 });
  f.text("How much water a job takes, and how many jobs fit in the tank",
    { size: LEAD, color: SUPPORT, after: 1.3 });
  f.text("Naman Kumar   ·   Ranu Raj   ·   Vansh Rana   ·   Priyanshu   ·   Rudransh",
    { color: SURFACE, after: 0.1 });
  f.text("Doorstep · Track A · Service as a Service", { size: MICRO, color: ON_DARK });
  s.addNotes(
    "Naman opens, 20 seconds. Doorstep washes cars wherever the customer already is. The " +
    "van carries its own water, so the tank limits the day, not demand. Our module answers " +
    "two questions: how much water will this job take, and how many jobs fit before a refill."
  );
}

/* ── 2 · the problem ────────────────────────────────────────────────────── */
{
  const s = slideDark("The constraint", "Run out at job six and the rest of the day is cancelled");
  flow(s, 0, 11).text("Capacity, not demand, is what bounds a crew's day.",
    { size: LEAD, color: ON_DARK });
  statRow(s, 4.05, [
    { value: "262 L", label: "average drawn per crew-day", color: SUPPORT },
    { value: "200–350 L", label: "tank capacity across the fleet", color: SUPPORT },
    { value: "61%", label: "of crew-days exceed the small van", color: ALERT },
  ], true);
  s.addNotes(
    "Naman. The three numbers do the work. Crews draw 262 litres a day, tanks hold 200 to " +
    "350, so on the small van six days in ten need a refill. That is the motivation: a " +
    "single jobs-per-tank number cannot describe this."
  );
}

/* ── 3 · the decoy ──────────────────────────────────────────────────────── */
{
  const s = slideLight("Finding 1", "The service tier tells you nothing");
  const L = flow(s, 0, SPLIT_L);
  L.text("All five slot types average 54.9–55.8 L. The variable that actually moves water " +
         "is an add-on hidden inside a pipe-separated item string.", { after: 0.22 });
  L.image(path.join(FIGS, "slot_vs_addon.png"), 2.9);

  const R = flow(s, SPLIT_L, SPLIT_R);
  R.card([
    { text: "interior_clean", size: LEAD, bold: true, color: BRAND, after: 0.2 },
    { text: "27.9% of jobs\n+18.0 L per job\nsold across every tier", leading: 30, after: 0.22 },
    { text: "Parsed from bookings.items — not a column of its own", size: MICRO, color: MUTED, after: 0.16 },
    { text: "Key off slot_type and you miss it entirely.", size: MICRO, color: MUTED, after: 0 },
  ]);
  footer(s, "39,302 completed jobs · bookings.items parsed for add-ons");
  s.addNotes(
    "Ranu presents. The point to land: we nearly missed the second-largest effect in the " +
    "data because it sat inside a delimited string rather than being exposed as a column. " +
    "Left chart flat, right chart not, same jobs. Likely question: how did you find it? By " +
    "exploding the items column and grouping — not from the correlation matrix."
  );
}

/* ── 4 · functional form ────────────────────────────────────────────────── */
{
  const s = slideLight("Finding 2", "Dirtiness multiplies, the add-on adds");
  flow(s, 0, SPLIT_L).image(path.join(FIGS, "functional_form.png"), 4.2);

  const R = flow(s, SPLIT_L, SPLIT_R);
  R.text("Dirtiness scales the vehicle-size base by identical factors:", { after: 0.18 });
  R.text("1.00 · 1.18 · 1.35 · 1.53", { size: ACCENT, bold: true, color: BRAND, face: HEAD, after: 0.28 });
  R.text("The interior add-on adds a flat +18 L, whatever the size or dirt.", { after: 0.3 });
  R.card([
    { text: "An additive model is the wrong shape — it needs the interaction.",
      bold: true, color: BRAND },
  ]);
  footer(s, "Exterior-only jobs · mean litres per cell");
  s.addNotes(
    "Ranu. Short slide. The curves are parallel in ratio, not in difference — that is what " +
    "multiplicative means, and the ratio table is how we saw it. Consequence in one line: " +
    "we add the interaction term."
  );
}

/* ── 5 · the constraint ─────────────────────────────────────────────────── */
{
  const s = slideLight("The design decision", "The best predictor arrives too late");
  flow(s, 0, 12).text(
    "dirtiness_level is recorded when the crew reaches the car. Nothing at booking time " +
    "predicts it — not rain, not temperature, not the customer's history.");

  cardPair(s, 3.15,
    [
      { text: "PLANNING MODEL", size: MICRO, bold: true, color: BRAND, charSpacing: 2, after: 0.18 },
      { text: "vehicle size + interior_clean", after: 0.22 },
      { text: "5.90 L", size: 36, bold: true, color: BRAND, face: HEAD, after: 0.12 },
      { text: "mean absolute error — routing, scheduling and quoting", size: MICRO, color: MUTED },
    ],
    [
      { text: "ON-SITE MODEL", size: MICRO, bold: true, color: SUPPORT, charSpacing: 2, after: 0.18 },
      { text: "adds dirtiness and its interaction", after: 0.22 },
      { text: "2.40 L", size: 36, bold: true, color: SUPPORT, face: HEAD, after: 0.12 },
      { text: "mean absolute error — once the crew has seen the car", size: MICRO, color: MUTED },
    ]);
  s.addNotes(
    "Vansh, and do not rush this — the whole module rests on it. Using dirtiness at booking " +
    "time would be leakage: the model benchmarks well and fails in deployment. So two models " +
    "on disjoint feature sets, with a test enforcing that planning features never include " +
    "dirtiness. Expect: why not predict dirtiness? We tried. It behaves as an independent " +
    "draw — uncorrelated with weather, flat across months, and the same customer varies more " +
    "than customers differ from each other."
  );
}

/* ── 6 · accuracy ───────────────────────────────────────────────────────── */
{
  const s = slideLight("Results", "Halved, then halved again");
  flow(s, 0, SPLIT_L).chart(
    [{
      name: "MAE (L)",
      labels: ["Global mean", "Vehicle-size mean", "Planning model", "On-site model"],
      values: [11.152, 8.922, 5.897, 2.397],
    }], 4.1,
    {
      colors: [MUTED, MUTED, BRAND, SUPPORT],
      extra: {
        dataLabelFormatCode: "0.00",
        valAxisTitle: "mean absolute error, litres", showValAxisTitle: true,
        valAxisTitleColor: MUTED, valAxisTitleFontSize: MICRO, valAxisTitleFontFace: BODY,
      },
    });

  const R = flow(s, SPLIT_L, SPLIT_R);
  R.text("Guessing the mean costs 11.15 L. Booking-time halves it; knowing the dirt " +
         "halves it again.", { after: 0.3 });
  R.card([
    { text: "Every figure is the mean of ten seeds.", bold: true, after: 0.18 },
    { text: "The on-site model is at the noise floor: within a cell, jobs scatter with " +
            "sd ≈ 3 L whatever we do.", size: MICRO, color: MUTED },
  ]);
  footer(s, "Held-out test split · mean of ten seeds · results/model_comparison.csv");
  s.addNotes(
    "Vansh. Name the baseline before the model — the rubric rewards that specifically. " +
    "Global mean 11.15 litres is what guessing gets you. Quote the spread: plus or minus " +
    "0.04 at planning, 0.014 on-site. Do not claim the on-site model could be improved; it " +
    "is at the irreducible noise floor."
  );
}

/* ── 7 · models tie ─────────────────────────────────────────────────────── */
{
  const s = slideLight("What did not work", "Three model families, one answer");
  const top = flow(s, 0, 12);
  top.text("Cell mean, linear with interaction, and gradient boosting differ by 0.001 L. " +
           "The seed-to-seed spread is 0.038 L.", { after: 0.26 });
  top.card([
    { text: "The noise between splits is about forty times the gap between models.",
      size: ACCENT, bold: true, color: BRAND, face: HEAD },
  ], { after: 0.3 });

  const y = top.y;
  flow(s, 0, 6, y).text(
    "From one split, the ranking would be an artefact of which rows landed in the test set.");
  flow(s, 6, 6, y).text(
    "We take the simplest family within 1% of the best — the cell mean — at both stages.");
  s.addNotes(
    "Vansh. The honesty slide, and the guidebook says explicitly that it scores. We are not " +
    "claiming a win; we are claiming we cannot tell the models apart, and we can only say " +
    "that because we ran ten seeds. Expect: why build the complex models? To establish the " +
    "simple one is sufficient. That is a result, not a failure."
  );
}

/* ── 8 · tank capacity ──────────────────────────────────────────────────── */
{
  const s = slideLight("Deliverable 1", "Mean arithmetic overstates the tank");
  flow(s, 0, SPLIT_L).chart(
    [
      { name: "Mean-based", labels: ["200 L van", "280 L van", "350 L van"], values: [3, 5, 6] },
      { name: "95% service level", labels: ["200 L van", "280 L van", "350 L van"], values: [2, 4, 5] },
    ], 4.1,
    {
      colors: [MUTED, BRAND],
      extra: {
        showLegend: true, legendPos: "b", legendFontSize: MICRO, legendFontFace: BODY,
        legendColor: MUTED,
        valAxisTitle: "jobs per tank", showValAxisTitle: true,
        valAxisTitleColor: MUTED, valAxisTitleFontSize: MICRO, valAxisTitleFontFace: BODY,
      },
    });

  const R = flow(s, SPLIT_L, SPLIT_R);
  R.text("Dividing capacity by the 55.7 L mean gives 3 / 5 / 6 jobs. Those loads fit:",
    { after: 0.22 });
  R.card([
    { text: "91%   53%   70%", size: ACCENT, bold: true, color: ALERT, face: HEAD, after: 0.1 },
    { text: "of the time — load the EV van for five and it runs dry every second day.",
      size: MICRO, color: MUTED, after: 0 },
  ], { after: 0.3 });
  R.text("A capacity figure without a service level is not a usable number.",
    { bold: true, color: BRAND });
  footer(s, "20,000 resampled crew-days · identical under all ten seeds · results/tank_capacity.csv");
  s.addNotes(
    "Priyanshu. One of the two required deliverables. The trap: 280 divided by 55.7 equals " +
    "five looks obviously right and is obviously wrong — it throws away the spread. We " +
    "resample 20,000 crew-days instead. Add that 2/4/5 is identical under all ten resampling " +
    "seeds, so it is a property of the distribution, not of one draw."
  );
}

/* ── 9 · refills ────────────────────────────────────────────────────────── */
{
  const s = slideLight("Deliverable 2", "One tank does not cover a working day");
  flow(s, 0, SPLIT_L).image(path.join(FIGS, "tank_feasibility.png"), 4.2);

  const R = flow(s, SPLIT_L, SPLIT_R);
  R.text("Mean refills needed per crew-day", { bold: true, after: 0.22 });
  R.card([
    { text: "0.88   ·   0.45   ·   0.26", size: ACCENT, bold: true, color: BRAND, face: HEAD, after: 0.08 },
    { text: "200 L        280 L        350 L", size: MICRO, color: MUTED },
  ], { after: 0.28 });
  R.text("A fifth of small-van days need two or more. For fleet sizing that is the " +
         "difference — not jobs per fill.", { color: BRAND, bold: true });
  footer(s, "8,342 crew-days · results/refill_planning.csv");
  s.addNotes(
    "Priyanshu. A single jobs-per-tank number hides the real constraint. We count refills by " +
    "walking each crew-day in arrival order and topping up before any job the remaining " +
    "water cannot cover. This is the number A12 needs for fleet sizing, and it is in " +
    "INTEGRATION.md."
  );
}

/* ── 10 · the surprise ──────────────────────────────────────────────────── */
{
  const s = slideLight("The surprise", "Optimising the plan made it fail more often");
  flow(s, 0, SPLIT_L).chart(
    [{
      name: "Crew-days that run dry (%)",
      labels: ["Booked order", "Greedy by value", "Exact knapsack", "Knapsack on interval"],
      values: [5.9, 8.1, 11.9, 0.0],
    }], 4.1,
    {
      colors: [MUTED, MUTED, ALERT, SUPPORT],
      extra: {
        dataLabelFormatCode: "0.0",
        valAxisTitle: "% of crew-days that run dry", showValAxisTitle: true,
        valAxisTitleColor: MUTED, valAxisTitleFontSize: MICRO, valAxisTitleFontFace: BODY,
      },
    });

  const R = flow(s, SPLIT_L, SPLIT_R);
  R.text("Exact knapsack captures 13 points more revenue than booked order — and doubles " +
         "the rate of running dry.", { after: 0.28 });
  R.card([
    { text: "Packing to the limit spends the slack that was absorbing prediction error.",
      bold: true, color: ALERT, after: 0.16 },
    { text: "Planning on the interval's upper bound removes it entirely, for about ten " +
            "points of throughput.", size: MICRO, color: MUTED },
  ]);
  footer(s, "200 L van · results/tank_plan.csv");
  s.addNotes(
    "Priyanshu — spend time here, it is the most interesting result we have. We expected a " +
    "better optimiser to be strictly better. It is not: the exact knapsack doubles the " +
    "failure rate against simply serving in booked order, because tight packing consumes the " +
    "slack that was quietly absorbing prediction error. The fix is to feed the optimiser the " +
    "interval instead of the point estimate. If asked whether this is known: yes, Elmachtoub " +
    "and Grigas, Smart Predict-then-Optimize — though their uncertainty sits in the objective " +
    "and ours is in the constraint. Also note greedy reaches 99% of the exact solution, so we " +
    "built the knapsack mainly to prove greedy was enough."
  );
}

/* ── 11 · sustainability ────────────────────────────────────────────────── */
{
  const s = slideLight("Sustainability", "The green claim, stated honestly");
  flow(s, 0, 12).text(
    "Doorstep uses 55.7 L per job, all of it freshwater — a van cannot reclaim.");

  cardPair(s, 3.05,
    [
    { text: "WHAT WE CAN CLAIM", size: MICRO, bold: true, color: SUPPORT, charSpacing: 2, after: 0.22 },
    { text: "25% of a home hose left running\n22% of an unreclaimed conveyor\n49% of the " + "measured conveyor fleet\nLevel with a self-service bay", leading: 32 },
    ],
    [
    { text: "WHAT WE CANNOT", size: MICRO, bold: true, color: ALERT, charSpacing: 2, after: 0.16 },
    { text: "189%", size: 36, bold: true, color: ALERT, face: HEAD, after: 0.12 },
    { text: "of a reclaim-equipped tunnel. It uses about half what we do per car, and the " + "gap is structural — reclaim needs captured runoff, which a driveway cannot give." },
    ]);
  footer(s, "EPA WaterSense 2012 · International Carwash Association 2018 · Zaneti et al. 2013");
  s.addNotes(
    "Rudransh. Every figure is cited — EPA WaterSense, the International Carwash " +
    "Association, and Zaneti et al., who audited a reclamation plant needing under 40 litres " +
    "of fresh water per wash. That corroborates our result from outside our own data. The " +
    "right-hand card is what earns marks: we are telling the examiner where our own product " +
    "loses. INTEGRATION.md records what other teams may and may not claim on our behalf."
  );
}

/* ── 12 · conclusions ───────────────────────────────────────────────────── */
{
  const s = slideDark("What we would tell the company", "Three recommendations");
  const points = [
    ["Quote capacity with a service level", "2 / 4 / 5 jobs at 95% — never a bare number"],
    ["Plan on refills, not jobs per tank", "0.88 / 0.45 / 0.26 interruptions per crew-day"],
    ["Feed the optimiser the interval", "the point estimate doubles the rate of running dry"],
  ];
  let y = 2.45;
  points.forEach(([head, sub], i) => {
    flow(s, 0, 1, y).text(String(i + 1), { size: ACCENT, bold: true, color: SUPPORT, face: HEAD });
    const f = flow(s, 1, 11, y);
    f.text(head, { size: LEAD, bold: true, color: SURFACE, after: 0.06 });
    f.text(sub, { size: MICRO, color: ON_DARK });
    y += 1.25;
  });
  flow(s, 0, 12, 6.25).text(
    "Biggest open gap: if A14's photo check can grade dirt at booking, our planning error " +
    "halves — from 5.90 L to 2.40 L.",
    { size: MICRO, color: SUPPORT, italic: true, after: 0 });
  s.addNotes(
    "Naman closes. Three recommendations, then the open gap — a good note to end on because " +
    "it points at another team and shows we understand the system. Then questions. Reminder " +
    "for all five: everyone is asked individually, so know the file you own line by line and " +
    "roughly what the others built."
  );
}

pres.writeFile({ fileName: path.join(__dirname, "A7_slides.pptx") })
  .then((f) => console.log("wrote", f));
