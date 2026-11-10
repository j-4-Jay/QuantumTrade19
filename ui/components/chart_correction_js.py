"""FT-H.37 event-driven chart correction retry; browser only."""

CHART_CORRECTION_JS = r'''
(function () {
  if (typeof window === "undefined" || window.QT19CreateCorrectionQueue) return;
  window.QT19CreateCorrectionQueue = function (o) {
    var chart=o.chart, dead=false, frame=null, pending={}, context=o.getContext(), applying=false;
    var actions=[], rawScroll=chart.scrollToRealTime, wrappedScroll=null;
    var receivedBatches=0, appliedResets=0, lastPatch=[], lastReport=-Infinity;
    function report(force) {
      var now=Date.now();
      if(dead || (!force && now-lastReport<5000)) return;
      lastReport=now;
      try {
        var data=chart.getDataList() || [], range=chart.getVisibleRange(), off=chart.getOffsetRightDistance();
        var baseline=chart.__qt19LiveOff;
        var visibleLast=!!(range && range.to>=data.length-1);
        var gateSnapshot=!data.length || !range || (visibleLast && (typeof baseline!=="number" || Math.abs(off-baseline)<3));
        var brief=function(r){return {timestamp:r.timestamp,close:r.close,volume:r.volume};};
        console.info("[QT19 FT-H37] "+JSON.stringify({context:context,receivedBatches:receivedBatches,appliedResets:appliedResets,pending:Object.keys(pending).length,ready:o.ready(),visibleRange:range,offset:off,liveOffset:typeof baseline==="number"?baseline:null,gateSnapshot:gateSnapshot,chartTail:data.slice(-4).map(brief),patchTail:lastPatch}));
      } catch(e) {console.info("[QT19 FT-H37] diagnostic unavailable: "+String(e));}
    }
    function syncContext() {
      var next=o.getContext();
      if (next!==context) { context=next; pending={}; }
    }
    var offsetTracePrevious=null;
    function traceOffset(reason) {
      if(dead) return;
      try {
        var data=chart.getDataList() || [];
        var range=chart.getVisibleRange();
        var bars=typeof chart.getBarSpace==="function" ? chart.getBarSpace() : null;
        var plot=typeof chart.getSize==="function" ? chart.getSize("candle_pane","main") : null;
        var state={offset:chart.getOffsetRightDistance(),liveOffset:typeof chart.__qt19LiveOff==="number"?chart.__qt19LiveOff:null,barSpace:bars?bars.bar:null,plotWidth:plot?plot.width:null,length:data.length,lastTimestamp:data.length?data[data.length-1].timestamp:null};
        var before=offsetTracePrevious;
        offsetTracePrevious=state;
        if(before && JSON.stringify(before)!==JSON.stringify(state)) {
          console.info("[QT19 FT-H37 OFFSET] "+JSON.stringify({at:Date.now(),reason:reason,context:o.getContext(),before:before,after:state,visibleRange:range,stack:(new Error("offset observation")).stack}));
        }
      } catch(e) { /* diagnostics must not interrupt the queue */ }
    }
    function schedule(reason) {
      if (dead) return;
      traceOffset(typeof reason==="string"?reason:"schedule");
      if (frame!==null) return;
      report(false);
      syncContext();
      if (!Object.keys(pending).length) return;
      frame=requestAnimationFrame(function () { frame=null; flush(); });
    }
    function flush() {
      if (dead || applying) return false;
      syncContext();
      var rows=Object.keys(pending).map(function(k){return pending[k];});
      if (!rows.length || !o.atLive(chart)) return false;
      var current=chart.getDataList();
      if (!Array.isArray(current) || !current.length) return false;
      var list=current.slice(), indexes={}, changed=false;
      list.forEach(function(b,i){indexes[b.timestamp]=i;});
      var consumed=[];
      rows.forEach(function(r){
        var i=indexes[r.timestamp];
        if (i===undefined) return;
        var b=list[i];
        if (["open","high","low","close","volume"].some(function(k){return b[k]!==r[k];})) {
          list[i]=Object.assign({},b,r); changed=true;
        }
        consumed.push(r.timestamp);
      });
      if (!changed) { consumed.forEach(function(t){delete pending[t];}); return false; }
      if (!o.ready() || typeof chart.resetData!=="function") return false;
      applying=true;
      try {
        o.setData(list);
        chart.resetData();
        appliedResets++;
        consumed.forEach(function(t){delete pending[t];});
        o.changed();
        return true;
      } catch(e) { if(o.error) o.error(e); return false; }
      finally { applying=false; }
    }
    function push(rows) {
      if (dead) return;
      syncContext();
      receivedBatches++;
      lastPatch=Array.isArray(rows)?rows.filter(function(r){return !!r;}).slice(-4).map(function(r){return {timestamp:r.timestamp,close:r.close,volume:r.volume};}):[];
      if (Array.isArray(rows)) rows.forEach(function(r){
        if(r && Number.isFinite(r.timestamp) && ["open","high","low","close","volume"].every(function(k){return Number.isFinite(r[k]);})) pending[r.timestamp]=r;
      });
      schedule();
    }
    if(typeof rawScroll==="function") {
      wrappedScroll=function(){
        var result=rawScroll.apply(chart,arguments);
        try {
          var off=chart.getOffsetRightDistance();
          if(Number.isFinite(off)) chart.__qt19LiveOff=off;
        } catch(e) {}
        schedule("scrollToRealTime"); return result;
      };
      chart.scrollToRealTime=wrappedScroll;
    }
    if(typeof chart.subscribeAction==="function" && typeof chart.unsubscribeAction==="function") {
      ["onScroll","onZoom","onVisibleRangeChange"].forEach(function(a){
        var listener=function(){schedule(a);};
        try {chart.subscribeAction(a,listener); actions.push({name:a,listener:listener});} catch(e) {}
      });
    }
    traceOffset("attach");
    report(true);
    return {push:push,schedule:schedule,flush:flush,pending:function(){return Object.keys(pending).length;},destroy:function(){
      dead=true; if(frame!==null) cancelAnimationFrame(frame); frame=null; pending={};
      actions.forEach(function(a){try{chart.unsubscribeAction(a.name,a.listener);}catch(e){}});
      if(wrappedScroll && chart.scrollToRealTime===wrappedScroll) chart.scrollToRealTime=rawScroll;
    }};
  };
})();
'''
