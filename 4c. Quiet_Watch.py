import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IDLE = "no waiting request"


def make_quiet_run(orig_run):
    state = {"shown": False}

    def quiet_run(ctx):
        real_say = ctx.say

        def say(msg, *a, **k):
            if IDLE in str(msg):
                if state["shown"]:
                    return None
                state["shown"] = True
            return real_say(msg, *a, **k)

        ctx.say = say
        try:
            result = orig_run(ctx)
        finally:
            ctx.say = real_say
        if result is not None:
            state["shown"] = False
        return result

    return quiet_run


def load_core():
    path = os.path.join(ROOT, "4. Project_Operations_Core.py")
    spec = importlib.util.spec_from_file_location("po_core_quiet", path)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


def main():
    core = load_core()
    core.cmd_run = make_quiet_run(core.cmd_run)
    sys.argv = [sys.argv[0], "watch"]
    return core.main()


if __name__ == "__main__":
    sys.exit(main())
