"""FT-H.37 isolated browser queue tests using existing Node or Bun."""
import ast
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
def find_js_runtime():
    runtime = shutil.which("node") or shutil.which("bun")
    if runtime:
        return runtime
    try:
        from reflex.utils import path_ops
        for name in ("get_node_path", "get_bun_path"):
            resolve = getattr(path_ops, name, None)
            candidate = resolve() if resolve else None
            if candidate and Path(candidate).is_file():
                return str(candidate)
    except (ImportError, AttributeError, OSError):
        pass
    return None


JS_RUNTIME = find_js_runtime()
CASES = {'live_merge_preserves_forming': 'q.push([patch]);tick();assert.equal(data[0].volume,9);assert.equal(data[1].close,3);assert.equal(resets,1);', 'held_then_scroll': 'live=false;q.push([patch]);tick();assert.equal(resets,0);live=true;handlers.onScroll();tick();assert.equal(resets,1);', 'held_then_live_tick': 'live=false;q.push([patch]);tick();live=true;q.schedule();tick();assert.equal(resets,1);', 'explicit_return_rebases_spacing': 'live=false;q.push([patch]);tick();chart.scrollToRealTime(0);tick();assert.equal(chart.__qt19LiveOff,180);assert.equal(resets,1);', 'coalesces_latest': 'q.push([patch]);q.push([Object.assign({},patch,{volume:10})]);assert.equal(frames.size,1);tick();assert.equal(data[0].volume,10);assert.equal(resets,1);', 'no_change_no_reset': 'q.push([Object.assign({},data[0])]);tick();assert.equal(resets,0);assert.equal(q.pending(),0);', 'not_ready_retains': 'ready=false;q.push([patch]);tick();assert.equal(resets,0);assert.equal(q.pending(),1);ready=true;q.schedule();tick();assert.equal(resets,1);', 'context_discards_old': "live=false;q.push([patch]);tick();key='BTC|1m';live=true;q.schedule();tick();assert.equal(resets,0);assert.equal(q.pending(),0);", 'reset_exception_retains': "chart.resetData=()=>{throw Error('test');};q.push([patch]);tick();assert.equal(q.pending(),1);", 'destroy_cleans': 'let raw=chart.scrollToRealTime;q.push([patch]);q.destroy();tick();assert.equal(resets,0);assert.equal(Object.keys(handlers).length,0);assert.notEqual(chart.scrollToRealTime,raw);', 'invalid_ignored': 'q.push([{timestamp:1,open:NaN},null]);tick();assert.equal(q.pending(),0);assert.equal(resets,0);', 'missing_timestamp_retained': 'q.push([Object.assign({},patch,{timestamp:99})]);tick();assert.equal(q.pending(),1);assert.equal(data.length,2);', 'idle_no_frame': 'q.schedule();handlers.onScroll();assert.equal(frames.size,0);'}
HARNESS = "\nconst assert=require('assert');\nlet frames=new Map(), seq=0;\nglobal.window={}; global.requestAnimationFrame=f=>{frames.set(++seq,f);return seq;};\nglobal.cancelAnimationFrame=id=>frames.delete(id);\nfunction tick(){let todo=[...frames.values()];frames.clear();todo.forEach(f=>f());}\n__SOURCE__\nlet live=true, ready=true, key='ETH|1m', resets=0, changes=0, data=[{timestamp:1,open:1,high:2,low:1,close:1,volume:1},{timestamp:2,open:2,high:3,low:2,close:3,volume:4}];\nlet staged=null; let handlers={},off=180;\nlet chart={getDataList:()=>data,getOffsetRightDistance:()=>off,resetData:()=>{resets++;data=staged;},scrollToRealTime:()=>{live=true;},subscribeAction:(a,f)=>handlers[a]=f,unsubscribeAction:(a,f)=>{if(handlers[a]===f)delete handlers[a];}};\nlet q=window.QT19CreateCorrectionQueue({chart,getContext:()=>key,atLive:()=>live,ready:()=>ready,setData:x=>staged=x,changed:()=>changes++,error:()=>{}});\nlet patch={timestamp:1,open:1,high:2,low:1,close:2,volume:9};\n__CASE__\nq.destroy();\n"


def source():
    tree = ast.parse((ROOT / "ui/components/chart_correction_js.py").read_text(encoding="utf-8"))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CHART_CORRECTION_JS" for t in statement.targets):
            return ast.literal_eval(statement.value)
    raise AssertionError("CHART_CORRECTION_JS missing")


@pytest.mark.skipif(JS_RUNTIME is None, reason="Node or Bun required for browser correction runtime tests")
@pytest.mark.parametrize("case", list(CASES))
def test_correction_queue_runtime(case):
    script = HARNESS.replace("__SOURCE__", source()).replace("__CASE__", CASES[case])
    result = subprocess.run([JS_RUNTIME, "-e", script], text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_correction_queue_wired_to_live_and_cleanup():
    chart = (ROOT / "ui/components/kline_chart.py").read_text(encoding="utf-8")
    assert "CHART_CORRECTION_JS," in chart
    assert "window.QT19CreateCorrectionQueue({" in chart
    assert "chart.__qt19CorrectionQueue.schedule();" in chart
    assert "window.QT19_PATCH_BARS[chartId] = corrections.push;" in chart
    assert "corrections.destroy();" in chart
    assert 'Math.abs(off - chart.__qt19LiveOff) < 3' in chart
