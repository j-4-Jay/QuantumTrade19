"""New York clock for the page header (status row FT-H.25).

PATH: ui/components/ny_clock.py  (NEW FILE)

Shows the New York date and time as DD-MM-YYYY HH:MM:SS AM/PM with a top-down
flip for every changing digit, glow, seconds in their own color and an IST
difference tag (IST +10.5h in winter, +9.5h in summer, read from the New York
time zone, so no code change is needed when daylight saving changes).
Pure browser code: no server calls, no state. Reduced motion (class
qt19-reduce-motion) switches the flip off.
"""
from __future__ import annotations

import reflex as rx

_CLOCK_JS = r"""(function () {
  if (window.__qt19NyClock) return;
  window.__qt19NyClock = true;
  var TZ = "America/New_York";
  var css = [
    ".qt19-nyc{display:inline-flex;align-items:center;gap:1.7rem;white-space:nowrap;font-family:ui-monospace,'JetBrains Mono',Consolas,monospace;font-weight:800;font-size:1.3rem;line-height:1;letter-spacing:.02em;margin-right:.5rem}",
    ".qt19-nyc .g{display:inline-flex;align-items:center}",
    ".qt19-nyc .pill{display:inline-flex;align-items:center;border-radius:9999px;padding:.42em 1em;background:linear-gradient(180deg,rgba(255,255,255,.07),rgba(255,255,255,.02));backdrop-filter:blur(6px)}",
    ".qt19-nyc .pill.pd{border:1px solid rgba(143,184,255,.4);box-shadow:inset 0 0 12px rgba(80,140,255,.14),0 0 14px rgba(80,140,255,.16)}",
    ".qt19-nyc .pill.pt{gap:.45rem;border:1px solid rgba(0,225,255,.4);box-shadow:inset 0 0 12px rgba(0,200,255,.14),0 0 14px rgba(0,200,255,.16)}",
    ".qt19-nyc .sp{opacity:.55;padding:0 .08em}",
    ".qt19-nyc .d{color:#8FB8FF;text-shadow:0 0 6px rgba(80,140,255,.85),0 0 16px rgba(80,140,255,.45)}",
    ".qt19-nyc .t{color:#FFFFFF;text-shadow:0 0 6px rgba(0,225,255,.9),0 0 18px rgba(0,200,255,.5)}",
    ".qt19-nyc .s{color:#FFB347;text-shadow:0 0 6px rgba(255,160,40,.95),0 0 18px rgba(255,140,0,.55)}",
    ".qt19-nyc .a{color:#B9A4FF;font-size:.8em;text-shadow:0 0 6px rgba(150,120,255,.9),0 0 14px rgba(130,100,255,.5)}",
    ".qt19-nyc .tag{font-size:.5em;font-weight:800;letter-spacing:.06em;color:#7DE3C0;border:1px solid rgba(125,227,192,.55);border-radius:9999px;padding:.28em .7em;text-shadow:0 0 8px rgba(60,220,170,.8);box-shadow:0 0 10px rgba(60,220,170,.25)}",
    ".qt19-fl{position:relative;display:inline-block;min-width:.64em;text-align:center;perspective:260px}",
    ".qt19-fl b{display:inline-block;font-weight:inherit}",
    ".qt19-fl i{position:absolute;left:0;right:0;top:0;font-style:normal;opacity:0;pointer-events:none}",
    ".qt19-fl.go b{animation:qt19FlipIn .4s cubic-bezier(.2,.9,.25,1) both;transform-origin:50% 0}",
    ".qt19-fl.go i{animation:qt19FlipOut .4s ease-in both;transform-origin:50% 100%}",
    "@keyframes qt19FlipIn{0%{transform:rotateX(90deg);opacity:0}100%{transform:rotateX(0deg);opacity:1}}",
    "@keyframes qt19FlipOut{0%{transform:rotateX(0deg);opacity:1}100%{transform:translateY(55%) rotateX(-70deg);opacity:0}}",
    ".qt19-reduce-motion .qt19-fl.go b,.qt19-reduce-motion .qt19-fl.go i{animation:none}"
  ].join("\n");
  var style = document.createElement("style");
  style.setAttribute("data-qt19", "ny-clock");
  style.textContent = css;
  document.head.appendChild(style);

  var fmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true });
  var offFmt = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric" });

  function nyOffsetHours(ms) {
    var o = {};
    offFmt.formatToParts(ms).forEach(function (p) { o[p.type] = p.value; });
    var asUtc = Date.UTC(+o.year, +o.month - 1, +o.day, (+o.hour) % 24, +o.minute, +o.second);
    return Math.round(((asUtc - Math.floor(ms / 1000) * 1000) / 36e5) * 2) / 2;
  }
  function istDiffText(ms) {
    var diff = 5.5 - nyOffsetHours(ms);
    return "IST +" + (Math.round(diff * 10) / 10) + "h";
  }
  function parts(ms) {
    var o = {};
    fmt.formatToParts(ms).forEach(function (p) { o[p.type] = p.value; });
    return { dd: o.day, mm: o.month, yyyy: o.year, hh: o.hour, mi: o.minute, ss: o.second, ap: String(o.dayPeriod || "").toUpperCase() };
  }
  window.QT19_NY_CLOCK_TEST = { nyOffsetHours: nyOffsetHours, istDiffText: istDiffText, parts: parts };

  function cell(cls) {
    var c = document.createElement("span");
    c.className = "qt19-fl " + cls;
    c.appendChild(document.createElement("i"));
    c.appendChild(document.createElement("b"));
    c._v = "";
    return c;
  }
  function setCell(c, v) {
    if (c._v === v) return;
    var old = c._v;
    c._v = v;
    c.firstChild.textContent = old;
    c.lastChild.textContent = v;
    if (old !== "") {
      c.classList.remove("go");
      void c.offsetWidth;
      c.classList.add("go");
    }
  }
  function group(cls) { var g = document.createElement("span"); g.className = "g " + cls; return g; }
  function sep(txt) { var s = document.createElement("span"); s.className = "sp"; s.textContent = txt; return s; }

  function build(el) {
    el.innerHTML = "";
    el.classList.add("qt19-nyc");
    var cells = {};
    var gd = group("d");
    ["d1", "d2", "-", "m1", "m2", "-", "y1", "y2", "y3", "y4"].forEach(function (k) {
      if (k === "-") { gd.appendChild(sep("-")); } else { cells[k] = cell("d"); gd.appendChild(cells[k]); }
    });
    var gt = group("t");
    ["h1", "h2", ":", "n1", "n2"].forEach(function (k) {
      if (k === ":") { gt.appendChild(sep(":")); } else { cells[k] = cell("t"); gt.appendChild(cells[k]); }
    });
    var gs = group("s");
    gs.appendChild(sep(":"));
    cells.s1 = cell("s"); cells.s2 = cell("s");
    gs.appendChild(cells.s1); gs.appendChild(cells.s2);
    var ga = group("a");
    cells.ap = cell("a");
    ga.appendChild(cells.ap);
    var tag = document.createElement("span");
    tag.className = "tag";
    tag.title = "New York time. IST is ahead by this many hours.";
    var pd = document.createElement("span"); pd.className = "pill pd"; pd.appendChild(gd);
    var pt = document.createElement("span"); pt.className = "pill pt"; pt.appendChild(gt); pt.appendChild(gs); pt.appendChild(ga);
    el.appendChild(pd); el.appendChild(pt); el.appendChild(tag);
    el._cells = cells;
    el._tag = tag;
    el._built = true;
    el._tagMin = -1;
  }

  function tick() {
    var el = document.getElementById("qt19-ny-clock");
    if (!el) return;
    if (!el._built) build(el);
    var now = Date.now();
    var p = parts(now);
    var c = el._cells;
    setCell(c.d1, p.dd[0]); setCell(c.d2, p.dd[1]);
    setCell(c.m1, p.mm[0]); setCell(c.m2, p.mm[1]);
    setCell(c.y1, p.yyyy[0]); setCell(c.y2, p.yyyy[1]); setCell(c.y3, p.yyyy[2]); setCell(c.y4, p.yyyy[3]);
    setCell(c.h1, p.hh[0]); setCell(c.h2, p.hh[1]);
    setCell(c.n1, p.mi[0]); setCell(c.n2, p.mi[1]);
    setCell(c.s1, p.ss[0]); setCell(c.s2, p.ss[1]);
    setCell(c.ap, p.ap);
    var minute = Math.floor(now / 60000);
    if (el._tagMin !== minute) { el._tagMin = minute; el._tag.textContent = istDiffText(now); }
  }
  setInterval(tick, 200);
  tick();
})();
"""


def qt19_ny_clock() -> rx.Component:
    return rx.box(id="qt19-ny-clock", flex_shrink="0")


def qt19_ny_clock_script() -> rx.Component:
    """Loaded ONCE for the whole app (quantumtrade19/quantumtrade19.py). A script placed
    inside the header does not run when the header is built after the login screen."""
    return rx.script(_CLOCK_JS)
