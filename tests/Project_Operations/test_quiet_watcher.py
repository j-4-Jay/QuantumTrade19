import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("quiet_watch", os.path.join(ROOT, "4c. Quiet_Watch.py"))
qw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qw)


class FakeCtx:
    def __init__(self):
        self.lines = []

    def say(self, msg, *a, **k):
        self.lines.append(msg)


class QuietWatcherTests(unittest.TestCase):
    def test_idle_line_printed_once(self):
        ctx = FakeCtx()

        def orig(c):
            c.say("i no waiting request in X")
            return None

        run = qw.make_quiet_run(orig)
        for _ in range(5):
            run(ctx)
        self.assertEqual(len(ctx.lines), 1)

    def test_idle_line_returns_after_a_request_runs(self):
        ctx = FakeCtx()
        calls = {"n": 0}

        def orig(c):
            calls["n"] += 1
            if calls["n"] == 3:
                c.say("ran a request")
                return object()
            c.say("i no waiting request in X")
            return None

        run = qw.make_quiet_run(orig)
        for _ in range(5):
            run(ctx)
        idle = [l for l in ctx.lines if "no waiting request" in l]
        self.assertEqual(len(idle), 2)
        self.assertIn("ran a request", ctx.lines)

    def test_other_messages_and_say_restored(self):
        ctx = FakeCtx()
        original = ctx.say

        def orig(c):
            c.say("2 requests are waiting")
            return None

        qw.make_quiet_run(orig)(ctx)
        qw.make_quiet_run(orig)(ctx)
        self.assertEqual(ctx.lines.count("2 requests are waiting"), 2)
        self.assertEqual(ctx.say, original)


if __name__ == "__main__":
    unittest.main()
