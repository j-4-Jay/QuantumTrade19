"""FULL PATH: ui/components/candle_info_popup_js.py
FT-H.39 Candle info popup (hold a candle for 2 seconds). Browser code only.
Spec: docs/specs/File_Candle_Info_Popup_Spec_v0.1.0.md

This file only holds the popup as one JavaScript string. Nothing here runs until a
later request adds a small hook in ui/components/kline_chart.py.

Browser API (window.QT19CandlePopup):
  attach({chartId, container, getChart, getSymbol, getTf, request, reducedMotion, candleAt?, timing?})
  receive(chartId, popupId, {kind: "db" | "compare", candle | null, error?})
  closeAll(chartId), detach(chartId)
Resource rule: no timer and no running listener while idle; one 1-second ticker only while a
popup is forming or syncing; one passive pointerdown listener on the chart container.
"""
from __future__ import annotations

CANDLE_INFO_POPUP_JS = r"""
(function () {
  if (typeof window === "undefined" || window.QT19CandlePopup) return;
  var MAX = 10, MOVE_PX = 3, SYNC_MS = 15000, MIN_W = 236, MIN_H = 196, DEF_W = 304, DEF_H = 286;
  var TF_MS = { "1m": 60000, "5m": 300000, "15m": 900000, "1H": 3600000, "4H": 14400000, "1D": 86400000 };
  var LABELS = [["o", "Open"], ["h", "High"], ["l", "Low"], ["c", "Close"], ["v", "Volume"]];
  var inst = {}, zTop = 60, cssDone = false, fmtCache = {};

  var CSS = [
    ".qt19-cip{position:absolute;left:0;top:0;box-sizing:border-box;display:flex;color:#EEF2F7;font:12px/1.3 Inter,Segoe UI,system-ui,sans-serif;border-radius:14px;overflow:hidden;container-type:inline-size;opacity:0;transform-origin:0 0;border:1px solid rgba(255,255,255,.14);box-shadow:0 14px 34px rgba(0,0,0,.5),0 0 0 1px rgba(0,0,0,.4);user-select:none;-webkit-user-select:none;will-change:transform,opacity}",
    ".qt19-cip.up{background:linear-gradient(135deg,rgba(18,160,108,.62) 0%,rgba(8,36,30,.94) 58%,rgba(5,16,14,.97) 100%);border-color:rgba(31,224,160,.45)}",
    ".qt19-cip.dn{background:linear-gradient(135deg,rgba(214,52,62,.62) 0%,rgba(46,12,18,.94) 58%,rgba(20,6,10,.97) 100%);border-color:rgba(255,92,100,.45)}",
    ".qt19-cip.fl{background:linear-gradient(135deg,rgba(120,132,150,.55) 0%,rgba(24,30,42,.94) 58%,rgba(10,14,22,.97) 100%);border-color:rgba(170,182,200,.4)}",
    ".qt19-cip-h{flex:0 0 14px;cursor:grab;background-image:radial-gradient(rgba(255,255,255,.55) 1.1px,transparent 1.3px);background-size:6px 6px;background-position:3px 3px;opacity:.7;touch-action:none}",
    ".qt19-cip-h:active{cursor:grabbing}",
    ".qt19-cip-b{flex:1;min-width:0;display:flex;flex-direction:column;padding:8px 10px 8px 8px;gap:5px;opacity:0}",
    ".qt19-cip-t{display:flex;align-items:center;gap:6px}",
    ".qt19-cip-t b{font-size:12.5px;letter-spacing:.02em;white-space:nowrap}",
    ".qt19-cip-badge{margin-left:auto;font-size:10.5px;padding:1px 8px;border-radius:99px;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.18);white-space:nowrap}",
    ".qt19-cip-badge.sync{color:#FFD76A;border-color:rgba(255,215,106,.5)}.qt19-cip-badge.settled{color:#9FE2BF;border-color:rgba(159,226,191,.5)}.qt19-cip-badge.forming{color:#8EC5FF;border-color:rgba(142,197,255,.5)}",
    ".qt19-cip-x{cursor:pointer;width:20px;height:20px;border-radius:6px;display:grid;place-items:center;background:rgba(0,0,0,.3);border:0;color:#EEF2F7;font-size:13px;line-height:1;padding:0}.qt19-cip-x:hover{background:rgba(255,255,255,.2)}",
    ".qt19-cip-tm{font-size:11px;opacity:.88;font-variant-numeric:tabular-nums;display:grid;grid-template-columns:auto 1fr;column-gap:8px}.qt19-cip-tm i{font-style:normal;opacity:.65}",
    ".qt19-cip-r{display:grid;grid-template-columns:54px 1fr;align-items:baseline;column-gap:6px;padding:2px 0;border-top:1px solid rgba(255,255,255,.08)}",
    ".qt19-cip-r .v{font-weight:700;font-size:13.5px;font-variant-numeric:tabular-nums;border-radius:4px;padding:0 3px}",
    ".qt19-cip-r .l{opacity:.7;font-size:11px}",
    ".qt19-cip-r .g{grid-column:2;display:flex;flex-wrap:wrap;gap:2px 8px;font-size:10.5px;font-variant-numeric:tabular-nums}",
    ".qt19-cip-r .g span{display:none}.qt19-cip-r .g span.on{display:inline}",
    ".qt19-cip-r .g .ch{color:#FFB4B4}.qt19-cip-r .g .cx{color:#FFD76A}",
    ".qt19-cip-r .v.flash{animation:qt19cipflash .9s ease-out}",
    "@keyframes qt19cipflash{0%{background:rgba(255,215,106,.85);color:#1a1a1a}100%{background:transparent}}",
    ".qt19-cip-f{display:flex;flex-wrap:wrap;gap:5px;margin-top:auto;align-items:center}",
    ".qt19-cip-btn{cursor:pointer;font:inherit;font-size:11px;color:#EEF2F7;padding:3px 9px;border-radius:8px;background:rgba(0,0,0,.32);border:1px solid rgba(255,255,255,.2)}.qt19-cip-btn:hover{background:rgba(255,255,255,.16)}.qt19-cip-btn[disabled]{opacity:.5;cursor:default}",
    ".qt19-cip-btn.on{background:rgba(31,224,160,.28);border-color:rgba(31,224,160,.7)}",
    ".qt19-cip-note{font-size:10.5px;color:#FFD76A;min-height:13px;width:100%}",
    ".qt19-cip-g{position:absolute;right:0;bottom:0;width:16px;height:16px;cursor:nwse-resize;touch-action:none;background:linear-gradient(135deg,transparent 55%,rgba(255,255,255,.5) 55% 62%,transparent 62% 72%,rgba(255,255,255,.5) 72% 79%,transparent 79%)}",
    "@container (max-width:268px){.qt19-cip-r{grid-template-columns:48px 1fr}.qt19-cip-tm{grid-template-columns:1fr}.qt19-cip-tm i{display:none}.qt19-cip-btn{padding:2px 6px}}",
    ".qt19-cip-ring{position:absolute;width:38px;height:38px;pointer-events:none;z-index:50}.qt19-cip-ring circle{fill:none;stroke:#FFD76A;stroke-width:2.5;stroke-linecap:round;stroke-dasharray:101;stroke-dashoffset:101;opacity:0;animation:qt19cipring 1.7s linear .3s forwards}",
    "@keyframes qt19cipring{0%{opacity:1;stroke-dashoffset:101}100%{opacity:1;stroke-dashoffset:0}}",
    ".qt19-cip-toast{position:absolute;pointer-events:none;z-index:70;background:rgba(10,14,22,.92);color:#FFD76A;border:1px solid rgba(255,215,106,.5);padding:4px 10px;border-radius:8px;font:11.5px Inter,Segoe UI,sans-serif}"
  ].join("\n");

  function injectCss() {
    if (cssDone) return;
    cssDone = true;
    var s = document.createElement("style");
    s.setAttribute("data-qt19", "candle-info-popup");
    s.textContent = CSS;
    document.head.appendChild(s);
  }
  function fmtOf(tz) {
    return fmtCache[tz] || (fmtCache[tz] = new Intl.DateTimeFormat("en-US", {
      timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true
    }));
  }
  function stamp(ms, tz) {
    var p = {};
    fmtOf(tz).formatToParts(new Date(ms)).forEach(function (x) { p[x.type] = x.value; });
    return p.day + "-" + p.month + "-" + p.year + "  " + p.hour + ":" + p.minute + ":" + p.second + " " + String(p.dayPeriod || "").toUpperCase();
  }
  function num(v, d) { return (v == null || isNaN(v)) ? "\u2014" : String(Number(Number(v).toFixed(d))); }
  function show(k, v) { return num(v, k === "v" ? 3 : 8); }
  function same(a, b) { return a != null && b != null && Math.abs(Number(a) - Number(b)) < 1e-6; }
  function pick(c) { return c ? { o: c.open, h: c.high, l: c.low, c: c.close, v: c.volume } : null; }
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function indexOfTs(list, ts) {
    for (var i = list.length - 1; i >= 0; i--) { if (list[i].timestamp === ts) return i; if (list[i].timestamp < ts) break; }
    return -1;
  }
  function reduced(st) { try { return !!(st.opts.reducedMotion && st.opts.reducedMotion()); } catch (e) { return false; } }
  function gapOf(st) { return reduced(st) ? 0 : st.timing.appearMs; }

  function defaultCandleAt(chart, x, y) {
    try {
      var r = chart.convertFromPixel([{ x: x, y: y }], { paneId: "candle_pane" });
      var o = Array.isArray(r) ? r[0] : r;
      var list = chart.getDataList() || [];
      var idx = (o && typeof o.dataIndex === "number") ? o.dataIndex : -1;
      if ((idx < 0 || idx >= list.length) && o && o.timestamp) idx = indexOfTs(list, o.timestamp);
      if (idx < 0 || idx >= list.length) return null;
      var bar = list[idx];
      var px = chart.convertToPixel({ dataIndex: idx, value: bar.close }, { paneId: "candle_pane" });
      var bs = typeof chart.getBarSpace === "function" ? chart.getBarSpace() : 8;
      var space = (typeof bs === "number") ? bs : ((bs && bs.bar) || 8);
      return { timestamp: bar.timestamp, x: px && typeof px.x === "number" ? px.x : x, barSpace: space };
    } catch (e) { return null; }
  }

  function clearCandleHighlight(st) {
    if (!st.highlight) return;
    cancelAnimationFrame(st.highlight.frame);
    if (st.highlight.el.parentNode) st.highlight.el.parentNode.removeChild(st.highlight.el);
    st.highlight = null;
  }
  function highlightCandle(st, p) {
    clearCandleHighlight(st);
    if (p.closed || st.opts.getSymbol() !== p.sym) return;
    if (st.opts.getTf() !== p.tf) { p.note.textContent = "Switch to " + p.tf + " to locate this candle."; return; }
    var glow = el("div", "qt19-cip-candle-glow");
    glow.style.cssText = "position:absolute;pointer-events:none;z-index:49;border-radius:5px;background:rgba(255,222,40,.24);border:1px solid rgba(255,225,65,.85);box-shadow:0 0 9px 4px rgba(255,220,30,.55),0 0 20px 7px rgba(255,220,30,.24);";
    st.container.appendChild(glow);
    var h = { el: glow, frame: 0, start: null };
    st.highlight = h;
    function draw(now) {
      if (st.highlight !== h) return;
      if (h.start === null) h.start = now;
      var elapsed = now - h.start;
      if (elapsed >= 2000 || p.closed || st.opts.getSymbol() !== p.sym || st.opts.getTf() !== p.tf) { clearCandleHighlight(st); return; }
      try {
        var chart = st.opts.getChart(), list = chart ? chart.getDataList() || [] : [];
        var idx = indexOfTs(list, p.ts);
        if (idx < 0) { p.note.textContent = "Candle is not loaded on this chart."; clearCandleHighlight(st); return; }
        var bar = list[idx];
        var hi = chart.convertToPixel({ dataIndex: idx, value: bar.high }, { paneId: "candle_pane" });
        var lo = chart.convertToPixel({ dataIndex: idx, value: bar.low }, { paneId: "candle_pane" });
        if (!hi || !lo || !Number.isFinite(hi.x) || !Number.isFinite(hi.y) || !Number.isFinite(lo.y)) { clearCandleHighlight(st); return; }
        var bs = chart.getBarSpace ? chart.getBarSpace() : 8;
        var width = Math.max(4, (typeof bs === "number" ? bs : (bs && bs.bar) || 8) + 4);
        var top = Math.min(hi.y, lo.y) - 4, height = Math.max(8, Math.abs(lo.y - hi.y) + 8);
        if (hi.x < 0 || hi.x > st.container.clientWidth || top + height < 0 || top > st.container.clientHeight) {
          p.note.textContent = "Candle is outside the visible chart."; clearCandleHighlight(st); return;
        }
        glow.style.left = (hi.x - width / 2) + "px";
        glow.style.top = top + "px";
        glow.style.width = width + "px";
        glow.style.height = height + "px";
        glow.style.opacity = reduced(st) ? "0.85" : String(0.35 + 0.55 * (0.5 - 0.5 * Math.cos(elapsed * Math.PI / 350)));
      } catch (e) { clearCandleHighlight(st); return; }
      h.frame = requestAnimationFrame(draw);
    }
    h.frame = requestAnimationFrame(draw);
  }

  function toast(st, x, y, msg) {
    var t = el("div", "qt19-cip-toast", msg);
    t.style.left = clamp(x + 10, 4, Math.max(4, st.container.clientWidth - 190)) + "px";
    t.style.top = clamp(y - 30, 4, Math.max(4, st.container.clientHeight - 30)) + "px";
    st.container.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 1600);
  }

  function endHold(st, keepRing) {
    var h = st.hold;
    if (!h) return;
    clearTimeout(h.timer);
    window.removeEventListener("pointermove", h.mv, true);
    window.removeEventListener("pointerup", h.end, true);
    window.removeEventListener("pointercancel", h.end, true);
    window.removeEventListener("contextmenu", h.end, true);
    window.removeEventListener("blur", h.end, true);
    if (!keepRing && h.ring && h.ring.parentNode) h.ring.parentNode.removeChild(h.ring);
    st.hold = null;
  }

  function onDown(st, e) {
    if (e.button !== 0 || e.isPrimary === false) return;
    if (e.target && e.target.closest && e.target.closest(".qt19-cip")) return;
    if (st.hold) endHold(st);
    var r = st.container.getBoundingClientRect();
    var h = { x0: e.clientX, y0: e.clientY, lx: e.clientX - r.left, ly: e.clientY - r.top };
    var ring = el("div", "qt19-cip-ring");
    ring.innerHTML = '<svg viewBox="0 0 38 38" width="38" height="38"><circle cx="19" cy="19" r="16" pathLength="101" transform="rotate(-90 19 19)"></circle></svg>';
    ring.style.left = (h.lx - 19) + "px";
    ring.style.top = (h.ly - 19) + "px";
    st.container.appendChild(ring);
    h.ring = ring;
    h.mv = function (ev) { if (Math.abs(ev.clientX - h.x0) > MOVE_PX || Math.abs(ev.clientY - h.y0) > MOVE_PX) endHold(st); };
    h.end = function () { endHold(st); };
    h.timer = setTimeout(function () { finishHold(st, h); }, st.timing.holdMs);
    window.addEventListener("pointermove", h.mv, true);
    window.addEventListener("pointerup", h.end, true);
    window.addEventListener("pointercancel", h.end, true);
    window.addEventListener("contextmenu", h.end, true);
    window.addEventListener("blur", h.end, true);
    st.hold = h;
  }

  function finishHold(st, h) {
    var lx = h.lx, ly = h.ly;
    endHold(st);
    var chart = st.opts.getChart();
    var c = chart ? (st.opts.candleAt ? st.opts.candleAt(lx, ly) : defaultCandleAt(chart, lx, ly)) : null;
    if (!c) { toast(st, lx, ly, "No candle here"); return; }
    if (st.list.length >= MAX) { toast(st, lx, ly, "Maximum " + MAX + " popups"); return; }
    createPopup(st, c, lx, ly);
  }

  function chartVals(st, ts) {
    var chart = st.opts.getChart();
    var list = chart && chart.getDataList ? (chart.getDataList() || []) : [];
    var i = indexOfTs(list, ts);
    return i < 0 ? null : { vals: pick(list[i]), isLast: i === list.length - 1 };
  }

  function createPopup(st, c, lx, ly) {
    injectCss();
    var tf = st.opts.getTf(), sym = st.opts.getSymbol();
    var p = { id: ++st.seq, ts: c.timestamp, tf: tf, sym: sym, dur: TF_MS[tf] || 60000, vals: null, src: "", cx: null, auto: false, w: DEF_W, h: DEF_H, closed: false, timers: [] };
    var cw = st.container.clientWidth, ch = st.container.clientHeight;
    var gap = 2 * (c.barSpace || 8);
    var x = (c.x || lx) + gap;
    if (x + p.w > cw) x = (c.x || lx) - gap - p.w;
    p.x = clamp(x, 0, Math.max(0, cw - p.w));
    p.y = clamp(ly - 40, 0, Math.max(0, ch - p.h));
    var cur = chartVals(st, p.ts);
    p.vals = cur ? cur.vals : null;
    p.src = "Live";
    p.chart = null;

    var root = el("div", "qt19-cip fl");
    root.style.width = p.w + "px"; root.style.height = p.h + "px";
    root.style.transform = "translate3d(" + p.x + "px," + p.y + "px,0)";
    root.style.zIndex = String(++zTop);
    var handle = el("div", "qt19-cip-h"); handle.title = "Drag";
    var body = el("div", "qt19-cip-b");
    var top = el("div", "qt19-cip-t");
    var title = el("b", "", sym + " \u00B7 " + tf);
    var badge = el("span", "qt19-cip-badge", "");
    var xb = el("button", "qt19-cip-x", "\u2715"); xb.title = "Close"; xb.type = "button";
    top.appendChild(title); top.appendChild(badge); top.appendChild(xb);
    var tm = el("div", "qt19-cip-tm");
    tm.appendChild(el("i", "", "NY")); var tNy = el("span", "", stamp(p.ts, "America/New_York")); tm.appendChild(tNy);
    tm.appendChild(el("i", "", "IST")); var tIs = el("span", "", stamp(p.ts, "Asia/Kolkata")); tm.appendChild(tIs);
    body.appendChild(top); body.appendChild(tm);
    var rows = {};
    LABELS.forEach(function (kv) {
      var r = el("div", "qt19-cip-r");
      r.appendChild(el("span", "l", kv[1]));
      var v = el("span", "v", "\u2014");
      var g = el("div", "g"); var sc = el("span", "ch"); var sx = el("span", "cx"); g.appendChild(sc); g.appendChild(sx);
      var wrap = el("div"); wrap.style.minWidth = "0"; wrap.appendChild(v); wrap.appendChild(g);
      r.appendChild(wrap); body.appendChild(r);
      rows[kv[0]] = { v: v, ch: sc, cx: sx };
    });
    var foot = el("div", "qt19-cip-f");
    var bR = el("button", "qt19-cip-btn", "Refresh");
    var bA = el("button", "qt19-cip-btn", "Auto: OFF");
    var bC = el("button", "qt19-cip-btn", "Copy");
    var bX = el("button", "qt19-cip-btn", "Compare CoinDCX");
    [bR, bA, bC, bX].forEach(function (b) { b.type = "button"; foot.appendChild(b); });
    var note = el("div", "qt19-cip-note", "");
    foot.appendChild(note);
    body.appendChild(foot);
    var grip = el("div", "qt19-cip-g");
    root.appendChild(handle); root.appendChild(body); root.appendChild(grip);
    st.container.appendChild(root);
    p.el = root; p.rows = rows; p.badge = badge; p.note = note;
    st.list.push(p);

    function paint(flashKeys) {
      var v = p.vals;
      LABELS.forEach(function (kv) {
        var k = kv[0], r = rows[k];
        r.v.textContent = v ? show(k, v[k]) : "\u2014";
        if (flashKeys && flashKeys.indexOf(k) >= 0) { r.v.classList.remove("flash"); void r.v.offsetWidth; r.v.classList.add("flash"); }
        var chv = p.chart ? p.chart[k] : null;
        var diffCh = v && chv != null && !same(v[k], chv);
        r.ch.className = diffCh ? "ch on" : "ch";
        r.ch.textContent = diffCh ? "chart: " + show(k, chv) : "";
        var xv = p.cx ? p.cx[k] : null;
        var diffX = v && xv != null && !same(v[k], xv);
        r.cx.className = diffX ? "cx on" : "cx";
        r.cx.textContent = diffX ? "CoinDCX: " + show(k, xv) + " (\u0394 " + num(xv - v[k], k === "v" ? 3 : 8) + ")" : "";
      });
      var up = v && v.c > v.o, dn = v && v.c < v.o;
      root.className = "qt19-cip " + (up ? "up" : dn ? "dn" : "fl") + (p.shown ? " show" : "");
      badgeUpdate();
    }
    function badgeUpdate() {
      var s = statusOf(p, Date.now());
      badge.className = "qt19-cip-badge " + s.k; badge.textContent = s.t;
    }
    p.paint = paint; p.badgeUpdate = badgeUpdate;
    paint(null);
    p.chart = null;

    // entrance
    var gapMs = gapOf(st);
    if (gapMs === 0) { root.style.transition = "none"; body.style.transition = "none"; }
    else { root.style.transition = "opacity .35s ease"; body.style.transition = "opacity .35s ease " + (gapMs / 1000) + "s"; }
    requestAnimationFrame(function () {
      p.shown = true; root.classList.add("show");
      root.style.opacity = "1"; body.style.opacity = "1";
    });
    p.body = body;

    // actions
    xb.addEventListener("click", function () { closePopup(st, p); });
    bR.addEventListener("click", function () { askDb(st, p); });
    bX.addEventListener("click", function () {
      note.textContent = "Comparing with CoinDCX\u2026"; bX.disabled = true;
      p.timers.push(setTimeout(function () { bX.disabled = false; }, 3000));
      st.opts.request("compare", p.id, p.ts, p.sym, p.tf);
    });
    bA.addEventListener("click", function () {
      if (!p.auto) {
        if (Date.now() >= p.ts + p.dur + SYNC_MS) { note.textContent = "Already settled \u2013 nothing to sync."; return; }
        p.auto = true; bA.textContent = "Auto: ON"; bA.classList.add("on"); askDb(st, p); ensureTicker(st);
      } else { autoOff(p); }
    });
    bC.addEventListener("click", function () {
      var v = p.vals || {};
      var t = [p.sym + " " + p.tf, "NY " + stamp(p.ts, "America/New_York"), "IST " + stamp(p.ts, "Asia/Kolkata"),
        "Open " + show("o", v.o), "High " + show("h", v.h), "Low " + show("l", v.l), "Close " + show("c", v.c), "Volume " + show("v", v.v), "Source " + p.src].join("\n");
      copyText(t);
      bC.textContent = "Copied"; setTimeout(function () { bC.textContent = "Copy"; }, 1200);
    });
    root.addEventListener("pointerdown", function (e) { e.stopPropagation(); root.style.zIndex = String(++zTop); });
    root.addEventListener("click", function (e) {
      if (e.target && e.target.closest && e.target.closest("button,.qt19-cip-h,.qt19-cip-g")) return;
      highlightCandle(st, p);
    });
    root.addEventListener("wheel", function (e) { e.stopPropagation(); }, { passive: true });
    handle.addEventListener("pointerdown", function (e) {
      e.preventDefault(); e.stopPropagation();
      var sx = e.clientX - p.x, sy = e.clientY - p.y;
      try { handle.setPointerCapture(e.pointerId); } catch (x) {}
      function mv(ev) {
        p.x = clamp(ev.clientX - sx, 0, Math.max(0, st.container.clientWidth - p.w));
        p.y = clamp(ev.clientY - sy, 0, Math.max(0, st.container.clientHeight - p.h));
        root.style.transform = "translate3d(" + p.x + "px," + p.y + "px,0)";
      }
      function up() { handle.removeEventListener("pointermove", mv); handle.removeEventListener("pointerup", up); handle.removeEventListener("pointercancel", up); }
      handle.addEventListener("pointermove", mv); handle.addEventListener("pointerup", up); handle.addEventListener("pointercancel", up);
    });
    grip.addEventListener("pointerdown", function (e) {
      e.preventDefault(); e.stopPropagation();
      var sx = e.clientX, sy = e.clientY, w0 = p.w, h0 = p.h;
      try { grip.setPointerCapture(e.pointerId); } catch (x) {}
      function mv(ev) {
        p.w = clamp(w0 + ev.clientX - sx, MIN_W, Math.max(MIN_W, st.container.clientWidth - p.x));
        p.h = clamp(h0 + ev.clientY - sy, MIN_H, Math.max(MIN_H, st.container.clientHeight - p.y));
        root.style.width = p.w + "px"; root.style.height = p.h + "px";
      }
      function up() { grip.removeEventListener("pointermove", mv); grip.removeEventListener("pointerup", up); grip.removeEventListener("pointercancel", up); }
      grip.addEventListener("pointermove", mv); grip.addEventListener("pointerup", up); grip.addEventListener("pointercancel", up);
    });

    askDb(st, p);
    if (statusOf(p, Date.now()).k !== "settled") ensureTicker(st);
  }

  function statusOf(p, now) {
    var close = p.ts + p.dur;
    if (now < close) return { k: "forming", t: "Forming" };
    var left = close + SYNC_MS - now;
    if (left > 0) return { k: "sync", t: "Closed, syncing " + Math.ceil(left / 1000) + "s" };
    return { k: "settled", t: "Settled" };
  }
  function autoOff(p) {
    p.auto = false;
    var b = p.el.querySelectorAll(".qt19-cip-btn")[1];
    if (b) { b.textContent = "Auto: OFF"; b.classList.remove("on"); }
  }
  function askDb(st, p) { st.opts.request("db", p.id, p.ts, p.sym, p.tf); }

  function ensureTicker(st) {
    if (st.ticker) return;
    st.ticker = setInterval(function () {
      var now = Date.now(), need = false;
      st.list.forEach(function (p) {
        if (p.closed) return;
        p.badgeUpdate();
        var s = statusOf(p, now);
        if (p.auto) {
          if (s.k === "settled") { autoOff(p); askDb(st, p); p.note.textContent = "Auto refresh finished \u2013 settled."; }
          else { askDb(st, p); need = true; }
        }
        if (s.k !== "settled") need = true;
      });
      if (!need) { clearInterval(st.ticker); st.ticker = null; }
    }, 1000);
  }

  function copyText(t) {
    try { if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(t); return; } } catch (e) {}
    var a = document.createElement("textarea"); a.value = t; a.style.position = "fixed"; a.style.opacity = "0";
    document.body.appendChild(a); a.select(); try { document.execCommand("copy"); } catch (e) {} document.body.removeChild(a);
  }

  function closePopup(st, p) {
    if (p.closed) return;
    clearCandleHighlight(st);
    p.closed = true; autoOff(p);
    p.timers.forEach(clearTimeout);
    var gapMs = gapOf(st);
    function remove() {
      if (p.el.parentNode) p.el.parentNode.removeChild(p.el);
      var i = st.list.indexOf(p); if (i >= 0) st.list.splice(i, 1);
      if (!st.list.length && st.ticker) { clearInterval(st.ticker); st.ticker = null; }
    }
    if (gapMs === 0) { remove(); return; }
    p.body.style.transition = "opacity .3s ease"; p.body.style.opacity = "0";
    p.el.style.transition = "opacity .35s ease " + (gapMs / 1000) + "s"; p.el.style.opacity = "0";
    setTimeout(remove, gapMs + 400);
  }

  function receive(chartId, popupId, payload) {
    var st = inst[chartId]; if (!st || !payload) return;
    var p = null;
    for (var i = 0; i < st.list.length; i++) if (st.list[i].id === popupId) p = st.list[i];
    if (!p || p.closed) return;
    if (payload.kind === "db") {
      var old = p.vals, nv = null, cur = chartVals(st, p.ts);
      if (payload.candle) { nv = pick(payload.candle); p.src = "DB"; }
      else if (cur && cur.isLast) { nv = cur.vals; p.src = "Live"; }
      else { p.note.textContent = "Not in the database."; return; }
      p.chart = cur ? cur.vals : null;
      var fk = [];
      if (old) LABELS.forEach(function (kv) { if (!same(old[kv[0]], nv[kv[0]])) fk.push(kv[0]); });
      p.vals = nv;
      p.note.textContent = "Source: " + p.src + " \u00B7 " + new Date().toLocaleTimeString("en-US");
      p.paint(fk);
    } else if (payload.kind === "compare") {
      if (payload.candle) {
        p.cx = pick(payload.candle);
        var diffs = 0;
        if (p.vals) LABELS.forEach(function (kv) { if (!same(p.vals[kv[0]], p.cx[kv[0]])) diffs++; });
        p.note.textContent = diffs ? ("CoinDCX differs in " + diffs + " value" + (diffs > 1 ? "s" : "")) : "CoinDCX matches all 5 values.";
        p.paint(null);
      } else { p.note.textContent = payload.error ? ("CoinDCX: " + payload.error) : "CoinDCX candle not found."; }
    }
  }

  function attach(opts) {
    var chartId = opts.chartId;
    if (inst[chartId]) detach(chartId);
    injectCss();
    var st = { opts: opts, container: opts.container, list: [], seq: 0, hold: null, ticker: null,
      timing: { holdMs: (opts.timing && opts.timing.holdMs) || 2000, appearMs: (opts.timing && opts.timing.appearMs != null) ? opts.timing.appearMs : 750 } };
    st.down = function (e) { onDown(st, e); };
    st.container.addEventListener("pointerdown", st.down, true);
    inst[chartId] = st;
    return { destroy: function () { detach(chartId); } };
  }
  function closeAll(chartId) {
    var st = inst[chartId]; if (!st) return;
    st.list.slice().forEach(function (p) { closePopup(st, p); });
  }
  function detach(chartId) {
    var st = inst[chartId]; if (!st) return;
    clearCandleHighlight(st);
    endHold(st);
    st.container.removeEventListener("pointerdown", st.down, true);
    if (st.ticker) { clearInterval(st.ticker); st.ticker = null; }
    st.list.slice().forEach(function (p) { p.closed = true; p.timers.forEach(clearTimeout); if (p.el.parentNode) p.el.parentNode.removeChild(p.el); });
    st.list = [];
    delete inst[chartId];
  }
  window.QT19CandlePopup = { attach: attach, detach: detach, closeAll: closeAll, receive: receive, _count: function (id) { return inst[id] ? inst[id].list.length : 0; } };
})();
"""


def candle_info_popup_script() -> str:
    """Return the popup browser code as text."""
    return CANDLE_INFO_POPUP_JS
