#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""4. Project_Operations_Core.py - Project_Operations v2.0.1 corrective build (universal tool, Jay's Software Build Kit SCR-0001).

Standard library only. Launchers: `4. Project_Operations.bat/.ps1` (run), `4a. New_Thread__Bundle.bat` (bundle),
`4b. Watch_Requests.bat` (watch), `4c. Test_And_Check.bat` (tests). Rules: Common_Project_Instructions v1.1.0, Section 7.
"""
import os, sys, re, json, hashlib, time, datetime, shutil, subprocess, ast, difflib, fnmatch, tempfile, platform, traceback, collections

TOOL_VERSION = "2.0.1"
STATUS_WORDS = ["LOCKED", "AWAITING_LOCK", "APPLIED_UNTESTED", "IN_PROGRESS", "APPROVED", "NOT_STARTED", "PENDING", "REVISED", "DISCARDED"]
STATUS_EMOJI = {"LOCKED": "\u2705", "AWAITING_LOCK": "\U0001F7E2", "APPLIED_UNTESTED": "\U0001F7E1", "IN_PROGRESS": "\U0001F6A7",
                "APPROVED": "\U0001F4DD", "NOT_STARTED": "\u23F3", "PENDING": "\u23F8", "REVISED": "\U0001F501", "DISCARDED": "\u274C"}
DEFAULT_CFG = {"clipboard_mode": "always", "auto_clutter": "auto", "auto_clutter_report_runs": 2, "auto_clutter_runs_done": 0,
               "kit_root": "", "downloads": "", "core_card_in_platform": False, "relay_max_chars": 15000, "chat_max_parts": 0,
               "auto_dry_run_lines": 60, "thread_request_limit": 25}
TEXT_EXT = [".py", ".md", ".json", ".ps1", ".bat", ".js", ".ts", ".tsx", ".css", ".html", ".txt", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".sql"]
CODE_EXT = {".py", ".css", ".js", ".ts", ".tsx", ".html", ".json", ".bat", ".ps1", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".sql", ".cmd"}
SKIP_DIRS = {".git", "venv", ".venv", "node_modules", ".web", "__pycache__", "Debug", "Clutter", "New_Thread__Bundle", ".states"}
TRACKER_FOLDER = "Documentation/BlueprintTracker_&_ContinuationPrompt"
BUNDLE_FOLDER = "New_Thread__Bundle"
TOOL_STATE_FILES = ["Debug/Project_Operations.config.json", "Debug/Ops_State.json", "Debug/Ops_Log.md", "Debug/ops.lock",
                    "Debug/relay_state.json", "Debug/Machine_Profile.json", "Debug/Live_Check_Report.md"]
TOOL_FILES = ["4. Project_Operations_Core.py", "4. Project_Operations.bat", "4. Project_Operations.ps1",
              "4a. New_Thread__Bundle.bat", "4b. Watch_Requests.bat", "4c. Test_And_Check.bat"]


class ToolError(Exception):
    pass


_ICONS_U = {"ok": "\u2714", "warn": "\u26A0", "fail": "\u2716", "same": "\u2261", "info": "\u2022"}
_ICONS_A = {"ok": "[OK]", "warn": "[!!]", "fail": "[XX]", "same": "[==]", "info": "[..]"}
FORCE_ASCII = False


def icon(kind):
    if FORCE_ASCII:
        return _ICONS_A[kind]
    try:
        "\u2714\u26A0\u2716\u2261".encode(getattr(sys.stdout, "encoding", None) or "ascii")
        return _ICONS_U[kind]
    except Exception:
        return _ICONS_A[kind]


# ----------------------------------------------------------------------------- basic helpers
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def norm_text_for_hash(text):
    t = text.replace("\r\n", "\n")
    return t if t.endswith("\n") else t + "\n"


def sha256_text(text):
    return sha256_bytes(norm_text_for_hash(text).encode("utf-8"))


def read_text(path):
    b = open(path, "rb").read()
    bom = b.startswith(b"\xef\xbb\xbf")
    if bom:
        b = b[3:]
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        raise ToolError("not a UTF-8 text file: " + path)
    crlf = s.count("\r\n")
    lf = s.count("\n") - crlf
    return s.replace("\r\n", "\n"), {"bom": bom, "eol": "\r\n" if crlf > lf else "\n"}


def encode_text(s, meta):
    if meta.get("eol") == "\r\n":
        s = s.replace("\n", "\r\n")
    b = s.encode("utf-8")
    return (b"\xef\xbb\xbf" + b) if meta.get("bom") else b


def write_atomic(path, data):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d or ".", ".po_tmp_%d_%s" % (os.getpid(), os.path.basename(path)))
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    last = None
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last = e
            time.sleep(0.3)
    try:
        os.remove(tmp)
    except Exception:
        pass
    raise ToolError("cannot write (file locked?): %s (%s)" % (path, last))


def resolve(root, rel):
    r = (rel or "").replace("\\", "/").strip()
    if not r or r.startswith("/") or re.match(r"^[A-Za-z]:", r) or "\x00" in r:
        raise ToolError("path not allowed: %r" % rel)
    parts = [p for p in r.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise ToolError("path not allowed (..): %r" % rel)
    base = os.path.abspath(root)
    p = os.path.abspath(os.path.join(base, *parts))
    if os.path.normcase(os.path.commonpath([p, base])) != os.path.normcase(base):
        raise ToolError("path leaves the root: %r" % rel)
    return p


def relpath(root, path):
    return os.path.relpath(path, root).replace("\\", "/")


def forbidden_write(rel):
    r = rel.replace("\\", "/").lower()
    base = r.rsplit("/", 1)[-1]
    if r == ".git" or r.startswith(".git/"):
        return ".git is never touched"
    if base == ".env" or base.startswith(".env."):
        return ".env files are never touched"
    if base.endswith((".db", ".sqlite", ".sqlite3")):
        return "database files are never touched"
    return None


def forbidden_read(rel):
    r = rel.replace("\\", "/").lower()
    base = r.rsplit("/", 1)[-1]
    why = forbidden_write(rel)
    if why:
        return why
    if base.endswith((".pem", ".key", ".pfx", ".p12")) or base.startswith("id_rsa") or base.startswith("keyring"):
        return "key/secret file"
    if r.startswith("candidate database/") or r.startswith("uploaded_files/") or "/candidate database/" in r:
        return "personal data folder"
    return None


def glob_match(rel, pattern):
    rel = rel.replace("\\", "/").lstrip("./")
    pat = pattern.replace("\\", "/").strip()
    if not pat:
        return False
    rx = ""
    i = 0
    while i < len(pat):
        c = pat[i]
        if pat[i:i + 3] == "**/":
            rx += "(?:.*/)?"
            i += 3
            continue
        if pat[i:i + 2] == "**":
            rx += ".*"
            i += 2
            continue
        if c == "*":
            rx += "[^/]*"
        elif c == "?":
            rx += "[^/]"
        else:
            rx += re.escape(c)
        i += 1
    return re.fullmatch(rx, rel, re.I) is not None


def fence(text):
    runs = [len(m.group(0)) for m in re.finditer(r"`+", text)]
    n = max([3] + [r + 1 for r in runs])
    return "`" * n


def parse_dt(date_s, time_s):
    return datetime.datetime.strptime(date_s + " " + time_s, "%d-%m-%Y %I-%M-%p")


def stamp_now(now):
    return now.strftime("%Y%m%d_%H%M%S")


def hhmm_ampm(now):
    return now.strftime("%I-%M-%p")


def pc_name():
    return os.environ.get("COMPUTERNAME") or platform.node() or "PC"


# ----------------------------------------------------------------------------- clipboard / notify
class SystemClipboard:
    """Real clipboard. Windows: ctypes (CF_UNICODETEXT). macOS: pbcopy/pbpaste. Linux: xclip/xsel/wl-copy."""

    def copy(self, text):
        try:
            if os.name == "nt":
                return self._win_copy(text)
            if sys.platform == "darwin":
                return subprocess.run(["pbcopy"], input=text.encode("utf-8"), timeout=10).returncode == 0
            for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
                if shutil.which(cmd[0]):
                    return subprocess.run(cmd, input=text.encode("utf-8"), timeout=10).returncode == 0
        except Exception:
            return False
        return False

    def paste(self):
        try:
            if os.name == "nt":
                return self._win_paste()
            if sys.platform == "darwin":
                return subprocess.run(["pbpaste"], capture_output=True, timeout=10).stdout.decode("utf-8")
            for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
                if shutil.which(cmd[0]):
                    return subprocess.run(cmd, capture_output=True, timeout=10).stdout.decode("utf-8")
        except Exception:
            return None
        return None

    @staticmethod
    def _win_copy(text):
        import ctypes
        from ctypes import wintypes
        k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
        k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        k32.GlobalAlloc.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        u32.OpenClipboard.argtypes = [ctypes.c_void_p]
        u32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
        data = (text.replace("\r\n", "\n").replace("\n", "\r\n") + "\0").encode("utf-16-le")
        for _ in range(20):
            if u32.OpenClipboard(None):
                break
            time.sleep(0.1)
        else:
            return False
        try:
            u32.EmptyClipboard()
            h = k32.GlobalAlloc(0x0002, len(data))
            if not h:
                return False
            p = k32.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            k32.GlobalUnlock(h)
            return bool(u32.SetClipboardData(13, h))
        finally:
            u32.CloseClipboard()

    @staticmethod
    def _win_paste():
        import ctypes
        from ctypes import wintypes
        k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
        u32.GetClipboardData.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        u32.OpenClipboard.argtypes = [ctypes.c_void_p]
        for _ in range(20):
            if u32.OpenClipboard(None):
                break
            time.sleep(0.1)
        else:
            return None
        try:
            h = u32.GetClipboardData(13)
            if not h:
                return None
            p = k32.GlobalLock(h)
            try:
                return ctypes.wstring_at(p).replace("\r\n", "\n")
            finally:
                k32.GlobalUnlock(h)
        finally:
            u32.CloseClipboard()


def notify(ctx, kind="ok", text=""):
    """Best effort sound + toast. Never raises."""
    try:
        if getattr(ctx, "quiet", False):
            return
        if os.name == "nt":
            try:
                import winsound
                if kind == "ok":
                    winsound.Beep(1000, 120)
                elif kind == "wait":
                    winsound.Beep(800, 90)
                    winsound.Beep(1100, 90)
                else:
                    winsound.Beep(300, 350)
            except Exception:
                pass
            if text:
                ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                      "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                      "$n=$t.GetElementsByTagName('text');$n.Item(0).AppendChild($t.CreateTextNode('Project_Operations'))>$null;"
                      "$n.Item(1).AppendChild($t.CreateTextNode(%s))>$null;"
                      "$a='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
                      "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($a).Show([Windows.UI.Notifications.ToastNotification]::new($t))"
                      % ("'" + text.replace("'", "")[:120] + "'"))
                subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception:
        pass


# ----------------------------------------------------------------------------- context, config, state
def default_downloads():
    return os.path.join(os.path.expanduser("~"), "Downloads")


def detect_kit_root():
    cands = [os.environ.get("JAYS_KIT_ROOT", "")]
    cands += ["%s:\\Jays_Software_Build_Kit" % c for c in "DEFGHCZ"]
    cands += [os.path.join(os.path.expanduser("~"), "Jays_Software_Build_Kit")]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "00_Common_Instructions")):
            return c
    return ""


class Ctx:
    def __init__(self, root, kit_root=None, downloads=None, input_fn=None, out_fn=None, clip=None, now_fn=None, quiet=False):
        self.root = os.path.abspath(root)
        self.quiet = quiet
        self.cfg_path = os.path.join(self.root, "Debug", "Project_Operations.config.json")
        self.cfg = dict(DEFAULT_CFG)
        try:
            self.cfg.update(json.load(open(self.cfg_path, encoding="utf-8")))
        except Exception:
            pass
        self.kit_root = kit_root if kit_root is not None else (self.cfg.get("kit_root") or detect_kit_root())
        self.downloads = downloads or self.cfg.get("downloads") or default_downloads()
        self.input = input_fn or (lambda p="": input(p))
        self.out_fn = out_fn or (lambda s: print(s))
        self.clip = clip or SystemClipboard()
        self.now = now_fn or datetime.datetime.now
        self.buf = []
        self.state_path = os.path.join(self.root, "Debug", "Ops_State.json")
        self.state = {"last_file_number": 0, "processed": [], "log": []}
        try:
            self.state.update(json.load(open(self.state_path, encoding="utf-8")))
        except Exception:
            pass

    def say(self, s=""):
        self.buf.append(s)
        try:
            self.out_fn(s)
        except Exception:
            pass

    def save_cfg(self):
        os.makedirs(os.path.dirname(self.cfg_path), exist_ok=True)
        write_atomic(self.cfg_path, json.dumps(self.cfg, indent=2).encode("utf-8"))

    def save_state(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        write_atomic(self.state_path, json.dumps(self.state, indent=1).encode("utf-8"))

    def p(self, rel):
        return resolve(self.root, rel)


class Res:
    def __init__(self):
        self.status = "OK"
        self.detail = ""
        self.changed = []
        self.units = None

    def stop(self, why):
        self.status = "STOPPED"
        self.detail = why
        return self

    def cancel(self):
        self.status = "CANCELLED"
        return self

    def line(self):
        if self.status == "OK":
            return "RESULT: OK" + ((" " + self.detail) if self.detail else "")
        if self.status == "CANCELLED":
            return "RESULT: CANCELLED by Jay - files changed: none"
        return "RESULT: STOPPED - %s - files changed: none" % self.detail


def gate(ctx, kind, lines):
    for l in lines:
        ctx.say(l)
    notify(ctx, "wait", "Waiting for you in the terminal")
    if kind == "u":
        prompt, ok = "LOCKED AREA - type U then press ENTER to continue (anything else cancels): ", (lambda s: s.strip().lower() == "u")
    elif kind == "y":
        prompt, ok = "PERMANENT DELETE - type Y then press ENTER to continue (anything else cancels): ", (lambda s: s.strip().lower() == "y")
    else:
        prompt, ok = "Press ENTER to continue (any other key then ENTER cancels): ", (lambda s: s.strip() == "")
    try:
        ans = ctx.input(prompt)
    except (EOFError, KeyboardInterrupt):
        ans = None
    good = ans is not None and ok(ans)
    ctx.buf.append("[gate %s] %s" % (kind, "accepted" if good else "cancelled"))
    return good


# ----------------------------------------------------------------------------- tracker access
TRACKER_RE = re.compile(r"^(?P<proj>[A-Z0-9]+)__(?P<thr>\d{3})__(?P<date>\d{2}-\d{2}-\d{4})__(?P<time>\d{2}-\d{2}-(?:AM|PM))__(?P<phase>[^_]+)__(?P<name>.+)_v(?P<ver>\d+\.\d+\.\d+)\.md$")
REQ_RE = re.compile(r"^(?P<thr>\d{3})__(?P<num>\d{3})__(?P<mode>[A-Z_]+)_v(?P<ver>\d+\.\d+\.\d+)__(?P<date>\d{2}-\d{2}-\d{4})__(?P<time>\d{2}-\d{2}-(?:AM|PM))\.md$")


def tracker_dir(ctx):
    return os.path.join(ctx.root, *TRACKER_FOLDER.split("/"))


def list_trackers(ctx):
    d = tracker_dir(ctx)
    out = []
    if os.path.isdir(d):
        for f in os.listdir(d):
            m = TRACKER_RE.match(f)
            if m:
                try:
                    dt = parse_dt(m.group("date"), m.group("time"))
                except ValueError:
                    continue
                ver = tuple(int(x) for x in m.group("ver").split("."))
                out.append({"path": os.path.join(d, f), "file": f, "proj": m.group("proj"), "thr": int(m.group("thr")),
                            "dt": dt, "ver": ver, "phase": m.group("phase"), "name": m.group("name")})
    out.sort(key=lambda t: (t["thr"], t["dt"], t["ver"]))
    return out


def newest_tracker(ctx):
    t = list_trackers(ctx)
    return t[-1] if t else None


def project_code(ctx):
    p = os.path.join(ctx.root, "Documentation", "Project_Code.txt")
    try:
        c = open(p, encoding="utf-8").read().strip()
        if c:
            return c
    except Exception:
        pass
    t = newest_tracker(ctx)
    return t["proj"] if t else ""


def section_between(text, start, end):
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i + len(start))
    if j < 0:
        return None
    return text[i + len(start):j]


def block_lines(text, name):
    body = section_between(text, "<!-- %s_START -->" % name, "<!-- %s_END -->" % name)
    if body is None:
        return []
    return [l.rstrip() for l in body.split("\n") if l.strip()]


def tracker_text(ctx):
    t = newest_tracker(ctx)
    if not t:
        return None, ""
    return t, read_text(t["path"])[0]


def current_thread(ctx):
    t, text = tracker_text(ctx)
    if not t:
        return 1
    m = re.search(r"this thread = (\d+)", section_between(text, "<!-- CONTINUATION_PROMPT_START -->", "<!-- CONTINUATION_PROMPT_END -->") or "")
    if m:
        return int(m.group(1))
    m = re.search(r"^\| Thread number \| (\d+)", text, re.M)
    return int(m.group(1)) if m else t["thr"]


def protect_globs(ctx):
    _, text = tracker_text(ctx)
    return [l.split("|")[0].strip() for l in block_lines(text, "CLUTTER_PROTECT")]


def locked_globs(ctx):
    _, text = tracker_text(ctx)
    out = []
    for l in block_lines(text, "LOCKED_PATHS"):
        g = l.split("|")[0].strip()
        if g:
            out.append(g)
    return out


def scan_allow_globs(ctx):
    _, text = tracker_text(ctx)
    return [l.split("|")[0].strip() for l in block_lines(text, "SCAN_ALLOW")]


def is_locked(ctx, rel):
    return any(glob_match(rel, g) for g in locked_globs(ctx))


# ----------------------------------------------------------------------------- Clipboard Guard (secret scan)
_PH = re.compile(r"^(<|\{|\$|%|your|example|dummy|test|changeme|xxx|\*\*\*|none$|null$)", re.I)
GUARD = [
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("BOT_TOKEN", re.compile(r"(?<![\w:])\d{8,10}:[A-Za-z0-9_-]{35}(?![\w-])")),
    ("CLOUD_KEY", re.compile(r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{35}")),
    ("GENERIC_SECRET", re.compile(r"""(?ix)\b[\w.-]*(?:api[_-]?key|secret|token|passwd|password|pwd|auth[_-]?key|private[_-]?key)[\w.-]*["']?\s*[:=]\s*(?P<q>["'])(?P<v>[^"'\s]{8,})(?P=q)""")),
    ("EMAIL", re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9-]+\.[a-z]{2,}\b")),
    ("PHONE", re.compile(r"(?i)(?:\b(?:phone|mobile|contact|whatsapp|tel)\w*[\"']?\s*[:=\-]?\s*\+?\d[\d\s\-]{8,13}\d)|\+91[\s-]?[6-9]\d{9}")),
]
SOFT = {"EMAIL", "PHONE"}  # GENERIC_SECRET can never be allowlisted (Jay, 14-10-2026)


def scan_text(text, rel="", allow=()):
    soft_ok = bool(rel) and any(glob_match(rel, g) for g in allow if g)
    found = []
    for n, line in enumerate(text.split("\n"), 1):
        for kind, rx in GUARD:
            if kind in SOFT and soft_ok:
                continue
            m = rx.search(line)
            if not m:
                continue
            if kind == "GENERIC_SECRET" and _PH.match(m.group("v")):
                continue
            if kind == "EMAIL":
                dom = m.group(0).split("@")[1].lower()
                if dom.startswith("example.") or dom == "localhost":
                    continue
            found.append((n, kind))
    return found


def guard_items(ctx, items):
    """items: list of (label, rel, text). Returns list of (label, line, kind) findings; never includes secret values."""
    allow = scan_allow_globs(ctx)
    out = []
    for label, rel, text in items:
        why = forbidden_read(rel) if rel else None
        if why:
            out.append((label, 0, "PROTECTED_PATH (%s)" % why))
            continue
        for n, kind in scan_text(text, rel, allow):
            out.append((label, n, kind))
    return out


# ----------------------------------------------------------------------------- request parsing (strict)
TRK_HEADER = {"BUMP", "PHASE", "PHASE_NAME"}
TRK_BLOCKS = {"STATUS": ({"ID", "STATUS", "DATE", "NOTE"}, set()), "ADD_ITEM": ({"ROW"}, set()), "LOG": (set(), {"TEXT"}),
              "AMEND": ({"SECTION"}, {"TEXT"})}
for _i in range(1, 7):
    TRK_BLOCKS["SET_A%d" % _i] = (set(), {"TEXT"})
SPEC = {
    "SEARCH": (set(), {"FIND": ({"TERM", "EXT", "FOLDER", "CONTEXT", "MAX", "ROOT"}, set())}),
    "COLLECT": (set(), {"READ": ({"FULL", "PARTIAL", "FROM", "TO", "LINES", "FUNC", "SECTION", "ITEM", "FILE", "HEADING", "ROOT"}, set())}),
    "REPLACE": ({"DATA_REPAIR"}, {"OP": ({"KIND", "FILE", "OVERWRITE", "EOL", "FINAL_NEWLINE", "SHA256"}, {"ANCHOR", "NEW", "CONTENT"})}),
    "UNDO_LAST": (set(), {}),
    "RESTORE": (set(), {"FILE": ({"PATH", "BACKUP"}, set())}),
    "PLACE": (set(), {"FILE": ({"PROJECT_PATH", "KIT_PATH", "SHA256", "SOURCE_DOWNLOAD", "EOL", "FINAL_NEWLINE"}, {"CONTENT"})}),
    "MAP": (set(), {}),
    "TEST": (set(), {"RUN": ({"SET", "CHECK"}, set())}),
    "LOCK": ({"MESSAGE", "TAG", "PUSH"}, {"STAGE": ({"FILE"}, set())}),
    "ROLLBACK": ({"TAG"}, {"FILE": ({"PATH"}, set())}),
    "CLEAN": (set(), {"MOVE": ({"FILE", "REASON"}, set()), "DELETE": ({"FILE"}, set())}),
    "UNCLUTTER": (set(), {"BACK": ({"THREAD", "FILE"}, set())}),
    "PREFLIGHT": (set(), {}),
    "TRACKER": (set(TRK_HEADER), dict(TRK_BLOCKS)),
    "NEW_THREAD": (TRK_HEADER | {"LOCK", "LOCK_MESSAGE", "LOCK_TAG", "LOCK_PUSH", "NEXT_THREAD"}, dict(TRK_BLOCKS, RELAY=({"FILE", "ROOT"}, set()), STAGE=({"FILE"}, set()))),
    "SELFUPDATE": (set(), {"FILE": ({"SHA256"}, {"CONTENT"})}),
}
COMMON_HEADER = {"MODE", "PROJECT", "THREAD", "NOTE", "DRYRUN"}


class Block:
    def __init__(self, name, keys, sections):
        self.name, self.keys, self.sections = name, keys, sections


class Request:
    def __init__(self, path, header, blocks):
        self.path, self.name = path, os.path.basename(path)
        self.header, self.blocks = header, blocks
        m = REQ_RE.match(self.name)
        self.thr, self.num, self.mode = int(m.group("thr")), int(m.group("num")), m.group("mode")
        self.m = m

    def of(self, name):
        return [b for b in self.blocks if b.name == name]


def _suggest(bad, options):
    c = difflib.get_close_matches(bad, sorted(options), n=1, cutoff=0.6)
    return " (did you mean '%s'?)" % c[0] if c else ""


def parse_request(text, path):
    name = os.path.basename(path)
    m = REQ_RE.match(name)
    if not m:
        raise ToolError("file name does not follow the request naming <thread>__<file>__<MODE>_v<ver>__<DD-MM-YYYY>__<HH-MM-AM/PM>.md: " + name)
    lines = text.replace("\r\n", "\n").split("\n")
    i, header = 0, {}
    while i < len(lines):
        l = lines[i]
        if re.match(r"^=== [A-Z_0-9]+ ===$", l):
            break
        if l.strip() == "":
            i += 1
            continue
        hm = re.match(r"^([A-Z_]+):\s?(.*)$", l)
        if not hm:
            raise ToolError("line %d: unexpected text in the header: %r" % (i + 1, l[:60]))
        if hm.group(1) in header:
            raise ToolError("line %d: header key %s given twice" % (i + 1, hm.group(1)))
        header[hm.group(1)] = hm.group(2).strip()
        i += 1
    blocks = []
    while i < len(lines):
        l = lines[i]
        bm = re.match(r"^=== ([A-Z_0-9]+) ===$", l)
        if not bm:
            if l.strip() == "":
                i += 1
                continue
            raise ToolError("line %d: text outside a block: %r" % (i + 1, l[:60]))
        bname = bm.group(1)
        if bname == "END":
            raise ToolError("line %d: '=== END ===' without an open block" % (i + 1))
        i += 1
        keys, secs, cur, buf, closed = {}, {}, None, [], False
        while i < len(lines):
            l = lines[i]
            if l == "=== END ===":
                closed = True
                i += 1
                break
            sm = re.match(r"^--- ([A-Z_]+) ---$", l)
            if sm:
                if cur is not None:
                    secs[cur] = "\n".join(buf)
                cur, buf = sm.group(1), []
                if cur in secs:
                    raise ToolError("line %d: section %s given twice in block %s" % (i + 1, cur, bname))
                i += 1
                continue
            if cur is None:
                if l.strip() != "":
                    km = re.match(r"^([A-Z_0-9]+):\s?(.*)$", l)
                    if not km:
                        raise ToolError("line %d: expected KEY: value in block %s, got %r" % (i + 1, bname, l[:60]))
                    if km.group(1) in keys:
                        raise ToolError("line %d: key %s given twice in block %s" % (i + 1, km.group(1), bname))
                    keys[km.group(1)] = km.group(2).strip()
            else:
                buf.append(l)
            i += 1
        if not closed:
            raise ToolError("block %s is not closed with '=== END ==='" % bname)
        if cur is not None:
            secs[cur] = "\n".join(buf)
        blocks.append(Block(bname, keys, secs))
    mode = header.get("MODE")
    if not mode:
        raise ToolError("header line 'MODE:' is missing")
    if mode != m.group("mode"):
        raise ToolError("MODE in the file (%s) differs from the MODE in the file name (%s)" % (mode, m.group("mode")))
    if mode not in SPEC:
        raise ToolError("unknown MODE %s%s" % (mode, _suggest(mode, SPEC)))
    hdr_ok, blk_ok = SPEC[mode]
    for k in header:
        if k not in COMMON_HEADER and k not in hdr_ok:
            raise ToolError("unknown header key %s for MODE %s%s" % (k, mode, _suggest(k, COMMON_HEADER | set(hdr_ok))))
    for b in blocks:
        if b.name not in blk_ok:
            raise ToolError("unknown block %s for MODE %s%s" % (b.name, mode, _suggest(b.name, blk_ok)))
        kk, ss = blk_ok[b.name]
        for k in b.keys:
            if k not in kk:
                raise ToolError("unknown key %s in block %s%s" % (k, b.name, _suggest(k, kk)))
        for s in b.sections:
            if s not in ss:
                raise ToolError("unknown section %s in block %s%s" % (s, b.name, _suggest(s, ss)))
    return Request(path, header, blocks)


# ----------------------------------------------------------------------------- reading modes: SEARCH / COLLECT
def iter_files(base, folder="", exts=None):
    start = resolve(base, folder) if folder else base
    for dp, dns, fns in os.walk(start):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for f in sorted(fns):
            if exts and os.path.splitext(f)[1].lower() not in exts:
                continue
            yield os.path.join(dp, f)


def base_for(ctx, k):
    if (k.get("ROOT") or "PROJECT").upper() == "KIT":
        if not ctx.kit_root or not os.path.isdir(ctx.kit_root):
            raise ToolError("Kit folder not found (set kit_root in Debug\\Project_Operations.config.json)")
        return ctx.kit_root
    return ctx.root


def emit_code(ctx, header, text):
    f = fence(text)
    ctx.say(header)
    ctx.say(f)
    ctx.say(text)
    ctx.say(f)


def mode_search(ctx, req, res):
    blocks = req.of("FIND")
    if not blocks:
        return res.stop("no FIND block")
    for b in blocks:
        term = b.keys.get("TERM")
        if not term:
            return res.stop("FIND block without TERM")
        exts = [e if e.startswith(".") else "." + e for e in b.keys.get("EXT", "").replace(" ", "").lower().split(",") if e] or TEXT_EXT
        try:
            base = base_for(ctx, b.keys)
            cn, mx = int(b.keys.get("CONTEXT", "2")), int(b.keys.get("MAX", "100"))
        except ValueError:
            return res.stop("CONTEXT/MAX must be numbers")
        except ToolError as e:
            return res.stop(str(e))
        hits = shown = skipped = 0
        ctx.say('### FIND "%s"  (%s)' % (term, ", ".join(exts)))
        for path in iter_files(base, b.keys.get("FOLDER", ""), set(exts)):
            rel = relpath(base, path)
            if forbidden_read(rel):
                skipped += 1
                continue
            try:
                text = read_text(path)[0]
            except Exception:
                continue
            lines = text.split("\n")
            for idx, l in enumerate(lines):
                if term.lower() in l.lower():
                    hits += 1
                    if shown >= mx:
                        continue
                    a, z = max(0, idx - cn), min(len(lines), idx + cn + 1)
                    snip = "\n".join(lines[a:z])
                    shown += 1
                    fnd = guard_items(ctx, [(rel, rel, snip)])
                    if fnd:
                        ctx.say("- %s:%d  BLOCKED by Clipboard Guard (%s)" % (rel, idx + 1, fnd[0][2]))
                        continue
                    emit_code(ctx, "#### %s:%d" % (rel, idx + 1), "\n".join("%d: %s" % (k + 1, lines[k]) for k in range(a, z)))
        ctx.say("hits: %d, shown: %d%s" % (hits, shown, ", protected files skipped: %d" % skipped if skipped else ""))
    res.detail = "%d/%d read" % (len(blocks), len(blocks))


def find_lines(lines, block):
    ss = [l.strip() for l in block]
    k = len(ss)
    return [i for i in range(len(lines) - k + 1) if all(lines[i + j].strip() == ss[j] for j in range(k))]


def py_node(text, dotted):
    tree = ast.parse(text)
    body = tree.body
    node = None
    for part in dotted.split("."):
        node = None
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part:
                node = n
                break
        if node is None:
            raise ToolError("function/class not found: " + dotted)
        body = getattr(node, "body", [])
    start = min([d.lineno for d in node.decorator_list] + [node.lineno]) - 1
    return start, node.end_lineno


def heading_chunk(text, heading):
    lines = text.split("\n")
    infence, heads = False, []
    for i, l in enumerate(lines):
        if l.lstrip().startswith("```"):
            infence = not infence
        elif not infence:
            m = re.match(r"^(#+)\s+(.*)$", l)
            if m:
                heads.append((i, len(m.group(1)), m.group(2)))
    for n, (i, lvl, title) in enumerate(heads):
        if heading.lower() in title.lower():
            end = len(lines)
            for j, l2, _ in heads[n + 1:]:
                if l2 <= lvl:
                    end = j
                    break
            return "\n".join(lines[i:end])
    raise ToolError("heading not found: " + heading)


def tracker_section(ctx, sid):
    t, text = tracker_text(ctx)
    if not t:
        raise ToolError("no tracker found")
    body = section_between(text, "<!-- SECTION:%s -->" % sid, "<!-- /SECTION:%s -->" % sid)
    if body is not None:
        return body.strip("\n")
    m = re.match(r"^C-v(\d+\.\d+\.\d+)$", sid)
    if m:
        lines = text.split("\n")
        hx = re.compile(r"^## .*_v%s\.md$" % re.escape(m.group(1)))
        start = next((i for i, l in enumerate(lines) if hx.match(l)), None)
        if start is not None:
            end = len(lines)
            for j in range(start + 1, len(lines)):
                if lines[j].startswith("## APPENDIX A") or lines[j].startswith("<!-- /SECTION:") or re.match(r"^## .*_v\d+\.\d+\.\d+\.md$", lines[j]):
                    end = j
                    break
            return "\n".join(lines[start:end])
    raise ToolError("tracker section not found: " + sid)


def tracker_item(ctx, iid):
    t, text = tracker_text(ctx)
    if not t:
        raise ToolError("no tracker found")
    row = next((l for l in text.split("\n") if l.startswith("| %s |" % iid)), None)
    if row is None:
        raise ToolError("item not found on the status board: " + iid)
    hits = [l for l in text.split("\n") if iid in l and l != row]
    out = ["BOARD ROW:", row, "", "OTHER MENTIONS (%d, first 60 shown):" % len(hits)] + hits[:60]
    return "\n".join(out)


def collect_one(ctx, k):
    base = base_for(ctx, k)
    kinds = [x for x in ("FULL", "PARTIAL", "FUNC", "SECTION", "ITEM", "HEADING") if x in k]
    if len(kinds) != 1:
        raise ToolError("a READ block needs exactly one of FULL, PARTIAL, FUNC, SECTION, ITEM, FILE+HEADING")
    kind = kinds[0]
    if kind == "SECTION":
        return "SECTION " + k["SECTION"], "", tracker_section(ctx, k["SECTION"])
    if kind == "ITEM":
        return "ITEM " + k["ITEM"], "", tracker_item(ctx, k["ITEM"])
    if kind == "FUNC":
        if "::" not in k["FUNC"]:
            raise ToolError("FUNC needs path::name")
        rel, name = k["FUNC"].split("::", 1)
    elif kind == "HEADING":
        if "FILE" not in k:
            raise ToolError("HEADING needs FILE")
        rel = k["FILE"]
    else:
        rel = k[kind]
    why = forbidden_read(rel)
    if why:
        raise ToolError("protected path (%s): %s" % (why, rel))
    path = resolve(base, rel)
    if not os.path.isfile(path):
        raise ToolError("file not found: " + rel)
    text = read_text(path)[0]
    lines = text.split("\n")
    if kind == "FULL":
        return "FULL %s (%d lines, sha256 %s)" % (rel, len(lines), sha256_text(text)[:8]), rel, text
    if kind == "FUNC":
        a, z = py_node(text, name)
        return "FUNC %s (lines %d-%d)" % (k["FUNC"], a + 1, z), rel, "\n".join(lines[a:z])
    if kind == "HEADING":
        return "HEADING %s :: %s" % (rel, k["HEADING"]), rel, heading_chunk(text, k["HEADING"])
    if "LINES" in k:
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", k["LINES"])
        if not m:
            raise ToolError("LINES must look like 10-40")
        a, z = int(m.group(1)), int(m.group(2))
        return "PARTIAL %s (lines %d-%d)" % (rel, a, z), rel, "\n".join(lines[a - 1:z])
    if "FROM" not in k or "TO" not in k:
        raise ToolError("PARTIAL needs FROM and TO, or LINES")
    f = find_lines(lines, [k["FROM"]])
    if len(f) != 1:
        raise ToolError("PARTIAL FROM line %s (found %d times)" % ("not unique" if f else "not found", len(f)))
    t2 = next((i for i in range(f[0], len(lines)) if lines[i].strip() == k["TO"].strip()), None)
    if t2 is None:
        raise ToolError("PARTIAL TO line not found after FROM")
    return "PARTIAL %s (lines %d-%d)" % (rel, f[0] + 1, t2 + 1), rel, "\n".join(lines[f[0]:t2 + 1])


def mode_collect(ctx, req, res):
    blocks = req.of("READ")
    if not blocks:
        return res.stop("no READ block")
    ok = blocked = 0
    for b in blocks:
        try:
            label, rel, text = collect_one(ctx, b.keys)
        except ToolError as e:
            ctx.say("#### READ failed: %s" % e)
            continue
        fnd = guard_items(ctx, [(label, rel, text)])
        if fnd:
            blocked += 1
            ctx.say("#### %s  BLOCKED by Clipboard Guard: %s (secret values are never printed)" % (label, ", ".join("%s@line %d" % (k, n) if n else k for _, n, k in fnd[:6])))
            continue
        ok += 1
        emit_code(ctx, "#### " + label, text)
    res.detail = "%d/%d read%s" % (ok, len(blocks), (", %d blocked by the Clipboard Guard" % blocked) if blocked else "")
    if ok == 0:
        res.stop("nothing could be read (%d blocked)" % blocked)


# ----------------------------------------------------------------------------- batches (backup / undo)
def new_batch(ctx, req, kind):
    stamp = stamp_now(ctx.now())
    d, n = ctx.p("Debug/Backups/batch_" + stamp), 1
    while os.path.exists(d):
        n += 1
        d = ctx.p("Debug/Backups/batch_%s_%d" % (stamp, n))
    os.makedirs(os.path.join(d, "files"), exist_ok=True)
    return {"dir": d, "stamp": os.path.basename(d)[6:], "kind": kind, "request": req.name if req else "", "thread": req.thr if req else 0,
            "num": req.num if req else 0, "files": [], "status": "pending"}


def batch_base(ctx, key):
    return ctx.kit_root if key == "K" else ctx.root


def batch_save_original(ctx, batch, key, rel, path):
    existed = os.path.isfile(path)
    ent = {"base": key, "rel": rel, "existed": existed, "sha_before": None, "sha_after": None}
    if existed:
        data = open(path, "rb").read()
        ent["sha_before"] = sha256_bytes(data)
        dst = os.path.join(batch["dir"], "files", key, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(data)
    batch["files"].append(ent)
    return ent


def batch_write(batch):
    m = {k: v for k, v in batch.items() if k != "dir"}
    open(os.path.join(batch["dir"], "manifest.json"), "w", encoding="utf-8").write(json.dumps(m, indent=1))


def list_batches(ctx):
    d = ctx.p("Debug/Backups")
    out = []
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            mp = os.path.join(d, n, "manifest.json")
            if n.startswith("batch_") and os.path.isfile(mp):
                try:
                    m = json.load(open(mp, encoding="utf-8"))
                    m["dir"] = os.path.join(d, n)
                    out.append(m)
                except Exception:
                    pass
    return out


def restore_entry(ctx, batch, ent):
    path = os.path.join(batch_base(ctx, ent["base"]), *ent["rel"].split("/"))
    if ent["existed"]:
        src = os.path.join(batch["dir"], "files", ent["base"], *ent["rel"].split("/"))
        data = open(src, "rb").read()
        write_atomic(path, data)
        if sha256_bytes(open(path, "rb").read()) != ent["sha_before"]:
            raise ToolError("restore verification failed: " + ent["rel"])
    elif os.path.isfile(path):
        keep = os.path.join(batch["dir"], "created", ent["base"], *ent["rel"].split("/"))
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        shutil.copy2(path, keep)
        os.remove(path)


def mode_undo_last(ctx, req, res):
    cand = [b for b in list_batches(ctx) if b.get("status") == "applied"]
    if not cand:
        return res.stop("nothing to undo (no applied batch found)")
    b = cand[-1]
    lines = ["UNDO plan: batch %s (%s, request %s)" % (b["stamp"], b["kind"], b["request"])]
    for e in b["files"]:
        lines.append("  - %s  %s" % (e["rel"], "restore previous content" if e["existed"] else "remove (file was created by that batch)"))
    kind = "u" if any(e["base"] == "P" and is_locked(ctx, e["rel"]) for e in b["files"]) else "enter"
    if not gate(ctx, kind, lines):
        return res.cancel()
    for e in b["files"]:
        restore_entry(ctx, b, e)
        res.changed.append(e["rel"])
    b["status"] = "undone"
    batch_write(b)
    ctx.say("%s Undone: %d file(s) restored." % (icon("ok"), len(b["files"])))
    res.detail = "%d/%d restored" % (len(b["files"]), len(b["files"]))


def mode_restore(ctx, req, res):
    blocks = req.of("FILE")
    if not blocks:
        return res.stop("no FILE block")
    plan = []
    for bl in blocks:
        rel = bl.keys.get("PATH", "")
        try:
            resolve(ctx.root, rel)
        except ToolError as e:
            return res.stop(str(e))
        found = None
        for b in reversed(list_batches(ctx)):
            if bl.keys.get("BACKUP") and b["stamp"] != bl.keys["BACKUP"]:
                continue
            for e in b["files"]:
                if e["base"] == "P" and e["rel"] == rel and e["existed"]:
                    found = (b, e)
                    break
            if found:
                break
        if not found:
            return res.stop("no backup found for " + rel)
        plan.append(found)
    lines = ["RESTORE plan:"] + ["  - %s  from batch %s" % (e["rel"], b["stamp"]) for b, e in plan]
    kind = "u" if any(is_locked(ctx, e["rel"]) for b, e in plan) else "enter"
    if not gate(ctx, kind, lines):
        return res.cancel()
    nb = new_batch(ctx, req, "RESTORE")
    for b, e in plan:
        path = ctx.p(e["rel"])
        ent = batch_save_original(ctx, nb, "P", e["rel"], path)
        restore_entry(ctx, b, dict(e, existed=True, sha_before=e["sha_before"]))
        ent["sha_after"] = e["sha_before"]
        res.changed.append(e["rel"])
    nb["status"] = "applied"
    batch_write(nb)
    ctx.say("%s Restored %d file(s)." % (icon("ok"), len(plan)))
    res.detail = "%d/%d restored" % (len(plan), len(plan))


# ----------------------------------------------------------------------------- REPLACE
def dup_defs(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    dups = set()

    def scan(body, scope):
        seen = {}
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                decos = " ".join(ast.dump(d) for d in n.decorator_list)
                if any(w in decos for w in ("setter", "getter", "deleter", "overload")):
                    continue
                if n.name in seen:
                    dups.add("%s%s" % (scope, n.name))
                seen[n.name] = True
                if isinstance(n, ast.ClassDef):
                    scan(n.body, scope + n.name + ".")
    scan(tree.body, "")
    return dups


def diff_stats(a, b):
    add = rem = 0
    for l in difflib.unified_diff(a.split("\n"), b.split("\n"), lineterm="", n=0):
        if l.startswith("+") and not l.startswith("+++"):
            add += 1
        elif l.startswith("-") and not l.startswith("---"):
            rem += 1
    return add, rem


def lead(l):
    return len(l) - len(l.lstrip(" "))


def restart_hint(changes):
    full, mig, css = False, False, False
    for rel, old, new in changes:
        r = rel.lower()
        if r.endswith("rxconfig.py") or r.endswith("models.py") or "alembic/" in r:
            full = True
        if "alembic/" in r or r.endswith("models.py"):
            mig = True
        if r.endswith(".css"):
            css = True
        if r.endswith(".py") and ("rx.State" in new or "State)" in new):
            oldset = set(re.findall(r"^\s*(?:async\s+)?def\s+(\w+)|^\s{4}(\w+)\s*:\s*[\w\[\], .]+\s*=", old, re.M))
            newset = set(re.findall(r"^\s*(?:async\s+)?def\s+(\w+)|^\s{4}(\w+)\s*:\s*[\w\[\], .]+\s*=", new, re.M))
            if newset - oldset:
                full = True
    msg = "Restart hint: "
    if full:
        msg += "FULL SERVER RESTART (Ctrl+C, start again) then hard refresh (Ctrl+Shift+R) - new State members, config or models changed."
    elif css:
        msg += "hot reload is enough; hard refresh (Ctrl+Shift+R) if the style does not change."
    else:
        msg += "hot reload should be enough; do a full restart if something looks old."
    if mig:
        msg += " MIGRATION WARNING: models/alembic changed - check that a migration is needed."
    return msg


def default_eol(rel):
    return "\r\n" if rel.lower().endswith((".bat", ".ps1", ".cmd")) else "\n"


def plan_replace(ctx, req, res):
    files = {}
    ops = req.of("OP")
    if not ops:
        raise ToolError("no OP block")
    for n, b in enumerate(ops, 1):
        k = b.keys
        kind = (k.get("KIND") or "").upper()
        rel = (k.get("FILE") or "").replace("\\", "/")
        if kind not in ("REPLACE", "INSERT_AFTER", "WRITE_FILE"):
            raise ToolError("OP %d: KIND must be REPLACE, INSERT_AFTER or WRITE_FILE" % n)
        path = ctx.p(rel)
        why = forbidden_write(rel)
        if why:
            raise ToolError("OP %d: %s (%s)" % (n, rel, why))
        if os.path.basename(rel) == "4. Project_Operations_Core.py":
            raise ToolError("OP %d: the tool itself is changed only by SELFUPDATE" % n)
        st = files.get(rel)
        if st is None:
            if os.path.isfile(path):
                text, meta = read_text(path)
                st = {"exists": True, "orig": text, "text": text, "meta": meta, "notes": [], "applied": 0}
            else:
                st = {"exists": False, "orig": "", "text": "", "meta": None, "notes": [], "applied": 0}
            files[rel] = st
        if kind == "WRITE_FILE":
            if "CONTENT" not in b.sections:
                raise ToolError("OP %d: WRITE_FILE needs a --- CONTENT --- section" % n)
            new = b.sections["CONTENT"] + ("" if k.get("FINAL_NEWLINE", "yes").lower() == "no" else "\n")
            if k.get("SHA256") and sha256_text(new) != k["SHA256"].lower():
                raise ToolError("OP %d: SHA256 of the embedded content does not match (download damaged?)" % n)
            if st["exists"] and st["orig"] == new and st["text"] == new:
                st["notes"].append("already applied")
                continue
            if st["exists"] and k.get("OVERWRITE", "no").lower() != "yes" and st["text"] == st["orig"]:
                raise ToolError("OP %d: %s exists - add 'OVERWRITE: yes' to replace it" % (n, rel))
            st["text"] = new
            if st["meta"] is None:
                eol = {"crlf": "\r\n", "lf": "\n"}.get(k.get("EOL", "").lower(), default_eol(rel))
                st["meta"] = {"bom": False, "eol": eol}
            st["applied"] += 1
            continue
        if not st["exists"] and st["applied"] == 0:
            raise ToolError("OP %d: file not found: %s" % (n, rel))
        anchor = b.sections.get("ANCHOR")
        if anchor is None:
            raise ToolError("OP %d: %s needs a --- ANCHOR --- section" % (n, kind))
        alines = anchor.split("\n")
        while alines and alines[0].strip() == "":
            alines.pop(0)
        while alines and alines[-1].strip() == "":
            alines.pop()
        if not alines:
            raise ToolError("OP %d: the ANCHOR is empty" % n)
        new_s = b.sections.get("NEW")
        if new_s is None:
            raise ToolError("OP %d: %s needs a --- NEW --- section" % (n, kind))
        nlines = new_s.split("\n") if new_s != "" else []
        lines = st["text"].split("\n")
        hits = find_lines(lines, alines)
        if kind == "REPLACE":
            if not hits:
                if nlines and len(find_lines(lines, nlines)) == 1:
                    st["notes"].append("OP %d already applied" % n)
                    continue
                raise ToolError("OP %d: anchor not found in %s (first anchor line: %r)" % (n, rel, alines[0].strip()[:70]))
            if len(hits) > 1:
                raise ToolError("OP %d: anchor is not unique in %s (found %d times, lines %s) - add more lines to the anchor" % (n, rel, len(hits), ", ".join(str(h + 1) for h in hits[:6])))
            i = hits[0]
            nf = next((l for l in nlines if l.strip()), None)
            st.setdefault("echo", []).append("OP %d indentation: anchor first line=%d spaces, NEW first line=%s spaces" % (n, lead(lines[i]), lead(nf) if nf is not None else "-"))
            if nf is not None and lead(nf) != lead(lines[i]):
                st["notes"].append("indentation warning OP %d: anchor first line has %d spaces, NEW first line has %d" % (n, lead(lines[i]), lead(nf)))
            lines[i:i + len(alines)] = nlines
        else:
            if not hits:
                raise ToolError("OP %d: anchor not found in %s (first anchor line: %r)" % (n, rel, alines[0].strip()[:70]))
            if len(hits) > 1:
                raise ToolError("OP %d: anchor is not unique in %s (found %d times) - add more lines to the anchor" % (n, rel, len(hits)))
            i = hits[0] + len(alines)
            if nlines and [x.strip() for x in lines[i:i + len(nlines)]] == [x.strip() for x in nlines]:
                st["notes"].append("OP %d already applied" % n)
                continue
            last = lines[i - 1]
            nf = next((l for l in nlines if l.strip()), None)
            st.setdefault("echo", []).append("OP %d indentation: anchor last line=%d spaces, NEW first line=%s spaces" % (n, lead(last), lead(nf) if nf is not None else "-"))
            if nf is not None and lead(nf) != lead(last) and not (lead(nf) == lead(last) + 4 and last.rstrip().endswith(":")):
                st["notes"].append("indentation warning OP %d: anchor last line has %d spaces, NEW first line has %d" % (n, lead(last), lead(nf)))
            lines[i:i] = nlines
        st["text"] = "\n".join(lines)
        st["applied"] += 1
    for rel, st in files.items():
        if st["text"] == st["orig"] and st["exists"]:
            st["changed"] = False
            continue
        st["changed"] = st["text"] != st["orig"] or not st["exists"]
        if st["changed"]:
            if rel.lower().endswith(".py"):
                try:
                    ast.parse(st["text"])
                except SyntaxError as e:
                    raise ToolError("%s would have a syntax error (line %s: %s) - nothing was written" % (rel, e.lineno, e.msg))
            if rel.lower().endswith(".json"):
                try:
                    json.loads(st["text"])
                except ValueError as e:
                    raise ToolError("%s would not be valid JSON (%s) - nothing was written" % (rel, e))
            before, after = dup_defs(st["orig"]), dup_defs(st["text"])
            if after - before:
                st["notes"].append("DUPLICATE DEFINITIONS introduced: " + ", ".join(sorted(after - before)))
            if after & before:
                st["notes"].append("existing duplicate definitions (not caused by this change): " + ", ".join(sorted(after & before)))
    return files


def apply_batch(ctx, req, files, kind="REPLACE"):
    batch = new_batch(ctx, req, kind)
    written = []
    try:
        for rel, st in files.items():
            if not st["changed"]:
                continue
            path = ctx.p(rel)
            ent = batch_save_original(ctx, batch, "P", rel, path)
            data = encode_text(st["text"], st["meta"])
            write_atomic(path, data)
            if sha256_bytes(open(path, "rb").read()) != sha256_bytes(data):
                raise ToolError("write verification failed: " + rel)
            if rel.lower().endswith(".py"):
                compile(read_text(path)[0], path, "exec")
            ent["sha_after"] = sha256_bytes(data)
            written.append(ent)
        batch["status"] = "applied"
        batch_write(batch)
    except Exception as e:
        for ent in written + [x for x in batch["files"] if x not in written]:
            try:
                restore_entry(ctx, batch, ent)
            except Exception:
                pass
        batch["status"] = "failed"
        batch_write(batch)
        raise ToolError("post-check failed, previous content restored automatically: %s" % e)
    return batch


def mode_replace(ctx, req, res):
    try:
        files = plan_replace(ctx, req, res)
    except ToolError as e:
        return res.stop(str(e))
    changed = {r: s for r, s in files.items() if s["changed"]}
    ctx.say("### Plan")
    tot = 0
    locked = []
    for rel, st in files.items():
        if st["changed"]:
            a, d = diff_stats(st["orig"], st["text"])
            tot += a + d
            flag = "[new file]" if not st["exists"] else ""
            if is_locked(ctx, rel):
                locked.append(rel)
                flag += " [LOCKED AREA]"
            ctx.say("- %s  +%d -%d %s" % (rel, a, d, flag))
        else:
            ctx.say("- %s  no change (already applied)" % rel)
        for n in st["notes"]:
            ctx.say("    %s %s" % (icon("warn"), n))
        for n in st.get("echo", []):
            ctx.say("    %s %s" % (icon("info"), n))
    if not changed:
        res.detail = "0/0 applied - nothing to do (everything was already applied)"
        return res
    dry = req.header.get("DRYRUN", "no").lower() == "yes"
    big = tot > int(ctx.cfg.get("auto_dry_run_lines", 60)) or req.header.get("DATA_REPAIR", "no").lower() == "yes"
    if dry:
        ctx.say("%s DRY RUN: nothing was written." % icon("info"))
        res.detail = "dry run - %d file(s) would change, nothing written" % len(changed)
        return res
    lines = ["%s %d file(s), %d changed lines.%s" % (icon("info"), len(changed), tot, " LARGE CHANGE or data repair: the plan above is the dry-run report." if big else "")]
    if locked:
        lines.append("%s LOCKED AREA touched: %s" % (icon("warn"), ", ".join(locked)))
    if not gate(ctx, "u" if locked else "enter", lines):
        return res.cancel()
    try:
        batch = apply_batch(ctx, req, files)
    except ToolError as e:
        return res.stop(str(e))
    res.changed = [r for r in changed]
    for rel in changed:
        ctx.say("%s applied %s (backup in Debug\\Backups\\batch_%s)" % (icon("ok"), rel, batch["stamp"]))
    ctx.say(restart_hint([(r, s["orig"], s["text"]) for r, s in changed.items()]))
    fails = run_checks(ctx, "quick", only_if_defined=True)
    res.detail = "%d/%d applied" % (len(changed), len(changed))
    if fails:
        ctx.say("%s AUTOMATIC TESTS FAILED (%d). Use UNDO_LAST if the change is wrong:" % (icon("fail"), len(fails)))
        for f in fails:
            ctx.say(f)
        res.detail += " - TESTS FAILED (%d)" % len(fails)
    return res


# ----------------------------------------------------------------------------- PLACE
def find_download(ctx, sha, hint):
    d = ctx.downloads
    if not os.path.isdir(d):
        return None
    cands = []
    h = os.path.join(d, hint or "")
    if hint and os.path.isfile(h):
        cands.append(h)
    allf = [os.path.join(d, f) for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
    allf.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for p in cands + allf[:300]:
        try:
            if os.path.getsize(p) > 80 * 1024 * 1024:
                continue
            s1 = os.path.getsize(p)
            time.sleep(getattr(ctx, "stable_wait", 0.4))
            if os.path.getsize(p) != s1:
                continue
            data = open(p, "rb").read()
        except Exception:
            continue
        if sha256_bytes(data) == sha:
            return data
    return None


def mode_place(ctx, req, res):
    blocks = req.of("FILE")
    if not blocks:
        return res.stop("no FILE block")
    jobs = []
    for n, b in enumerate(blocks, 1):
        k = b.keys
        if not k.get("PROJECT_PATH") and not k.get("KIT_PATH"):
            return res.stop("FILE %d: give PROJECT_PATH and/or KIT_PATH" % n)
        text = data = None
        if "SOURCE_DOWNLOAD" in k:
            if not k.get("SHA256"):
                return res.stop("FILE %d: SOURCE_DOWNLOAD needs SHA256 (of the raw bytes)" % n)
            data = find_download(ctx, k["SHA256"].lower(), k["SOURCE_DOWNLOAD"])
            if data is None:
                return res.stop("FILE %d: no file with that SHA256 found in %s (download it first)" % (n, ctx.downloads))
        else:
            if "CONTENT" not in b.sections:
                return res.stop("FILE %d: needs --- CONTENT --- or SOURCE_DOWNLOAD" % n)
            text = b.sections["CONTENT"] + ("" if k.get("FINAL_NEWLINE", "yes").lower() == "no" else "\n")
            if k.get("SHA256") and sha256_text(text) != k["SHA256"].lower():
                return res.stop("FILE %d: SHA256 of the embedded content does not match (download damaged?)" % n)
        for key, label in (("PROJECT_PATH", "P"), ("KIT_PATH", "K")):
            if not k.get(key):
                continue
            rel = k[key].replace("\\", "/")
            try:
                if label == "K":
                    if not ctx.kit_root or not os.path.isdir(ctx.kit_root):
                        return res.stop("Kit folder not found; set kit_root in Debug\\Project_Operations.config.json")
                    path = resolve(ctx.kit_root, rel)
                else:
                    path = resolve(ctx.root, rel)
            except ToolError as e:
                return res.stop(str(e))
            why = forbidden_write(rel)
            if why:
                return res.stop("%s (%s)" % (rel, why))
            jobs.append({"label": label, "rel": rel, "path": path, "text": text, "data": data, "key": k})
    ctx.say("### PLACE   PC: %s   Project: %s   Kit: %s" % (pc_name(), ctx.root, ctx.kit_root or "(not found)"))
    need_u, need_enter = [], []
    for j in jobs:
        ex = os.path.isfile(j["path"])
        j["state"] = "new"
        meta = None
        if j["text"] is not None:
            if ex:
                old, meta = read_text(j["path"])
                j["state"] = "same" if old == j["text"] else "replace"
            else:
                eol = {"crlf": "\r\n", "lf": "\n"}.get(j["key"].get("EOL", "").lower(), default_eol(j["rel"]))
                meta = {"bom": False, "eol": eol}
            j["bytes"] = encode_text(j["text"], meta) if meta else None
        else:
            j["bytes"] = j["data"]
            if ex:
                j["state"] = "same" if open(j["path"], "rb").read() == j["data"] else "replace"
        if j["state"] == "replace":
            ext = os.path.splitext(j["rel"])[1].lower()
            if j["label"] == "P" and is_locked(ctx, j["rel"]):
                need_u.append(j["rel"])
            elif ext in CODE_EXT or os.path.basename(j["rel"]).startswith("Common_Project_Instructions"):
                need_enter.append(j["rel"])
    if need_u or need_enter:
        lines = ["%s These files already exist and will be replaced (a backup is kept):" % icon("warn")] + ["  - " + r for r in need_u + need_enter]
        if not gate(ctx, "u" if need_u else "enter", lines):
            return res.cancel()
    batch = new_batch(ctx, req, "PLACE")
    okc = same = fail = 0
    try:
        for j in jobs:
            tag = "project" if j["label"] == "P" else "kit    "
            if j["state"] == "same":
                same += 1
                ctx.say(" %s %s  %s  (already identical, skipped)" % (icon("same"), tag, j["path"]))
                continue
            ent = batch_save_original(ctx, batch, j["label"], j["rel"], j["path"])
            write_atomic(j["path"], j["bytes"])
            back = open(j["path"], "rb").read()
            good = sha256_bytes(back) == sha256_bytes(j["bytes"])
            ent["sha_after"] = sha256_bytes(back)
            if good:
                okc += 1
                ctx.say(" %s %s  %s  (%s, hash verified)" % (icon("ok"), tag, j["path"], "replaced, backup kept" if j["state"] == "replace" else "new"))
                if j["label"] == "P":
                    res.changed.append(j["rel"])
            else:
                fail += 1
                ctx.say(" %s %s  %s  (HASH MISMATCH)" % (icon("fail"), tag, j["path"]))
        batch["status"] = "applied"
        batch_write(batch)
    except Exception as e:
        batch["status"] = "failed"
        batch_write(batch)
        return res.stop("could not place: %s" % e)
    total = len(jobs)
    if fail:
        return res.stop("%d of %d targets failed verification" % (fail, total))
    ctx.say("%s PLACE complete: %d placed, %d identical (of %d targets)." % (icon("ok"), okc, same, total))
    res.detail = "%d of %d targets OK (%d placed, %d identical)" % (okc + same, total, okc, same)


# ----------------------------------------------------------------------------- TEST
def load_checks(ctx):
    p = ctx.p("Documentation/Checks.json")
    if not os.path.isfile(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        raise ToolError("Documentation/Checks.json is not valid JSON: %s" % e)


def builtin_syntax(ctx):
    bad = []
    for path in iter_files(ctx.root, "", {".py"}):
        try:
            compile(read_text(path)[0], path, "exec")
        except SyntaxError as e:
            bad.append("%s line %s: %s" % (relpath(ctx.root, path), e.lineno, e.msg))
        except ToolError:
            pass
    return bad


def run_one_check(ctx, name, spec):
    cmd = [sys.executable if c == "python" else c for c in spec.get("cmd", [])]
    if not cmd:
        return "- %s: FAILED (no cmd)" % name
    try:
        p = subprocess.run(cmd, cwd=ctx.root, capture_output=True, text=True, timeout=int(spec.get("timeout", 300)))
    except Exception as e:
        return "- %s: FAILED (%s)" % (name, e)
    if p.returncode == 0:
        return None
    tail = "\n".join(((p.stdout or "") + (p.stderr or "")).strip().split("\n")[-25:])
    return "- %s: FAILED (exit %d)\n%s" % (name, p.returncode, tail)


def run_checks(ctx, setname="quick", only_if_defined=False, names=None):
    cfg = load_checks(ctx)
    if cfg is None:
        if only_if_defined:
            return []
        bad = builtin_syntax(ctx)
        return ["- syntax: " + b for b in bad]
    checks, sets = cfg.get("checks", {}), cfg.get("sets", {})
    if names is None:
        if setname not in sets:
            return [] if only_if_defined else ["- set %r is not defined in Checks.json" % setname]
        names = sets[setname]
    fails = []
    for n in names:
        if n == "syntax":
            fails += ["- syntax: " + b for b in builtin_syntax(ctx)]
        elif n in checks:
            r = run_one_check(ctx, n, checks[n])
            if r:
                fails.append(r)
        else:
            fails.append("- check %r is not defined in Checks.json" % n)
    return fails


def mode_test(ctx, req, res):
    runs = req.of("RUN")
    total, fails = 0, []
    if not runs:
        runs = [Block("RUN", {"SET": "quick"}, {})]
    cfg = load_checks(ctx)
    for b in runs:
        if "CHECK" in b.keys:
            names = [b.keys["CHECK"]]
        else:
            sname = b.keys.get("SET", "quick")
            names = ((cfg or {}).get("sets", {}).get(sname)) or (["syntax"] if cfg is None else None)
            if names is None:
                return res.stop("set %r is not defined in Checks.json" % sname)
        total += len(names)
        fails += run_checks(ctx, names=names)
    ctx.say("### TEST: %d check(s), %d failed" % (total, len(fails)))
    for f in fails:
        ctx.say(f)
    if fails:
        ctx.say("%s FAILURES ONLY are shown above." % icon("fail"))
    else:
        ctx.say("%s all checks passed" % icon("ok"))
    res.detail = "%d/%d passed" % (total - len(fails), total)


# ----------------------------------------------------------------------------- MAP
def project_files(ctx):
    files = []
    used_git = False
    if os.path.isdir(ctx.p(".git")) and shutil.which("git"):
        try:
            p = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ctx.root, capture_output=True, timeout=60)
            if p.returncode == 0:
                used_git = True
                for r in p.stdout.decode("utf-8", "replace").split("\0"):
                    if r and not (set(r.replace("\\", "/").split("/")[:-1]) & SKIP_DIRS) and os.path.isfile(ctx.p(r)):
                        files.append(r.replace("\\", "/"))
        except Exception:
            used_git = False
    if not used_git:
        for dp, dns, fns in os.walk(ctx.root):
            dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
            for f in sorted(fns):
                files.append(relpath(ctx.root, os.path.join(dp, f)))
    return sorted(set(files))


def py_symbols(text):
    out = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out

    def walk(body, ind):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = (ast.get_docstring(n) or "").split("\n")[0][:80]
                kind = "class" if isinstance(n, ast.ClassDef) else "def"
                out.append("%sL%d %s %s%s" % ("  " * ind, n.lineno, kind, n.name, (" - " + doc) if doc else ""))
                if isinstance(n, ast.ClassDef):
                    walk(n.body, ind + 1)
    walk(tree.body, 0)
    return out


def build_map(ctx):
    files = project_files(ctx)
    dirs = {}
    for f in files:
        parts = f.split("/")
        size = os.path.getsize(ctx.p(f))
        for d in range(len(parts)):
            key = "/".join(parts[:d]) if d else ""
            c = dirs.setdefault(key, [0, 0])
            c[0] += 1
            c[1] += size
    full = ["# Project_Map_Full", "Generated %s | root %s | tool %s | files %d" % (ctx.now().strftime("%d-%m-%Y %H:%M"), ctx.root, TOOL_VERSION, len(files)), "", "## Files"]
    for f in files:
        full.append("%s  (%d bytes)" % (f, os.path.getsize(ctx.p(f))))
        if f.lower().endswith(".py"):
            try:
                full += ["    " + s for s in py_symbols(read_text(ctx.p(f))[0])]
            except ToolError:
                pass
    summ = ["# Project_Map_Summary (tree to depth 3)", "root: %s | files: %d" % (os.path.basename(ctx.root), len(files))]
    for key in sorted(k for k in dirs if k and k.count("/") < 3):
        n, sz = dirs[key]
        summ.append("%s%s/  (%d files, %d KB)" % ("  " * key.count("/"), key.split("/")[-1], n, max(1, sz // 1024)))
    top = [f for f in files if "/" not in f]
    summ.append("top-level files: " + ", ".join(top[:40]) + (" ..." if len(top) > 40 else ""))
    s = "\n".join(summ)
    if len(s) > 6000:
        s = s[:5900].rsplit("\n", 1)[0] + "\n... (truncated at 6,000 characters)"
    d = ctx.p(BUNDLE_FOLDER)
    os.makedirs(d, exist_ok=True)
    write_atomic(os.path.join(d, "Project_Map_Full.md"), ("\n".join(full) + "\n").encode("utf-8"))
    write_atomic(os.path.join(d, "Project_Map_Summary.md"), (s + "\n").encode("utf-8"))
    return s, len(files)


def mode_map(ctx, req, res):
    s, n = build_map(ctx)
    ctx.say("%s Map built: %d files. Full map and summary are in %s\\" % (icon("ok"), n, BUNDLE_FOLDER))
    ctx.say(s)
    res.detail = "%d files mapped" % n


# ----------------------------------------------------------------------------- PREFLIGHT
GITIGNORE_LINES = ["venv/", ".venv/", "__pycache__/", ".web/", "node_modules/", ".env", "Clutter/", BUNDLE_FOLDER + "/", "Debug/Backups/", "Debug/Restore_Maintenance/",
                   "Debug/Project_Operations.config.json", "Debug/Ops_State.json", "Debug/Ops_Log.md", "Debug/relay_state.json", "Debug/ops.lock", "Debug/ops_run.lock"]


def required_rows(ctx):
    rows = []
    _, text = tracker_text(ctx)
    for l in block_lines(text, "REQUIRED_SCRIPTS"):
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].lower() != "slot" and not set(cells[0]) <= set("-: "):
            rows.append({"slot": cells[0], "file": cells[1], "purpose": cells[2], "level": cells[3].upper()})
    return rows


def preflight(ctx):
    out = {"problems": [], "verify": [], "planned": [], "repaired": [], "gitignore_gaps": []}
    for d in ("Documentation", TRACKER_FOLDER, "Documentation/PathReference", "Documentation/Help_Source", "Debug", "Debug/Backups"):
        p = ctx.p(d)
        if not os.path.isdir(p):
            os.makedirs(p, exist_ok=True)
            out["repaired"].append("created folder " + d)
    need = [{"slot": "4.", "file": f, "purpose": "Project_Operations tool file", "level": "REQUIRED"} for f in TOOL_FILES]
    need.append({"slot": "-", "file": "Documentation/Project_Code.txt", "purpose": "one line with the project code", "level": "REQUIRED"})
    need += required_rows(ctx)
    seen = set()
    for r in need:
        if r["file"] in seen:
            continue
        seen.add(r["file"])
        try:
            p = ctx.p(r["file"])
        except ToolError:
            continue
        if os.path.exists(p):
            continue
        fixed = False
        if ctx.kit_root and os.path.isdir(ctx.kit_root):
            base = os.path.basename(r["file"])
            for c in (os.path.join(ctx.kit_root, "Scripts", "Project_Operations", base), os.path.join(ctx.kit_root, "Scripts", base)):
                if os.path.isfile(c):
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    shutil.copy2(c, p)
                    out["repaired"].append("restored %s from the Kit" % r["file"])
                    fixed = True
                    break
        if fixed:
            continue
        key = {"REQUIRED": "problems", "VERIFY": "verify", "PLANNED": "planned"}.get(r["level"], "problems")
        out[key].append(r)
    gi = ctx.p(".gitignore")
    have = set()
    if os.path.isfile(gi):
        have = {l.strip().strip("/").lstrip("/") for l in read_text(gi)[0].split("\n")}
    out["gitignore_gaps"] = [l for l in GITIGNORE_LINES if l.strip("/") not in have]  # report only, never edited (Jay, 14-10-2026)
    if out["problems"]:
        lines = ["# Preflight report", ""] + ["- MISSING: %s (slot %s) - %s" % (r["file"], r["slot"], r["purpose"]) for r in out["problems"]]
        write_atomic(ctx.p("Debug/Preflight_Report.md"), ("\n".join(lines) + "\n").encode("utf-8"))
        prompt = ("Please generate these missing project files first, so that I can operate the process (Common instructions, Section 7.13). "
                  "For each file give the full path and say plainly what to do with it:\n" +
                  "\n".join("- %s  (slot %s: %s)" % (r["file"], r["slot"], r["purpose"]) for r in out["problems"]))
        write_atomic(ctx.p("Debug/AI_Prompt_Generate_Missing.txt"), prompt.encode("utf-8"))
        out["prompt"] = prompt
    return out


def mode_preflight(ctx, req, res):
    r = preflight(ctx)
    for x in r["repaired"]:
        ctx.say("%s repaired: %s" % (icon("ok"), x))
    for x in r["verify"]:
        ctx.say("%s verify: %s (%s)" % (icon("warn"), x["file"], x["purpose"]))
    for x in r["planned"]:
        ctx.say("%s planned (not built yet): %s" % (icon("info"), x["file"]))
    for x in r["problems"]:
        ctx.say("%s MISSING: %s (slot %s) - %s" % (icon("fail"), x["file"], x["slot"], x["purpose"]))
    if r.get("gitignore_gaps"):
        ctx.say("%s .gitignore is missing %d recommended line(s) (report only, nothing was edited): %s" % (icon("warn"), len(r["gitignore_gaps"]), ", ".join(r["gitignore_gaps"])))
    if r["problems"]:
        ok = safe_copy(ctx, r["prompt"], "PREFLIGHT prompt") == "ok"
        ctx.say("%s Paste this to the AI first (%s):" % (icon("warn"), "it is on your clipboard" if ok else "clipboard unavailable or blocked - see Debug\\AI_Prompt_Generate_Missing.txt"))
        ctx.say(r["prompt"])
        res.detail = "PREFLIGHT: %d missing" % len(r["problems"])
    else:
        ctx.say("%s PREFLIGHT: OK" % icon("ok"))
        res.detail = "PREFLIGHT: OK"
    return r


# ----------------------------------------------------------------------------- TRACKER operations
HEADER_ROW = r"^\| %s \|.*\|$"


def set_header_row(text, label, value):
    head_end = text.find("## PART A")
    head_end = head_end if head_end > 0 else len(text)
    head = text[:head_end]
    pat = re.compile(HEADER_ROW % re.escape(label), re.M)
    if pat.search(head):
        head = pat.sub(lambda m: "| %s | %s |" % (label, value), head, count=1)
    else:
        lines = head.split("\n")
        idx = next((i for i, l in enumerate(lines) if l.startswith("| This file |")), None)
        pos = (idx + 1) if idx is not None else next((i for i, l in enumerate(lines) if l.startswith("|---")), 1) + 1
        lines.insert(pos, "| %s | %s |" % (label, value))
        head = "\n".join(lines)
    return head + text[head_end:]


def board_bounds(text):
    a = text.find("<!-- STATUS_BOARD_START -->")
    b = text.find("<!-- STATUS_BOARD_END -->")
    if a < 0 or b < 0:
        raise ToolError("status board markers not found in the tracker")
    return a + len("<!-- STATUS_BOARD_START -->"), b


def board_rows(text):
    a, b = board_bounds(text)
    return [l for l in text[a:b].split("\n") if l.startswith("| ") and not l.startswith("| ID |") and not l.startswith("|---")]


def cells_of(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def validate_tracker(text):
    for m in re.finditer(r"<!-- SECTION:([A-Za-z0-9_.-]+) -->", text):
        if text.count("<!-- /SECTION:%s -->" % m.group(1)) != 1 or text.count("<!-- SECTION:%s -->" % m.group(1)) != 1:
            raise ToolError("section anchor %s is not balanced" % m.group(1))
    for n in ("CONTINUATION_PROMPT", "STATUS_BOARD"):
        if text.count("<!-- %s_START -->" % n) != 1 or text.count("<!-- %s_END -->" % n) != 1:
            raise ToolError("marker pair %s is missing or duplicated" % n)
    ids = []
    for r in board_rows(text):
        c = cells_of(r)
        if len(c) != 6:
            raise ToolError("status board row does not have 6 columns: " + r[:60])
        if not any(w in c[2] for w in STATUS_WORDS):
            raise ToolError("status board row %s has no valid status word" % c[0])
        ids.append(c[0])
    if len(ids) != len(set(ids)):
        raise ToolError("duplicate IDs on the status board")


def bump(ver, how):
    a, b, c = ver
    if how == "major":
        return (a + 1, 0, 0)
    if how == "minor":
        return (a, b + 1, 0)
    return (a, b, c + 1)


def tracker_apply(ctx, req, res, next_thread=None):
    cur, text = tracker_text(ctx)
    if not cur:
        raise ToolError("no tracker found in " + TRACKER_FOLDER)
    summary = []
    for b in req.of("STATUS"):
        k = b.keys
        word = (k.get("STATUS") or "").upper()
        if word not in STATUS_WORDS:
            raise ToolError("STATUS block: %r is not a status word (%s)" % (word, ", ".join(STATUS_WORDS)))
        iid = k.get("ID", "")
        rows = board_rows(text)
        row = next((r for r in rows if cells_of(r)[0] == iid), None)
        if not row:
            raise ToolError("STATUS block: ID %s is not on the status board" % iid)
        c = cells_of(row)
        c[2] = "%s %s" % (STATUS_EMOJI[word], word)
        if k.get("DATE"):
            c[4] = k["DATE"]
        text = text.replace(row, "| " + " | ".join(c) + " |", 1)
        summary.append("%s -> %s" % (iid, word))
    for b in req.of("ADD_ITEM"):
        row = (b.keys.get("ROW") or "").strip()
        c = cells_of(row)
        if len(c) != 6 or not row.startswith("|"):
            raise ToolError("ADD_ITEM: ROW must be a table row with 6 columns")
        if any(cells_of(r)[0] == c[0] for r in board_rows(text)):
            raise ToolError("ADD_ITEM: ID %s already exists" % c[0])
        if not any(w in c[2] for w in STATUS_WORDS):
            raise ToolError("ADD_ITEM: row has no valid status word")
        a, e = board_bounds(text)
        text = text[:e].rstrip("\n") + "\n" + row + "\n" + text[e:]
        summary.append("added " + c[0])
    for b in req.of("AMEND"):
        sid = b.keys.get("SECTION", "")
        body = (b.sections.get("TEXT") or "").strip("\n")
        if not body:
            raise ToolError("AMEND: TEXT is empty")
        close = "<!-- /SECTION:%s -->" % sid
        if text.count(close) != 1:
            raise ToolError("AMEND: section %s not found" % sid)
        entry = "- %s, %s" % (ctx.now().strftime("%d-%m-%Y"), body)
        i = text.find(close)
        text = text[:i].rstrip("\n") + "\n" + entry + "\n" + text[i:]
        summary.append("amended " + sid)
    for i in range(1, 7):
        for b in req.of("SET_A%d" % i):
            body = (b.sections.get("TEXT") or "").strip("\n")
            a_, z_ = "<!-- SECTION:A%d -->" % i, "<!-- /SECTION:A%d -->" % i
            if text.count(a_) != 1:
                raise ToolError("SET_A%d: section A%d not found" % (i, i))
            s = text.find(a_) + len(a_)
            e = text.find(z_)
            text = text[:s] + "\n" + body + "\n" + text[e:]
            summary.append("replaced A%d" % i)
    logs = [(b.sections.get("TEXT") or "").strip("\n") for b in req.of("LOG")]
    return cur, text, summary, logs


def finish_tracker(ctx, req, res, cur, text, logs, auto_log=True):
    thr = req.thr
    if auto_log:
        auto = ["- %03d %s - %s (%d file(s))" % (e["num"], e["mode"], e["result"], e.get("changed", 0)) for e in ctx.state["log"] if e.get("thread") == thr]
        logs = logs + (["Automatic operations log (thread %03d):" % thr] + auto if auto else [])
    if logs:
        sid = "C-LOG-T%03d" % thr
        entry = "\n".join(l for l in logs if l)
        if "<!-- SECTION:%s -->" % sid in text:
            close = "<!-- /SECTION:%s -->" % sid
            i = text.find(close)
            text = text[:i].rstrip("\n") + "\n" + entry + "\n" + text[i:]
        else:
            block = "<!-- SECTION:%s -->\n### %s - thread log\n%s\n<!-- /SECTION:%s -->\n\n" % (sid, sid, entry, sid)
            marker = "<!-- /SECTION:C-INDEX -->\n\n"
            if marker in text:
                text = text.replace(marker, marker + block, 1)
            else:
                text = text.rstrip("\n") + "\n\n" + block
    ver = bump(cur["ver"], req.header.get("BUMP", "patch").lower())
    now = ctx.now()
    proj = cur["proj"]
    phase = req.header.get("PHASE", cur["phase"])
    pname = req.header.get("PHASE_NAME", cur["name"])
    name = "%s__%03d__%s__%s__%s__%s_v%d.%d.%d.md" % (proj, thr, now.strftime("%d-%m-%Y"), hhmm_ampm(now), phase, pname, *ver)
    path = os.path.join(tracker_dir(ctx), name)
    if os.path.exists(path):
        raise ToolError("the new tracker file already exists (same minute): " + name)
    note = req.header.get("NOTE", "updated by Project_Operations")
    text = set_header_row(text, "This file", "`%s`" % name)
    text = set_header_row(text, "Tracker version", "v%d.%d.%d (%s)" % (*ver, note))
    text = set_header_row(text, "Thread number", "%03d" % thr)
    text = set_header_row(text, "Last file number issued", "%03d" % max(ctx.state.get("last_file_number", 0), req.num))
    text = set_header_row(text, "Generated", now.strftime("%d-%m-%Y, %I:%M %p IST"))
    text = set_header_row(text, "Previous version", "`%s` (kept side by side)" % cur["file"])
    validate_tracker(text)
    return path, name, text, ver


def mode_tracker(ctx, req, res):
    try:
        cur, text, summary, logs = tracker_apply(ctx, req, res)
        path, name, text, ver = finish_tracker(ctx, req, res, cur, text, logs, auto_log=False)
    except ToolError as e:
        return res.stop(str(e))
    write_atomic(path, encode_text(text, {"bom": False, "eol": "\n"}))
    res.changed.append(relpath(ctx.root, path))
    ctx.say("%s New tracker written: %s" % (icon("ok"), name))
    ctx.say("  changes: " + ("; ".join(summary) if summary else "header only"))
    pa = text.find("## PART B")
    ctx.say("  Part A size: %d bytes%s" % (len(text[:pa].encode("utf-8")), " (over 10 KB: trim it)" if len(text[:pa].encode("utf-8")) > 10240 else ""))
    res.detail = "tracker %s written" % name


# ============================================================================= v2.0.1 runtime: guard / clutter / git / pack / relay / runner
HARD_PROTECT = ("Documentation/", "Debug_Scripts/", "Debug/Restore_Maintenance/")
LOCAL_ONLY_FILES = ("app_config.json", "Debug_Scripts/Auto_Backup_Task.log", "Debug/Start_Log.txt", "Debug/Project_Operations.config.json",
                    "Debug/Ops_State.json", "Debug/Ops_Log.md", "Debug/relay_state.json", "Debug/Machine_Profile.json",
                    "Debug/Live_Check_Report.md", "Debug/ops.lock", "Debug/ops_run.lock", "Debug/Preflight_Report.md",
                    "Debug/AI_Prompt_Generate_Missing.txt")
LOCAL_ONLY_PREFIXES = ("Debug/Backups/", "Debug/Restore_Maintenance/", "Debug/Blocked_Output/", "uploaded_files/", "candidate database/",
                       "clutter/", "new_thread__bundle/", ".states/", ".web/", "venv/", ".venv/", "node_modules/", "__pycache__/")
RELAY_CAP = 15000


def relay_cap(ctx):
    try:
        v = int(ctx.cfg.get("relay_max_chars", RELAY_CAP))
    except Exception:
        v = RELAY_CAP
    return max(2000, min(v, RELAY_CAP))


def safe_copy(ctx, text, label="output", rel=""):
    """Every clipboard write goes through here. Returns 'ok', 'blocked' (Clipboard Guard) or 'fail' (no clipboard)."""
    found = guard_items(ctx, [(label, rel, text)])
    if found:
        ctx.say("%s CLIPBOARD BLOCKED by the Clipboard Guard (%s) - nothing was copied:" % (icon("fail"), label))
        for l, n, k in found[:10]:
            ctx.say("    %s line %s: %s" % (l, n, k))
        return "blocked"
    return "ok" if ctx.clip.copy(text) else "fail"


# ----------------------------------------------------------------------------- git helpers
def run_git(ctx, args, binary=False, timeout=180):
    try:
        p = subprocess.run(["git"] + list(args), cwd=ctx.root, capture_output=True, timeout=timeout)
    except Exception as e:
        return 127, (b"" if binary else "git unavailable: %s" % e)
    if binary:
        return p.returncode, p.stdout
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode:
        out = (out + p.stderr.decode("utf-8", "replace")).strip()
    return p.returncode, out


def git_ready(ctx):
    return bool(shutil.which("git")) and os.path.exists(ctx.p(".git"))


def git_tracked(ctx):
    rc, out = run_git(ctx, ["ls-files", "-z"], binary=True)
    if rc:
        return set()
    return {x.decode("utf-8", "replace") for x in out.split(b"\0") if x}


def local_only_reason(ctx, rel):
    r = rel.replace("\\", "/").strip("/")
    low = r.lower()
    if low in [x.lower() for x in LOCAL_ONLY_FILES]:
        return "machine-local file (never committed)"
    if any(low.startswith(p) for p in LOCAL_ONLY_PREFIXES):
        return "machine-local or personal-data folder"
    if ".bak_" in low or low.endswith((".bak", ".tmp", ".db", ".sqlite", ".sqlite3", ".pyc")):
        return "backup/temporary/database file"
    return None


def stage_refusal(ctx, rel):
    why = forbidden_read(rel) or local_only_reason(ctx, rel)
    if why:
        return why
    if git_ready(ctx):
        rc, _ = run_git(ctx, ["check-ignore", "-q", "--", rel])
        if rc == 0 and rel not in git_tracked(ctx):
            return "ignored by .gitignore"
    return None


def do_lock(ctx, req, res, files, message, tag, push):
    """Explicit-file-list git save + annotated tag (+ push). Never uses 'git add -A'. Returns True on success."""
    if not tag or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,80}$", tag):
        res.stop("LOCK needs a TAG made of letters, digits and . _ - /")
        return False
    if not git_ready(ctx):
        res.stop("git repository not available")
        return False
    if not files:
        res.stop("LOCK needs at least one STAGE block with FILE: (no file list = nothing is staged)")
        return False
    rc, branch = run_git(ctx, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch.strip()
    if rc or branch in ("", "HEAD"):
        res.stop("git is not on a normal branch (detached HEAD)")
        return False
    rc, staged = run_git(ctx, ["diff", "--cached", "--name-only"])
    if staged.strip():
        res.stop("the git index already holds staged files (%s) - nothing was changed; unstage them first" % ", ".join(staged.split()[:6]))
        return False
    rc, _ = run_git(ctx, ["rev-parse", "-q", "--verify", "refs/tags/" + tag])
    if rc == 0:
        res.stop("tag %s already exists" % tag)
        return False
    tracked = git_tracked(ctx)
    clean = []
    for f in files:
        rel = f.replace("\\", "/").strip().strip("/")
        try:
            path = ctx.p(rel)
        except ToolError as e:
            res.stop(str(e))
            return False
        why = stage_refusal(ctx, rel)
        if why:
            res.stop("refused to stage %s (%s)" % (rel, why))
            return False
        if not os.path.exists(path) and rel not in tracked:
            res.stop("not found and not tracked: " + rel)
            return False
        if os.path.isfile(path):
            try:
                txt = read_text(path)[0]
            except ToolError:
                txt = None
            if txt is not None:
                fnd = guard_items(ctx, [(rel, rel, txt)])
                if fnd:
                    res.stop("Clipboard Guard found possible secrets/personal data in %s (%s) - not staged" % (rel, ", ".join(sorted({k for _, _, k in fnd}))))
                    return False
        if rel not in clean:
            clean.append(rel)
    rc, status = run_git(ctx, ["status", "--short"])
    plan = ["LOCK plan: tag %s on branch %s, push=%s" % (tag, branch, "yes" if push else "no"), "git status now:"]
    plan += ["    " + l for l in status.split("\n")[:40] if l.strip()]
    plan += ["Will stage ONLY these %d file(s):" % len(clean)] + ["    + " + c for c in clean]
    other = [l for l in status.split("\n") if l.strip() and not any(l[3:].strip().strip('"') == c for c in clean)]
    plan.append("%d other change(s) are NOT included." % len(other))
    locked = [c for c in clean if is_locked(ctx, c)]
    if locked:
        plan.append("%s LOCKED AREA touched: %s" % (icon("warn"), ", ".join(locked)))
    if push:
        run_git(ctx, ["fetch", "--quiet", "origin"])
        rc, cnt = run_git(ctx, ["rev-list", "--left-right", "--count", "HEAD...origin/" + branch])
        parts = cnt.split()
        if rc == 0 and len(parts) == 2 and int(parts[1]) > 0:
            res.stop("GitHub has %s newer commit(s) - pull first (nothing was changed)" % parts[1])
            return False
    if not gate(ctx, "u" if locked else "enter", plan):
        res.cancel()
        return False
    rc, out = run_git(ctx, ["add", "--"] + clean)
    if rc:
        res.stop("git add failed: " + out)
        return False
    rc, _ = run_git(ctx, ["diff", "--cached", "--quiet"])
    if rc != 0:
        rc, out = run_git(ctx, ["commit", "-m", message or ("Lock " + tag)])
        if rc:
            run_git(ctx, ["reset", "-q", "--"] + clean)
            res.stop("git commit failed (files were unstaged again): " + out)
            return False
        ctx.say("%s committed %d file(s)" % (icon("ok"), len(clean)))
    else:
        ctx.say("%s no file content changed; tagging the current commit" % icon("info"))
    rc, out = run_git(ctx, ["tag", "-a", tag, "-m", message or ("Lock " + tag)])
    if rc:
        res.stop("git tag failed: " + out)
        return False
    ctx.say("%s tag %s created" % (icon("ok"), tag))
    res.changed += [c for c in clean if c not in res.changed]
    if push:
        rc, out = run_git(ctx, ["push", "origin", branch])
        rc2, out2 = run_git(ctx, ["push", "origin", "refs/tags/" + tag])
        if rc or rc2:
            ctx.say("%s PUSH FAILED (the lock is saved locally; run the push again later): %s" % (icon("warn"), (out if rc else out2)[:300]))
            res.detail = "locked %s locally; PUSH FAILED" % tag
            return True
        ctx.say("%s pushed branch and tag (no force)" % icon("ok"))
    res.detail = "locked " + tag
    return True


def mode_lock(ctx, req, res):
    files = [b.keys.get("FILE", "") for b in req.of("STAGE")]
    push = req.header.get("PUSH", "yes").lower() != "no"
    do_lock(ctx, req, res, files, req.header.get("MESSAGE", ""), req.header.get("TAG", ""), push)


def mode_rollback(ctx, req, res):
    """Non-destructive restore-from-tag: backs up current files into a batch (UNDO_LAST works), never resets git history."""
    tag = req.header.get("TAG", "")
    if not tag or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,80}$", tag):
        return res.stop("ROLLBACK needs a TAG")
    if not git_ready(ctx):
        return res.stop("git repository not available")
    rc, _ = run_git(ctx, ["rev-parse", "-q", "--verify", "refs/tags/%s^{commit}" % tag])
    if rc:
        return res.stop("tag not found: " + tag)
    subset = [b.keys.get("PATH", "").replace("\\", "/").strip("/") for b in req.of("FILE")]
    rc, diff = run_git(ctx, ["diff", "--name-status", "--no-renames", tag, "--"])
    if rc:
        return res.stop("git diff failed: " + diff)
    todo, kept, skipped = [], [], []
    for line in diff.split("\n"):
        if not line.strip():
            continue
        st, _, rel = line.partition("\t")
        rel = rel.strip().strip('"')
        if subset and rel not in subset:
            continue
        if st.startswith("A"):
            kept.append(rel)
            continue
        why = local_only_reason(ctx, rel) or forbidden_write(rel)
        if why:
            skipped.append("%s (%s)" % (rel, why))
            continue
        todo.append((st[0], rel))
    for s in subset:
        if s and not any(r == s for _, r in todo) and s not in kept and not any(x.startswith(s + " ") for x in skipped):
            return res.stop("%s is identical to tag %s or not tracked - nothing to restore for it" % (s, tag))
    if not todo:
        res.detail = "0/0 restored - working files already match tag %s" % tag
        return res
    lines = ["ROLLBACK (restore from tag %s). Git history is NOT touched; current files are backed up first (UNDO_LAST can reverse)." % tag]
    lines += ["    %s %s" % ("restore" if s == "M" else "re-create", r) for s, r in todo]
    if kept:
        lines.append("%d file(s) added after the tag stay untouched." % len(kept))
    for s_ in skipped:
        lines.append("%s skipped: %s" % (icon("warn"), s_))
    if not gate(ctx, "u", lines):
        return res.cancel()
    batch = new_batch(ctx, req, "ROLLBACK")
    try:
        for st, rel in todo:
            path = ctx.p(rel)
            rc, data = run_git(ctx, ["cat-file", "blob", "%s:%s" % (tag, rel)], binary=True)
            if rc:
                raise ToolError("cannot read %s from tag" % rel)
            ent = batch_save_original(ctx, batch, "P", rel, path)
            if os.path.isfile(path):
                try:
                    old_text, meta = read_text(path)
                    new_text = data.decode("utf-8").replace("\r\n", "\n")
                    data = encode_text(new_text, meta)
                except (ToolError, UnicodeDecodeError):
                    pass
            write_atomic(path, data)
            if sha256_bytes(open(path, "rb").read()) != sha256_bytes(data):
                raise ToolError("write verification failed: " + rel)
            ent["sha_after"] = sha256_bytes(data)
        batch["status"] = "applied"
        batch_write(batch)
    except Exception as e:
        for ent in batch["files"]:
            try:
                restore_entry(ctx, batch, ent)
            except Exception:
                pass
        batch["status"] = "failed"
        batch_write(batch)
        return res.stop("restore failed, previous content put back automatically: %s" % e)
    res.changed = [r for _, r in todo]
    for _, r in todo:
        ctx.say("%s restored %s (backup in Debug\\Backups\\batch_%s)" % (icon("ok"), r, batch["stamp"]))
    ctx.say(restart_hint([(r, "", "") for _, r in todo]))
    res.detail = "%d/%d restored from %s" % (len(todo), len(todo), tag)


# ----------------------------------------------------------------------------- clutter
def age_threshold(ctx, thr):
    ts = [t for t in list_trackers(ctx) if t["thr"] <= thr - 2]
    return ts[-1]["dt"] if ts else None


def protected(ctx, rel):
    r = rel.replace("\\", "/").strip("/")
    why = forbidden_write(r)
    if why:
        return why
    low = r.lower() + ("/" if os.path.isdir(ctx.p(r)) else "")
    for h in HARD_PROTECT:
        if low.startswith(h.lower()) or low == h.lower().rstrip("/"):
            return "permanently protected (%s)" % h.rstrip("/")
    if r in TOOL_STATE_FILES or r in TOOL_FILES or r.startswith((TRACKER_FOLDER + "/", BUNDLE_FOLDER + "/")):
        return "protected"
    if any(glob_match(r, g) for g in protect_globs(ctx)):
        return "CLUTTER_PROTECT"
    if is_locked(ctx, r):
        return "locked"
    return None


def move_clutter(ctx, rels, thr, reason):
    base = ctx.p("Clutter/%03d" % thr)
    os.makedirs(base, exist_ok=True)
    mp = os.path.join(base, "manifest.json")
    try:
        man = json.load(open(mp, encoding="utf-8"))
    except Exception:
        man = []
    for rel in rels:
        src = ctx.p(rel)
        dst = os.path.join(base, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        man.append({"orig": rel, "dest": relpath(ctx.root, dst), "reason": reason})
    write_atomic(mp, json.dumps(man, indent=1).encode("utf-8"))


def auto_clutter(ctx, thr):
    th = age_threshold(ctx, thr)
    done, lim = int(ctx.cfg.get("auto_clutter_runs_done", 0)), int(ctx.cfg.get("auto_clutter_report_runs", 2))
    if th is None:
        ctx.say("%s Auto-clutter: nothing is older than two threads yet." % icon("info"))
        return 0
    tracked = git_tracked(ctx) if git_ready(ctx) else set()
    skip = (SKIP_DIRS - {"Debug"}) | {"Clutter", BUNDLE_FOLDER}
    cand, left = [], []
    for dp, dns, fns in os.walk(ctx.root):
        dns[:] = sorted(d for d in dns if d not in skip)
        for f in sorted(fns):
            p = os.path.join(dp, f)
            rel = relpath(ctx.root, p)
            in_debug = rel.startswith("Debug/")
            if in_debug and rel.count("/") != 1:
                continue
            if os.path.getmtime(p) >= th.timestamp() or protected(ctx, rel):
                continue
            if ".bak" in f.lower() or f.endswith(".tmp") or "_Pre_" in f or in_debug:
                (left if rel in tracked else cand).append(rel)
    mode = ctx.cfg.get("auto_clutter", "auto")
    report = mode == "report" or (mode == "auto" and done < lim)
    for x in left[:10]:
        ctx.say("    %s tracked by git, left in place: %s" % (icon("info"), x))
    if report:
        ctx.say("%s Auto-clutter REPORT ONLY (run %d of %d): %d item(s) would move." % (icon("info"), done + 1, lim, len(cand)))
        for x in cand[:30]:
            ctx.say("    would move: " + x)
    elif cand:
        move_clutter(ctx, cand, thr, "safe automatic clutter")
        ctx.say("%s Auto-clutter moved %d item(s) into Clutter\\%03d (UNCLUTTER reverses it)." % (icon("ok"), len(cand), thr))
    ctx.cfg["auto_clutter_runs_done"] = done + 1
    ctx.save_cfg()
    return 0 if report else len(cand)


def mode_clean(ctx, req, res):
    moves, dels = req.of("MOVE"), req.of("DELETE")
    if not moves and not dels:
        return res.stop("no MOVE or DELETE block")
    rels = []
    for b in moves:
        rel = b.keys.get("FILE", "").replace("\\", "/")
        try:
            ok = os.path.exists(ctx.p(rel))
        except ToolError as e:
            return res.stop(str(e))
        if not ok:
            return res.stop("not found: " + rel)
        why = protected(ctx, rel)
        if why:
            return res.stop("not allowed to move %s (%s)" % (rel, why))
        rels.append(rel)
    if rels and not gate(ctx, "enter", ["CLEAN plan:"] + ["  move " + x for x in rels]):
        return res.cancel()
    if rels:
        move_clutter(ctx, rels, req.thr, "approved by Jay")
        res.changed += rels
    if dels:
        for b in dels:
            rel = b.keys.get("FILE", "").replace("\\", "/")
            if not rel.startswith("Clutter/") or not os.path.isfile(ctx.p(rel)):
                return res.stop("DELETE allowed only for existing files inside Clutter")
        if not gate(ctx, "y", ["Permanent deletion requested:"] + ["  delete " + b.keys.get("FILE", "") for b in dels]):
            return res.cancel()
        for b in dels:
            rel = b.keys.get("FILE", "").replace("\\", "/")
            os.remove(ctx.p(rel))
            res.changed.append(rel)
    res.detail = "%d moved, %d deleted" % (len(rels), len(dels))


def mode_unclutter(ctx, req, res):
    blocks = req.of("BACK")
    if not blocks:
        return res.stop("no BACK block")
    found = []
    cdir = ctx.p("Clutter")
    for dp, dns, fns in (os.walk(cdir) if os.path.isdir(cdir) else []):
        if "manifest.json" in fns:
            try:
                man = json.load(open(os.path.join(dp, "manifest.json"), encoding="utf-8"))
            except Exception:
                continue
            for m in man:
                if any((not b.keys.get("FILE") or b.keys["FILE"].replace("\\", "/") == m["orig"]) for b in blocks):
                    found.append((dp, m))
    if not found:
        return res.stop("nothing found in Clutter")
    if not gate(ctx, "enter", ["UNCLUTTER plan:"] + ["  put back " + m["orig"] for _, m in found]):
        return res.cancel()
    for dp, m in found:
        src, dst = ctx.p(m["dest"]), ctx.p(m["orig"])
        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            res.changed.append(m["orig"])
    res.detail = "%d restored" % len(res.changed)


# ----------------------------------------------------------------------------- new-thread pack and relay
def current_thread_from_text(text):
    m = re.search(r"this thread = (\d+)", section_between(text, "<!-- CONTINUATION_PROMPT_START -->", "<!-- CONTINUATION_PROMPT_END -->") or "")
    return int(m.group(1)) if m else 1


def find_common(ctx):
    d = os.path.join(ctx.kit_root or "", "00_Common_Instructions")
    best = None
    if os.path.isdir(d):
        for f in os.listdir(d):
            m = re.match(r"^Common_Project_Instructions_v(\d+)\.(\d+)\.(\d+).*\.md$", f)
            if m and "DRAFT" not in f.upper() and (best is None or tuple(map(int, m.groups())) > best[0]):
                best = (tuple(map(int, m.groups())), os.path.join(d, f))
        if best is None:
            for f in os.listdir(d):
                m = re.match(r"^Common_Project_Instructions_v(\d+)\.(\d+)\.(\d+).*\.md$", f)
                if m and (best is None or tuple(map(int, m.groups())) > best[0]):
                    best = (tuple(map(int, m.groups())), os.path.join(d, f))
    return best[1] if best else None


def build_pack(ctx, pline="PREFLIGHT: not run"):
    t, text = tracker_text(ctx)
    if not t:
        raise ToolError("no tracker")
    cp = find_common(ctx)
    card = "(Core Rules Card unavailable)"
    if cp:
        card = (section_between(read_text(cp)[0], "<!-- CORE_CARD_START -->", "<!-- CORE_CARD_END -->") or card).strip()
    a, b = board_bounds(text)
    br = text[a:b].strip().split("\n")
    opens = [x for x in br[2:] if "LOCKED" not in cells_of(x)[2] or "AWAITING_LOCK" in cells_of(x)[2]]
    locks = [cells_of(x)[0] for x in br[2:] if " LOCKED" in cells_of(x)[2] and "AWAITING_LOCK" not in cells_of(x)[2]]

    def A(n):
        return (section_between(text, "<!-- SECTION:A%d -->\n" % n, "\n<!-- /SECTION:A%d -->" % n) or "").strip()
    head = text.split("## PART A")[0].split("\n", 1)[-1].strip()
    mp = ctx.p(BUNDLE_FOLDER + "/Project_Map_Summary.md")
    maps = read_text(mp)[0] if os.path.isfile(mp) else "(no map yet)"
    thr = current_thread_from_text(text)
    pack = ("# NEW THREAD PACK - %s - for thread %03d\n\n%s\n\n## HEADER\n%s\n\n%s\n\n### A2 OPEN\n%s\nLOCKED omitted (%d): %s\n\n%s\n\n%s\n\n%s\n\n%s\n\n## MAP\n%s\n\n## PREFLIGHT\n%s\n"
            % (t["proj"], thr, card, head, A(1), "\n".join(br[:2] + opens), len(locks), ", ".join(locks), A(3), A(4), A(5), A(6), maps, pline))
    d = ctx.p(BUNDLE_FOLDER)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "New_Thread_Pack__%s__T%03d.md" % (t["proj"], thr))
    write_atomic(path, pack.encode("utf-8"))
    return path, pack


def build_parts(items, mx=15000):
    out, cur = [], ""
    lim = mx - 400
    for label, rel, text in items:
        block = "#### FILE: %s\n%s\n" % (label, text)
        if len(block) > lim:
            chunks, x = [], ""
            for l in text.splitlines(True):
                if x and len(x) + len(l) > lim:
                    chunks.append(x)
                    x = ""
                while len(l) > lim:
                    chunks.append(l[:lim])
                    l = l[lim:]
                x += l
            if x:
                chunks.append(x)
            for i, c in enumerate(chunks, 1):
                b = "#### FILE: %s (%d/%d)\n%s\n" % (label, i, len(chunks), c)
                if cur and len(cur) + len(b) > lim:
                    out.append(cur)
                    cur = ""
                cur += b
        else:
            if cur and len(cur) + len(block) > lim:
                out.append(cur)
                cur = ""
            cur += block
    if cur:
        out.append(cur)
    n, total = len(out), sum(map(len, out))
    return [("RELAY START - %d part(s). Wait for RELAY END.\n" % n if i == 0 else "") + "=== RELAY PART %d of %d | %d chars ===\n%s%s" % (i + 1, n, len(p), p, "=== RELAY END | parts %d | total chars %d ===\n" % (n, total) if i == n - 1 else "") for i, p in enumerate(out)]


def relay_state_save(ctx, parts_n, idx, status):
    try:
        write_atomic(ctx.p("Debug/relay_state.json"), json.dumps({"parts": parts_n, "index": idx, "status": status, "time": ctx.now().isoformat()}).encode("utf-8"))
    except Exception:
        pass


def relay_run(ctx, items, res):
    f = guard_items(ctx, items)
    if f:
        ctx.say("%s RELAY BLOCKED by the Clipboard Guard - no part was copied (secret values are never printed):" % icon("fail"))
        for l, n, k in f[:12]:
            ctx.say("  %s line %s: %s" % (l, n, k))
        return res.stop("relay blocked by Clipboard Guard (%d finding(s))" % len(f))
    parts = build_parts(items, relay_cap(ctx))
    d = ctx.p(BUNDLE_FOLDER + "/Relay_Parts")
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        if old.startswith("part_") and old.endswith(".txt"):
            os.remove(os.path.join(d, old))
    for i, p in enumerate(parts, 1):
        write_atomic(os.path.join(d, "part_%02d.txt" % i), p.encode("utf-8"))
    ctx.say("%s Relay ready: %d part(s), at most %d characters each. Append ALL parts in ONE new-chat message, then send once." % (icon("info"), len(parts), relay_cap(ctx)))
    try:
        a = ctx.input("Press ENTER to start the relay (Q = stop): ")
    except (EOFError, KeyboardInterrupt):
        a = "q"
    if a.strip().lower() == "q":
        relay_state_save(ctx, len(parts), 0, "cancelled")
        return res.cancel()
    i = 0
    while i < len(parts):
        r = safe_copy(ctx, parts[i], "relay part %d" % (i + 1))
        if r == "blocked":
            return res.stop("relay blocked by Clipboard Guard at part %d" % (i + 1))
        ctx.say("%s part %d of %d %s. Paste it into the SAME new-chat message." % (icon("ok") if r == "ok" else icon("warn"), i + 1, len(parts), "copied" if r == "ok" else "NOT copied (clipboard unavailable) - open Relay_Parts\\part_%02d.txt" % (i + 1)))
        relay_state_save(ctx, len(parts), i + 1, "running")
        try:
            k = ctx.input("ENTER next | R repeat | B back | Q stop: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            k = "q"
        if k == "":
            i += 1
        elif k == "b":
            i = max(0, i - 1)
        elif k == "r":
            pass
        else:
            relay_state_save(ctx, len(parts), i + 1, "stopped")
            return res.cancel()
    relay_state_save(ctx, len(parts), len(parts), "complete")
    ctx.say("%s RELAY complete: send the message now." % icon("ok"))
    return res


def mode_new_thread(ctx, req, res):
    done = []

    def fail(step, why):
        return res.stop("step %s: %s%s" % (step, why, ("; finished before: " + ", ".join(done)) if done else ""))
    p = preflight(ctx)
    pline = "PREFLIGHT: OK" if not p["problems"] else "PREFLIGHT: %d missing" % len(p["problems"])
    done.append("PREFLIGHT")
    try:
        cur, text, summary, logs = tracker_apply(ctx, req, res)
        path, fn, text, ver = finish_tracker(ctx, req, res, cur, text, logs, auto_log=True)
    except ToolError as e:
        return fail("TRACKER", e)
    want = int(req.header.get("NEXT_THREAD", req.thr + 1))
    if current_thread_from_text(text) != want:
        return fail("TRACKER", "A1 next thread (%d) differs from NEXT_THREAD (%d); nothing was written" % (current_thread_from_text(text), want))
    plan = ["NEW_THREAD plan (approval gate, Jay's decision 14-10-2026):", "  new tracker file: " + fn, "  tracker changes: " + ("; ".join(summary) if summary else "header only"),
            "  LOCK: %s" % req.header.get("LOCK", "no"), "  then: auto-clutter, map, New Thread Pack, clipboard relay"]
    if not gate(ctx, "enter", plan):
        return res.cancel()
    write_atomic(path, encode_text(text, {"bom": False, "eol": "\n"}))
    res.changed.append(relpath(ctx.root, path))
    done.append("TRACKER")
    if req.header.get("LOCK", "no").lower() == "yes":
        files = [relpath(ctx.root, path)] + [b.keys.get("FILE", "") for b in req.of("STAGE")]
        sub = Res()
        ok = do_lock(ctx, req, sub, files, req.header.get("LOCK_MESSAGE", ""), req.header.get("LOCK_TAG", ""), req.header.get("LOCK_PUSH", "yes").lower() != "no")
        res.changed += [c for c in sub.changed if c not in res.changed]
        if not ok:
            return fail("LOCK", sub.detail or "cancelled by Jay")
        done.append("LOCK")
    try:
        auto_clutter(ctx, req.thr)
        done.append("AUTO-CLUTTER")
        build_map(ctx)
        done.append("MAP")
        pp, pack = build_pack(ctx, pline)
        done.append("PACK")
    except ToolError as e:
        return fail("PACK", e)
    items = [("New_Thread_Pack", relpath(ctx.root, pp), pack)]
    for b in req.of("RELAY"):
        rel = b.keys.get("FILE", "")
        try:
            items.append((rel, rel, read_text(resolve(base_for(ctx, b.keys), rel))[0]))
        except ToolError as e:
            return fail("RELAY", e)
    relay_res = Res()
    relay_run(ctx, items, relay_res)
    if relay_res.status != "OK":
        res.status, res.detail = relay_res.status, "step RELAY: " + (relay_res.detail or "cancelled") + "; finished before: " + ", ".join(done)
        return res
    done.append("RELAY")
    ctx.say("%s NEW THREAD READY" % icon("ok"))
    for rel in res.changed + [relpath(ctx.root, pp)]:
        fp = ctx.p(rel)
        ctx.say("    %s  (%d bytes)" % (fp, os.path.getsize(fp) if os.path.isfile(fp) else 0))
    res.detail = "new thread ready"


def cmd_bundle(ctx):
    res = Res()
    p = preflight(ctx)
    auto_clutter(ctx, current_thread(ctx))
    build_map(ctx)
    pp, pack = build_pack(ctx, "PREFLIGHT: OK" if not p["problems"] else "PREFLIGHT: %d missing" % len(p["problems"]))
    return relay_run(ctx, [("New_Thread_Pack", relpath(ctx.root, pp), pack)], res)


# ----------------------------------------------------------------------------- SELFUPDATE
def mode_selfupdate(ctx, req, res):
    blocks = req.of("FILE")
    if len(blocks) != 1:
        return res.stop("SELFUPDATE needs exactly one FILE block")
    b = blocks[0]
    if "CONTENT" not in b.sections or not b.keys.get("SHA256"):
        return res.stop("SELFUPDATE needs SHA256 and a --- CONTENT --- section")
    new_text = b.sections["CONTENT"] + "\n"
    if sha256_text(new_text) != b.keys["SHA256"].lower():
        return res.stop("SHA256 of the embedded content does not match (download damaged?) - nothing changed")
    try:
        tree = ast.parse(new_text)
    except SyntaxError as e:
        return res.stop("new core has a syntax error (line %s: %s) - nothing changed" % (e.lineno, e.msg))
    dd = sorted(n for n, c in collections.Counter(x.name for x in tree.body if isinstance(x, (ast.FunctionDef, ast.ClassDef))).items() if c > 1)
    if dd:
        return res.stop("new core defines %s more than once - nothing changed" % ", ".join(dd))
    if "TOOL_VERSION" not in new_text:
        return res.stop("new core has no TOOL_VERSION - nothing changed")
    core_path = os.path.abspath(__file__)
    core_name = os.path.basename(core_path)
    cur_text, meta = read_text(core_path)
    if cur_text == new_text:
        res.detail = "0/0 applied - the tool is already this version"
        return res
    tests = ctx.p("Tests/Project_Operations/test_project_operations.py")
    if not os.path.isfile(tests):
        return res.stop("Tests/Project_Operations/test_project_operations.py is missing - cannot self-test; nothing changed")
    tmp = tempfile.mkdtemp(prefix="po_selfupdate_")
    try:
        os.makedirs(os.path.join(tmp, "Tests", "Project_Operations"))
        shutil.copy2(tests, os.path.join(tmp, "Tests", "Project_Operations", "test_project_operations.py"))
        cand = os.path.join(tmp, core_name)
        write_atomic(cand, encode_text(new_text, meta))
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PO_SELFUPDATE_CHILD="1")
        try:
            q = subprocess.run([sys.executable, cand, "selftest"], cwd=tmp, capture_output=True, text=True, timeout=600, env=env, encoding="utf-8", errors="replace")
        except Exception as e:
            return res.stop("self-test could not run: %s - nothing changed" % e)
        tail = "\n".join(((q.stdout or "") + (q.stderr or "")).strip().split("\n")[-12:])
        if q.returncode != 0 or "SELFTEST: PASSED" not in (q.stdout or ""):
            ctx.say(tail)
            return res.stop("the new core FAILED its self-test in a temporary folder - nothing changed")
        ctx.say("%s new core passed its self-test in a temporary folder" % icon("ok"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not gate(ctx, "enter", ["SELFUPDATE plan: replace %s (%s -> new version), previous kept as 4. Project_Operations_Core_prev.py" % (core_name, TOOL_VERSION)]):
        return res.cancel()
    batch = new_batch(ctx, req, "SELFUPDATE")
    ent = batch_save_original(ctx, batch, "P", core_name, core_path)
    prev = os.path.join(os.path.dirname(core_path), "4. Project_Operations_Core_prev.py")
    shutil.copy2(core_path, prev)
    data = encode_text(new_text, meta)
    try:
        write_atomic(core_path, data)
        if sha256_bytes(open(core_path, "rb").read()) != sha256_bytes(data):
            raise ToolError("write verification failed")
        compile(new_text, core_path, "exec")
    except Exception as e:
        restore_entry(ctx, batch, ent)
        batch["status"] = "failed"
        batch_write(batch)
        return res.stop("swap failed, previous core put back: %s" % e)
    ent["sha_after"] = sha256_bytes(data)
    batch["status"] = "applied"
    batch_write(batch)
    res.changed.append(core_name)
    ctx.say("%s core replaced. Restart the watcher / launcher so it runs the new version." % icon("ok"))
    res.detail = "tool updated"


# ----------------------------------------------------------------------------- dispatcher / gates / output
def output_name(n):
    m = REQ_RE.match(n)
    return "%s__%s__Output__%s_v%s__%s__%s.md" % (m.group("thr"), m.group("num"), m.group("mode"), m.group("ver"), m.group("date"), m.group("time"))


def peek_header(t):
    h = {}
    for l in t.splitlines():
        if l.startswith("=== "):
            break
        m = re.match(r"^([A-Z_]+):\s?(.*)$", l)
        if m:
            h[m.group(1)] = m.group(2).strip()
    return h


def check_header(ctx, n, t):
    m = REQ_RE.match(n)
    h = peek_header(t)
    code = project_code(ctx)
    if not m:
        return "bad request filename"
    if h.get("PROJECT") != code:
        return "PROJECT mismatch"
    if not h.get("THREAD", "").isdigit() or int(h["THREAD"]) != current_thread(ctx):
        return "THREAD mismatch"
    if int(m.group("thr")) != int(h["THREAD"]):
        return "filename/thread mismatch"
    return None


MODE_FUNCS = {"SEARCH": mode_search, "COLLECT": mode_collect, "REPLACE": mode_replace, "UNDO_LAST": mode_undo_last, "RESTORE": mode_restore, "PLACE": mode_place,
              "MAP": mode_map, "TEST": mode_test, "LOCK": mode_lock, "ROLLBACK": mode_rollback, "PREFLIGHT": mode_preflight, "TRACKER": mode_tracker,
              "NEW_THREAD": mode_new_thread, "CLEAN": mode_clean, "UNCLUTTER": mode_unclutter, "SELFUPDATE": mode_selfupdate}


class RunLock:
    def __init__(self, ctx):
        self.p = ctx.p("Debug/ops_run.lock")

    def __enter__(self):
        os.makedirs(os.path.dirname(self.p), exist_ok=True)
        if os.path.exists(self.p) and time.time() - os.path.getmtime(self.p) < 900:
            raise ToolError("another run is in progress")
        open(self.p, "w").write(str(os.getpid()))
        return self

    def __exit__(self, *a):
        try:
            os.remove(self.p)
        except OSError:
            pass


class WatcherLock:
    """Single watcher instance (Debug\\ops.lock) with a heartbeat so a crashed watcher does not block forever."""
    def __init__(self, ctx):
        self.p = ctx.p("Debug/ops.lock")

    def alive(self):
        try:
            d = json.load(open(self.p, encoding="utf-8"))
            return time.time() - float(d.get("beat", 0)) < 20 and int(d.get("pid", 0)) != os.getpid()
        except Exception:
            return False

    def beat(self):
        os.makedirs(os.path.dirname(self.p), exist_ok=True)
        write_atomic(self.p, json.dumps({"pid": os.getpid(), "beat": time.time()}).encode("utf-8"))

    def release(self):
        try:
            os.remove(self.p)
        except OSError:
            pass


def write_ops_log(ctx, req, res, out_name):
    p = ctx.p("Debug/Ops_Log.md")
    new = not os.path.isfile(p)
    hashes = []
    for rel in res.changed[:20]:
        try:
            fp = ctx.p(rel)
            hashes.append("%s=%s" % (rel, sha256_bytes(open(fp, "rb").read())[:12] if os.path.isfile(fp) else "-"))
        except Exception:
            pass
    row = "| %s | %s | %s | %s | %s | %s | %s |\n" % (ctx.now().strftime("%d-%m-%Y %H:%M:%S"), req.name, req.mode, res.status, (res.detail or "").replace("|", "/")[:80], "; ".join(hashes).replace("|", "/"), TOOL_VERSION)
    head = "# Ops_Log (written by Project_Operations %s)\n\n| time | request | mode | result | detail | changed files (sha256, first 12) | tool |\n|---|---|---|---|---|---|---|\n" % TOOL_VERSION
    old = open(p, encoding="utf-8").read() if not new else head
    write_atomic(p, (old + row).encode("utf-8"))


def deliver(ctx, path, body):
    """Writes the output file. Clipboard Guard findings BLOCK the whole delivery (no clipboard, no relay, no redacted copy)."""
    found = guard_items(ctx, [("output", "", body)])
    if found:
        kinds = ", ".join(sorted({"%s@line %s" % (k, n) if n else k for _, n, k in found})[:12])
        raw = ctx.p("Debug/Blocked_Output/" + os.path.basename(path))
        write_atomic(raw, body.encode("utf-8"))
        msg = "# OUTPUT BLOCKED by the Clipboard Guard\n\nThe output contained possible secrets or personal data (%s). Nothing was copied to the clipboard.\nThe raw output is kept only on this PC at Debug\\Blocked_Output\\%s - review it there; do not paste it.\n\nRESULT: BLOCKED - clipboard output withheld\n" % (kinds, os.path.basename(path))
        write_atomic(path, msg.encode("utf-8"))
        ctx.say("%s OUTPUT BLOCKED by the Clipboard Guard (%s). Nothing copied; raw output kept at Debug\\Blocked_Output\\" % (icon("fail"), kinds))
        return "blocked"
    write_atomic(path, body.encode("utf-8"))
    if ctx.cfg.get("clipboard_mode", "always") == "never":
        return "file"
    if len(body) <= relay_cap(ctx):
        r = safe_copy(ctx, body, "output")
        if r == "ok":
            ctx.say("%s output copied to clipboard (%d chars)" % (icon("ok"), len(body)))
        return r
    relay_run(ctx, [(os.path.basename(path), "", body)], Res())
    return "relay"


def run_request(ctx, path):
    n = os.path.basename(path)
    raw = open(path, "rb").read()
    t = raw.decode("utf-8-sig")
    why = check_header(ctx, n, t)
    if why:
        ctx.say("%s ignored %s: %s" % (icon("warn"), n, why))
        return None
    try:
        req = parse_request(t, path)
    except ToolError as e:
        res = Res().stop(str(e))
        body = "# OUTPUT - %s\n\n%s\n\n%s\n" % (n, icon("warn") + " " + str(e), res.line())
        deliver(ctx, os.path.join(os.path.dirname(path), output_name(n)), body)
        return res
    res = Res()
    ctx.buf = []
    ctx.say("=== %s | %s | Project_Operations %s ===" % (n, req.mode, TOOL_VERSION))
    try:
        with RunLock(ctx):
            if "%03d:%03d" % (req.thr, req.num) in ctx.state["processed"]:
                res.stop("request already processed")
            else:
                if req.mode not in ("PREFLIGHT", "NEW_THREAD"):
                    preflight(ctx)
                MODE_FUNCS[req.mode](ctx, req, res)
    except ToolError as e:
        res.stop(str(e))
    except Exception as e:
        res.stop("internal error: %s" % e)
        ctx.say(traceback.format_exc())
    ctx.say(("%s " % (icon("ok") if res.status == "OK" else icon("warn"))) + res.line())
    if "already processed" not in res.detail:
        ctx.state["processed"].append("%03d:%03d" % (req.thr, req.num))
        ctx.state["last_file_number"] = max(ctx.state.get("last_file_number", 0), req.num)
        ctx.state["log"].append({"thread": req.thr, "num": req.num, "mode": req.mode, "result": res.status, "changed": len(res.changed)})
        ctx.save_state()
        try:
            write_ops_log(ctx, req, res, output_name(n))
        except Exception:
            pass
    body = "# OUTPUT - %s\n\n%s\n\n%s\n" % (n, "\n".join(ctx.buf), res.line())
    deliver(ctx, os.path.join(os.path.dirname(path), output_name(n)), body)
    return res


def pick(ctx):
    out = []
    if os.path.isdir(ctx.downloads):
        for f in os.listdir(ctx.downloads):
            m = REQ_RE.match(f)
            if m and not os.path.exists(os.path.join(ctx.downloads, output_name(f))):
                out.append((int(m.group("thr")), int(m.group("num")), f))
    return sorted(out)


def stable_file(p, wait=0.4):
    try:
        a = os.path.getsize(p)
        time.sleep(wait)
        return a == os.path.getsize(p)
    except OSError:
        return False


def cmd_run(ctx):
    waiting = pick(ctx)
    if len(waiting) > 1:
        ctx.say("%s %d requests are waiting; running the lowest first (thread, then file number)." % (icon("info"), len(waiting)))
    for _, _, f in waiting:
        p = os.path.join(ctx.downloads, f)
        if stable_file(p, getattr(ctx, "stable_wait", 0.4)):
            return run_request(ctx, p)
        return None
    ctx.say("%s no waiting request in %s" % (icon("info"), ctx.downloads))
    return None


def cmd_watch(ctx):
    wl = WatcherLock(ctx)
    if wl.alive():
        ctx.say("%s Another watcher is already running for this project (Debug\\ops.lock). This one will not start." % icon("warn"))
        return 1
    ctx.say("WATCHER running (Ctrl+C to stop) - Project_Operations %s" % TOOL_VERSION)
    preflight(ctx)
    try:
        while True:
            wl.beat()
            r = cmd_run(ctx)
            if r is not None and r.status == "STOPPED":
                if ctx.input("stopped: ENTER continue, Q quit: ").strip().lower() == "q":
                    break
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        wl.release()
    return 0


# ----------------------------------------------------------------------------- menu, relay calibration, VS Code task
def calib_sample(size):
    head = "CALIBRATION SAMPLE (%d characters). Paste it into a NEW chat message but do NOT send it. Check that the very last line is END-OF-CALIBRATION-%d.\n" % (size, size)
    tail = "\nEND-OF-CALIBRATION-%d" % size
    body_len = max(0, size - len(head) - len(tail))
    body, n = "", 0
    while len(body) < body_len:
        n += 1
        body += "%05d %s\n" % (n, "x" * 90)
    return head + body[:body_len] + tail


def cmd_calibrate(ctx):
    ctx.say("RELAY CALIBRATION - finds the largest part your chat window accepts (never above %d characters)." % RELAY_CAP)
    probe = "calibration-roundtrip-" + str(time.time())
    if ctx.clip.copy(probe) and ctx.clip.paste() == probe:
        ctx.say("%s clipboard round-trip works" % icon("ok"))
    else:
        ctx.say("%s clipboard round-trip FAILED; parts will be written to New_Thread__Bundle\\Relay_Parts\\ instead" % icon("warn"))
    for size in (15000, 12000, 10000, 8000, 6000, 4000):
        s = calib_sample(size)
        if safe_copy(ctx, s, "calibration sample") != "ok":
            ctx.say("%s could not copy the sample" % icon("fail"))
            return 1
        ctx.say("A %d-character sample is on your clipboard. Paste it into the chat box (do not send)." % size)
        try:
            a = ctx.input("Is the last line END-OF-CALIBRATION-%d visible and was nothing cut? (y = yes, n = no, q = quit): " % size).strip().lower()
        except (EOFError, KeyboardInterrupt):
            a = "q"
        if a == "y":
            ctx.cfg["relay_max_chars"] = size
            ctx.save_cfg()
            ctx.say("%s relay_max_chars saved as %d" % (icon("ok"), size))
            return 0
        if a == "q":
            ctx.say("%s calibration stopped; nothing saved" % icon("info"))
            return 1
    ctx.say("%s no tested size worked; relay_max_chars left unchanged" % icon("warn"))
    return 1


VSCODE_TASK = {"label": "Project_Operations Watcher", "type": "shell", "command": "4b. Watch_Requests.bat", "isBackground": True,
               "runOptions": {"runOn": "folderOpen"}, "presentation": {"reveal": "always", "panel": "dedicated", "focus": False}, "problemMatcher": []}


def install_vscode_task(ctx):
    p = ctx.p(".vscode/tasks.json")
    data = {"version": "2.0.0", "tasks": []}
    if os.path.isfile(p):
        try:
            data = json.loads(read_text(p)[0])
        except ValueError:
            ctx.say("%s .vscode/tasks.json exists but is not strict JSON (comments?). Nothing was changed - add the task by hand or ask the AI." % icon("warn"))
            return False
    tasks = data.setdefault("tasks", [])
    if any(t.get("label") == VSCODE_TASK["label"] for t in tasks):
        ctx.say("%s the VS Code task is already installed" % icon("same"))
        return True
    if not gate(ctx, "enter", ["Install the VS Code auto-start task for the watcher in .vscode/tasks.json.", "VS Code asks once to allow automatic tasks. Only do this after the tool is audited."]):
        return False
    if os.path.isfile(p):
        os.makedirs(ctx.p("Debug/Backups"), exist_ok=True)
        shutil.copy2(p, ctx.p("Debug/Backups/tasks.json.bak_" + stamp_now(ctx.now())))
    tasks.append(dict(VSCODE_TASK))
    write_atomic(p, (json.dumps(data, indent=2) + "\n").encode("utf-8"))
    ctx.say("%s task added to %s" % (icon("ok"), p))
    return True


def cmd_status(ctx):
    t = newest_tracker(ctx)
    ctx.say("Project_Operations %s | root %s" % (TOOL_VERSION, ctx.root))
    ctx.say("project code: %s | thread: %s | newest tracker: %s" % (project_code(ctx) or "(none)", current_thread(ctx), t["file"] if t else "(none)"))
    ctx.say("downloads: %s | kit: %s" % (ctx.downloads, ctx.kit_root or "(not found)"))
    ctx.say("waiting requests: %d | relay_max_chars: %d | clutter runs done: %s" % (len(pick(ctx)), relay_cap(ctx), ctx.cfg.get("auto_clutter_runs_done", 0)))
    if git_ready(ctx):
        ctx.say("git branch: %s" % run_git(ctx, ["rev-parse", "--abbrev-ref", "HEAD"])[1].strip())


def cmd_menu(ctx):
    items = ["1  Run the next waiting request", "2  Start the watcher", "3  Run the self-test", "4  Build the New Thread Pack (4a)", "5  PREFLIGHT report",
             "6  Relay calibration", "7  Install the VS Code auto-start task", "8  Tool status", "Q  Quit"]
    while True:
        ctx.say("")
        ctx.say("=== Project_Operations %s ===" % TOOL_VERSION)
        for i in items:
            ctx.say("  " + i)
        try:
            k = ctx.input("Choose: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return 0
        if k == "q" or k == "":
            return 0
        if k == "1":
            cmd_run(ctx)
        elif k == "2":
            cmd_watch(ctx)
        elif k == "3":
            selftest()
        elif k == "4":
            cmd_bundle(ctx)
        elif k == "5":
            mode_preflight(ctx, None, Res())
        elif k == "6":
            cmd_calibrate(ctx)
        elif k == "7":
            install_vscode_task(ctx)
        elif k == "8":
            cmd_status(ctx)
        else:
            ctx.say("%s unknown choice" % icon("warn"))


def selftest():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Tests", "Project_Operations", "test_project_operations.py")
    if not os.path.isfile(p):
        print("SELFTEST: FAILED - test file missing: " + p)
        return 1
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.call([sys.executable, p], env=env)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    a = sys.argv[1:]
    cmd = a[0] if a else "menu"
    if cmd == "selftest":
        return selftest()
    if cmd == "version":
        print(TOOL_VERSION)
        return 0
    ctx = Ctx(os.path.dirname(os.path.abspath(__file__)))
    if cmd == "menu":
        return cmd_menu(ctx)
    if cmd == "run":
        cmd_run(ctx)
        return 0
    if cmd == "watch":
        return cmd_watch(ctx)
    if cmd == "bundle":
        cmd_bundle(ctx)
        return 0
    if cmd == "calibrate":
        return cmd_calibrate(ctx)
    if cmd == "vscode-task":
        return 0 if install_vscode_task(ctx) else 1
    if cmd == "status":
        cmd_status(ctx)
        return 0
    print("unknown command " + cmd + " (menu, run, watch, bundle, selftest, calibrate, vscode-task, status, version)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
