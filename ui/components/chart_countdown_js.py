"""FT-H.26 browser-only countdown renderer; no header or market-data changes."""

CHART_COUNTDOWN_JS = r"""
(function () {
  if (typeof window === "undefined" || window.QT19CreateCountdown) return;
  function formatSeconds(secs) {
    secs = Math.max(0, Math.floor(secs));
    return String(Math.floor(secs / 60)).padStart(2, "0") + ":" + String(secs % 60).padStart(2, "0") + " s";
  }
  window.QT19CreateCountdown = function (el, getChart, getPeriod, reducedMotion) {
    if (!document.querySelector('style[data-qt19="chart-countdown"]')) {
      var style = document.createElement("style");
      style.setAttribute("data-qt19", "chart-countdown");
      style.textContent = [
        ".qt19-countdown{position:absolute;pointer-events:none;white-space:nowrap;display:none;font-family:ui-monospace,'JetBrains Mono',Consolas,monospace;font-weight:800;font-size:1.3rem;line-height:1;letter-spacing:.02em;transform:translateY(-100%);transition:none;border:1px solid currentColor;border-radius:9999px;padding:.42em .7em;background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(255,255,255,.02));text-shadow:0 0 6px currentColor;box-shadow:inset 0 0 12px rgba(0,200,255,.14),0 0 14px rgba(0,200,255,.16)}",
        ".qt19-countdown .digit{position:relative;display:inline-block;min-width:.64em;text-align:center;perspective:260px}.qt19-countdown b{display:inline-block;font-weight:inherit}.qt19-countdown i{position:absolute;left:0;right:0;top:0;font-style:normal;opacity:0;pointer-events:none}",
        ".qt19-countdown .go b{animation:qt19CountdownIn .4s cubic-bezier(.2,.9,.25,1) both;transform-origin:50% 0}.qt19-countdown .go i{animation:qt19CountdownOut .4s ease-in both;transform-origin:50% 100%}",
        "@keyframes qt19CountdownIn{0%{transform:rotateX(90deg);opacity:0}100%{transform:rotateX(0deg);opacity:1}}@keyframes qt19CountdownOut{0%{transform:rotateX(0deg);opacity:1}100%{transform:translateY(55%) rotateX(-70deg);opacity:0}}",
        ".qt19-reduce-motion .qt19-countdown .go b,.qt19-reduce-motion .qt19-countdown .go i,.qt19-countdown.rm .go b,.qt19-countdown.rm .go i{animation:none}"
      ].join("\n");
      document.head.appendChild(style);
    }
    var frame = 0, timer = 0, dead = false, previous = "", cells = [];
    var AXIS_GAP = 6;
    var ownerChart = null, ownerKey = "", reservePending = true;
    function resetPlacement() { reservePending = true; schedule(); }
    el.className = "qt19-countdown";
    function hide() { el.style.display = "none"; }
    function render(text) {
      var rm = !!reducedMotion() || !!document.querySelector(".qt19-reduce-motion");
      el.classList.toggle("rm", rm);
      if (previous === text) return;
      if (cells.length !== text.length) {
        el.textContent = ""; cells = [];
        Array.from(text).forEach(function (ch) {
          var c = document.createElement("span"); c.className = /[0-9]/.test(ch) ? "digit" : "sep";
          c.appendChild(document.createElement("i")); c.appendChild(document.createElement("b"));
          c._v = ""; el.appendChild(c); cells.push(c);
        });
      }
      cells.forEach(function (c, i) {
        var ch = text[i]; if (c._v === ch) return;
        var old = c._v; c._v = ch;
        c.firstChild.textContent = old; c.lastChild.textContent = ch;
        c.classList.remove("go");
        if (old !== "" && !rm && /[0-9]/.test(ch)) { void c.offsetWidth; c.classList.add("go"); }
      });
      el.setAttribute("aria-label", text); previous = text;
    }
    function update() {
      if (dead) return;
      try {
        var chart = getChart();
        if (!chart || !chart.getDataList || !chart.convertToPixel) { hide(); return; }
        var list = chart.getDataList() || [], last = list[list.length - 1];
        if (!last) { hide(); return; }
        var p = getPeriod() || {}, span = p.span || 1;
        var key = String(p.type) + ":" + span;
        if (ownerChart !== chart || ownerKey !== key) {
          if (ownerChart && ownerChart.__qt19CountdownReset === resetPlacement) delete ownerChart.__qt19CountdownReset;
          ownerChart = chart; ownerKey = key; reservePending = true;
          chart.__qt19CountdownReset = resetPlacement;
        }
        var unit = {second:1000,minute:60000,hour:3600000,day:86400000,week:604800000,month:2592000000,year:31536000000};
        var dur = span * (unit[p.type] || 60000), now = Date.now();
        var rem = last.timestamp + dur - now;
        if (rem <= 0) rem = dur - ((now - last.timestamp) % dur);
        render(formatSeconds(Math.max(0, Math.floor(rem / 1000))));
        var pixel = chart.convertToPixel({dataIndex:list.length - 1,value:last.close},{paneId:"candle_pane"});
        if (!pixel || !Number.isFinite(pixel.x) || !Number.isFinite(pixel.y)) { hide(); return; }
        var bs = chart.getBarSpace ? chart.getBarSpace() : null;
        var bar = bs && Number.isFinite(bs.bar) ? bs.bar : 8;
        var host = el.parentElement;
        var box = host ? host.getBoundingClientRect() : null;
        var main = chart.getDom ? chart.getDom("candle_pane", "main") : null;
        var plot = main ? main.getBoundingClientRect() : null;
        if (!box || !plot || plot.width <= 0 || plot.height <= 0 || box.width <= 0) { hide(); return; }
        var left = plot.left - box.left, right = plot.right - box.left;
        var top = plot.top - box.top, bottom = plot.bottom - box.top;
        if (pixel.y < 0 || pixel.y > plot.height) { hide(); return; }
        // Three complete bar widths from the candle's right slot edge to capsule border.
        var candleToBorder = 3.5 * bar;
        var naturalX = left + pixel.x + candleToBorder;
        el.style.visibility = "hidden"; el.style.display = "block";
        var width = el.offsetWidth;
        if (!width || width + 2 * AXIS_GAP > plot.width) { el.style.visibility = ""; hide(); return; }
        if (reservePending) {
          reservePending = false;
          var required = Math.ceil(candleToBorder + width + AXIS_GAP);
          if (required + bar / 2 + AXIS_GAP <= plot.width &&
              typeof chart.setOffsetRightDistance === "function" && typeof chart.scrollToRealTime === "function") {
            var current = chart.getOffsetRightDistance ? chart.getOffsetRightDistance() : 0;
            chart.setOffsetRightDistance(Math.max(required, Number.isFinite(current) ? current : 0));
            chart.scrollToRealTime(0);
            if (chart.getOffsetRightDistance) chart.__qt19LiveOff = chart.getOffsetRightDistance();
            el.style.visibility = ""; hide(); schedule(); return;
          }
        }
        var minX = left + AXIS_GAP;
        var maxX = right - AXIS_GAP - width;
        var x = Math.max(minX, Math.min(maxX, naturalX));
        el.style.color = last.close > last.open ? "#2DC08E" : last.close < last.open ? "#F92855" : "#888888";
        el.style.left = x + "px"; el.style.top = (top + pixel.y - 4) + "px";
        el.style.zIndex = "40";
        // Body stays fully visible. Only trim any outer glow at the plot boundary.
        var clipLeft = Math.max(-24, left - x);
        var clipRight = Math.max(-24, x + width - right);
        el.style.clipPath = "inset(-24px " + clipRight + "px -24px " + clipLeft + "px)";
        el.style.visibility = "";
      } catch (e) { hide(); }
    }
    function schedule() {
      if (!dead && !frame) frame = requestAnimationFrame(function () { frame = 0; update(); });
    }
    function clock() {
      if (dead) return;
      update(); timer = setTimeout(clock, 1000 - (Date.now() % 1000) + 5);
    }
    clock();
    return { schedule:schedule, destroy:function () {
      dead = true; clearTimeout(timer); if (frame) cancelAnimationFrame(frame);
      if (ownerChart && ownerChart.__qt19CountdownReset === resetPlacement) delete ownerChart.__qt19CountdownReset;
      hide();
    }};
  };
})();
"""
