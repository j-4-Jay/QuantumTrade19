# D:\Jay\Works\Jay\QuantumTrade19\QuantumTrade19\quantumtrade19\docs\# react-klinecharts README.md


# react-klinecharts

A flexible React wrapper for [KlineCharts](https://klinecharts.com) with hooks, declarative sub-components, and full TypeScript support.

[Live Demo](https://nemezzizz.github.io/react-klinecharts/)

- Declarative props for all reactive chart settings
- `<KLineChart.Indicator>`, `<KLineChart.Overlay>`, `<KLineChart.Widget>` and `<KLineChart.YAxis>` sub-components
- Hooks: `useKLineChart`, `useIndicator`, `useOverlay`, `useYAxis`, `useChartEvent`, `useCrosshair`, `useVisibleRange`, `useBarSpace`, `useDataList`, `usePane`, `useYAxes`
- **Strongly typed event callbacks** — no more `as Crosshair` casts
- Full imperative access via ref
- Re-exports all klinecharts types and utilities
- StrictMode-safe, no extra dependencies (klinecharts manages its own `ResizeObserver`)

## Installation

```bash
pnpm add react-klinecharts
# or
npm install react-klinecharts
```

Peer dependencies: `react >= 17`, `react-dom >= 17`.

## Quick Start

```tsx
import { KLineChart, type Chart } from "react-klinecharts";
import { useRef } from "react";

function App() {
  const chartRef = useRef<Chart>(null);

  const data = [
    { timestamp: 1680000000000, open: 28000, high: 28500, low: 27800, close: 28200, volume: 100 },
    // ...
  ]

  return (
    <KLineChart
      ref={chartRef}
      data={data}
      symbol={{ ticker: "BTC/USDT" }}
      period={{ type: "minute", span: 15 }}
      style={{ width: "100%", height: 600 }}
    >
      <KLineChart.Indicator value={{ name: "MA", calcParams: [5, 10, 30] }} />
      <KLineChart.Indicator value="VOL" pane={{ height: 80 }} />
    </KLineChart>
  );
}
```

## API Reference

### `<KLineChart>`

The core component. Manages chart lifecycle, provides context for hooks and sub-components.

All standard HTML `div` attributes (`className`, `style`, `id`, etc.) are passed through to the container element. The native DOM `onScroll` handler is passed through unchanged; chart scroll events use [`onChartScroll`](#event-callbacks) instead.

#### Init-only Props

| Prop | Type | Description |
|------|------|-------------|
| `options` | `Options` | Chart initialization options. Applied once on mount. |

#### Data Props

| Prop | Type | Description |
|------|------|-------------|
| `data` | `KLineData[]` | Static data array. Replacing the array re-applies the data (use `dataLoader` for streaming). |
| `dataLoader` | `DataLoader` | Data loader with `getBars`, `subscribeBar`, `unsubscribeBar`. Calls `setDataLoader`. |
| `symbol` | `SymbolInfo` | Symbol info (ticker, precision). Calls `setSymbol`. |
| `period` | `Period` | Time period (`{ type, span }`). Calls `setPeriod`. |

#### Reactive Props

These props are synced to the chart instance via `useEffect`. Changing them updates the chart without re-initialization.

| Prop | Type | Chart Method |
|------|------|-------------|
| `styles` | `string \| DeepPartial<Styles>` | `setStyles()` |
| `locale` | `string` | `setLocale()` |
| `timezone` | `string` | `setTimezone()` |
| `formatter` | `Partial<Formatter>` | `setFormatter()` |
| `thousandsSeparator` | `Partial<ThousandsSeparator>` | `setThousandsSeparator()` |
| `decimalFold` | `Partial<DecimalFold>` | `setDecimalFold()` |
| `zoomEnabled` | `boolean` | `setZoomEnabled()` |
| `scrollEnabled` | `boolean` | `setScrollEnabled()` |
| `zoomAnchor` | `ZoomAnchorType \| Partial<ZoomAnchor>` | `setZoomAnchor()` |
| `offsetRightDistance` | `number` | `setOffsetRightDistance()` |
| `maxOffsetLeftDistance` | `number` | `setMaxOffsetLeftDistance()` |
| `maxOffsetRightDistance` | `number` | `setMaxOffsetRightDistance()` |
| `leftMinVisibleBarCount` | `number` | `setLeftMinVisibleBarCount()` |
| `rightMinVisibleBarCount` | `number` | `setRightMinVisibleBarCount()` |
| `barSpace` | `number` | `setBarSpace()` |
| `hotkey` | `Partial<Hotkey>` | `setHotkey()` |
| `xAxis` | `XAxisOverride` | `overrideXAxis()` |
| `yAxis` | `YAxisOverride` | `overrideYAxis()` |

#### Event Callbacks

Event callbacks are **strongly typed**: the `data` argument matches the payload klinecharts emits for that action. For example, `onCrosshairChange` receives a `Crosshair` and `onCandleBarClick` receives the clicked `KLineData` — no casts required.

| Prop | Signature | Description |
|------|-----------|-------------|
| `onReady` | `(chart: Chart) => void` | Fired after chart initialization |
| `onZoom` | `(data: { scale: number }) => void` | Chart zoom event |
| `onChartScroll` | `(data: { distance: number }) => void` | Chart scroll event (klinecharts `onScroll` action; renamed to avoid colliding with the native DOM `onScroll`) |
| `onVisibleRangeChange` | `(data: VisibleRange) => void` | Visible data range changed |
| `onCrosshairChange` | `(data: Crosshair) => void` | Crosshair position changed |
| `onCandleBarClick` | `(data: KLineData) => void` | Candle bar clicked |
| `onPaneDrag` | `(data: { paneId: string }) => void` | Pane drag event |
| `onCandleTooltipFeatureClick` | `(data: unknown) => void` | Candle tooltip feature clicked |
| `onIndicatorTooltipFeatureClick` | `(data: unknown) => void` | Indicator tooltip feature clicked |
| `onCrosshairFeatureClick` | `(data: unknown) => void` | Crosshair feature clicked |

### `<KLineChart.Indicator>`

Declarative indicator management. Renders nothing — purely manages indicator lifecycle.

```tsx
<KLineChart.Indicator
  value={{ name: "MA", calcParams: [5, 10, 30] }}
  isStack={false}
  pane={{ height: 100 }}
/>

// Or simply by name:
<KLineChart.Indicator value="VOL" />
```

| Prop | Type | Description |
|------|------|-------------|
| `value` | `string \| IndicatorCreate` | Indicator name or full config |
| `isStack` | `boolean` | Stack on existing indicators in same pane |
| `pane` | `Partial<PaneOptions>` | Options applied to the indicator pane via `setPaneOptions` (e.g. `{ height: 80 }`) |
| `yAxis` | `YAxisOverride` | Y axis config for the indicator pane, applied via `createYAxis` |

> **v10 note:** klinecharts 10.0.0 changed `createIndicator(value, isStack)` — `paneId`/`yAxisId` are now properties of the `IndicatorCreate` value itself. `useIndicator` returns the indicator id (not the pane id).

### `<KLineChart.YAxis>`

Declarative standalone Y axis management. KLineCharts v10 supports multiple Y axes per pane. Renders nothing — purely manages the axis lifecycle via `createYAxis` / `overrideYAxis` / `removeYAxis`.

```tsx
<KLineChart.YAxis value={{ paneId: "candle", position: "left" }} />
```

| Prop | Type | Description |
|------|------|-------------|
| `value` | `YAxisOverride` | Y axis config. `createYAxis` is idempotent, so changing `value` re-applies safely. |

### `<KLineChart.Overlay>`

Declarative overlay (drawing tool) management. Renders nothing — purely manages overlay lifecycle.

```tsx
<KLineChart.Overlay
  value={{
    name: "segment",
    points: [
      { timestamp: 1234567890000, value: 100 },
      { timestamp: 1234567900000, value: 200 },
    ],
  }}
/>
```

| Prop | Type | Description |
|------|------|-------------|
| `value` | `string \| OverlayCreate \| Array<string \| OverlayCreate>` | Overlay config(s) |

### `<KLineChart.Widget>`

Declarative portal component that injects standard HTML/React elements directly into the chart DOM utilizing `createPortal` and the native `chart.getDom()` method.

If the target pane has not been laid out yet (e.g. an indicator pane that is created asynchronously), the widget retries on the next animation frame until the node is available.

```tsx
<KLineChart.Widget paneId="candle" position="main">
  <div className="custom-tooltip">My interactive React tooltip!</div>
</KLineChart.Widget>
```

| Prop | Type | Description |
|------|------|-------------|
| `paneId` | `string` | ID of the pane to inject into (e.g. `"candle"`, `"xAxis"`, or custom indicator pane IDs). If undefined, binds to root container. |
| `position` | `"root" \| "main" \| "yAxis"` | Layer position relative to the pane. Default is `"main"`. |

### Hooks

#### `useKLineChart()`

Access the `Chart` instance from any descendant of `<KLineChart>`.

```tsx
function MyComponent() {
  const chart = useKLineChart();
  // chart is Chart | null
  return <button onClick={() => chart?.scrollToRealTime()}>Go to now</button>;
}
```

#### State-tracking hooks

These hooks subscribe to chart actions and re-render the host component when the tracked value changes. They return `null` (or an empty array for `usePane()`) before the chart is initialized.

| Hook | Returns | Re-renders on |
|------|---------|---------------|
| `useCrosshair()` | `Crosshair \| null` | `onCrosshairChange` |
| `useVisibleRange()` | `VisibleRange \| null` | `onVisibleRangeChange` |
| `useBarSpace()` | `BarSpace \| null` | `onVisibleRangeChange` (covers zoom/resize) |
| `useDataList()` | `KLineData[] \| null` | `onVisibleRangeChange` |
| `usePane()` / `usePane(id)` | `PaneOptions[]` or `Nullable<PaneOptions>` | `onVisibleRangeChange` |
| `useYAxes(filter?)` | `YAxis[]` | `onVisibleRangeChange` |

```tsx
function CrosshairInfo() {
  const crosshair = useCrosshair();
  if (!crosshair?.kLineData) return <span>Hover the chart</span>;
  return <span>{crosshair.kLineData.close}</span>;
}
```

#### `useIndicator(options)`

Manages indicator lifecycle. Creates on mount, removes on unmount, overrides on config change.

```tsx
function MyIndicator() {
  const paneId = useIndicator({
    value: { name: "RSI", calcParams: [14] },
    pane: { height: 80 },
  });
  return null;
}
```

#### `useOverlay(options)`

Manages overlay lifecycle. Creates on mount, removes on unmount, overrides on config change.

```tsx
function MyOverlay() {
  const id = useOverlay({
    value: { name: "priceLine", points: [{ value: 50000 }] },
  });
  return null;
}
```

#### `useYAxis(options)`

Manages a standalone Y axis lifecycle. Creates via `createYAxis` on mount, overrides on change, removes on unmount. Returns the axis id.

```tsx
function MyYAxis() {
  const id = useYAxis({ value: { paneId: "candle", position: "left" } });
  return null;
}
```

#### `useYAxes(filter?)`

Reactive read of the chart's Y axes. Returns `YAxis[]` and re-renders on visible-range change.

```tsx
function AxisCount() {
  const axes = useYAxes({ paneId: "candle" });
  return <span>{axes.length} axis(es)</span>;
}
```

#### `useChartEvent(type, callback)`

Subscribe to any chart action event with a stable ref-based handler. The callback is strongly typed based on the action type.

```tsx
function Logger() {
  useChartEvent("onCrosshairChange", (crosshair) => {
    console.log("Crosshair:", crosshair.x, crosshair.y);
  });
  return null;
}
```

Available event types: `"onZoom"`, `"onScroll"`, `"onVisibleRangeChange"`, `"onCrosshairChange"`, `"onCandleBarClick"`, `"onPaneDrag"`, `"onCandleTooltipFeatureClick"`, `"onIndicatorTooltipFeatureClick"`, `"onCrosshairFeatureClick"`.

### Imperative API (ref)

For operations not covered by declarative props, use the `Chart` ref:

```tsx
const chartRef = useRef<Chart>(null);

// Navigation
chartRef.current?.scrollToRealTime(300);
chartRef.current?.scrollToTimestamp(timestamp);
chartRef.current?.zoomAtCoordinate(1.5);

// Data queries
chartRef.current?.getDataList();
chartRef.current?.getVisibleRange();
chartRef.current?.getBarSpace();

// Coordinate conversion
chartRef.current?.convertToPixel(points, filter);
chartRef.current?.convertFromPixel(coordinates, filter);

// Export
chartRef.current?.getConvertPictureUrl(true, "png");

// DOM access
chartRef.current?.getDom(paneId, position);
chartRef.current?.getSize(paneId, position);

// Pane management
chartRef.current?.setPaneOptions(options);
chartRef.current?.getPaneOptions(id);

// Y axis management (v10 multi-YAxis)
chartRef.current?.createYAxis(yAxisOverride);
chartRef.current?.removeYAxis({ id });
chartRef.current?.getYAxes(filter);
chartRef.current?.overrideYAxis(yAxisOverride);

// Imperative indicator/overlay operations
chartRef.current?.createIndicator(value, isStack);
chartRef.current?.getIndicators(filter);
chartRef.current?.createOverlay(value);
chartRef.current?.getOverlays(filter);
```

See the full [KlineCharts API documentation](https://klinecharts.com) for all available methods.

### Registration Functions

Module-level registration functions are re-exported from klinecharts:

```tsx
import {
  registerIndicator,
  registerOverlay,
  registerFigure,
  registerLocale,
  registerStyles,
  registerXAxis,
  registerYAxis,
  registerHotkey,
} from "react-klinecharts";

// Register a custom indicator
registerIndicator({
  name: "MyIndicator",
  calc: (dataList) => {
    return dataList.map((d) => ({ value: d.close }));
  },
  figures: [{ key: "value", title: "VAL: ", type: "line" }],
});
```

### Type Re-exports

All klinecharts types are re-exported for convenience, plus the wrapper's own helper types:

```tsx
import type {
  Chart,
  KLineData,
  Styles,
  Options,
  Indicator,
  IndicatorCreate,
  Overlay,
  OverlayCreate,
  Crosshair,
  ActionType,
  ActionCallback,
  DataLoader,
  SymbolInfo,
  Period,
  // wrapper-specific
  ActionPayloadMap,
  TypedActionCallback,
  // ... all klinecharts types
} from "react-klinecharts";
```

## Examples

### Custom Indicator with Hooks

```tsx
function BollingerBands({ period = 20 }: { period?: number }) {
  useIndicator({
    value: { name: "BOLL", calcParams: [period, 2] },
  });
  return null;
}

function App() {
  const [period, setPeriod] = useState(20);

  return (
    <KLineChart dataLoader={loader} symbol={symbol} period={period}>
      <BollingerBands period={period} />
    </KLineChart>
  );
}
```

### Theming

```tsx
<KLineChart
  dataLoader={loader}
  symbol={symbol}
  period={period}
  styles={{
    grid: { show: false },
    candle: {
      type: "area",
      area: {
        lineColor: "#2196F3",
        backgroundColor: [
          { offset: 0, color: "rgba(33, 150, 243, 0.3)" },
          { offset: 1, color: "rgba(33, 150, 243, 0)" },
        ],
      },
    },
  }}
/>
```

### Custom Locale

```tsx
import { registerLocale } from "react-klinecharts";

registerLocale("ru-RU", {
  time: "Время",
  open: "Откр.",
  high: "Макс.",
  low: "Мин.",
  close: "Закр.",
  volume: "Объём",
  change: "Изм.",
  turnover: "Оборот",
  second: "сек",
  minute: "мин",
  hour: "час",
  day: "дн",
  week: "нед",
  month: "мес",
  year: "год",
});

<KLineChart locale="ru-RU" ... />
```

## Architecture

```
src/
  index.ts                    # Public API barrel export
  types.ts                    # React-specific types (props, payload maps)
  events.ts                   # ActionPayloadMap + TypedActionCallback
  subscribeChartAction.ts     # Shared action subscribe/unsubscribe helper
  KLineChartContext.ts        # React context for chart instance
  KLineChart.tsx              # Core component
  hooks/
    useKLineChart.ts          # Context-based chart access
    useChartEvent.ts          # Typed event subscription hook
    useIndicator.ts           # Indicator lifecycle hook
    useOverlay.ts             # Overlay lifecycle hook
    useYAxis.ts               # Y axis lifecycle hook
    useCrosshair.ts           # Reactive crosshair state
    useVisibleRange.ts        # Reactive visible range
    useBarSpace.ts            # Reactive bar space
    useDataList.ts            # Reactive data list
    usePane.ts                # Reactive pane options
    useYAxes.ts               # Reactive Y axes
  components/
    Indicator.tsx             # <KLineChart.Indicator>
    Overlay.tsx               # <KLineChart.Overlay>
    Widget.tsx                # <KLineChart.Widget>
    YAxis.tsx                 # <KLineChart.YAxis>
```

**Design principles:**

- **Thin wrapper** — never re-implements what klinecharts already does
- **Reactive props** drive `useEffect` calls to chart methods
- **Ref escape hatch** exposes the full `Chart` instance for imperative operations
- **Context** enables hooks and sub-components in descendants
- **Stable event subscriptions** — callbacks stored in refs, no re-subscribe churn
- **Strongly typed events** — payloads carry their real types
- **StrictMode-safe** — React unmounts children before parent, so indicators/overlays clean up before `dispose()`
- **No duplicate observers** — klinecharts v10 manages its own `ResizeObserver`; the wrapper does not add another

## Development

```bash
pnpm install
pnpm build          # Build library
pnpm dev            # Build in watch mode
pnpm typecheck      # TypeScript type check
pnpm test           # Run vitest unit tests
pnpm test:watch     # Run tests in watch mode

# Run the docs site (Starlight) — includes a live, interactive demo
cd docs
pnpm install --ignore-workspace
pnpm dev
```

Full documentation lives in [`docs/`](./docs) and is published at
<https://nemezzizz.github.io/react-klinecharts/>.

## License

MIT
