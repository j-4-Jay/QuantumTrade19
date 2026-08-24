"""Interactive React KLineCharts wrapper for Reflex.

PATH: ui/components/kline_chart.py

The Trading Panel chart menu is browser-local and persists in localStorage.
"""
from __future__ import annotations

import reflex as rx
from reflex.utils.imports import ImportVar


class KLineChart(rx.Component):
    """Named react-klinecharts component with a local chart-control hook."""

    library = "react-klinecharts"
    tag = "KLineChart"
    is_default = False

    data: rx.Var[list[dict]]
    symbol: rx.Var[dict]
    period: rx.Var[dict]

    def add_imports(self) -> dict[str, list[ImportVar]]:
        """Import the hook as a named React import for Reflex-generated JSX."""
        return {"react": [ImportVar(tag="useEffect")]}

    def add_custom_code(self) -> list[str]:
        return [
            r"""
const QT19_KLINE_SETTINGS_KEY = "qt19:kline-controls:v3";
const QT19_KLINE_DEFAULTS = { style: "candle", grid: true, zoom: true, pan: true, barSpace: 6, theme: "night" };

function qt19ReadSettings() {
  try { return { ...QT19_KLINE_DEFAULTS, ...JSON.parse(localStorage.getItem(QT19_KLINE_SETTINGS_KEY) || "{}") }; }
  catch (_) { return { ...QT19_KLINE_DEFAULTS }; }
}

function qt19WriteSettings(settings) {
  try { localStorage.setItem(QT19_KLINE_SETTINGS_KEY, JSON.stringify(settings)); } catch (_) {}
}

function qt19Call(chart, names, ...args) {
  if (!chart) return undefined;
  for (const name of names) {
    if (typeof chart[name] === "function") {
      try { return chart[name](...args); } catch (_) {}
    }
  }
  return undefined;
}

function qt19FindChart(root) {
  for (const node of [root, ...root.querySelectorAll("*")]) {
    for (const key of Object.keys(node)) {
      const value = node[key];
      if (value && typeof value === "object" && (typeof value.setStyles === "function" || typeof value.scrollToRealTime === "function")) return value;
    }
  }
  return null;
}

function qt19ApplySettings(root, chart, settings) {
  const day = settings.theme === "day";
  const background = day ? "#f7f9fc" : "#101722";
  const foreground = day ? "#152238" : "#dce8f7";
  const gridColor = day ? "rgba(56,78,108,.14)" : "rgba(151,176,207,.15)";
  root.style.background = background;
  root.style.color = foreground;
  root.dataset.qt19Style = settings.style;
  root.dataset.qt19Grid = String(settings.grid);
  root.dataset.qt19Zoom = String(settings.zoom);
  root.dataset.qt19Pan = String(settings.pan);

  qt19Call(chart, ["setStyles", "setStyleOptions"], {
    grid: { horizontal: { color: settings.grid ? gridColor : "transparent" }, vertical: { color: settings.grid ? gridColor : "transparent" } },
    candle: { type: settings.style === "bar" ? "stroke" : "candle_solid", bar: { upColor: "#16c784", downColor: "#ea3943", noChangeColor: "#8b98aa" } },
    xAxis: { axisLine: { color: gridColor }, tickLine: { color: gridColor }, tickText: { color: foreground } },
    yAxis: { axisLine: { color: gridColor }, tickLine: { color: gridColor }, tickText: { color: foreground } }
  });
  qt19Call(chart, ["setBarSpace"], settings.barSpace);
  qt19Call(chart, ["setScrollEnabled", "setPanEnabled"], settings.pan);
  qt19Call(chart, ["setZoomEnabled"], settings.zoom);
}

function qt19InstallKlineControls(chartId) {
  const root = document.getElementById(chartId);
  if (!root || root.dataset.qt19ControlsInstalled === "true") return;
  root.dataset.qt19ControlsInstalled = "true";
  root.style.position = "relative";
  root.style.overflow = "hidden";
  let chart = null;
  let settings = qt19ReadSettings();
  let menu = null;

  const apply = () => {
    chart = chart || qt19FindChart(root);
    qt19ApplySettings(root, chart, settings);
  };
  const close = () => { if (menu) menu.remove(); menu = null; };
  const divider = () => {
    const line = document.createElement("div");
    line.style.cssText = "height:1px;background:rgba(255,255,255,.13);margin:4px 0";
    return line;
  };
  const item = (label, action, selected) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = (selected ? "✓  " : "") + label;
    button.style.cssText = "display:block;width:100%;border:0;background:" + (selected ? "rgba(243,194,66,.18)" : "transparent") + ";color:#eef5ff;text-align:left;padding:8px 12px;font:12px system-ui,Segoe UI,sans-serif;cursor:pointer;white-space:nowrap";
    button.onmouseenter = () => { button.style.background = "rgba(243,194,66,.22)"; };
    button.onmouseleave = () => { button.style.background = selected ? "rgba(243,194,66,.18)" : "transparent"; };
    button.onclick = (event) => { event.stopPropagation(); action(); close(); };
    return button;
  };
  const open = (x, y) => {
    close();
    menu = document.createElement("div");
    menu.style.cssText = "position:fixed;z-index:9999;min-width:200px;padding:5px;background:rgba(15,23,35,.98);border:1px solid rgba(243,194,66,.43);border-radius:10px;box-shadow:0 18px 46px rgba(0,0,0,.45);backdrop-filter:blur(14px)";
    const set = (patch) => { settings = { ...settings, ...patch }; qt19WriteSettings(settings); apply(); };
    menu.append(item("Candle", () => set({ style: "candle" }), settings.style === "candle"));
    menu.append(item("Bar", () => set({ style: "bar" }), settings.style === "bar"));
    menu.append(divider());
    menu.append(item(settings.grid ? "Hide grid" : "Show grid", () => set({ grid: !settings.grid }), settings.grid));
    menu.append(item(settings.zoom ? "Disable zoom" : "Enable zoom", () => set({ zoom: !settings.zoom }), settings.zoom));
    menu.append(item(settings.pan ? "Disable pan" : "Enable pan", () => set({ pan: !settings.pan }), settings.pan));
    menu.append(divider());
    menu.append(item("Decrease candle width", () => set({ barSpace: Math.max(2, settings.barSpace - 1) }), false));
    menu.append(item("Increase candle width", () => set({ barSpace: Math.min(24, settings.barSpace + 1) }), false));
    menu.append(divider());
    menu.append(item("Reset / auto-scale", () => { qt19Call(chart || qt19FindChart(root), ["resetData", "reset", "resetView"]); }, false));
    menu.append(item("Go to real-time", () => { qt19Call(chart || qt19FindChart(root), ["scrollToRealTime", "scrollToLatest"], 0); }, false));
    menu.append(item(settings.theme === "night" ? "Chart day mode" : "Chart night mode", () => set({ theme: settings.theme === "night" ? "day" : "night" }), false));
    document.body.appendChild(menu);
    const rect = menu.getBoundingClientRect();
    menu.style.left = Math.min(x, window.innerWidth - rect.width - 8) + "px";
    menu.style.top = Math.min(y, window.innerHeight - rect.height - 8) + "px";
  };

  root.addEventListener("contextmenu", (event) => { event.preventDefault(); event.stopPropagation(); open(event.clientX, event.clientY); });
  root.addEventListener("dblclick", () => qt19Call(chart || qt19FindChart(root), ["resetData", "reset", "resetView"]));
  document.addEventListener("pointerdown", (event) => { if (menu && !menu.contains(event.target)) close(); }, true);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  const observer = new MutationObserver(apply);
  observer.observe(root, { childList: true, subtree: true });
  requestAnimationFrame(() => { apply(); setTimeout(apply, 250); setTimeout(apply, 1000); });
}
"""
        ]

    def add_hooks(self) -> list[str]:
        return [
            """
useEffect(() => {
  qt19InstallKlineControls("qt19-trading-panel-kline");
}, []);
"""
        ]


kline_chart = KLineChart.create
