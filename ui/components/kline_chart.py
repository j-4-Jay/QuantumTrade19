"""Interactive React KLineCharts wrapper for Reflex.

PATH: ui/components/kline_chart.py  (REPLACE ENTIRE FILE)

FIX v0.5.0-r5 - chart now calls the real, documented klinecharts v10
instance API `chart.setTimezone('America/New_York')`
(https://klinecharts.com/en-US/api/instance/setTimezone) right after the
chart is ready. This converts every DISPLAYED time on the chart - x-axis
labels, the crosshair's time readout, and the OHLC tooltip's "Time:" line
- to America/New_York with automatic DST, while every underlying data
timestamp (candles, POI overlays) stays exactly as the broker/engine
already computed it in UTC epoch ms. No data conversion needed anywhere
else - this is purely a display-layer instruction to klinecharts itself.

FIX v0.5.0-r4 (carried forward) - qt19_poi_vline draws its "Prv. TF
Start"/"Prv. TF End" (or custom line name) label near the bottom of the
chart, offset by `data.lane` so nearby markers' labels don't overlap.

FIX v0.4.62 (carried forward, unchanged) - self-healing live-callback
registry via window.QT19_ensureLiveCallback.
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

    poi_overlays: rx.Var[list[dict]] = []
    poi_overlays_version: rx.Var[int] = 0

    def add_imports(self) -> dict[str, list[ImportVar]]:
        return {
            "react": [ImportVar(tag="useEffect"), ImportVar(tag="useRef")],
            "react-klinecharts": [
                ImportVar(tag="KLineChart", alias="RKLineChart"),
                ImportVar(tag="registerOverlay"),
            ],
        }

    def get_event_triggers(self) -> dict:
        return {
            **super().get_event_triggers(),
            "on_context_menu": lambda e: [e.clientX, e.clientY],
        }

    def add_custom_code(self) -> list[str]:
        return [
            r"""
if (typeof window !== "undefined" && !window.QT19_OVERLAYS_REGISTERED) {
  window.QT19_OVERLAYS_REGISTERED = true;


  registerOverlay({
    name: "qt19_poi_line",
    totalStep: 2,
    needDefaultPointFigure: false,
    needDefaultXAxisFigure: false,
    needDefaultYAxisFigure: false,
    createPointFigures: ({ coordinates, bounding, overlay }) => {
      if (coordinates.length < 1) return [];
      const data = overlay.extendData || {};
      const y = coordinates[0].y;
      const color = data.color || "#38BDF8";
      const width = data.width || 1;
      const figures = [
        {
          type: "line",
          attrs: { coordinates: [{ x: 0, y }, { x: bounding.width, y }] },
          styles: { color: color, size: width, style: "dashed" },
        },
      ];
      if (data.label) {
        figures.push({
          type: "text",
          attrs: {
            x: bounding.width - 6,
            y: y - 4,
            text: data.label,
            align: "right",
            baseline: "bottom",
          },
          styles: { color: color, size: 11, backgroundColor: "rgba(10,16,26,0.65)" },
        });
      }
      return figures;
    },
  });


  registerOverlay({
    name: "qt19_poi_vline",
    totalStep: 2,
    needDefaultPointFigure: false,
    needDefaultXAxisFigure: false,
    needDefaultYAxisFigure: false,
    createPointFigures: ({ coordinates, bounding, overlay }) => {
      if (coordinates.length < 1) return [];
      const data = overlay.extendData || {};
      const x = coordinates[0].x;
      const color = data.color || "#38BDF8";
      const dashed = data.dashed !== false;
      const lane = data.lane || 0;
      const figures = [
        {
          type: "line",
          attrs: { coordinates: [{ x, y: 0 }, { x, y: bounding.height }] },
          styles: { color: color, size: 1, style: dashed ? "dashed" : "solid" },
        },
      ];
      if (data.label) {
        const y = bounding.height - 8 - lane * 14;
        figures.push({
          type: "text",
          attrs: {
            x: x + 4,
            y: y,
            text: data.label,
            align: "left",
            baseline: "bottom",
          },
          styles: { color: color, size: 10, backgroundColor: "rgba(10,16,26,0.65)" },
        });
      }
      return figures;
    },
  });


  registerOverlay({
    name: "qt19_poi_zone",
    totalStep: 3,
    needDefaultPointFigure: false,
    needDefaultXAxisFigure: false,
    needDefaultYAxisFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      if (coordinates.length < 2) return [];
      const data = overlay.extendData || {};
      const color = data.color || "rgba(150,150,150,0.22)";
      const dashed = !!data.dashed;
      const figures = [
        {
          type: "polygon",
          attrs: {
            coordinates: [
              { x: coordinates[0].x, y: coordinates[0].y },
              { x: coordinates[1].x, y: coordinates[0].y },
              { x: coordinates[1].x, y: coordinates[1].y },
              { x: coordinates[0].x, y: coordinates[1].y },
            ],
          },
          styles: {
            style: dashed ? "stroke" : "fill",
            color: color,
            borderColor: color,
            borderSize: dashed ? 1 : 0,
            borderStyle: dashed ? "dashed" : "solid",
          },
        },
      ];
      if (data.label) {
        figures.push({
          type: "text",
          attrs: { x: coordinates[0].x + 4, y: coordinates[0].y + 12, text: data.label },
          styles: { color: data.textColor || "#dce8f7", size: 11 },
        });
      }
      return figures;
    },
  });
}


function QT19KLineChart(props) {
  const {
    chartId, data, dataVersion, symbol, period, styles, zoomEnabled,
    scrollEnabled, onContextMenu, poiOverlays, poiOverlaysVersion, ...rest
  } = props;
  const chartRef = useRef(null);
  const dataRef = useRef(data);
  const loaderReadyRef = useRef(false);
  const lastVersionRef = useRef(null);
  const overlayIdsRef = useRef([]);
  const lastPoiVersionRef = useRef(null);


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
        chartRef.current.resetData();
      }
    }
  }, [dataVersion]);


  const rebuildPoiOverlays = () => {
    const chart = chartRef.current;
    if (!chart || typeof chart.removeOverlay !== "function") return;
    overlayIdsRef.current.forEach((id) => {
      try { chart.removeOverlay(id); } catch (err) { /* already gone */ }
    });
    overlayIdsRef.current = [];
    const list = poiOverlays || [];
    list.forEach((item) => {
      try {
        if (item.kind === "zone") {
          const endTime = item.end_time || (Date.now() + 365 * 24 * 60 * 60 * 1000);
          const id = chart.createOverlay({
            name: "qt19_poi_zone",
            points: [
              { timestamp: item.start_time, value: item.price_high },
              { timestamp: endTime, value: item.price_low },
            ],
            lock: true,
            extendData: { color: item.color, dashed: item.dashed, label: item.label },
          });
          if (id) overlayIdsRef.current.push(id);
        } else if (item.kind === "vline") {
          const id = chart.createOverlay({
            name: "qt19_poi_vline",
            points: [{ timestamp: item.timestamp, value: 0 }],
            lock: true,
            extendData: { color: item.color, dashed: item.dashed, label: item.label, lane: item.lane },
          });
          if (id) overlayIdsRef.current.push(id);
        } else {
          const id = chart.createOverlay({
            name: "qt19_poi_line",
            points: [{ value: item.price }],
            lock: true,
            extendData: { color: item.color, width: item.width, label: item.label },
          });
          if (id) overlayIdsRef.current.push(id);
        }
      } catch (err) {
        console.error("QT19KLineChart: failed to create POI overlay", item, err);
      }
    });
  };


  useEffect(() => {
    if (lastPoiVersionRef.current === null) {
      lastPoiVersionRef.current = poiOverlaysVersion;
      if (chartRef.current) rebuildPoiOverlays();
      return;
    }
    if (poiOverlaysVersion !== lastPoiVersionRef.current) {
      lastPoiVersionRef.current = poiOverlaysVersion;
      rebuildPoiOverlays();
    }
  }, [poiOverlaysVersion]);


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
        // v0.4.62: deliberately does NOT delete the registry entry -
        // see prior version's docstring. Unchanged by this patch.
      },
    });
  };


  const handleReady = (chart) => {
    chartRef.current = chart;
    if (typeof window !== "undefined") {
      window.QT19_CHARTS = window.QT19_CHARTS || {};
      window.QT19_CHARTS[chartId] = chart;


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


    if (typeof chart.setTimezone === "function") {
      try {
        chart.setTimezone("America/New_York");
      } catch (err) {
        console.error("QT19KLineChart: setTimezone('America/New_York') failed:", err);
      }
    } else {
      console.warn("QT19KLineChart: this klinecharts version has no setTimezone() - chart will show browser-local time instead of NY time.");
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


    rebuildPoiOverlays();
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
