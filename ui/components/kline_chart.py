"""Interactive React KLineCharts wrapper for Reflex.

PATH: ui/components/kline_chart.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.8 - fix right-click menu not opening): klinecharts renders on
an HTML <canvas> and calls preventDefault() on the browser's native
"contextmenu" event itself (to suppress the OS/browser right-click menu).
Radix's rx.context_menu relies on that same native event to detect a
right-click, so it was silently never firing - hence the previous menu
"not opening" at all.

Fix: this wrapper now attaches its OWN onContextMenu handler on the
wrapping <div> (one level above the chart's own canvas). React's synthetic
event system still bubbles this handler even though klinecharts already
called preventDefault() on the underlying native event (preventDefault
does not stop propagation/bubbling - only stopPropagation would, and
klinecharts does not call that). This handler calls preventDefault() again
defensively, then invokes a real Reflex event trigger (on_context_menu)
with the click's screen coordinates, which state/app_state_mixins/
trading_panel_mixin.py uses to open a fully custom, Reflex-rendered menu
(see ui/pages/trading_panel.py) - no dependency on Radix's native-event
detection at all anymore.
"""
from __future__ import annotations

import reflex as rx
from reflex.utils.imports import ImportVar


class KLineChart(rx.Component):
    """Registry-backed wrapper around react-klinecharts' <KLineChart>."""

    tag = "QT19KLineChart"

    data: rx.Var[list[dict]]
    symbol: rx.Var[dict]
    period: rx.Var[dict]
    styles: rx.Var[dict]
    zoom_enabled: rx.Var[bool] = True
    scroll_enabled: rx.Var[bool] = True
    chart_id: rx.Var[str]

    def add_imports(self) -> dict[str, list[ImportVar]]:
        return {
            "react": [ImportVar(tag="useEffect"), ImportVar(tag="useRef")],
            "react-klinecharts": [ImportVar(tag="KLineChart", alias="RKLineChart")],
        }

    def get_event_triggers(self) -> dict:
        return {
            **super().get_event_triggers(),
            "on_context_menu": lambda e: [e.clientX, e.clientY],
        }

    def add_custom_code(self) -> list[str]:
        return [
            r"""
function QT19KLineChart(props) {
  const { chartId, data, symbol, period, styles, zoomEnabled, scrollEnabled, onContextMenu, ...rest } = props;
  const chartRef = useRef(null);

  const handleReady = (chart) => {
    chartRef.current = chart;
    if (typeof window !== "undefined") {
      window.QT19_CHARTS = window.QT19_CHARTS || {};
      window.QT19_CHARTS[chartId] = chart;
    }
  };

  const handleContextMenu = (e) => {
    e.preventDefault();
    if (typeof onContextMenu === "function") {
      onContextMenu(e);
    }
  };

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.QT19_CHARTS) {
        delete window.QT19_CHARTS[chartId];
      }
    };
  }, [chartId]);

  return (
    <div
      onContextMenu={handleContextMenu}
      style={{ width: "100%", height: "100%" }}
    >
      <RKLineChart
        data={data}
        symbol={symbol}
        period={period}
        styles={styles}
        zoomEnabled={zoomEnabled}
        scrollEnabled={scrollEnabled}
        onReady={handleReady}
        {...rest}
      />
    </div>
  );
}
"""
        ]


kline_chart = KLineChart.create
