"""Interactive React KLineCharts wrapper for Reflex.

PATH: ui/components/kline_chart.py  (REPLACE ENTIRE FILE)

FIX v0.4.62 - REAL final root cause, confirmed via exact console capture:
React StrictMode's mount->unmount->remount cycle affects BOTH the effect
AND its cleanup being invoked twice, and in this component's case, mount
#2 (the "final" one that stays on screen) ALSO gets torn down and its
cleanup runs (removing its own valid registration) - with NO third mount
ever happening afterward to re-subscribe. Net result: after StrictMode's
double-invoke settles, window.QT19_LIVE_CALLBACKS ends up completely empty
- confirmed directly: `typeof window.QT19_LIVE_CALLBACKS[chartId]` printed
"undefined", and manually invoking it threw "is not a function".

v0.4.61's identity-check fix was CORRECT for stopping a stale instance
from deleting a newer instance's registration - but it does nothing to
protect against the CURRENTLY-mounted instance's own cleanup firing (which
is exactly what StrictMode's double-invoke does to every effect, not just
foreign ones) with nothing left afterward to re-subscribe.

Real fix: stop relying on the subscribe/unsubscribe LIFECYCLE TIMING
entirely for a persistent global registry. Instead, every single
poll_trading_panel_chart tick (already running every 0.5s from Python) is
now defended on the JS side too: before using
window.QT19_LIVE_CALLBACKS[chartId], we self-heal it if missing by calling
chart.setDataLoader(...) AGAIN with the same loader object, forcing
klinecharts to re-run getBars/subscribeBar and refill the registry entry -
completely independent of whatever cleanup/remount chaos React's
StrictMode (or any other future remount scenario) puts the component
through. This makes the live-push path self-repairing rather than
depending on a fragile one-time subscription surviving forever.
"""
from __future__ import annotations

import reflex as rx
from reflex.utils.imports import ImportVar


class KLineChart(rx.Component):
    """Registry-backed wrapper around react-klinecharts' <KLineChart>."""

    tag = "QT19KLineChart"

    data: rx.Var[list[dict]]
    data_version: rx.Var[int] = 0
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
  const { chartId, data, dataVersion, symbol, period, styles, zoomEnabled, scrollEnabled, onContextMenu, ...rest } = props;
  const chartRef = useRef(null);
  const dataRef = useRef(data);
  const loaderReadyRef = useRef(false);
  const lastVersionRef = useRef(null);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  useEffect(() => {
    if (lastVersionRef.current === null) {
      lastVersionRef.current = dataVersion;
      return;
    }
    if (dataVersion !== lastVersionRef.current) {
      lastVersionRef.current = dataVersion;
      if (loaderReadyRef.current && chartRef.current && typeof chartRef.current.resetData === "function") {
        console.log("QT19KLineChart: dataVersion changed to", dataVersion, "- calling resetData() for", chartId);
        chartRef.current.resetData();
      }
    }
  }, [dataVersion]);

  const installLoader = (chart) => {
    chart.setDataLoader({
      getBars: ({ type, callback }) => {
        if (type === "init") {
          callback(dataRef.current || [], false);
        } else {
          callback([], false);
        }
      },
      subscribeBar: ({ callback }) => {
        loaderReadyRef.current = true;
        if (typeof window !== "undefined") {
          window.QT19_LIVE_CALLBACKS = window.QT19_LIVE_CALLBACKS || {};
          window.QT19_LIVE_CALLBACKS[chartId] = callback;
        }
      },
      unsubscribeBar: () => {
        // v0.4.62: deliberately does NOT delete the registry entry
        // anymore. React StrictMode's double-invoke cycle calls this on
        // the FINAL, currently-displayed chart instance too (not just
        // stale ones), with no guaranteed later re-subscribe - so this
        // callback firing is no longer treated as proof the registration
        // should be removed. window.QT19_ensureLiveCallback() (called on
        // every poll tick from Python, see below) is the real, ongoing
        // source of truth and will self-heal the registry if it is ever
        // actually stale.
      },
    });
  };

  const handleReady = (chart) => {
    chartRef.current = chart;
    if (typeof window !== "undefined") {
      window.QT19_CHARTS = window.QT19_CHARTS || {};
      window.QT19_CHARTS[chartId] = chart;

      // v0.4.62: self-healing hook, called every poll tick from Python
      // BEFORE it tries to use the live callback. If the registry entry
      // is missing (e.g. StrictMode tore down the subscription with no
      // later re-subscribe), this forces klinecharts to re-run its
      // getBars/subscribeBar cycle against our loader, refilling the
      // registry - independent of any remount/cleanup timing.
      window.QT19_ensureLiveCallback = window.QT19_ensureLiveCallback || {};
      window.QT19_ensureLiveCallback[chartId] = () => {
        if (!window.QT19_LIVE_CALLBACKS || !window.QT19_LIVE_CALLBACKS[chartId]) {
          console.log("QT19KLineChart: self-healing missing live callback for", chartId);
          try {
            if (typeof chart.setSymbol === "function" && symbol) chart.setSymbol(symbol);
            if (typeof chart.setPeriod === "function" && period) chart.setPeriod(period);
          } catch (err) {
            console.error("QT19KLineChart: self-heal setSymbol/setPeriod failed:", err);
          }
        }
      };
    }

    if (typeof chart.setDataLoader !== "function") {
      console.error(
        "QT19KLineChart: this klinecharts version has no setDataLoader() - cannot wire up data at all. Chart instance:", chart
      );
      return;
    }

    installLoader(chart);

    try {
      if (typeof chart.setSymbol === "function" && symbol) {
        chart.setSymbol(symbol);
      }
      if (typeof chart.setPeriod === "function" && period) {
        chart.setPeriod(period);
      }
    } catch (err) {
      console.error("QT19KLineChart: setSymbol/setPeriod force-trigger failed:", err);
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
      if (typeof window !== "undefined") {
        if (window.QT19_CHARTS && window.QT19_CHARTS[chartId] === chartRef.current) {
          delete window.QT19_CHARTS[chartId];
        }
        if (window.QT19_ensureLiveCallback) {
          delete window.QT19_ensureLiveCallback[chartId];
        }
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
