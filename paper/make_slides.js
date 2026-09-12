// Builds paper/A7_slides.pptx.
//   npm install pptxgenjs && node paper/make_slides.js
// Every figure here comes from results/; regenerate those with `python src/train.py`.

const pptxgen = require("pptxgenjs");
const path = require("path");

const INK = "0B2B3A";
const DEEP = "065A82";
const SEA = "00A896";
const WARN = "D9532B";
const WHITE = "FFFFFF";
const MUTED = "5A6B73";
const PALE = "EAF2F5";

const HEAD = "Cambria";
const BODY = "Calibri";
const PLOTS = path.join(__dirname, "..", "results", "plots");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "A7 Water and Supplies";
pres.title = "A7 — Water and Supplies";

const W = 13.3;
const M = 0.7;

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}

function lightSlide(title, kicker) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: M, y: 0.42, w: W - 2 * M, h: 0.3,
      fontSize: 18, bold: true, color: SEA, fontFace: BODY,
      charSpacing: 1.5, isTextBox: true, margin: 0,
    });
  }
  s.addText(title, {
    x: M, y: kicker ? 0.78 : 0.6, w: W - 2 * M, h: 0.95,
    fontSize: 38, bold: true, color: INK, fontFace: HEAD,
    isTextBox: true, margin: 0,
  });
  return s;
}

function statBlock(slide, x, y, w, value, label, color) {
  slide.addText(value, {
    x, y, w, h: 1.0,
    fontSize: 60, bold: true, color, fontFace: HEAD,
    isTextBox: true, margin: 0,
  });
  slide.addText(label, {
    x, y: y + 1.02, w, h: 0.85,
    fontSize: 18, color: MUTED, fontFace: BODY,
    isTextBox: true, margin: 0,
  });
}

function card(slide, x, y, w, h) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: PALE }, line: { color: PALE },
  });
}

const chartFrame = {
  showLegend: false,
  catAxisLabelColor: MUTED, valAxisLabelColor: MUTED,
  catAxisLabelFontSize: 14, valAxisLabelFontSize: 14,
  catAxisLabelFontFace: BODY, valAxisLabelFontFace: BODY,
  valGridLine: { color: "DDE6EA", size: 1 },
  catGridLine: { style: "none" },
  showValue: true, dataLabelPosition: "outEnd",
  dataLabelFontSize: 14, dataLabelFontFace: BODY, dataLabelColor: INK,
};

/* 1 — title ------------------------------------------------------------- */
{
  const s = darkSlide();
  s.addText("Water and Supplies", {
    x: M, y: 2.15, w: W - 2 * M, h: 1.1,
    fontSize: 54, bold: true, color: WHITE, fontFace: HEAD,
    isTextBox: true, margin: 0,
  });
  s.addText("How much water a job takes, and how many jobs fit in the tank", {
    x: M, y: 3.3, w: W - 2 * M - 1.5, h: 0.6,
    fontSize: 22, color: SEA, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addText("Module A7  ·  Doorstep, Track A", {
    x: M, y: 4.35, w: 6, h: 0.4,
    fontSize: 18, color: "9FB6C0", fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addText("Naman Kumar  ·  Ranu Raj  ·  Vansh Rana  ·  Priyanshu  ·  Rudransh", {
    x: M, y: 4.8, w: W - 2 * M, h: 0.4,
    fontSize: 18, color: WHITE, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addNotes(
    "Naman opens. One sentence: Doorstep washes cars at the customer, the van carries its own " +
    "water, so the tank is what limits the day. Our module answers two questions - how much " +
    "water will this job take, and how many jobs fit before a refill. Keep this to 20 seconds."
  );
}

/* 2 — the problem ------------------------------------------------------- */
{
  const s = darkSlide();
  s.addText("The van carries its own water", {
    x: M, y: 1.0, w: W - 2 * M, h: 0.9,
    fontSize: 40, bold: true, color: WHITE, fontFace: HEAD,
    isTextBox: true, margin: 0,
  });
  s.addText(
    "Run out at job six and the rest of the day is cancelled.\n" +
    "Capacity, not demand, is what bounds a crew's day.",
    {
      x: M, y: 2.05, w: 7.2, h: 1.4,
      fontSize: 22, color: "CFE2E9", fontFace: BODY, lineSpacing: 32,
      isTextBox: true, margin: 0,
    }
  );
  statBlock(s, M, 3.8, 3.4, "262 L", "average water drawn per crew-day", SEA);
  statBlock(s, M + 4.2, 3.8, 3.4, "200–350 L", "tank capacity across the fleet", SEA);
  statBlock(s, M + 8.4, 3.8, 3.6, "61%", "of crew-days exceed the small van", WARN);
  s.addNotes(
    "Naman. The framing slide. The three numbers do the work: crews draw 262 litres a day, " +
    "tanks hold 200 to 350, so on the small van six days in ten need a refill. That is the " +
    "whole motivation - a single jobs-per-tank number cannot describe this."
  );
}

/* 3 — the decoy --------------------------------------------------------- */
{
  const s = lightSlide("The service tier tells you nothing", "Finding 1");
  s.addText(
    "All five slot types average 54.9–55.8 L. The real driver is an add-on " +
    "hidden inside a pipe-separated item string.",
    {
      x: M, y: 1.85, w: 5.4, h: 1.5,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 28,
      isTextBox: true, margin: 0,
    }
  );
  card(s, M, 3.5, 5.4, 2.3);
  s.addText("interior_clean", {
    x: M + 0.3, y: 3.7, w: 4.8, h: 0.4,
    fontSize: 20, bold: true, color: DEEP, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addText(
    "27.9% of jobs  ·  +18.0 L  ·  sold across every tier\n" +
    "Parsed from bookings.items, not a column of its own",
    {
      x: M + 0.3, y: 4.2, w: 4.8, h: 1.3,
      fontSize: 18, color: INK, fontFace: BODY, lineSpacing: 26,
      isTextBox: true, margin: 0,
    }
  );
  s.addImage({ path: path.join(PLOTS, "02_slot_type_vs_addon.png"), x: 6.5, y: 1.8, w: 6.1, h: 4.1 });
  s.addNotes(
    "Ranu presents this one. The point to land: we nearly missed the second-largest effect in " +
    "the data because it was inside a delimited string rather than exposed as a column. " +
    "Left chart is flat, right chart is not, same jobs. If asked why it matters: a consumer " +
    "keying off slot_type gets nothing."
  );
}

/* 4 — functional form --------------------------------------------------- */
{
  const s = lightSlide("Dirtiness multiplies, the add-on adds", "Finding 2");
  s.addImage({ path: path.join(PLOTS, "03_functional_form.png"), x: M, y: 1.85, w: 6.4, h: 4.2 });
  s.addText(
    "Dirtiness scales a vehicle-size base by the same factors for every size:",
    {
      x: 7.5, y: 1.95, w: 5.1, h: 0.8,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 26,
      isTextBox: true, margin: 0,
    }
  );
  s.addText("1.00   ·   1.18   ·   1.35   ·   1.53", {
    x: 7.5, y: 2.85, w: 5.1, h: 0.6,
    fontSize: 26, bold: true, color: DEEP, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "The interior add-on contributes a flat +18 L regardless of size or dirtiness.\n\n" +
    "So a purely additive linear model is mis-specified — it needs a size × dirtiness " +
    "interaction.",
    {
      x: 7.5, y: 3.7, w: 5.1, h: 2.3,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 28,
      isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Ranu. Short slide. The curves are parallel in ratio, not in difference - that is what " +
    "multiplicative means. Consequence in one line: additive model is the wrong shape, so we " +
    "add the interaction term. Expect a viva question on how you spotted it: the ratio table, " +
    "not the correlation matrix."
  );
}

/* 5 — the constraint ---------------------------------------------------- */
{
  const s = lightSlide("The best predictor arrives too late", "The constraint");
  s.addText(
    "dirtiness_level is recorded when the crew reaches the car. Nothing at booking " +
    "time predicts it — not rain, not temperature, not the customer's history.",
    {
      x: M, y: 1.9, w: 11.9, h: 1.0,
      fontSize: 20, color: INK, fontFace: BODY, lineSpacing: 28,
      isTextBox: true, margin: 0,
    }
  );
  card(s, M, 3.1, 5.7, 2.9);
  s.addText("PLANNING MODEL", {
    x: M + 0.35, y: 3.35, w: 5.0, h: 0.35,
    fontSize: 18, bold: true, color: DEEP, fontFace: BODY, charSpacing: 1.2,
    isTextBox: true, margin: 0,
  });
  s.addText("vehicle size + interior_clean", {
    x: M + 0.35, y: 3.78, w: 5.0, h: 0.4,
    fontSize: 19, color: INK, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addText("5.90 L", {
    x: M + 0.35, y: 4.3, w: 5.0, h: 0.8,
    fontSize: 44, bold: true, color: DEEP, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText("mean absolute error — used for routing and quoting", {
    x: M + 0.35, y: 5.15, w: 5.0, h: 0.7,
    fontSize: 17, color: MUTED, fontFace: BODY, isTextBox: true, margin: 0,
  });

  card(s, 7.0, 3.1, 5.6, 2.9);
  s.addText("ON-SITE MODEL", {
    x: 7.35, y: 3.35, w: 4.9, h: 0.35,
    fontSize: 18, bold: true, color: SEA, fontFace: BODY, charSpacing: 1.2,
    isTextBox: true, margin: 0,
  });
  s.addText("adds dirtiness and its interaction", {
    x: 7.35, y: 3.78, w: 4.9, h: 0.4,
    fontSize: 19, color: INK, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addText("2.40 L", {
    x: 7.35, y: 4.3, w: 4.9, h: 0.8,
    fontSize: 44, bold: true, color: SEA, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText("mean absolute error — used once the crew arrives", {
    x: 7.35, y: 5.15, w: 4.9, h: 0.7,
    fontSize: 17, color: MUTED, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addNotes(
    "Vansh. This is the design decision the whole module rests on, so do not rush it. " +
    "Using dirtiness at booking time would be leakage - the model would benchmark well and " +
    "fail in deployment. Two models on disjoint feature sets, and a test in tests/ enforces " +
    "that planning features never include dirtiness. Likely viva question: why not just " +
    "predict dirtiness? Answer: we tried, it is an independent draw - uncorrelated with " +
    "weather, flat across months, and the same customer varies more than customers differ."
  );
}

/* 6 — accuracy ---------------------------------------------------------- */
{
  const s = lightSlide("Against a baseline, over ten seeds", "Results");
  s.addChart(
    pres.ChartType.bar,
    [{
      name: "MAE (L)",
      labels: ["Global mean\n(baseline)", "Vehicle-size\nmean", "Planning\nmodel", "On-site\nmodel"],
      values: [11.152, 8.922, 5.897, 2.397],
    }],
    {
      x: M, y: 1.9, w: 7.3, h: 4.2,
      barDir: "col",
      chartColors: [MUTED, MUTED, DEEP, SEA],
      ...chartFrame,
      valAxisTitle: "mean absolute error, litres",
      showValAxisTitle: true,
      valAxisTitleColor: MUTED, valAxisTitleFontSize: 14, valAxisTitleFontFace: BODY,
    }
  );
  s.addText(
    "Every number is the mean of ten seeds, each reshuffling the split.\n\n" +
    "The on-site model sits at the noise floor — within an exact feature cell, jobs " +
    "scatter with sd ≈ 3 L no matter what we do.",
    {
      x: 8.4, y: 2.1, w: 4.2, h: 3.0,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 28,
      isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Vansh. Name the baseline before the model - that is what the rubric rewards. Global mean " +
    "11.15 litres is what you get by guessing. Planning halves it, on-site halves it again. " +
    "Mention the spread: plus or minus 0.04 at planning, 0.014 on-site. Do not claim the " +
    "on-site model could be improved - it is at the irreducible noise floor."
  );
}

/* 7 — models tie -------------------------------------------------------- */
{
  const s = lightSlide("Three model families, one answer", "What did not work");
  s.addText(
    "Cell mean, linear with interaction, and gradient boosting differ by 0.001 L. " +
    "The seed-to-seed spread is 0.038 L.",
    {
      x: M, y: 1.9, w: 11.9, h: 0.9,
      fontSize: 20, color: INK, fontFace: BODY, lineSpacing: 28,
      isTextBox: true, margin: 0,
    }
  );
  card(s, M, 3.0, 11.9, 1.55);
  s.addText("The noise between splits is ~40× the gap between models.", {
    x: M + 0.4, y: 3.35, w: 11.1, h: 0.85,
    fontSize: 26, bold: true, color: DEEP, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "Reported from a single split, the ranking would be an artefact of which rows landed " +
    "in the test set. We select the simplest family within 1% of the best — the cell mean — " +
    "at both stages. Picking by raw argmin would have shipped gradient boosting for a " +
    "0.0003 L gain.",
    {
      x: M, y: 4.9, w: 11.9, h: 1.7,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 28,
      isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Vansh. This is the honesty slide and it scores well - the guidebook says so explicitly. " +
    "We are not claiming a win, we are claiming we cannot tell them apart, and we can only " +
    "say that because we ran ten seeds. Be ready for: so why build the complex models? " +
    "Answer: to establish the simple one is sufficient. That is a result, not a failure."
  );
}

/* 8 — tank capacity ----------------------------------------------------- */
{
  const s = lightSlide("Mean arithmetic overstates the tank", "Deliverable 1");
  s.addChart(
    pres.ChartType.bar,
    [
      { name: "Mean-based", labels: ["200 L van", "280 L van", "350 L van"], values: [3, 5, 6] },
      { name: "95% service level", labels: ["200 L van", "280 L van", "350 L van"], values: [2, 4, 5] },
    ],
    {
      x: M, y: 1.95, w: 7.1, h: 4.1,
      barDir: "col",
      chartColors: [MUTED, DEEP],
      ...chartFrame,
      showLegend: true, legendPos: "b", legendFontSize: 16, legendFontFace: BODY,
      valAxisTitle: "jobs per tank",
      showValAxisTitle: true,
      valAxisTitleColor: MUTED, valAxisTitleFontSize: 14, valAxisTitleFontFace: BODY,
    }
  );
  s.addText("Dividing capacity by the 55.7 L mean gives 3 / 5 / 6 jobs.\nThose loads actually fit:", {
    x: 8.2, y: 2.0, w: 4.4, h: 1.0,
    fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 26, isTextBox: true, margin: 0,
  });
  s.addText("91%   53%   70%", {
    x: 8.2, y: 3.1, w: 4.4, h: 0.7,
    fontSize: 30, bold: true, color: WARN, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "of the time. Load the EV van for five jobs and the crew runs dry roughly every " +
    "second day.\n\nA capacity figure without a service level is not a usable number.",
    {
      x: 8.2, y: 3.95, w: 4.4, h: 2.1,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 28, isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Priyanshu. One of the two required deliverables. The trap is that 280 divided by 55.7 " +
    "equals 5 looks obviously right and is obviously wrong - it throws away the spread. " +
    "We resample 20,000 crew-days instead. Add that the 2/4/5 figures are identical under " +
    "all ten resampling seeds, so this is a property of the distribution, not one draw."
  );
}

/* 9 — refills ----------------------------------------------------------- */
{
  const s = lightSlide("One tank does not cover a working day", "Deliverable 2");
  s.addImage({ path: path.join(PLOTS, "07_tank_feasibility.png"), x: M, y: 1.9, w: 6.3, h: 4.1 });
  s.addText("Mean refills needed per crew-day", {
    x: 7.4, y: 1.95, w: 5.2, h: 0.4,
    fontSize: 19, bold: true, color: INK, fontFace: BODY, isTextBox: true, margin: 0,
  });
  statBlock(s, 7.4, 2.5, 1.6, "0.88", "200 L van", WARN);
  statBlock(s, 9.2, 2.5, 1.6, "0.45", "280 L van", DEEP);
  statBlock(s, 11.0, 2.5, 1.6, "0.26", "350 L van", SEA);
  s.addText(
    "A fifth of small-van days need two or more refills. Refilling is normal operation, " +
    "not an exception.\n\nFor fleet planning the real difference between a 200 L and a " +
    "350 L van is not jobs per fill — it is 0.88 against 0.26 interruptions a day, each " +
    "costing travel to a water source.",
    {
      x: 7.4, y: 4.35, w: 5.2, h: 2.2,
      fontSize: 18, color: INK, fontFace: BODY, lineSpacing: 26, isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Priyanshu. The point: a single jobs-per-tank number hides the real constraint. We count " +
    "refills by walking each crew-day in arrival order and topping up before any job the " +
    "remaining water cannot cover. This is the number A12 actually needs for fleet sizing, " +
    "and it is in INTEGRATION.md."
  );
}

/* 10 — the optimiser ---------------------------------------------------- */
{
  const s = lightSlide("Optimising the plan made it fail more often", "The surprise");
  s.addChart(
    pres.ChartType.bar,
    [{
      name: "Crew-days that overflow the tank (%)",
      labels: ["Booked order", "Greedy by\nvalue density", "Exact\nknapsack", "Exact knapsack,\nplanned on interval"],
      values: [5.9, 8.1, 11.9, 0.0],
    }],
    {
      x: M, y: 1.95, w: 7.4, h: 4.1,
      barDir: "col",
      chartColors: [MUTED, MUTED, WARN, SEA],
      ...chartFrame,
      valAxisTitle: "% of crew-days that run dry",
      showValAxisTitle: true,
      valAxisTitleColor: MUTED, valAxisTitleFontSize: 14, valAxisTitleFontFace: BODY,
    }
  );
  s.addText(
    "Choosing jobs by exact knapsack captures 13 points more revenue than serving in " +
    "booked order — and doubles the rate of running dry.",
    {
      x: 8.5, y: 2.05, w: 4.1, h: 1.5,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 28, isTextBox: true, margin: 0,
    }
  );
  s.addText(
    "Packing a tank to its limit spends exactly the slack that was absorbing prediction " +
    "error. A loose plan is accidentally robust.\n\nPlanning against the interval's upper " +
    "bound removes overflow entirely, for about ten points of throughput.",
    {
      x: 8.5, y: 3.7, w: 4.1, h: 2.4,
      fontSize: 18, color: INK, fontFace: BODY, lineSpacing: 26, isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Priyanshu, and this is the slide to spend time on - it is the most interesting result " +
    "we have. We expected a better optimiser to be strictly better. It is not: the exact " +
    "knapsack doubles the failure rate against simply serving in booked order, because " +
    "tight packing consumes the slack that was quietly absorbing prediction error. " +
    "The fix is to feed the optimiser the interval instead of the point estimate. " +
    "If asked whether this is known: yes - Elmachtoub and Grigas, Smart Predict-then-Optimize, " +
    "though their uncertainty is in the objective and ours is in the constraint. " +
    "Also worth saying: the greedy rule reaches 99% of the exact solution, so we built the " +
    "knapsack mainly to prove greedy was enough."
  );
}

/* 11 — sustainability --------------------------------------------------- */
{
  const s = lightSlide("The green claim, stated honestly", "Sustainability");
  s.addText("Doorstep uses 55.7 L per job, all of it freshwater — a van cannot reclaim.", {
    x: M, y: 1.85, w: 11.9, h: 0.5,
    fontSize: 20, color: INK, fontFace: BODY, isTextBox: true, margin: 0,
  });
  card(s, M, 2.6, 5.8, 3.5);
  s.addText("WHAT WE CAN CLAIM", {
    x: M + 0.35, y: 2.85, w: 5.1, h: 0.35,
    fontSize: 18, bold: true, color: SEA, fontFace: BODY, charSpacing: 1.2, isTextBox: true, margin: 0,
  });
  s.addText(
    "25% of a home hose left running\n" +
    "22% of an unreclaimed conveyor\n" +
    "49% of the measured conveyor fleet\n" +
    "Level with a self-service bay",
    {
      x: M + 0.35, y: 3.35, w: 5.1, h: 2.4,
      fontSize: 19, color: INK, fontFace: BODY, lineSpacing: 32, isTextBox: true, margin: 0,
    }
  );
  card(s, 7.1, 2.6, 5.5, 3.5);
  s.addText("WHAT WE CANNOT", {
    x: 7.45, y: 2.85, w: 4.8, h: 0.35,
    fontSize: 18, bold: true, color: WARN, fontFace: BODY, charSpacing: 1.2, isTextBox: true, margin: 0,
  });
  s.addText("189%", {
    x: 7.45, y: 3.3, w: 4.8, h: 0.9,
    fontSize: 48, bold: true, color: WARN, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "of a reclaim-equipped tunnel. It uses about half what we do per car, and the gap is " +
    "structural — reclaim needs captured runoff, which a driveway cannot give.",
    {
      x: 7.45, y: 4.3, w: 4.8, h: 1.6,
      fontSize: 18, color: INK, fontFace: BODY, lineSpacing: 26, isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Rudransh. Every figure here is cited - EPA WaterSense, the International Carwash " +
    "Association, and Zaneti et al., who audited a reclamation plant needing under 40 litres " +
    "of fresh water per wash. That last one corroborates our result from outside our data. " +
    "The right-hand card is the one that earns marks: we are telling the examiner where our " +
    "own product loses. INTEGRATION.md records what other teams may and may not claim on our " +
    "behalf, so marketing cannot quote us as beating a modern tunnel."
  );
}

/* 12 — conclusions ------------------------------------------------------ */
{
  const s = darkSlide();
  s.addText("What we would tell the company", {
    x: M, y: 0.85, w: W - 2 * M, h: 0.85,
    fontSize: 40, bold: true, color: WHITE, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  const points = [
    ["Quote capacity with a service level", "2 / 4 / 5 jobs at 95%, never a bare number"],
    ["Plan on refills, not jobs per tank", "0.88 / 0.45 / 0.26 interruptions per crew-day"],
    ["Feed the optimiser the interval", "the point estimate doubles the rate of running dry"],
  ];
  points.forEach(([head, sub], i) => {
    const y = 2.0 + i * 1.35;
    s.addText(String(i + 1), {
      x: M, y, w: 0.6, h: 0.6,
      fontSize: 30, bold: true, color: SEA, fontFace: HEAD, isTextBox: true, margin: 0,
    });
    s.addText(head, {
      x: M + 0.75, y, w: 11.0, h: 0.45,
      fontSize: 24, bold: true, color: WHITE, fontFace: BODY, isTextBox: true, margin: 0,
    });
    s.addText(sub, {
      x: M + 0.75, y: y + 0.5, w: 11.0, h: 0.45,
      fontSize: 19, color: "9FB6C0", fontFace: BODY, isTextBox: true, margin: 0,
    });
  });
  s.addText(
    "Biggest open gap: if A14's photo check can grade dirt at booking, our planning error " +
    "halves — from 5.90 L to 2.40 L.",
    {
      x: M, y: 6.15, w: 11.9, h: 0.8,
      fontSize: 19, color: SEA, fontFace: BODY, italic: true, isTextBox: true, margin: 0,
    }
  );
  s.addNotes(
    "Naman closes. Three recommendations, then the open gap - which is a good note to end on " +
    "because it points at another team and shows we understand the system. " +
    "Then hand to questions. Reminder for all five: everyone is asked individually, so know " +
    "the file you own line by line, and roughly what the others built."
  );
}

pres.writeFile({ fileName: path.join(__dirname, "A7_slides.pptx") })
  .then((f) => console.log("wrote", f));
