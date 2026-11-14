"""Read-only comparison of failed QT19 CSV anchors. No requests are executed."""
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent
NAMES = (
    "009__843__REPLACE_v1.0.0__12-11-2026__04-57-AM.md",
    "009__846__REPLACE_v1.0.0__12-11-2026__05-04-AM.md",
)
TARGET = "Documentation/Project_Status/QT19_Project_Status.csv"


def read_utf8(path):
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")


def first_anchor(text):
    # Match the first OP only, preserving its section content exactly.
    lines = text.replace("\r\n", "\n").split("\n")
    try:
        start = lines.index("=== OP ===")
        end = lines.index("=== END ===", start + 1)
    except ValueError:
        raise ValueError("first OP block missing or unclosed")
    body = lines[start + 1:end]
    a = body.index("--- ANCHOR ---")
    fields = {}
    for line in body[:a]:
        m = re.match(r"^([A-Z_0-9]+):\s?(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    if fields.get("KIND") != "REPLACE" or fields.get("FILE", "").replace("\\", "/") != TARGET:
        raise ValueError("first OP is not the expected CSV REPLACE")
    stop = next((i for i in range(a + 1, len(body)) if re.fullmatch(r"--- [A-Z_]+ ---", body[i])), len(body))
    anchor = body[a + 1:stop]
    while anchor and not anchor[0].strip():
        anchor.pop(0)
    while anchor and not anchor[-1].strip():
        anchor.pop()
    if not anchor:
        raise ValueError("empty anchor")
    return anchor


def describe(ch):
    if ch is None:
        return "<END>"
    return f"{ch!r} U+{ord(ch):04X} {unicodedata.name(ch, 'UNNAMED')}"


def comparison(anchor_lines, target):
    expected = target.strip()
    anchor = "\n".join(line.strip() for line in anchor_lines)
    pos = next((i for i, (a, b) in enumerate(zip(anchor, expected)) if a != b), min(len(anchor), len(expected)))
    match = len(anchor_lines) == 1 and anchor == expected
    result = [f"Anchor lines: {len(anchor_lines)}; anchor characters: {len(anchor)}; current row characters: {len(expected)}",
              f"MATCH under core whole-line/strip semantics: {match}"]
    if not match:
        result.extend([
            f"First difference: zero-based character {pos} (one-based {pos + 1})",
            "Request character: " + describe(anchor[pos] if pos < len(anchor) else None),
            "CSV character:     " + describe(expected[pos] if pos < len(expected) else None),
            "Request context: " + repr(anchor[max(0, pos-70):pos+71]),
            "CSV context:     " + repr(expected[max(0, pos-70):pos+71]),
        ])
    result.append("Comparison is against the CURRENT row only; it cannot establish execution-time file history.")
    return result


def locate(name):
    # Only exact request basenames; never recurse or inspect unrelated Downloads files.
    candidates = [ROOT / name, Path.home() / "Downloads" / name]
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.name == name:
            candidates.append(p)
    return list(dict.fromkeys(p for p in candidates if p.is_file()))


def main():
    print("QT19 READ-ONLY ANCHOR DIAGNOSIS - no CSV changes, no tool execution")
    try:
        rows = [line for line in read_utf8(ROOT / TARGET).split("\n") if line.strip().startswith("FT-H.37,")]
        if len(rows) != 1:
            print(f"STOP: expected one FT-H.37 row; found {len(rows)}")
            return 1
        missing = False
        for name in NAMES:
            print("\nREQUEST:", name)
            paths = locate(name)
            if not paths:
                print("MISSING: original request not found in project root or current user's Downloads.")
                print("No output file, reconstruction or replacement was substituted.")
                missing = True
                continue
            for path in paths:
                print("File:", path)
                try:
                    for line in comparison(first_anchor(read_utf8(path)), rows[0]):
                        print(line)
                except (OSError, UnicodeError, ValueError) as exc:
                    print("STOP:", type(exc).__name__, str(exc))
                    missing = True
        return 1 if missing else 0
    except (OSError, UnicodeError) as exc:
        print("STOP:", type(exc).__name__, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
