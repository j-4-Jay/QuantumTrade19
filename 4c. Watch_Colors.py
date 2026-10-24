"""4c. Watch_Colors.py - terminal colours for the quiet watcher (display only).

PATH: 4c. Watch_Colors.py (NEW FILE)

Used by 4c. Quiet_Watch.py. Colours the terminal text of each request:
banner with the request name, "your action" lines, results (green OK, red
problems), plan headings. After the output it prints a closing block that
repeats the request name and the result. The text copied to the clipboard
is NOT changed (colours exist only on the screen). If the terminal cannot
show colours, or anything fails, the plain text is shown as before.
"""
from __future__ import annotations

import os
import re
import sys
import time

RESET = "\033[0m"
STYLE = {
    "banner": "\033[1;96m",
    "action": "\033[1;93m",
    "ok": "\033[1;92m",
    "bad": "\033[1;91m",
    "head": "\033[95m",
    "plan": "\033[36m",
    "name": "\033[1;97;44m",
    "sep": "\033[90m",
}
SEP = "\u2550" * 72
HEADER = re.compile(r"^=== (\S+\.md) \| (\w+) \|")


def _enable_vt() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


def classify(line: str) -> str:
    s = line.strip()
    low = s.lower()
    if not s:
        return ""
    if HEADER.match(s):
        return "banner"
    if "[gate" in low or "press enter" in low or "needs your" in low:
        return "action"
    if s.startswith(("\u2718", "\u2716", "\u2717")) or "STOPPED" in s or "anchor not found" in low or "traceback" in low:
        return "bad"
    if s.startswith("\u2714") or s.startswith("RESULT: OK"):
        return "ok"
    if s.startswith("RESULT:"):
        return "bad"
    if s.startswith("###") or s.startswith("#### "):
        return "head"
    if s.startswith("- ") or s.startswith("\u2022"):
        return "plan"
    return ""


def _paint(kind: str, text: str) -> str:
    if not kind:
        return text
    return STYLE[kind] + text + RESET


class _Out:
    def __init__(self, real, state):
        self._real = real
        self._state = state
        self._tail = ""

    def _emit_line(self, line: str, newline: bool) -> None:
        kind = classify(line)
        st = self._state
        if kind == "banner":
            m = HEADER.match(line.strip())
            st["name"], st["mode"] = m.group(1), m.group(2)
            st["result"] = ""
            self._real.write(_paint("sep", SEP) + "\n")
        if "RESULT" in line:
            st["result"] = line.strip()
        self._real.write(_paint(kind, line) + ("\n" if newline else ""))

    def write(self, text):
        if not text:
            return 0
        parts = (self._tail + text).split("\n")
        self._tail = parts.pop()
        for ln in parts:
            self._emit_line(ln.rstrip("\r"), True)
        if self._tail:
            self._emit_line(self._tail, False)
            self._tail = ""
        return len(text)

    def flush(self):
        try:
            self._real.flush()
        except Exception:
            pass

    def isatty(self):
        return True

    def __getattr__(self, name):
        return getattr(self._real, name)


def wrap(run):
    """Return a replacement for cmd_run that colours its screen output."""
    try:
        if not _enable_vt():
            return run
    except Exception:
        return run

    def coloured_run(ctx):
        state = {"name": "", "mode": "", "result": ""}
        real = sys.stdout
        sys.stdout = _Out(real, state)
        try:
            return run(ctx)
        finally:
            sys.stdout = real
            if state["name"]:
                stamp = time.strftime("%I:%M:%S %p")
                real.write(_paint("sep", SEP) + "\n")
                real.write(_paint("name", " DONE: " + state["name"] + " ") + "\n")
                final = state["result"] or "(no result line)"
                kind = "ok" if "OK" in final and "STOPPED" not in final else "bad"
                real.write(_paint(kind, "  " + final + "   [" + stamp + "]") + "\n")
                real.write(_paint("sep", SEP) + "\n")
                real.flush()

    return coloured_run
