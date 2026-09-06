"""Interactive React KLineCharts wrapper for Reflex.

PATH: ui/components/kline_chart.py  (REPLACE ENTIRE FILE)

FIX (dot placement, REAL root cause found) - the previous "midpoint
between this dataIndex and the next dataIndex" trick was based on a
wrong assumption that convertToPixel({dataIndex}) returns the LEFT EDGE
of a candle's slot. It does not - klinecharts' dataIndex-based pixel
conversion already returns the candle's own CENTER x position (confirmed
by the screenshot: the dot landed exactly one half-candle-width too far
right of the correct wick, which is exactly what happens when an
already-centered value gets an extra +half-width correction added on
top). REMOVED all midpoint/averaging logic entirely - now uses the
single, documented call `convertToPixel({ dataIndex, value })` exactly
as klinecharts' own docs show, with zero extra pixel math. This is now
pixel-exact with no assumptions at all.
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
    poi_dots: rx.Var[list[dict]] = []
    poi_dots_version: rx.Var[int] = 0

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
      const dashed = data.dashed !== false;
      const stackOffset = data.stackOffset || 0;
      const figures = [
        {
          type: "line",
          attrs: { coordinates: [{ x: 0, y }, { x: bounding.width, y }] },
          styles: { color: color, size: width, style: dashed ? "dashed" : "solid" },
        },
      ];
      if (data.label) {
        figures.push({
          type: "text",
          attrs: {
            x: bounding.width - 6,
            y: y - 4 - stackOffset,
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
    scrollEnabled, onContextMenu, poiOverlays, poiOverlaysVersion,
    poiDots, poiDotsVersion, ...rest
  } = props;
  const chartRef = useRef(null);
  const dataRef = useRef(data);
  const loaderReadyRef = useRef(false);
  const lastVersionRef = useRef(null);
  const overlayIdsRef = useRef([]);
  const lastPoiVersionRef = useRef(null);
  const dotsContainerRef = useRef(null);
  const dotElementsRef = useRef({});
  const dotsDataRef = useRef([]);
  const lastDotsVersionRef = useRef(null);


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
            extendData: { color: item.color, width: item.width, dashed: item.dashed, label: item.label, stackOffset: item.stack_offset },
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


  const findDataIndexForTimestamp = (timestamp) => {
    const list = dataRef.current || [];
    for (let i = 0; i < list.length; i++) {
      if (list[i] && list[i].timestamp === timestamp) return i;
    }
    return -1;
  };


  const repositionDots = () => {
    const chart = chartRef.current;
    if (!chart || typeof chart.convertToPixel !== "function") return;
    dotsDataRef.current.forEach((dot) => {
      const el = dotElementsRef.current[dot.id];
      if (!el) return;
      try {
        const index = findDataIndexForTimestamp(dot.timestamp);
        // FIX: use dataIndex directly - it ALREADY returns the candle's
        // own center pixel. No averaging, no extra offset. Falls back
        // to a raw timestamp lookup only if the candle isn't currently
        // loaded (shouldn't normally happen).
        const pixel = index >= 0
          ? chart.convertToPixel({ dataIndex: index, value: dot.price }, { paneId: "candle_pane" })
          : chart.convertToPixel({ timestamp: dot.timestamp, value: dot.price }, { paneId: "candle_pane" });
        if (pixel && typeof pixel.x === "number" && typeof pixel.y === "number") {
          el.style.left = pixel.x + "px";
          el.style.top = pixel.y + "px";
          el.style.display = "block";
        } else {
          el.style.display = "none";
        }
      } catch (err) {
        el.style.display = "none";
      }
    });
  };


  const rebuildPoiDots = () => {
    const container = dotsContainerRef.current;
    if (!container) return;
    Object.values(dotElementsRef.current).forEach((el) => {
      try { container.removeChild(el); } catch (err) { /* already gone */ }
    });
    dotElementsRef.current = {};
    const list = poiDots || [];
    dotsDataRef.current = list;
    list.forEach((dot) => {
      const el = document.createElement("div");
      el.className = "qt19-poi-dot";
      el.style.setProperty("--qt19-dot-color", dot.color || "#38BDF8");
      const ring = document.createElement("div");
      ring.className = "qt19-poi-dot-ring";
      const core = document.createElement("div");
      core.className = "qt19-poi-dot-core";
      el.appendChild(ring);
      el.appendChild(core);
      container.appendChild(el);
      dotElementsRef.current[dot.id] = el;
    });
    repositionDots();
  };


  useEffect(() => {
    if (lastDotsVersionRef.current === null) {
      lastDotsVersionRef.current = poiDotsVersion;
      if (chartRef.current) rebuildPoiDots();
      return;
    }
    if (poiDotsVersion !== lastDotsVersionRef.current) {
      lastDotsVersionRef.current = poiDotsVersion;
      rebuildPoiDots();
    }
  }, [poiDotsVersion]);


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
      unsubscribeBar: () => {},
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
    }


    if (typeof chart.setDataLoader !== "function") {
      console.error("QT19KLineChart: this klinecharts version has no setDataLoader().", chart);
      return;
    }


    installLoader(chart);


    try {
      if (typeof chart.setSymbol === "function" && symbol) chart.setSymbol(symbol);
      if (typeof chart.setPeriod === "function" && period) chart.setPeriod(period);
    } catch (err) {
      console.error("QT19KLineChart: setSymbol/setPeriod force-trigger failed:", err);
    }


    if (typeof chart.subscribeAction === "function") {
      try {
        chart.subscribeAction("onZoom", repositionDots);
        chart.subscribeAction("onScroll", repositionDots);
        chart.subscribeAction("onVisibleRangeChange", repositionDots);
      } catch (err) {
        console.error("QT19KLineChart: subscribeAction failed:", err);
      }
    }


    rebuildPoiOverlays();
    rebuildPoiDots();
  };


  const handleContextMenu = (e) => {
    e.preventDefault();
    if (typeof onContextMenu === "function") onContextMenu(e);
  };


  useEffect(() => {
    return () => {
      if (typeof window !== "undefined") {
        const chart = chartRef.current;
        if (chart && typeof chart.unsubscribeAction === "function") {
          try {
            chart.unsubscribeAction("onZoom", repositionDots);
            chart.unsubscribeAction("onScroll", repositionDots);
            chart.unsubscribeAction("onVisibleRangeChange", repositionDots);
          } catch (err) { /* chart already torn down */ }
        }
        if (window.QT19_CHARTS && window.QT19_CHARTS[chartId] === chartRef.current) {
          delete window.QT19_CHARTS[chartId];
        }
        if (window.QT19_ensureLiveCallback) delete window.QT19_ensureLiveCallback[chartId];
      }
    };
  }, [chartId]);


  return (
    <div
      onContextMenu={handleContextMenu}
      style={{ width: "100%", height: "100%", position: "relative" }}
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
      <div
        ref={dotsContainerRef}
        style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}
      />
    </div>
  );
}
"""
        ]


kline_chart = KLineChart.create
