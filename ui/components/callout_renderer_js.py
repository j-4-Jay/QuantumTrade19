"""PATH: ui/components/callout_renderer_js.py  (NEW FILE)

FT-H.16 step 1 - the browser code that draws the setup callouts (mini and big views).
It is plain JavaScript text. ui/components/kline_chart.py adds it to the page once.
Look: docs/specs/File_04.1c_Callouts_Spec_v2.md and Addendum 1 (pictures v10).
Preview in the browser console (F12), then switch the timeframe and back:
  window.QT19_CALLOUT_DEMO = {state: "sl_hit", fade: 1, score: 87, poi: "4H FVG", mode: "big"}
  window.QT19_CALLOUT_DEMO = null
state: running, sl_hit, win, be. fade 0 to 1 is the journey toward the SL (running only).
"""

CALLOUT_RENDERER_JS = r"""
const QT19_CO_R = 14, QT19_CO_TAIL = 28, QT19_CO_TIPX = 40, QT19_CO_HALF = 10;
const QT19_BIG = { W: 320, H: 201 };
const QT19_MINI = { W: 190, H: 130 };
const QT19_MINI_SCALE = 0.5;
const QT19_CO_FONT = "Inter, 'Segoe UI', system-ui, sans-serif";
const QT19_CO_MONO = "'JetBrains Mono', 'Cascadia Mono', Consolas, monospace";
const QT19_STATE_LOOK = {
  running: { name: "Running", body: null, ink: "light", sticker: null },
  sl_hit: { name: "SL Hit", body: "#FF6200", ink: "dark", sticker: "#2B343C" },
  win: { name: "Win", body: "#9FE2BF", ink: null, sticker: "#0A3A29" },
  be: { name: "B.E.", body: "#FFCE1B", ink: null, sticker: "#EC267D" },
};
const qt19Svg = (tag, attrs) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.keys(attrs || {}).forEach((k) => node.setAttribute(k, attrs[k]));
  return node;
};
const qt19MixHex = (a, b, t) => {
  const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
  const mix = (shift) => { const ca = (pa >> shift) & 255, cb = (pb >> shift) & 255; return Math.round(ca + (cb - ca) * t); };
  const toHex = (v) => v.toString(16).padStart(2, "0");
  return "#" + toHex(mix(16)) + toHex(mix(8)) + toHex(mix(0));
};
const qt19Lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
const qt19Rel = (hex) => { const n = parseInt(hex.slice(1), 16); return 0.2126 * qt19Lin((n >> 16) & 255) + 0.7152 * qt19Lin((n >> 8) & 255) + 0.0722 * qt19Lin(n & 255); };
const qt19Contrast = (a, b) => { const la = qt19Rel(a), lb = qt19Rel(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
const qt19ToLch = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  const r = qt19Lin((n >> 16) & 255), g = qt19Lin((n >> 8) & 255), b = qt19Lin(n & 255);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
  return { L: L, C: Math.hypot(A, B), h: (Math.atan2(B, A) * 180 / Math.PI + 360) % 360 };
};
const qt19FromLch = (L, C, h) => {
  const A = C * Math.cos(h * Math.PI / 180), B = C * Math.sin(h * Math.PI / 180);
  const l = Math.pow(L + 0.3963377774 * A + 0.2158037573 * B, 3);
  const m = Math.pow(L - 0.1055613458 * A - 0.0638541728 * B, 3);
  const s = Math.pow(L - 0.0894841775 * A - 1.2914855480 * B, 3);
  const lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
  const enc = (c) => { const v = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; return Math.max(0, Math.min(255, Math.round(v * 255))); };
  return "#" + lin.map((c) => enc(c).toString(16).padStart(2, "0")).join("");
};
const qt19Journey = (from, to, t) => {
  const a = qt19ToLch(from), b = qt19ToLch(to);
  let dh = b.h - a.h; if (dh > 180) dh -= 360; if (dh < -180) dh += 360;
  return qt19FromLch(a.L + (b.L - a.L) * t, a.C + (b.C - a.C) * t, (a.h + dh * t + 360) % 360);
};
const qt19CalloutPath = (isBull, W, H) => {
  const R = QT19_CO_R, T = QT19_CO_TAIL, X = QT19_CO_TIPX, S = QT19_CO_HALF;
  if (isBull) {
    return "M " + R + " 0 L " + (X - S) + " 0 L " + X + " " + (-T) + " L " + (X + S) + " 0 L " + (W - R) + " 0 Q " + W + " 0 " + W + " " + R
      + " L " + W + " " + (H - R) + " Q " + W + " " + H + " " + (W - R) + " " + H + " L " + R + " " + H + " Q 0 " + H + " 0 " + (H - R)
      + " L 0 " + R + " Q 0 0 " + R + " 0 Z";
  }
  return "M " + R + " 0 L " + (W - R) + " 0 Q " + W + " 0 " + W + " " + R + " L " + W + " " + (H - R) + " Q " + W + " " + H + " " + (W - R) + " " + H
    + " L " + (X + S) + " " + H + " L " + X + " " + (H + T) + " L " + (X - S) + " " + H + " L " + R + " " + H + " Q 0 " + H + " 0 " + (H - R)
    + " L 0 " + R + " Q 0 0 " + R + " 0 Z";
};
const qt19Palette = (body, H, force, ys) => {
  const dark = "#050B18";
  const Lm = { top: qt19MixHex(body, dark, 0.25), bot: qt19MixHex(body, dark, 0.78), ink: "#FFFFFF", sheen: 0.16 };
  const Dm = { top: qt19MixHex(body, "#FFFFFF", 0.3), bot: qt19MixHex(body, "#0A1A14", 0.2), ink: qt19MixHex(body, "#000000", 0.88), sheen: 0.55 };
  const worst = (m) => Math.min.apply(null, ys.map((y) => {
    let c = qt19MixHex(m.top, m.bot, y / H);
    if (y < 66) c = qt19MixHex(c, "#FFFFFF", m.sheen + (0.04 - m.sheen) * ((y - 6) / 60));
    return qt19Contrast(m.ink, c);
  }));
  const wl = worst(Lm), wd = worst(Dm);
  const useDark = force === "dark" ? true : force === "light" ? false : wd > wl + 0.4;
  const m = useDark ? Dm : Lm;
  return { s: useDark ? 1 : 0, top: m.top, bot: m.bot, ink: m.ink, sheen: m.sheen };
};
const qt19StickerFrom = (base, ink, halo) => ({ hi: qt19MixHex(base, "#FFFFFF", 0.45), mid: base, lo: qt19MixHex(base, "#000000", 0.5), ink: ink, halo: halo });
const qt19StickerGold = { hi: "#FFF3B0", mid: "#FFC83D", lo: "#FF8A00", ink: "#2B1600", halo: "rgba(255,255,255,0)" };
let qt19Canvas = null;
const qt19Measure = (str, size, weight, family) => {
  qt19Canvas = qt19Canvas || document.createElement("canvas");
  const c = qt19Canvas.getContext("2d");
  c.font = weight + " " + size + "px " + family;
  return c.measureText(str).width;
};
const qt19ClosePopup = () => {
  const p = document.getElementById("qt19-score-popup");
  if (p && p.parentNode) p.parentNode.removeChild(p);
};
const qt19PopupOutside = (ev) => {
  const p = document.getElementById("qt19-score-popup");
  if (p && !(ev.target && p.contains(ev.target))) qt19ClosePopup();
};
const qt19ShowScorePopup = (anchorEl) => {
  qt19ClosePopup();
  const r = anchorEl.getBoundingClientRect();
  const pop = document.createElement("div");
  pop.id = "qt19-score-popup";
  pop.style.cssText = "position:fixed;z-index:10000;min-width:230px;padding:16px 20px;border-radius:14px;color:#EAF2FF;font-family:" + QT19_CO_FONT + ";"
    + "background:linear-gradient(160deg,rgba(18,28,56,0.97),rgba(6,12,28,0.97));border:1px solid rgba(120,160,255,0.38);"
    + "box-shadow:0 14px 44px rgba(0,0,0,0.6),0 0 0 1px rgba(255,255,255,0.05) inset;";
  const title = document.createElement("div");
  title.textContent = "CONFIDENCE SCORE";
  title.style.cssText = "font-size:11px;font-weight:800;letter-spacing:1.4px;color:#8FB4FF;margin-bottom:8px;";
  const body = document.createElement("div");
  body.textContent = "Score Table Coming Soon";
  body.style.cssText = "font-size:17px;font-weight:700;";
  pop.appendChild(title);
  pop.appendChild(body);
  document.body.appendChild(pop);
  const w = pop.offsetWidth, h = pop.offsetHeight;
  const left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left + r.width / 2 - w / 2));
  const top = Math.max(8, Math.min(window.innerHeight - h - 8, r.bottom + 10));
  pop.style.left = left + "px";
  pop.style.top = top + "px";
};
const qt19BuildCallout = (co, mode) => {
  const mini = mode === "mini";
  const W = mini ? QT19_MINI.W : QT19_BIG.W, H = mini ? QT19_MINI.H : QT19_BIG.H;
  const sc = mini ? QT19_MINI_SCALE : 1;
  const bull = !!co.is_bull;
  window.QT19_CO_SEQ = (window.QT19_CO_SEQ || 0) + 1;
  const key = "qt19cg" + window.QT19_CO_SEQ;
  const demo = window.QT19_CALLOUT_DEMO || null;
  const look = QT19_STATE_LOOK[(demo && demo.state) || co.state || "running"] || QT19_STATE_LOOK.running;
  const fade = Math.max(0, Math.min(1, Number(demo && demo.fade != null ? demo.fade : co.fade) || 0));
  const bodyColor = look.body || qt19Journey(co.fill_from, co.fill_to, fade);
  const ys = mini ? [12, 52, 90, 110] : [12, 37, 60, 91, 131, 150, 174, 194];
  const pal = qt19Palette(bodyColor, H, look.ink, ys);
  const s = pal.s, ink = pal.ink;
  const score = demo && demo.score != null ? String(demo.score) : (co.confidence_value ? String(co.confidence_value) : "");
  const poiShort = demo && demo.poi != null ? String(demo.poi) : (co.poi_short || "");
  const glow = co.glow_color || co.border_color;
  const core = qt19MixHex(glow, "#FFFFFF", 0.65);
  const shapeD = qt19CalloutPath(bull, W, H);
  const area = { x: "-70", y: "-80", width: String(W + 140), height: String(H + 160) };
  const wrap = document.createElement("div");
  wrap.className = "qt19-callout";
  wrap.style.cssText = "position:absolute;left:0;top:0;display:none;pointer-events:auto;cursor:pointer;will-change:transform;width:" + (W * sc) + "px;height:" + (H * sc) + "px;";
  wrap._size = { W: W * sc, H: H * sc };
  wrap._tip = { x: QT19_CO_TIPX * sc, t: QT19_CO_TAIL * sc };
  const svg = qt19Svg("svg", { width: W, height: H, viewBox: "0 0 " + W + " " + H });
  svg.style.overflow = "visible";
  svg.style.transformOrigin = "0 0";
  svg.style.transform = "scale(" + sc + ")";
  const defs = qt19Svg("defs");
  const grad = qt19Svg("linearGradient", { id: key, x1: "0", y1: "0", x2: "0", y2: "1" });
  grad.appendChild(qt19Svg("stop", { offset: "0%", "stop-color": pal.top, "stop-opacity": "0.93" }));
  grad.appendChild(qt19Svg("stop", { offset: "100%", "stop-color": pal.bot, "stop-opacity": "0.95" }));
  defs.appendChild(grad);
  const sheen = qt19Svg("linearGradient", { id: key + "-sh", x1: "0", y1: "0", x2: "0", y2: "1" });
  sheen.appendChild(qt19Svg("stop", { offset: "0%", "stop-color": "#FFFFFF", "stop-opacity": String(pal.sheen) }));
  sheen.appendChild(qt19Svg("stop", { offset: "100%", "stop-color": "#FFFFFF", "stop-opacity": "0.04" }));
  defs.appendChild(sheen);
  const f1 = qt19Svg("filter", Object.assign({ id: key + "-f1", filterUnits: "userSpaceOnUse" }, area));
  f1.appendChild(qt19Svg("feGaussianBlur", { stdDeviation: "2" }));
  defs.appendChild(f1);
  const f2 = qt19Svg("filter", Object.assign({ id: key + "-f2", filterUnits: "userSpaceOnUse" }, area));
  f2.appendChild(qt19Svg("feGaussianBlur", { stdDeviation: "5" }));
  defs.appendChild(f2);
  const mask = qt19Svg("mask", Object.assign({ id: key + "-mk", maskUnits: "userSpaceOnUse" }, area));
  mask.appendChild(qt19Svg("rect", Object.assign({ fill: "#FFFFFF" }, area)));
  mask.appendChild(qt19Svg("path", { d: shapeD, fill: "#000000" }));
  defs.appendChild(mask);
  svg.appendChild(defs);
  const led = qt19Svg("g", { mask: "url(#" + key + "-mk)" });
  led.appendChild(qt19Svg("path", { d: shapeD, fill: "none", stroke: glow, "stroke-width": "7", "stroke-linejoin": "round", opacity: "0.55", filter: "url(#" + key + "-f2)" }));
  led.appendChild(qt19Svg("path", { d: shapeD, fill: "none", stroke: glow, "stroke-width": "4", "stroke-linejoin": "round", opacity: "1", filter: "url(#" + key + "-f1)" }));
  svg.appendChild(led);
  svg.appendChild(qt19Svg("path", { d: shapeD, fill: "url(#" + key + ")", stroke: co.border_color, "stroke-width": "3", "stroke-linejoin": "round" }));
  svg.appendChild(qt19Svg("rect", { x: "6", y: "6", width: String(W - 12), height: mini ? "52" : "60", rx: "10", fill: "url(#" + key + "-sh)" }));
  svg.appendChild(qt19Svg("rect", { x: "3.5", y: "3.5", width: String(W - 7), height: String(H - 7), rx: "11", fill: "none", stroke: "#FFFFFF", "stroke-opacity": "0.16", "stroke-width": "1" }));
  svg.appendChild(qt19Svg("path", { d: shapeD, fill: "none", stroke: core, "stroke-width": "1.2", "stroke-linejoin": "round", opacity: "0.95" }));

  const text = (x, y, str, size, weight, extra) => {
    const attrs = Object.assign({
      x: String(x), y: String(y), fill: ink, "font-size": String(size), "font-weight": String(weight),
      "font-family": QT19_CO_FONT, "paint-order": "stroke", "stroke-linejoin": "round",
      stroke: "rgba(2,8,20,0.5)", "stroke-width": String((2.4 * (1 - s)).toFixed(2)),
    }, extra || {});
    const node = qt19Svg("text", attrs);
    node.textContent = str;
    svg.appendChild(node);
    return node;
  };
  const icon = (kind, cx, cy, color) => {
    const g = qt19Svg("g", { transform: "translate(" + cx + " " + cy + ")", fill: "none", stroke: color, "stroke-width": "1.7", "stroke-linecap": "round", "stroke-linejoin": "round" });
    if (kind === "entry") {
      g.appendChild(qt19Svg("circle", { r: "5", cx: "0", cy: "0" }));
      g.appendChild(qt19Svg("circle", { r: "1.4", cx: "0", cy: "0", fill: color }));
    } else if (kind === "sl") {
      g.appendChild(qt19Svg("path", { d: "M0 -5.5 L5 -3.5 L5 1 Q5 4 0 6 Q-5 4 -5 1 L-5 -3.5 Z" }));
    } else if (kind === "ticks") {
      g.appendChild(qt19Svg("path", { d: "M0 -5.5 L0 5.5 M-3 -2.5 L0 -5.5 L3 -2.5 M-3 2.5 L0 5.5 L3 2.5" }));
    } else if (kind === "peak") {
      g.appendChild(qt19Svg("path", { d: "M-5.5 4 L-1.5 -3.5 L1 0 L3 -2 L5.5 4 Z" }));
    } else if (kind === "live") {
      g.appendChild(qt19Svg("circle", { r: "2.2", cx: "0", cy: "0", fill: color }));
      g.appendChild(qt19Svg("circle", { r: "5", cx: "0", cy: "0", "stroke-opacity": "0.55" }));
    } else if (kind === "qty") {
      g.appendChild(qt19Svg("path", { d: "M-4.5 5 L-4.5 0 M0 5 L0 -3 M4.5 5 L4.5 -5.5" }));
    } else if (kind === "profit") {
      g.appendChild(qt19Svg("path", { d: "M-5.5 3.5 L-1.5 -0.5 L1 2 L5 -3 M2 -3.5 L5.2 -3.2 L5.2 0" }));
    }
    svg.appendChild(g);
  };
  const badge = (x, w, label, value, color, kind) => {
    svg.appendChild(qt19Svg("rect", { x: String(x), y: "53", width: String(w), height: "46", rx: "10", fill: "#0D142C", stroke: color, "stroke-width": "1.8" }));
    icon(kind, x + 13, 67, color);
    text(x + 24, 71, label, 10, 800, { fill: color, "letter-spacing": "1", stroke: "none", "stroke-width": "0" });
    const v = String(value);
    const size = Math.max(11, 17 - Math.max(0, v.length - 7) * 1.6);
    text(x + 10, 91, v, size, 800, { fill: "#FFFFFF", stroke: "rgba(0,0,0,0.5)", "stroke-width": "2", "font-family": QT19_CO_MONO });
  };
  const cell = (x, y, label, value, kind, valueColor) => {
    icon(kind, x + 5, y - 4, qt19MixHex(ink, bodyColor, 0.25));
    text(x + 16, y, label, 10, 800, { "letter-spacing": "1", "fill-opacity": "0.8", stroke: "none", "stroke-width": "0" });
    text(x, y + 19, value, 16, 800, valueColor ? { fill: valueColor, "font-family": QT19_CO_MONO } : { "font-family": QT19_CO_MONO });
  };
  const pair = (x, y, label, value, kind, valueColor) => {
    icon(kind, x + 5, y - 4, qt19MixHex(ink, bodyColor, 0.25));
    text(x + 16, y, label, 10.5, 800, { "letter-spacing": "1", "fill-opacity": "0.78", stroke: "none", "stroke-width": "0" });
    text(x + 16 + label.length * 7.4 + 6, y + 1, value, 16, 800, valueColor ? { fill: valueColor, "font-family": QT19_CO_MONO } : { "font-family": QT19_CO_MONO });
  };

  const ix = mini ? 30 : 32, iy = mini ? 110 : 29, ir = mini ? 10 : 15, k = ir / 15;
  svg.appendChild(qt19Svg("circle", { cx: String(ix), cy: String(iy), r: String(ir), fill: co.border_color, stroke: "#FFFFFF", "stroke-width": mini ? "1.8" : "2.4" }));
  const tri = bull ? [[0, -8], [8, 6], [-8, 6]] : [[0, 8], [8, -6], [-8, -6]];
  svg.appendChild(qt19Svg("path", { d: "M" + tri.map((p) => (ix + p[0] * k).toFixed(1) + " " + (iy + p[1] * k).toFixed(1)).join(" L") + " Z", fill: "#FFFFFF" }));

  if (mini) {
    const avail = W - 46 - 16;
    let nameSize = 18, poiSize = 12.5;
    const poi = poiShort ? "\u00B7 " + poiShort : "";
    const total = () => qt19Measure(look.name, nameSize, 800, QT19_CO_FONT) + (poi ? 6 + qt19Measure(poi, poiSize, 700, QT19_CO_FONT) : 0);
    const w0 = total();
    if (w0 > avail) { const f = avail / w0; nameSize = Math.max(11, nameSize * f); poiSize = Math.max(9, poiSize * f); }
    const nm = text(46, 110 + nameSize * 0.36, look.name, nameSize.toFixed(1), 800, { "letter-spacing": "0.3" });
    if (poi) {
      const ps = qt19Svg("tspan", { "font-weight": "700", "fill-opacity": "0.85", dx: "6", "font-size": poiSize.toFixed(1) });
      ps.textContent = poi;
      nm.appendChild(ps);
    }
  } else {
    const avail = 236 - 56;
    const meta = "\u00B7 " + (co.timeframe || "") + (poiShort ? " \u00B7 " + poiShort : "");
    let nameSize = 22, metaSize = 15;
    const total = () => qt19Measure(look.name, nameSize, 800, QT19_CO_FONT) + 8 + qt19Measure(meta, metaSize, 600, QT19_CO_FONT);
    const w0 = total();
    if (w0 > avail) { const f = avail / w0; nameSize = Math.max(13, nameSize * f); metaSize = Math.max(10, metaSize * f); }
    const title = text(56, 37, look.name, nameSize.toFixed(1), 800, { "letter-spacing": "0.3" });
    const tf = qt19Svg("tspan", { "font-weight": "600", "fill-opacity": "0.8", dx: "8", "font-size": metaSize.toFixed(1) });
    tf.textContent = meta;
    title.appendChild(tf);

    badge(16, 94, "ENTRY", co.entry_text || co.entry, "#35D0FF", "entry");
    badge(118, 94, "SL", co.sl_text || co.sl, "#FF5A5F", "sl");
    badge(220, 84, "TICKS", co.ticks_text || co.risk_ticks, "#FFC83D", "ticks");

    svg.appendChild(qt19Svg("line", { x1: "16", y1: "113", x2: String(W - 16), y2: "113", stroke: ink, "stroke-opacity": "0.18" }));
    const pv = String(co.profit_text || "\u2014");
    const pos = pv.charAt(0) === "+", neg = pv.charAt(0) === "-";
    const pcol = pos ? (s ? "#0B5D36" : "#5CF0A8") : neg ? (s ? "#B0001E" : "#FF7A85") : null;
    cell(16, 131, "QTY", co.qty_text || "\u2014", "qty");
    cell(112, 131, "RISK", co.risk_text || "\u2014", "sl");
    cell(208, 131, "PROFIT", pv, "profit", pcol);
    pair(16, 174, "LIVE", co.live_text || "\u2014", "live");
    pair(170, 174, "PEAK", co.peak_text || "\u2014", "peak", qt19MixHex("#FFE08A", "#7A4B00", s));
    const uidText = String(co.uid);
    const uidShort = uidText.length > 36 ? uidText.slice(0, 18) + "\u2026" + uidText.slice(-14) : uidText;
    text(16, 194, "UID \u00B7 " + uidShort, 10.5, 600, { "font-family": QT19_CO_MONO, "fill-opacity": "0.75", stroke: "none", "stroke-width": "0", "letter-spacing": "0.3" });
  }

  const sticker = (cx, cy, rot) => {
    const pl = look.sticker ? qt19StickerFrom(look.sticker, "#FFFFFF", "rgba(0,0,0,0.55)") : qt19StickerGold;
    const R1 = 37, R2 = 34.2, N = 20;
    let burst = "";
    for (let i = 0; i < N * 2; i++) {
      const ang = (Math.PI * i) / N - Math.PI / 2;
      const r = i % 2 === 0 ? R1 : R2;
      burst += (i === 0 ? "M " : " L ") + (r * Math.cos(ang)).toFixed(2) + " " + (r * Math.sin(ang)).toFixed(2);
    }
    burst += " Z";
    const g = qt19Svg("g", { transform: "translate(" + cx + " " + cy + ") rotate(" + rot + ")", "data-qt19": "badge" });
    g.style.cursor = "pointer";
    const sd = qt19Svg("defs");
    const lg = qt19Svg("linearGradient", { id: key + "-st", x1: "0", y1: "0", x2: "1", y2: "1" });
    lg.appendChild(qt19Svg("stop", { offset: "0%", "stop-color": pl.hi }));
    lg.appendChild(qt19Svg("stop", { offset: "48%", "stop-color": pl.mid }));
    lg.appendChild(qt19Svg("stop", { offset: "100%", "stop-color": pl.lo }));
    sd.appendChild(lg);
    const shine = qt19Svg("linearGradient", { id: key + "-sn", x1: "0", y1: "0", x2: "1", y2: "1" });
    shine.appendChild(qt19Svg("stop", { offset: "0%", "stop-color": "#FFFFFF", "stop-opacity": "0.85" }));
    shine.appendChild(qt19Svg("stop", { offset: "100%", "stop-color": "#FFFFFF", "stop-opacity": "0" }));
    sd.appendChild(shine);
    const shadow = qt19Svg("filter", { id: key + "-sw", x: "-40%", y: "-40%", width: "180%", height: "180%" });
    shadow.appendChild(qt19Svg("feDropShadow", { dx: "0", dy: "2.5", stdDeviation: "2.6", "flood-color": "#000000", "flood-opacity": "0.7" }));
    sd.appendChild(shadow);
    const clip = qt19Svg("clipPath", { id: key + "-cl" });
    clip.appendChild(qt19Svg("circle", { r: "31", cx: "0", cy: "0" }));
    sd.appendChild(clip);
    sd.appendChild(qt19Svg("path", { id: key + "-ar", d: "M -26 0 A 26 26 0 1 1 26 0 A 26 26 0 1 1 -26 0" }));
    g.appendChild(sd);
    const num = Math.max(0, Math.min(100, Number(score) || 0));
    if (score) {
      const ringC = 2 * Math.PI * 42.5;
      const ringColor = qt19MixHex(pl.mid, "#FFFFFF", 0.4);
      g.appendChild(qt19Svg("circle", { r: "42.5", cx: "0", cy: "0", fill: "none", stroke: ringColor, "stroke-opacity": "0.28", "stroke-width": "3.2" }));
      g.appendChild(qt19Svg("circle", { r: "42.5", cx: "0", cy: "0", fill: "none", stroke: ringColor, "stroke-width": "3.2", "stroke-linecap": "round", "stroke-dasharray": (ringC * num / 100).toFixed(2) + " " + ringC.toFixed(2), transform: "rotate(-90)" }));
    }
    g.appendChild(qt19Svg("path", { d: burst, fill: "url(#" + key + "-st)", stroke: "#FFFFFF", "stroke-width": "2.2", "stroke-linejoin": "round", filter: "url(#" + key + "-sw)" }));
    g.appendChild(qt19Svg("circle", { r: "30", cx: "0", cy: "0", fill: "none", stroke: pl.ink, "stroke-opacity": "0.3", "stroke-width": "0.9" }));
    const gl = qt19Svg("g", { "clip-path": "url(#" + key + "-cl)" });
    gl.appendChild(qt19Svg("ellipse", { cx: "-10", cy: "-15", rx: "26", ry: "9", fill: "url(#" + key + "-sn)", transform: "rotate(-32 -10 -15)" }));
    g.appendChild(gl);
    g.appendChild(qt19Svg("path", { d: "M -19 -20 L -17.6 -16.6 L -14.2 -15.2 L -17.6 -13.8 L -19 -10.4 L -20.4 -13.8 L -23.8 -15.2 L -20.4 -16.6 Z", fill: "#FFFFFF", opacity: "0.95" }));
    const arc = qt19Svg("text", { "font-size": "7.4", "font-weight": "900", "font-family": QT19_CO_FONT, "letter-spacing": "0.5", fill: pl.ink, "text-anchor": "middle", stroke: pl.halo, "stroke-width": "1.6", "paint-order": "stroke" });
    const tp = qt19Svg("textPath", { href: "#" + key + "-ar", startOffset: "25%" });
    tp.textContent = "CONFIDENCE SCORE";
    arc.appendChild(tp);
    g.appendChild(arc);
    const val = qt19Svg("text", { x: "0", y: "8", "font-size": "22", "font-weight": "900", "font-family": QT19_CO_MONO, fill: pl.ink, "text-anchor": "middle", stroke: pl.halo, "stroke-width": "2", "paint-order": "stroke" });
    val.textContent = score || "\u2014";
    g.appendChild(val);
    if (!score) {
      const cap = qt19Svg("text", { x: "0", y: "18.5", "font-size": "6.6", "font-weight": "800", "font-family": QT19_CO_FONT, "letter-spacing": "0.8", fill: pl.ink, "fill-opacity": "0.85", "text-anchor": "middle" });
      cap.textContent = "FILE 05";
      g.appendChild(cap);
    }
    svg.appendChild(g);
  };
  if (mini) sticker(W / 2, 52, 0); else sticker(W - 46, 6, -11);
  wrap.appendChild(svg);
  return wrap;
};
"""
