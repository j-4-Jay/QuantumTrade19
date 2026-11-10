"""Offline tests for FT-H.37 observer v1.0.0."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "4c. Validate_Settle_5m15m.py"
spec = importlib.util.spec_from_file_location("qt19_settle_observer", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestSettleObserver(unittest.TestCase):
    def test_schedule(self):
        events = m.schedule(901)
        self.assertEqual(len(events), 48)
        self.assertEqual(sum(e[1] == "15m" for e in events), 24)
        self.assertTrue(all(e[2] % m.PERIODS[e[1]] == 0 and e[2] > 901 for e in events))
        self.assertEqual(events, sorted(events))
    def test_exact_boundary_is_future(self):
        self.assertEqual(min(e[2] for e in m.schedule(900)), 1200)
    def test_three_constituents(self):
        rows = [dict(time=i*300000, open=10+i, high=20+i, low=5+i, close=15+i, volume=2+i) for i in range(3)]
        self.assertEqual(m.exchange_values(rows, "15m", 0), (10,22,5,17,9))
    def test_missing_rejected(self):
        with self.assertRaises(ValueError):
            m.exchange_values([], "15m", 0)
    def test_duplicate_rejected(self):
        row = dict(time=0, open=1, high=2, low=0, close=1, volume=3)
        with self.assertRaises(ValueError):
            m.exchange_values([row,row], "5m", 0)
    def test_invalid_number(self):
        with self.assertRaises(ValueError):
            m.values(dict(open=1,high=2,low=0,close=1,volume=float("nan")))
    def test_late_and_errors(self):
        a = (1,2,0,1,3)
        self.assertEqual(m.classify(a,a,a,False,""), "MATCH")
        self.assertEqual(m.classify(a,a,a,True,""), "LATE_INCONCLUSIVE")
        self.assertEqual(m.classify(a,a,a,False,"timeout"), "ERROR")
        self.assertEqual(m.classify(None,a,a,False,""), "MISSING_DB")
        self.assertEqual(m.classify(a,a,(1,2,0,1,4),False,""), "DIFFERENT")
    def test_later_revision_breaks_suffix(self):
        a=(1,2,0,1,3); b=(1,2,0,1,4)
        records=[dict(timeframe="5m",open_ms=0,status="MATCH",exchange=x,complete_offset=t)
                 for x,t in [(a,1),(b,10),(b,55)]]
        self.assertEqual(m.summary(records)[0]["matching_suffix_start_complete_offset"],10)
    def test_incomplete_final_is_not_settled(self):
        r=dict(timeframe="5m",open_ms=0,status="ERROR",exchange=None,complete_offset=55)
        self.assertIsNone(m.summary([r])[0]["matching_suffix_start_complete_offset"])

    def test_skipped_request_has_no_io(self):
        with patch.object(m.time, "time", return_value=110), patch.object(m, "fetch") as fetch, patch.object(m, "read_db") as read:
            result=m.observe((101,"5m",100,1),Path("unused"))
        self.assertEqual(result["status"],"SKIPPED_LATE")
        fetch.assert_not_called(); read.assert_not_called()
    def test_request_completion_is_recorded(self):
        a=(1,2,0,1,3)
        with patch.object(m.time,"time",side_effect=[109,112]), patch.object(m.time,"monotonic",side_effect=[0,3]), patch.object(m,"fetch",return_value=a), patch.object(m,"read_db",return_value=a):
            result=m.observe((109,"5m",100,9),Path("unused"))
        self.assertEqual(result["complete_offset"],12)
        self.assertEqual(result["status"],"LATE_INCONCLUSIVE")
    def test_read_only_database(self):
        import tempfile, sqlite3
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/"candles.db"
            con=sqlite3.connect(db)
            con.execute("CREATE TABLE candles(symbol,timeframe,open_time,open,high,low,close,volume)")
            con.execute("INSERT INTO candles VALUES('B-ETH_USDT','5m',0,1,2,0,1,3)")
            con.commit(); con.close()
            before=db.read_bytes()
            self.assertEqual(m.read_db(db,"5m",0),(1,2,0,1,3))
            self.assertEqual(before,db.read_bytes())

if __name__ == "__main__":
    unittest.main()
