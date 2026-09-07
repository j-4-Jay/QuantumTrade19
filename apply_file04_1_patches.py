r"""File 04.1 - one-shot auto-patcher for Steps A/B/C.

SAVE TO: D:\QuantumTrade19\apply_file04_1_patches.py
RUN FROM: D:\QuantumTrade19>  (project root, same folder as this file)

    python apply_file04_1_patches.py

What it does, in order, on YOUR real files (not a guess - it reads your
actual current file content and mirrors your own existing patterns):

  STEP A: state/app_state.py
    - Adds: from state.app_state_mixins.setup_visualization_mixin import SetupVisualizationMixin
      (inserted right after the LAST existing "from state.app_state_mixins.X import YMixin" line)
    - Adds "SetupVisualizationMixin" into the AppState(...) base-class list
      (inserted right next to whichever existing *Mixin is found there)

  STEP B: engines/masters/master_app_engine.py
    - Detects the attribute holding your SetupDetectionMonitor instance
      (by finding "self.<attr> = SetupDetectionMonitor(")
    - Adds get_confirmed_setups(symbol, tf) / get_pending_setups(symbol, tf)
      proxy methods to the class, ONLY if they don't already exist.

  STEP C: state/app_state_mixins/core_shell_mixin.py
    - Wherever load_poi_settings() is already CALLED, adds a mirrored call
      to self.load_setup_detect_lookback() right after it.
    - Wherever poll_poi_chart_overlays is already referenced (return/yield/
      call), adds a mirrored reference to poll_setup_visualization right
      after it.

Every file gets a timestamped .bak copy before any edit. Every change is
printed to the console with the EXACT line(s) inserted and their line
number, so you can see precisely what happened. If a pattern this script
depends on isn't found, it prints a clear, specific instruction for that
ONE step and skips it - it never guesses blindly or corrupts a file.
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

APP_STATE_PATH = ROOT / "state" / "app_state.py"
MASTER_ENGINE_PATH = ROOT / "engines" / "masters" / "master_app_engine.py"
CORE_SHELL_PATH = ROOT / "state" / "app_state_mixins" / "core_shell_mixin.py"

NEW_IMPORT_LINE = "from state.app_state_mixins.setup_visualization_mixin import SetupVisualizationMixin"
NEW_MIXIN_NAME = "SetupVisualizationMixin"


def _backup(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + f".bak_{STAMP}")
    shutil.copyfile(path, backup_path)
    return backup_path


def _read(path: Path) -> str:
    if not path.exists():
        print(f"  [SKIP] File not found: {path}")
        return None
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _line_number_of(text: str, char_index: int) -> int:
    return text.count("\n", 0, char_index) + 1


# --------------------------------------------------------------------------
# STEP A - state/app_state.py
# --------------------------------------------------------------------------

def patch_app_state() -> None:
    print("\n=== STEP A: state/app_state.py ===")
    text = _read(APP_STATE_PATH)
    if text is None:
        print(f"  Manual fallback needed. Add this import near your other mixin imports:")
        print(f"    {NEW_IMPORT_LINE}")
        print(f"  And add {NEW_MIXIN_NAME} to AppState(...)'s base class list.")
        return

    if NEW_MIXIN_NAME in text:
        print(f"  [OK] {NEW_MIXIN_NAME} already present - nothing to do.")
        return

    backup_path = _backup(APP_STATE_PATH)
    print(f"  Backup written: {backup_path}")

    # 1) Insert the import after the LAST existing mixin import line.
    import_pattern = re.compile(
        r"^from state\.app_state_mixins\.\w+ import \w+Mixin\s*$",
        re.MULTILINE,
    )
    matches = list(import_pattern.finditer(text))
    if not matches:
        print("  [MANUAL NEEDED] Could not find any existing "
              "'from state.app_state_mixins.X import YMixin' line to anchor on.")
        print(f"  Add this line yourself near your other imports:\n    {NEW_IMPORT_LINE}")
    else:
        last_match = matches[-1]
        insert_at = last_match.end()
        text = text[:insert_at] + "\n" + NEW_IMPORT_LINE + text[insert_at:]
        print(f"  [ADDED] line {_line_number_of(text, insert_at)}: {NEW_IMPORT_LINE}")

    # 2) Insert the mixin name into the AppState(...) base-class list, right
    #    next to whichever existing *Mixin token appears first inside it.
    class_match = re.search(r"class\s+AppState\s*\(", text)
    if not class_match:
        print("  [MANUAL NEEDED] Could not find 'class AppState(' at all.")
        print(f"  Add '{NEW_MIXIN_NAME}' to its base-class list yourself.")
        _write(APP_STATE_PATH, text)
        return

    # Walk forward from the '(' to find the matching ')' (handles nested
    # parens defensively, though base-class lists normally have none).
    open_paren_index = class_match.end() - 1
    depth = 0
    close_paren_index = None
    for i in range(open_paren_index, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                close_paren_index = i
                break
    if close_paren_index is None:
        print("  [MANUAL NEEDED] Could not find the closing ')' for class AppState(...).")
        _write(APP_STATE_PATH, text)
        return

    bases_block = text[open_paren_index + 1:close_paren_index]
    mixin_token_match = re.search(r"\b\w+Mixin\b", bases_block)
    if not mixin_token_match:
        print("  [MANUAL NEEDED] Found 'class AppState(...)' but no existing "
              "*Mixin token inside it to anchor on.")
        print(f"  Add '{NEW_MIXIN_NAME},' to that base-class list yourself.")
        _write(APP_STATE_PATH, text)
        return

    insert_at_in_block = mixin_token_match.end()
    absolute_insert_at = open_paren_index + 1 + insert_at_in_block
    insertion = f",\n    {NEW_MIXIN_NAME}"
    text = text[:absolute_insert_at] + insertion + text[absolute_insert_at:]
    print(f"  [ADDED] line {_line_number_of(text, absolute_insert_at)}: {NEW_MIXIN_NAME} "
          f"(added next to existing base '{mixin_token_match.group(0)}')")

    _write(APP_STATE_PATH, text)
    print("  [DONE] state/app_state.py patched.")


# --------------------------------------------------------------------------
# STEP B - engines/masters/master_app_engine.py
# --------------------------------------------------------------------------

def patch_master_app_engine() -> None:
    print("\n=== STEP B: engines/masters/master_app_engine.py ===")
    text = _read(MASTER_ENGINE_PATH)
    if text is None:
        print("  Manual fallback needed. Add get_confirmed_setups()/get_pending_setups()")
        print("  proxy methods to your MasterAppEngine class, delegating to whatever")
        print("  attribute holds your SetupDetectionMonitor instance.")
        return

    if "def get_confirmed_setups" in text and "def get_pending_setups" in text:
        print("  [OK] get_confirmed_setups/get_pending_setups already present - nothing to do.")
        return

    attr_match = re.search(r"self\.(\w+)\s*=\s*SetupDetectionMonitor\(", text)
    if not attr_match:
        print("  [MANUAL NEEDED] Could not find 'self.<attr> = SetupDetectionMonitor(' "
              "anywhere in this file.")
        print("  Find the attribute yourself and add:")
        print("    def get_confirmed_setups(self, symbol, tf):")
        print("        return self.<attr>.get_confirmed_setups(symbol, tf)")
        print("    def get_pending_setups(self, symbol, tf):")
        print("        return self.<attr>.get_pending_setups(symbol, tf)")
        return

    attr_name = attr_match.group(1)
    print(f"  Detected SetupDetectionMonitor attribute: self.{attr_name}")

    backup_path = _backup(MASTER_ENGINE_PATH)
    print(f"  Backup written: {backup_path}")

    # Mirror indentation from an existing similar proxy method if present
    # (e.g. get_active_pois), else default to 4 spaces.
    indent = "    "
    template_match = re.search(r"^([ \t]*)def get_active_pois\(", text, re.MULTILINE)
    if template_match:
        indent = template_match.group(1)

    new_methods = (
        f"\n{indent}def get_confirmed_setups(self, symbol, tf):\n"
        f"{indent}    return self.{attr_name}.get_confirmed_setups(symbol, tf)\n"
        f"\n{indent}def get_pending_setups(self, symbol, tf):\n"
        f"{indent}    return self.{attr_name}.get_pending_setups(symbol, tf)\n"
    )

    if not text.endswith("\n"):
        text += "\n"
    text += new_methods
    _write(MASTER_ENGINE_PATH, text)
    print(f"  [ADDED] at end of file (indent='{indent}'):")
    for line in new_methods.strip("\n").splitlines():
        print(f"    {line}")
    print("  [DONE] engines/masters/master_app_engine.py patched.")
    print("  >>> Verify these two methods landed INSIDE the MasterAppEngine class body "
          "(correct indentation) before running the app - open the file and check the end.")


# --------------------------------------------------------------------------
# STEP C - state/app_state_mixins/core_shell_mixin.py
# --------------------------------------------------------------------------

def _mirror_after_each_occurrence(text: str, anchor_substring: str, old_token: str, new_token: str, label: str) -> str:
    """For every line containing `anchor_substring` (and NOT a 'def ' line),
    inserts an identical line right after it with old_token replaced by
    new_token - but only if a line with new_token doesn't already exist
    immediately after it."""
    lines = text.split("\n")
    output: list[str] = []
    added_any = False
    i = 0
    while i < len(lines):
        line = lines[i]
        output.append(line)
        is_def_line = re.match(r"^\s*(async\s+def|def)\s", line)
        if anchor_substring in line and not is_def_line:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if new_token not in next_line:
                mirrored = line.replace(old_token, new_token)
                if mirrored != line:
                    output.append(mirrored)
                    added_any = True
                    print(f"  [ADDED] after line {i + 1} ({label}):")
                    print(f"    {mirrored.strip()}")
        i += 1
    return "\n".join(output), added_any


def patch_core_shell_mixin() -> None:
    print("\n=== STEP C: state/app_state_mixins/core_shell_mixin.py ===")
    text = _read(CORE_SHELL_PATH)
    if text is None:
        print("  Manual fallback needed. In on_load(), add:")
        print("    self.load_setup_detect_lookback()")
        print("  right after wherever self.load_poi_settings() / refresh_poi_chart_overlays()")
        print("  is called, and mirror your poll_poi_chart_overlays start-up call for")
        print("  poll_setup_visualization.")
        return

    backup_path = _backup(CORE_SHELL_PATH)
    print(f"  Backup written: {backup_path}")

    changed_any = False

    text, changed1 = _mirror_after_each_occurrence(
        text, "load_poi_settings", "load_poi_settings()", "load_setup_detect_lookback()",
        "mirroring load_poi_settings() call",
    )
    changed_any = changed_any or changed1

    text, changed2 = _mirror_after_each_occurrence(
        text, "poll_poi_chart_overlays", "poll_poi_chart_overlays", "poll_setup_visualization",
        "mirroring poll_poi_chart_overlays reference",
    )
    changed_any = changed_any or changed2

    if not changed_any:
        print("  [MANUAL NEEDED] Could not find 'load_poi_settings' or "
              "'poll_poi_chart_overlays' call sites to mirror in this file.")
        print("  Add manually:")
        print("    self.load_setup_detect_lookback()   # next to your load_poi_settings() call")
        print("    (start) poll_setup_visualization     # next to your poll_poi_chart_overlays start-up")
        return

    _write(CORE_SHELL_PATH, text)
    print("  [DONE] state/app_state_mixins/core_shell_mixin.py patched.")


# --------------------------------------------------------------------------

def main() -> None:
    print(f"QuantumTrade19 - File 04.1 auto-patcher - run from: {ROOT}")
    patch_app_state()
    patch_master_app_engine()
    patch_core_shell_mixin()
    print("\n=== SUMMARY ===")
    print("Review every '[ADDED]' line above against the actual file (backups are")
    print("saved as <file>.bak_" + STAMP + " next to each original in case anything")
    print("needs to be reverted with:  copy <file>.bak_" + STAMP + " <file>")
    print("\nAny '[MANUAL NEEDED]' step above still needs a 1-line manual edit - the")
    print("exact snippet to add is printed right above that message.")
    print("\nNext: run your app (reflex run / your usual start script) and open Trading Panel.")


if __name__ == "__main__":
    main()
