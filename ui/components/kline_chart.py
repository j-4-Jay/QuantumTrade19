"""Interactive React KLineCharts wrapper for Reflex.

PATH: ui/components/kline_chart.py

CHANGE (v0.3.6 - real Chart-instance registry): react-klinecharts v1.0.1
(wrapping klinecharts v10.0.2) exposes a real forwardRef + onReady(chart)
callback that hands back the actual klinecharts `Chart` instance. This file
now defines a tiny wrapper component that captures that instance into
window.QT19_CHARTS[chartId] on mount and removes it on unmount.

This replaces the old approach (scanning the DOM for an object with a
setStyles/scrollToRealTime method), which was unreliable and only ever
worked for CSS-level changes (background color). Grid and Day/Night are now
driven declaratively through the real `styles` prop (see
ui/components/trading_panel_chart.py + AppState.trading_panel_styles).
Reset View, Go Live, and the Follow-Live candle-close snap use the real
Chart instance via window.QT19_CHARTS[chartId], called from
state/app_state_mixins/trading_panel_mixin.py through rx.call_script.
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

    def add_custom_code(self) -> list[str]:
        return [
            r"""
function QT19KLineChart(props) {
  const { chartId, data, symbol, period, styles, zoomEnabled, scrollEnabled, ...rest } = props;
  const chartRef = useRef(null);

  const handleReady = (chart) => {
    chartRef.current = chart;
    if (typeof window !== "undefined") {
      window.QT19_CHARTS = window.QT19_CHARTS || {};
      window.QT19_CHARTS[chartId] = chart;
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
  );
}
"""
        ]


kline_chart = KLineChart.create
