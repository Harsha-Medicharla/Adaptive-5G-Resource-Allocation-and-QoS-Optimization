// build_deck.js  -  midsem deck (10 slides), dark technical theme
// Run: node build_deck.js   (expects ../results/figs_dark/*.png and bg_*.png here)
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/mnt/skills/public/pptx/scripts/apply_theme.js");

const FIG = "../results/figs_dark/";
const THEME = {
  name: "Slicing Dark",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B0F14", lt1: "E6EDF3", dk2: "121A24", lt2: "8B98A9",
    accent1: "22D3EE", accent2: "F5A524", accent3: "3987E5",
    accent4: "D95926", accent5: "199E70", accent6: "E66767",
    hlink: "22D3EE", folHlink: "F5A524",
  },
};
// hex copies for options that only take hex
const HX = { bg: "0B0F14", panel: "121A24", panel2: "18222F", line: "263241", text: "E6EDF3",
  muted: "8B98A9", cyan: "22D3EE", amber: "F5A524", embb: "3987E5", urllc: "D95926",
  mmtc: "199E70", red: "E66767" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Adaptive 5G Resource Allocation and QoS Optimization";
pres.author = "Sai Govardhan Rao Medikurthi, Avulakonda Siva Sai";
const C = pres.SchemeColor;
const MONO = "Courier New";

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "TITLE",
  background: { path: "bg_title.png" },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { path: "bg_grid.png" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.62, w: 12.1, h: 0.8,
        fontFace: THEME.headFontFace, fontSize: 32, bold: true, color: HX.text, valign: "top", align: "left", margin: 0 },
        text: "" } },
    { text: { text: "IT365  //  ADAPTIVE 5G SLICING  //  MIDSEM", options: { x: 0.6, y: 7.0, w: 7, h: 0.3,
        fontFace: MONO, fontSize: 9, color: HX.muted, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontFace: MONO, fontSize: 9, color: HX.muted, align: "right" },
});

// ------------------------------------------------------------------ helpers
function tag(slide, text, x = 0.6, y = 0.3) {
  slide.addText(text, { x, y, w: 6, h: 0.28, fontFace: MONO, fontSize: 11, color: HX.cyan, bold: true,
    margin: 0, isTextBox: true, objectName: "section-tag" });
}
function panel(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08,
    fill: { color: opts.fill || HX.panel }, line: { color: opts.line || HX.line, width: opts.lw || 1 },
    objectName: opts.name || "panel" });
}
// corner brackets: the deck's motif (scope-frame on key visuals)
function brackets(slide, x, y, w, h, color = HX.cyan) {
  const L = 0.22, t = 1.5;
  const segs = [[x, y, L, 0], [x, y, 0, L], [x + w - L, y, L, 0], [x + w, y, 0, L],
    [x, y + h, L, 0], [x, y + h - L, 0, L], [x + w - L, y + h, L, 0], [x + w, y + h - L, 0, L]];
  segs.forEach(([sx, sy, sw, sh]) => slide.addShape(pres.shapes.LINE,
    { x: sx, y: sy, w: sw, h: sh, line: { color, width: t }, objectName: "bracket" }));
}
function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.75, fontFace: THEME.headFontFace, fontSize: 40, bold: true,
    color, margin: 0, isTextBox: true });
  slide.addText(label, { x, y: y + 0.78, w, h: 0.62, fontSize: 13, color: HX.muted, margin: 0,
    valign: "top", isTextBox: true });
}
function chip(slide, x, y, text, color) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 1.25, h: 0.3, rectRadius: 0.15,
    fill: { color: HX.bg }, line: { color, width: 1 } });
  slide.addText(text, { x, y, w: 1.25, h: 0.3, fontFace: MONO, fontSize: 9.5, color, bold: true,
    align: "center", valign: "middle", margin: 0, isTextBox: true });
}

// ================================================================== 1. TITLE
pres.addSection({ title: "Introduction" });
let s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Introduction" });
s.addText("IT365 ADVANCED COMPUTER NETWORKS  //  MIDSEM REVIEW", { x: 0.7, y: 1.2, w: 9, h: 0.35,
  fontFace: MONO, fontSize: 12, color: HX.cyan, bold: true, margin: 0, isTextBox: true });
s.addText("Adaptive 5G Resource Allocation and QoS Optimization", { x: 0.7, y: 1.7, w: 8.6, h: 2.0,
  fontFace: THEME.headFontFace, fontSize: 38, bold: true, color: HX.text, margin: 0, valign: "top", isTextBox: true });
s.addText("Learning-driven adaptive network slicing for eMBB, URLLC and mMTC traffic", { x: 0.7, y: 3.3,
  w: 7.6, h: 0.8, fontSize: 20, color: HX.amber, margin: 0, valign: "top", isTextBox: true });
[["eMBB", HX.embb], ["URLLC", HX.urllc], ["mMTC", HX.mmtc]].forEach(([t, c], i) =>
  chip(s, 0.7 + i * 1.4, 4.35, t, c));
s.addText([
  { text: "Sai Govardhan Rao Medikurthi", options: { breakLine: true } },
  { text: "Avulakonda Siva Sai" }],
  { x: 0.7, y: 5.2, w: 6, h: 0.8, fontSize: 16, color: HX.text, margin: 0, valign: "top", isTextBox: true });
s.addText("ns-3  |  C++  |  Python", { x: 0.7, y: 6.1, w: 6, h: 0.3, fontFace: MONO, fontSize: 11,
  color: HX.muted, margin: 0, isTextBox: true });
s.addNotes("Introduce the project: we study whether learning-based allocation can beat a static split of shared 5G resources among three slices. Midsem covers the full simulation and the static baseline; the RL controller is designed but not yet trained.");

// ================================================================== 2. PROBLEM
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction" });
tag(s, "// 01  PROBLEM");
s.addText("One shared pool, three very different slices", { placeholder: "title" });
const slices = [
  ["eMBB", "Enhanced Mobile Broadband", "Needs high throughput", "Video streaming, AR/VR", HX.embb],
  ["URLLC", "Ultra-Reliable Low-Latency", "Needs low delay and reliability", "Industrial control, autonomous systems", HX.urllc],
  ["mMTC", "Massive Machine-Type", "Needs to serve many devices", "IoT sensors, smart city", HX.mmtc],
];
slices.forEach(([name, full, need, ex, col], i) => {
  const x = 0.6 + i * 4.1;
  panel(s, x, 1.75, 3.8, 2.75);
  s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 2.05, w: 0.42, h: 0.42, fill: { color: col }, line: { color: col } });
  s.addText(name, { x: x + 0.85, y: 2.0, w: 2.8, h: 0.5, fontFace: THEME.headFontFace, fontSize: 24,
    bold: true, color: HX.text, margin: 0, valign: "middle", isTextBox: true });
  s.addText(full, { x: x + 0.3, y: 2.65, w: 3.3, h: 0.35, fontSize: 13, color: HX.muted, margin: 0, isTextBox: true });
  s.addText(need, { x: x + 0.3, y: 3.1, w: 3.3, h: 0.45, fontSize: 17, bold: true, color: col, margin: 0, isTextBox: true });
  s.addText(ex, { x: x + 0.3, y: 3.6, w: 3.3, h: 0.7, fontSize: 14, color: HX.text, margin: 0, valign: "top", isTextBox: true });
});
panel(s, 0.6, 4.85, 12.1, 1.75, { fill: HX.panel2, line: HX.amber });
s.addText("THE PROBLEM", { x: 0.95, y: 5.05, w: 3, h: 0.3, fontFace: MONO, fontSize: 11, bold: true,
  color: HX.amber, margin: 0, isTextBox: true });
s.addText("A fixed split such as 50 / 30 / 20 works while traffic is steady. When one slice bursts, its packets queue and drop, even while another slice's share sits idle. Can an adaptive controller move resources to where the traffic is?",
  { x: 0.95, y: 5.4, w: 11.4, h: 1.05, fontSize: 17, color: HX.text, margin: 0, valign: "top", isTextBox: true });
s.addNotes("Three service types with different needs share one pool. The static split is the industry-simple baseline; the question is whether adapting it helps.");

// ================================================================== 3. PLAN
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction" });
tag(s, "// 02  APPROACH");
s.addText("Two phases on one simulation", { placeholder: "title" });
const cols = [
  ["PHASE 1  //  MIDSEM", "Built and measured", HX.cyan, "DONE", [
    "ns-3 topology: 3 eMBB UEs, 3 URLLC UEs, up to 60 mMTC devices",
    "Enforced per-slice resource share, changeable at run time",
    "Five-phase dynamic traffic scenario",
    "Per-100 ms QoS measurement, 5 random seeds",
    "Static 50/30/20 baseline results and graphs"]],
  ["PHASE 2  //  POST-MIDSEM", "Designed, not yet built", HX.amber, "NEXT", [
    "ns3-ai link between ns-3 and Python",
    "DQN agent picks the allocation every 1 s",
    "Multi-objective reward, URLLC weighted highest",
    "Compare Static vs Random vs DQN on 5 experiments",
    "Streamlit dashboard; optional demand forecasting"]],
];
cols.forEach(([head, sub, col, st, items], i) => {
  const x = 0.6 + i * 6.15;
  panel(s, x, 1.75, 5.95, 4.85, { line: col });
  s.addText(head, { x: x + 0.35, y: 2.0, w: 4, h: 0.32, fontFace: MONO, fontSize: 13, bold: true, color: col, margin: 0, isTextBox: true });
  chip(s, x + 4.4, 2.0, st, col);
  s.addText(sub, { x: x + 0.35, y: 2.42, w: 5.2, h: 0.4, fontSize: 18, bold: true, color: HX.text, margin: 0, isTextBox: true });
  s.addText(items.map((t, k) => ({ text: t, options: { bullet: { code: "25A0" }, breakLine: k < items.length - 1 } })),
    { x: x + 0.35, y: 3.05, w: 5.3, h: 3.4, fontSize: 17, color: HX.text, margin: 0, valign: "top",
      paraSpaceAfter: 14, isTextBox: true });
});
s.addNotes("Phase 2 extends the same code: the RL action is a call to the ApplyAllocation function that already exists in the simulation.");

// ================================================================== 4. TOPOLOGY
pres.addSection({ title: "Methodology" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
tag(s, "// 03  METHODOLOGY: NETWORK MODEL");
s.addText("Slices as rate pipes in ns-3", { placeholder: "title" });
s.addImage({ path: FIG + "arch_topology.png", x: 0.6, y: 1.85, w: 8.1, h: 3.71, objectName: "topology diagram" });
brackets(s, 0.5, 1.75, 8.3, 3.91);
const facts = [
  ["100 units = 20 Mbps", "1 unit = 0.2 Mbps. A documented abstraction, not physical PRBs."],
  ["Hard isolation", "Each slice gets its own pipe; idle capacity cannot be borrowed."],
  ["Explicit FIFO, 100 packets", "Default FqCoDel removed so the allocation is what we measure."],
  ["ApplyAllocation(units)", "Sets pipe rates at run time: the future RL action."],
];
facts.forEach(([h, b], i) => {
  const y = 1.75 + i * 1.22;
  s.addText(h, { x: 9.15, y, w: 3.6, h: 0.38, fontSize: 16, bold: true, color: i === 3 ? HX.amber : HX.cyan,
    fontFace: i === 3 ? MONO : THEME.bodyFontFace, margin: 0, isTextBox: true });
  s.addText(b, { x: 9.15, y: y + 0.4, w: 3.6, h: 0.72, fontSize: 13, color: HX.text, margin: 0, valign: "top", isTextBox: true });
});
s.addText("Modules: point-to-point, internet, traffic-control, applications.   Links: access 100 Mbps / 0.1 ms, slice pipe 1 ms.   Uplink, UDP.",
  { x: 0.6, y: 5.95, w: 12.1, h: 0.6, fontSize: 13, color: HX.muted, margin: 0, isTextBox: true });
s.addNotes("We chose a rate abstraction over 5G-LENA because the allocation question does not need PHY/MAC detail and RL needs fast steps. The FIFO was installed explicitly; otherwise ns-3 silently uses a fair queue which redistributes capacity.");

// ================================================================== 5. TRAFFIC + BASELINE
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
tag(s, "// 04  METHODOLOGY: TRAFFIC AND BASELINE");
s.addText("Five phases that push each slice past its share", { placeholder: "title" });
const hdr = (t) => ({ text: t, options: { bold: true, color: HX.cyan, fill: { color: HX.panel2 }, fontFace: MONO, fontSize: 12 } });
const cell = (t, over) => ({ text: t, options: { color: over ? HX.amber : HX.text, bold: !!over, fontSize: 14 } });
const rows = [
  [hdr("PHASE"), hdr("TIME"), hdr("eMBB (Mbps)"), hdr("URLLC (Mbps)"), hdr("mMTC (devices)")],
  [cell("P1 Normal"), cell("0-10 s"), cell("6"), cell("2"), cell("30")],
  [cell("P2 eMBB burst"), cell("10-20 s"), cell("14", 1), cell("2"), cell("30")],
  [cell("P3 eMBB + URLLC high"), cell("20-30 s"), cell("14", 1), cell("5 (96% load)", 1), cell("30")],
  [cell("P4 URLLC very high"), cell("30-40 s"), cell("6"), cell("9", 1), cell("15")],
  [cell("P5 mMTC surge"), cell("40-50 s"), cell("9"), cell("2"), cell("60", 1)],
  [{ text: "Static share", options: { bold: true, color: HX.muted, fontSize: 13 } }, cell(""),
   { text: "50 u = 10", options: { color: HX.embb, bold: true, fontSize: 14 } },
   { text: "30 u = 6", options: { color: HX.urllc, bold: true, fontSize: 14 } },
   { text: "20 u = 4 Mbps", options: { color: HX.mmtc, bold: true, fontSize: 14 } }],
];
s.addTable(rows, { x: 0.6, y: 1.8, w: 7.9, colW: [2.35, 1.1, 1.35, 1.6, 1.5], rowH: 0.52,
  fill: { color: HX.panel }, border: { type: "solid", pt: 0.75, color: HX.line }, fontFace: THEME.bodyFontFace,
  valign: "middle", margin: [0, 0.1, 0, 0.1] });
s.addText("Amber = offered load above the slice's fixed share (wire rate incl. 30 B headers)",
  { x: 0.6, y: 5.6, w: 7.9, h: 0.3, fontSize: 11, color: HX.muted, margin: 0, italic: true, isTextBox: true });
panel(s, 8.9, 1.8, 3.8, 4.8);
const tm = [["eMBB", "CBR, 1200 B packets", HX.embb], ["URLLC", "Poisson, 200 B packets", HX.urllc],
  ["mMTC", "Poisson, 64 B, 100 pkt/s per device", HX.mmtc]];
s.addText("TRAFFIC MODELS", { x: 9.2, y: 2.0, w: 3.3, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: HX.cyan, margin: 0, isTextBox: true });
tm.forEach(([n, d, c], i) => {
  s.addText([{ text: n + "  ", options: { bold: true, color: c } }, { text: d, options: { color: HX.text } }],
    { x: 9.2, y: 2.4 + i * 0.55, w: 3.3, h: 0.5, fontSize: 13, margin: 0, valign: "top", isTextBox: true });
});
s.addText("METRICS (EVERY 100 ms)", { x: 9.2, y: 4.2, w: 3.3, h: 0.3, fontFace: MONO, fontSize: 11, bold: true, color: HX.cyan, margin: 0, isTextBox: true });
s.addText("Throughput, mean and p95 delay, loss, URLLC delay > 10 ms, served mMTC devices (PDR >= 90%), utilisation",
  { x: 9.2, y: 4.55, w: 3.3, h: 1.6, fontSize: 13, color: HX.text, margin: 0, valign: "top", isTextBox: true });
s.addNotes("The 10 ms URLLC budget is a simulation choice: links alone add about 1.1 ms, so the 3GPP 1 ms radio target cannot apply end to end. Every result is the mean of 5 seeds.");

// ================================================================== 6. RL DESIGN
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methodology" });
tag(s, "// 05  METHODOLOGY: ADAPTIVE CONTROLLER (POST-MIDSEM)");
s.addText("DQN closes the loop every second", { placeholder: "title" });
s.addImage({ path: FIG + "arch_system.png", x: 0.6, y: 1.8, w: 7.3, h: 3.96, objectName: "system architecture" });
brackets(s, 0.5, 1.7, 7.5, 4.16);
const rl = [
  ["STATE (10)", "Offered load x3, allocation x3, eMBB delivered ratio, URLLC p95 / budget, URLLC loss, mMTC served fraction"],
  ["ACTION (36)", "Every split in 10-unit steps, each slice >= 10. Results show URLLC needs > 52 units in P4"],
  ["REWARD", "+ throughput  - URLLC violations (x5)  - loss  + mMTC served  + utilisation  + fairness  - switching"],
  ["DQN", "MLP 64-64, replay 20k, target net, e-greedy, 300-500 randomised episodes"],
];
rl.forEach(([h, b], i) => {
  const y = 1.75 + i * 1.18;
  s.addText(h, { x: 8.35, y, w: 4.4, h: 0.3, fontFace: MONO, fontSize: 12, bold: true, color: HX.amber, margin: 0, isTextBox: true });
  s.addText(b, { x: 8.35, y: y + 0.32, w: 4.4, h: 0.8, fontSize: 13, color: HX.text, margin: 0, valign: "top", isTextBox: true });
});
s.addText("Compared on identical scenarios: Static  vs  Random  vs  DQN  (+ demand-proportional heuristic)",
  { x: 0.6, y: 6.15, w: 12.1, h: 0.4, fontSize: 14, color: HX.cyan, margin: 0, isTextBox: true });
s.addNotes("This is the design only; no RL results are claimed. Note the action set: the proposal's 5 actions cap URLLC at 50 units, but the measured P4 load needs at least 52, so we use 36 actions. Reward weights start at (1,5,2,1,0.5,0.5,0.1) and will be justified with a sweep.");

// ================================================================== 7. RESULT: OVERFLOW
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
tag(s, "// 06  RESULTS: STATIC 50/30/20");
s.addText("Every burst overflows its fixed share", { placeholder: "title" });
s.addImage({ path: FIG + "fig1_demand_vs_capacity.png", x: 0.6, y: 1.75, w: 7.5, h: 4.93, objectName: "demand vs capacity" });
brackets(s, 0.5, 1.65, 7.7, 5.13);
stat(s, 8.6, 1.8, 4.1, "~30%", "eMBB packets lost in P2 and P3 (delay 2.5 to 99 ms)", HX.embb);
stat(s, 8.6, 3.4, 4.1, "41.8%", "URLLC packets lost in P4 (10.35 Mbps into a 6 Mbps share)", HX.urllc);
stat(s, 8.6, 5.0, 4.1, "32.5 / 60", "mMTC devices served in the P5 surge (loss 11%)", HX.mmtc);
s.addNotes("Shaded red is traffic dropped because offered load exceeds the fixed share. All numbers are 5-seed means.");

// ================================================================== 8. RESULT: URLLC LATENCY
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
tag(s, "// 07  RESULTS: URLLC LATENCY");
s.addText("URLLC misses its delay budget, even below capacity", { placeholder: "title" });
s.addImage({ path: FIG + "fig3_urllc_latency.png", x: 0.6, y: 1.8, w: 8.2, h: 3.51, objectName: "URLLC latency" });
brackets(s, 0.5, 1.7, 8.4, 3.71);
stat(s, 9.3, 1.8, 3.4, "99.9%", "URLLC packets over 10 ms in P4 (32 ms delay)", HX.urllc);
stat(s, 9.3, 3.5, 3.4, "9.5%", "over budget in P3 at 96% load, with zero loss", HX.amber);
panel(s, 0.6, 5.65, 12.1, 0.95, { fill: HX.panel2 });
s.addText([
  { text: "MODEL CHECK  ", options: { fontFace: MONO, bold: true, color: HX.cyan } },
  { text: "M/D/1 predicts 4.95 ms URLLC delay in P3, measured 4.92 ms. Full-buffer delay B x S / C predicts 30.7 ms, measured 32.1 ms.", options: { color: HX.text } }],
  { x: 0.9, y: 5.7, w: 11.6, h: 0.85, fontSize: 14, margin: 0, valign: "middle", isTextBox: true });
s.addNotes("P3 shows that a slice can break its latency target while still under capacity: near 100% utilisation the Poisson queue grows. So the controller must keep URLLC load well below its share. The queueing-theory match validates the simulation.");

// ================================================================== 9. RESULT: STRANDED CAPACITY (native chart)
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
tag(s, "// 08  RESULTS: WHY ADAPT");
s.addText("Capacity sits idle while other slices drop traffic", { placeholder: "title" });
s.addChart(pres.charts.BAR, [
  { name: "Idle allocated capacity", labels: ["P1 Normal", "P2 eMBB burst", "P3 eMBB+URLLC", "P4 URLLC v.high", "P5 mMTC surge"], values: [9.31, 5.43, 1.99, 6.63, 4.45] },
  { name: "Dropped demand", labels: ["P1 Normal", "P2 eMBB burst", "P3 eMBB+URLLC", "P4 URLLC v.high", "P5 mMTC surge"], values: [0.03, 4.36, 4.36, 4.35, 0.51] },
], { x: 0.6, y: 1.75, w: 7.9, h: 4.85, barDir: "col", barGapWidthPct: 60, chartColors: [HX.muted, HX.red],
  showLegend: true, legendPos: "t", legendColor: HX.text, legendFontSize: 12, legendFontFace: "+mn-lt",
  showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HX.text, dataLabelFontSize: 11, dataLabelFormatCode: "0.0", dataLabelFontFace: "+mn-lt",
  catAxisLabelColor: HX.muted, valAxisLabelColor: HX.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  valGridLine: { color: HX.line, size: 0.5 }, catGridLine: { style: "none" },
  showValAxisTitle: true, valAxisTitle: "Mbps (wire)", valAxisTitleColor: HX.muted, valAxisTitleFontSize: 11, valAxisTitleFontFace: "+mn-lt",
  valAxisMaxVal: 10, objectName: "idle vs dropped chart" });
stat(s, 9.0, 1.8, 3.7, "27.8%", "of the 20 Mbps pool idle on average (utilisation 72.2%)", HX.cyan);
stat(s, 9.0, 3.4, 3.7, "3 of 5", "phases where idle capacity exceeds dropped demand: re-splitting could avoid the loss", HX.amber);
s.addText("P3 is true overload (22.4 Mbps offered): an allocator can only choose which slice absorbs the loss, and should protect URLLC.",
  { x: 9.0, y: 5.05, w: 3.7, h: 1.4, fontSize: 13, color: HX.text, margin: 0, valign: "top", isTextBox: true });
s.addNotes("This is the core motivation. In P2, P4 and P5 the same total capacity, split differently, would have carried all traffic. That gap is what the DQN controller will try to close.");

// ================================================================== 10. CONCLUSION
pres.addSection({ title: "Conclusion" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Conclusion" });
tag(s, "// 09  CONCLUSION");
s.addText("Static slicing fails; next we make it adaptive", { placeholder: "title" });
panel(s, 0.6, 1.75, 5.9, 4.85);
s.addText("WHAT MIDSEM SHOWS", { x: 0.95, y: 2.0, w: 5, h: 0.3, fontFace: MONO, fontSize: 12, bold: true, color: HX.cyan, margin: 0, isTextBox: true });
const take = [
  "Working, validated ns-3 slicing model with a real, run-time adjustable split",
  "Static 50/30/20 drops 30-42% of a bursting slice's traffic",
  "URLLC breaks its 10 ms budget in P3 and P4",
  "On average 27.8% of capacity is idle at the same time",
];
s.addText(take.map((t, k) => ({ text: t, options: { bullet: { code: "25A0" }, breakLine: k < take.length - 1 } })),
  { x: 0.95, y: 2.5, w: 5.3, h: 3.9, fontSize: 18, color: HX.text, margin: 0, valign: "top", paraSpaceAfter: 16, isTextBox: true });
const steps = [["01", "ns3-ai environment", "state out, allocation in, every 1 s"],
  ["02", "DQN training", "randomised scenarios, reward sweep"],
  ["03", "Comparison", "Static vs Random vs DQN, 5 experiments"],
  ["04", "Dashboard", "Streamlit, Static vs DQN side by side"],
  ["05", "Optional", "demand forecasting in the state"]];
s.addText("POST-MIDSEM", { x: 6.95, y: 1.8, w: 5, h: 0.3, fontFace: MONO, fontSize: 12, bold: true, color: HX.amber, margin: 0, isTextBox: true });
steps.forEach(([n, h, b], i) => {
  const y = 2.25 + i * 0.88;
  s.addShape(pres.shapes.OVAL, { x: 6.95, y, w: 0.6, h: 0.6, fill: { color: HX.bg }, line: { color: HX.amber, width: 1.5 } });
  s.addText(n, { x: 6.95, y, w: 0.6, h: 0.6, fontFace: MONO, fontSize: 12, bold: true, color: HX.amber, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(h, { x: 7.75, y: y - 0.02, w: 4.9, h: 0.34, fontSize: 16, bold: true, color: HX.text, margin: 0, isTextBox: true });
  s.addText(b, { x: 7.75, y: y + 0.32, w: 4.9, h: 0.3, fontSize: 13, color: HX.muted, margin: 0, isTextBox: true });
  if (i < steps.length - 1) s.addShape(pres.shapes.LINE, { x: 7.25, y: y + 0.6, w: 0, h: 0.28, line: { color: HX.line, width: 1.5 } });
});
s.addNotes("Close with the story: dynamic traffic, fixed allocation, measurable QoS failure and idle capacity, therefore adaptive allocation. Code and all figures are reproducible from the repository.");

(async () => {
  await pres.writeFile({ fileName: "Adaptive_5G_Slicing_Midsem.pptx" });
  await applyTheme("Adaptive_5G_Slicing_Midsem.pptx", THEME);
  console.log("deck written");
})();
