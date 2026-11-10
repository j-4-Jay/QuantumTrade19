"""FT-H.37 installed-wrapper loader ownership regressions; Node or Bun."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def runtime():
    found = shutil.which("node") or shutil.which("bun")
    if found:
        return found
    try:
        from reflex.utils import path_ops
        for name in ("get_node_path", "get_bun_path"):
            resolver = getattr(path_ops, name, None)
            found = resolver() if resolver else None
            if found and Path(found).is_file():
                return str(found)
    except (ImportError, AttributeError, OSError):
        pass
    return None


JS_RUNTIME = runtime()
CASES = {'actual_wrapper_uses_corrected_ref': 'let stale=dataRef.current;installLoader(chart);wrapperEffect(stale,chartDataLoaderRef.current);dataRef.current=[{timestamp:1,close:2,volume:9},{timestamp:2,close:3,volume:4}];chart.resetData();assert.equal(rows[0].close,2);assert.equal(rows[0].volume,9);assert.equal(rows[1].close,3);', 'static_wrapper_reproduces_original_bug': 'let stale=dataRef.current;installLoader(chart);wrapperEffect(stale,null);dataRef.current=[{timestamp:1,close:2,volume:9}];chart.resetData();assert.equal(rows[0].volume,1);', 'stable_identity_after_rerender': 'let first=chartDataLoaderRef.current;__RENDER__;assert.strictEqual(first,chartDataLoaderRef.current);', 'non_init_no_duplicate_history': "let out;chartDataLoaderRef.current.getBars({type:'forward',callback:(x,more)=>{out=x;assert.deepEqual(more,{forward:false,backward:false});}});assert.equal(out.length,0);", 'live_callback_and_retry_preserved': 'let received;chartDataLoaderRef.current.subscribeBar({callback:r=>{received=r;return 42;}});let r={timestamp:2};assert.equal(window.QT19_LIVE_CALLBACKS.test(r),42);assert.strictEqual(received,r);assert.equal(retries,1);assert.equal(countdowns,1);assert.equal(loaderReadyRef.current,true);', 'reset_reads_latest_not_captured_array': 'installLoader(chart);chart.resetData();assert.equal(rows[0].volume,1);dataRef.current=[{timestamp:1,close:2,volume:50}];chart.resetData();assert.equal(rows[0].volume,50);'}
FIXTURE = "\nconst assert=require('assert');global.window={};\nlet chartDataLoaderRef={current:null},dataRef={current:[{timestamp:1,close:1,volume:1}]},loaderReadyRef={current:false},chartId='test',countdowns=0,retries=0;\nfunction qt19CountdownSchedule(){countdowns++;}\nlet active=null, rows=[], chart={setDataLoader:x=>active=x,resetData:()=>active.getBars({type:'init',callback:(x,more)=>{rows=x;}}),__qt19CorrectionQueue:{schedule:()=>retries++}};\nlet chartRef={current:chart};\n__LOADER__\nfunction wrapperEffect(data,dataLoader){if(dataLoader)chart.setDataLoader(dataLoader);else if(data)chart.setDataLoader({getBars:({callback})=>callback(data,{forward:false,backward:false})});}\n__CASE__\n"


def chart_source():
    return (ROOT / "ui/components/kline_chart.py").read_text(encoding="utf-8")


@pytest.mark.skipif(JS_RUNTIME is None, reason="Node or Bun required for loader ownership regression tests")
@pytest.mark.parametrize("case", list(CASES))
def test_real_qt19_loader_with_wrapper_effect_model(case):
    text = chart_source()
    start = text.index("  if (!chartDataLoaderRef.current) {")
    end = text.index("  const handleReady = (chart) => {", start)
    loader = text[start:end]
    rerender = loader[:loader.index("  const installLoader")]
    scenario = CASES[case].replace("__RENDER__", rerender)
    script = FIXTURE.replace("__LOADER__", loader).replace("__CASE__", scenario)
    result = subprocess.run([JS_RUNTIME, "-e", script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_wrapper_receives_stable_loader_not_static_data():
    text = chart_source()
    assert "const chartDataLoaderRef = useRef(null);" in text
    assert "dataLoader={chartDataLoaderRef.current}" in text
    assert "data={data}" not in text
    assert "chart.setDataLoader(chartDataLoaderRef.current);" in text
