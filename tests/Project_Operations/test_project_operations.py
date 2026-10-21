# -*- coding: utf-8 -*-
"""Project_Operations regression suite (v2.0.1). Run by `4c. Test_And_Check.bat` or `4. Project_Operations_Core.py selftest`.
Every test works in a temporary folder; nothing here touches the real project."""
import os, sys, io, re, json, shutil, hashlib, tempfile, unittest, subprocess, importlib.util, ast, collections, time

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.abspath(os.path.join(HERE, "..", "..", "4. Project_Operations_Core.py"))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def load_core(path, name="po_core"):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


c = load_core(CORE)
HAVE_GIT = shutil.which("git") is not None
# Synthetic secret-shaped strings are ALWAYS built from pieces, so this file itself never trips the Clipboard Guard or the push scan.
BOTSTR = "123456789" + ":" + "A" * 35
PWLINE = "db_" + "pass" + "word" + ' = "' + "hunter2hunter2" + '"'
PEMLINE = "-----BEGIN RSA " + "PRIVATE KEY-----"
MAILSTR = "mail: someone" + "@" + "corp.com"


def w(path, text, enc="utf-8", newline=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding=enc, newline=newline) as f:
        f.write(text)


def rd(path):
    with open(path, "rb") as f:
        return f.read()


def sha(path):
    return hashlib.sha256(rd(path)).hexdigest()


TRACKER = """# T
| This file | `x` |
| Thread number | 001 |
## PART A
<!-- SECTION:A1 -->
<!-- CONTINUATION_PROMPT_START -->
this thread = 002
<!-- CONTINUATION_PROMPT_END -->
<!-- /SECTION:A1 -->
<!-- SECTION:A2 -->
<!-- STATUS_BOARD_START -->
| ID | Item | Status | Phase/Batch | Date | Source |
|---|---|---|---|---|---|
| X-1 | first | \u2705 LOCKED | p | d | s |
| X-2 | second | \u23f3 NOT_STARTED | p | d | s |
<!-- STATUS_BOARD_END -->
<!-- /SECTION:A2 -->
<!-- SECTION:A3 -->
a3
<!-- /SECTION:A3 -->
<!-- SECTION:A4 -->
a4
<!-- /SECTION:A4 -->
<!-- SECTION:A5 -->
a5
<!-- /SECTION:A5 -->
<!-- SECTION:A6 -->
a6
<!-- /SECTION:A6 -->
<!-- SECTION:C-INDEX -->
idx
<!-- /SECTION:C-INDEX -->
<!-- CLUTTER_PROTECT_START -->
<!-- CLUTTER_PROTECT_END -->
<!-- LOCKED_PATHS_START -->
locked.py | x
<!-- LOCKED_PATHS_END -->
<!-- SCAN_ALLOW_START -->
<!-- SCAN_ALLOW_END -->
<!-- REQUIRED_SCRIPTS_START -->
| Slot | File | Purpose | Level |
|---|---|---|---|
<!-- REQUIRED_SCRIPTS_END -->
## PART B
"""


class Clip:
    def __init__(self):
        self.x = None

    def copy(self, x):
        self.x = x
        return True

    def paste(self):
        return self.x


class Base(unittest.TestCase):
    core = c

    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp(prefix="po_t_"))
        self.n = 0
        self.a = []
        self.clip = Clip()
        self.mk_project()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def mk_project(self, tracker=TRACKER):
        w(self.p("Documentation/Project_Code.txt"), "TST")
        w(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt/TST__001__01-01-2026__10-00-AM__1__A_v1.0.0.md"), tracker)
        os.makedirs(self.p("Debug/Backups"), exist_ok=True)
        self.ctx = self.core.Ctx(self.d, kit_root=self.p("Kit"), downloads=self.p("Downloads"), clip=self.clip,
                                 input_fn=lambda p="": self.a.pop(0) if self.a else "", out_fn=lambda s: None, quiet=True)
        self.ctx.stable_wait = 0
        os.makedirs(self.ctx.downloads, exist_ok=True)

    def p(self, x):
        return os.path.join(self.d, *x.split("/"))

    def req(self, mode, body="", thread="002", project="TST", num=None, header_extra=""):
        self.n += 1
        num = num or self.n
        name = "%s__%03d__%s_v1.0.0__01-01-2026__10-00-AM.md" % (thread, num, mode)
        f = os.path.join(self.ctx.downloads, name)
        w(f, "MODE: %s\nPROJECT: %s\nTHREAD: %s\n%s%s" % (mode, project, thread, header_extra, body))
        return f

    def run_req(self, mode, body="", **kw):
        return self.core.run_request(self.ctx, self.req(mode, body, **kw))

    def output_of(self, f):
        return open(os.path.join(os.path.dirname(f), self.core.output_name(os.path.basename(f))), encoding="utf-8").read()

    def replace_body(self, file, anchor, new, kind="REPLACE"):
        return "=== OP ===\nKIND: %s\nFILE: %s\n--- ANCHOR ---\n%s\n--- NEW ---\n%s\n=== END ===" % (kind, file, anchor, new)


class T01_Basics(Base):
    def test_hash_is_newline_normalised(self):
        self.assertEqual(c.sha256_text("x"), hashlib.sha256(b"x\n").hexdigest())
        self.assertEqual(c.sha256_text("x\r\n"), hashlib.sha256(b"x\n").hexdigest())

    def test_path_dotdot_refused(self):
        with self.assertRaises(c.ToolError):
            c.resolve(self.d, "../x")

    def test_path_absolute_refused(self):
        with self.assertRaises(c.ToolError):
            c.resolve(self.d, "C:/Windows/x")
        with self.assertRaises(c.ToolError):
            c.resolve(self.d, "/etc/x")

    def test_path_inside_ok(self):
        self.assertTrue(c.resolve(self.d, "a/b").startswith(self.d))

    def test_clipboard_fake_roundtrip(self):
        self.assertTrue(self.clip.copy("a"))
        self.assertEqual(self.clip.paste(), "a")

    def test_glob_match(self):
        self.assertTrue(c.glob_match("Documentation/x/y.md", "Documentation/**"))
        self.assertFalse(c.glob_match("src/x.md", "Documentation/**"))

    def test_icons_have_ascii_fallback(self):
        c.FORCE_ASCII = True
        try:
            self.assertEqual(c.icon("ok"), "[OK]")
        finally:
            c.FORCE_ASCII = False


class T02_Parsing(Base):
    def parse(self, text, mode="SEARCH"):
        f = self.p("Downloads/002__001__%s_v1.0.0__01-01-2026__10-00-AM.md" % mode)
        return c.parse_request(text, f)

    def test_parse_ok(self):
        r = self.parse("MODE: SEARCH\nPROJECT: TST\nTHREAD: 002\n=== FIND ===\nTERM: x\n=== END ===")
        self.assertEqual(r.mode, "SEARCH")

    def test_unknown_mode(self):
        with self.assertRaises(c.ToolError) as e:
            self.parse("MODE: SEARCHH\n", mode="SEARCHH")
        self.assertIn("unknown MODE", str(e.exception))

    def test_mode_differs_from_filename(self):
        with self.assertRaises(c.ToolError) as e:
            self.parse("MODE: COLLECT\nPROJECT: TST\nTHREAD: 002\n")
        self.assertIn("differs", str(e.exception))

    def test_unknown_key_suggests(self):
        with self.assertRaises(c.ToolError) as e:
            self.parse("MODE: SEARCH\nPROJECT: TST\nTHREAD: 002\n=== FIND ===\nTERMM: x\n=== END ===")
        self.assertIn("unknown key", str(e.exception))

    def test_unknown_block(self):
        with self.assertRaises(c.ToolError):
            self.parse("MODE: SEARCH\nPROJECT: TST\nTHREAD: 002\n=== NOPE ===\n=== END ===")

    def test_duplicate_header_key(self):
        with self.assertRaises(c.ToolError):
            self.parse("MODE: SEARCH\nPROJECT: TST\nPROJECT: TST\nTHREAD: 002\n")

    def test_missing_end(self):
        with self.assertRaises(c.ToolError):
            self.parse("MODE: SEARCH\nPROJECT: TST\nTHREAD: 002\n=== FIND ===\nTERM: x\n")

    def test_invalid_mode_run_writes_stopped_output_and_changes_nothing(self):
        f = self.req("NOPE")
        res = c.run_request(self.ctx, f)
        self.assertEqual(res.status, "STOPPED")
        self.assertIn("RESULT: STOPPED", self.output_of(f))

    def test_project_mismatch_is_ignored(self):
        f = self.req("MAP", project="OTHER")
        self.assertIsNone(c.run_request(self.ctx, f))
        self.assertFalse(os.path.exists(os.path.join(self.ctx.downloads, c.output_name(os.path.basename(f)))))

    def test_thread_mismatch_is_ignored(self):
        self.assertIsNone(c.run_request(self.ctx, self.req("MAP", thread="009", num=5)))

    def test_every_spec_mode_has_a_handler(self):
        self.assertEqual(sorted(c.SPEC), sorted(c.MODE_FUNCS))
        self.assertEqual(len(c.MODE_FUNCS), 16)


class T03_Replace(Base):
    def setUp(self):
        super().setUp()
        w(self.p("a.py"), "x=1\ny=2\n")

    def test_replace_ok_and_result_line(self):
        f = self.req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        r = c.run_request(self.ctx, f)
        self.assertEqual(r.status, "OK")
        self.assertIn("x=2", open(self.p("a.py")).read())
        self.assertIn("RESULT: OK 1/1 applied", self.output_of(f))

    def test_bad_anchor_changes_nothing_by_hash(self):
        before = sha(self.p("a.py"))
        r = self.run_req("REPLACE", self.replace_body("a.py", "nothere=9", "x=2"))
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual(before, sha(self.p("a.py")))
        self.assertIn("files changed: none", r.line())

    def test_non_unique_anchor_changes_nothing(self):
        w(self.p("b.py"), "x=1\nx=1\n")
        before = sha(self.p("b.py"))
        r = self.run_req("REPLACE", self.replace_body("b.py", "x=1", "x=2"))
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual(before, sha(self.p("b.py")))

    def test_syntax_error_refused_file_identical(self):
        before = sha(self.p("a.py"))
        r = self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=("))
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual(before, sha(self.p("a.py")))

    def test_already_applied_is_reported_not_error(self):
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        r = self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        self.assertEqual(r.status, "OK")
        self.assertIn("nothing to do", r.detail)

    def test_insert_after(self):
        r = self.run_req("REPLACE", self.replace_body("a.py", "x=1", "z=3", kind="INSERT_AFTER"))
        self.assertEqual(r.status, "OK")
        self.assertEqual(open(self.p("a.py")).read().split("\n")[:3], ["x=1", "z=3", "y=2"])

    def test_write_file_new_and_overwrite_rule(self):
        body = "=== OP ===\nKIND: WRITE_FILE\nFILE: n.txt\n--- CONTENT ---\nhello\n=== END ==="
        self.assertEqual(self.run_req("REPLACE", body).status, "OK")
        body2 = body.replace("hello", "bye")
        self.assertEqual(self.run_req("REPLACE", body2).status, "STOPPED")
        self.assertEqual(open(self.p("n.txt")).read().strip(), "hello")
        self.assertEqual(self.run_req("REPLACE", body2.replace("KIND: WRITE_FILE", "KIND: WRITE_FILE\nOVERWRITE: yes")).status, "OK")

    def test_locked_area_needs_u(self):
        w(self.p("locked.py"), "x=1\n")
        before = sha(self.p("locked.py"))
        self.a = [""]
        r = self.run_req("REPLACE", self.replace_body("locked.py", "x=1", "x=2"))
        self.assertEqual(r.status, "CANCELLED")
        self.assertEqual(before, sha(self.p("locked.py")))
        self.a = ["u"]
        r = self.run_req("REPLACE", self.replace_body("locked.py", "x=1", "x=2"))
        self.assertEqual(r.status, "OK")

    def test_enter_gate_cancel_by_other_key(self):
        before = sha(self.p("a.py"))
        self.a = ["n"]
        r = self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        self.assertEqual(r.status, "CANCELLED")
        self.assertEqual(before, sha(self.p("a.py")))
        self.assertIn("RESULT: CANCELLED by Jay - files changed: none", r.line())

    def test_indentation_echo_printed(self):
        w(self.p("i.py"), "def f():\n    x=1\n")
        self.run_req("REPLACE", self.replace_body("i.py", "    x=1", "  x=2"))
        text = "\n".join(self.ctx.buf)
        self.assertIn("indentation: anchor first line=4 spaces, NEW first line=2 spaces", text)
        self.assertIn("indentation warning", text)

    def test_duplicate_definition_warning(self):
        w(self.p("d.py"), "def f():\n    return 1\n")
        self.run_req("REPLACE", self.replace_body("d.py", "    return 1", "    return 1\ndef f():\n    return 2"))
        self.assertIn("DUPLICATE DEFINITIONS introduced", "\n".join(self.ctx.buf))

    def test_dry_run_writes_nothing(self):
        before = sha(self.p("a.py"))
        r = self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"), header_extra="DRYRUN: yes\n")
        self.assertEqual(r.status, "OK")
        self.assertIn("dry run", r.detail)
        self.assertEqual(before, sha(self.p("a.py")))

    def test_large_change_is_flagged_as_dry_run_report(self):
        new = "\n".join("v%d=%d" % (i, i) for i in range(70))
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", new))
        self.assertIn("LARGE CHANGE", "\n".join(self.ctx.buf))

    def test_crlf_preserved(self):
        with open(self.p("c.py"), "wb") as f:
            f.write(b"x=1\r\ny=2\r\n")
        self.run_req("REPLACE", self.replace_body("c.py", "x=1", "x=5"))
        self.assertEqual(rd(self.p("c.py")), b"x=5\r\ny=2\r\n")

    def test_bom_preserved(self):
        with open(self.p("bom.py"), "wb") as f:
            f.write(b"\xef\xbb\xbfx=1\n")
        self.run_req("REPLACE", self.replace_body("bom.py", "x=1", "x=5"))
        self.assertEqual(rd(self.p("bom.py")), b"\xef\xbb\xbfx=5\n")

    def test_env_and_db_never_touched(self):
        for name in (".env", "my.db", ".git/config"):
            body = "=== OP ===\nKIND: WRITE_FILE\nFILE: %s\n--- CONTENT ---\nx\n=== END ===" % name
            self.assertEqual(self.run_req("REPLACE", body).status, "STOPPED", name)

    def test_tool_itself_only_by_selfupdate(self):
        body = "=== OP ===\nKIND: WRITE_FILE\nFILE: 4. Project_Operations_Core.py\n--- CONTENT ---\nx=1\n=== END ==="
        r = self.run_req("REPLACE", body)
        self.assertEqual(r.status, "STOPPED")
        self.assertIn("SELFUPDATE", r.detail)

    def test_whole_batch_is_all_or_nothing(self):
        w(self.p("b.py"), "q=1\n")
        h1, h2 = sha(self.p("a.py")), sha(self.p("b.py"))
        body = self.replace_body("a.py", "x=1", "x=2") + "\n" + self.replace_body("b.py", "nothere", "q=2")
        r = self.run_req("REPLACE", body)
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual((h1, h2), (sha(self.p("a.py")), sha(self.p("b.py"))))

    def test_backup_created_with_manifest_hash(self):
        before = sha(self.p("a.py"))
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        bs = self.core.list_batches(self.ctx)
        self.assertEqual(len(bs), 1)
        self.assertEqual(bs[0]["files"][0]["sha_before"], before)

    def test_restart_hint_for_models(self):
        w(self.p("models.py"), "class A:\n    x = 1\n")
        self.run_req("REPLACE", self.replace_body("models.py", "    x = 1", "    x = 1\n    y = 2"))
        self.assertIn("MIGRATION WARNING", "\n".join(self.ctx.buf))

    def test_auto_test_failure_is_reported_after_apply(self):
        w(self.p("Documentation/Checks.json"), json.dumps({"checks": {"boom": {"cmd": ["python", "-c", "import sys; sys.exit(3)"]}}, "sets": {"quick": ["boom"]}}))
        r = self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        self.assertIn("TESTS FAILED", r.detail)


class T04_UndoRestore(Base):
    def setUp(self):
        super().setUp()
        w(self.p("a.py"), "x=1\n")
        w(self.p("b.py"), "q=1\n")

    def test_undo_last_reverts_whole_batch(self):
        h = (sha(self.p("a.py")), sha(self.p("b.py")))
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2") + "\n" + self.replace_body("b.py", "q=1", "q=2"))
        self.assertNotEqual(h[0], sha(self.p("a.py")))
        r = self.run_req("UNDO_LAST")
        self.assertEqual(r.status, "OK")
        self.assertEqual(h, (sha(self.p("a.py")), sha(self.p("b.py"))))

    def test_undo_removes_file_created_by_batch(self):
        self.run_req("REPLACE", "=== OP ===\nKIND: WRITE_FILE\nFILE: new.txt\n--- CONTENT ---\nhi\n=== END ===")
        self.assertTrue(os.path.exists(self.p("new.txt")))
        self.run_req("UNDO_LAST")
        self.assertFalse(os.path.exists(self.p("new.txt")))

    def test_undo_with_nothing_to_undo(self):
        self.assertEqual(self.run_req("UNDO_LAST").status, "STOPPED")

    def test_undo_cancelled_keeps_change(self):
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        self.a = ["no"]
        self.assertEqual(self.run_req("UNDO_LAST").status, "CANCELLED")
        self.assertIn("x=2", open(self.p("a.py")).read())

    def test_undo_in_locked_area_needs_u(self):
        w(self.p("locked.py"), "x=1\n")
        self.a = ["u"]
        self.run_req("REPLACE", self.replace_body("locked.py", "x=1", "x=2"))
        self.a = [""]
        self.assertEqual(self.run_req("UNDO_LAST").status, "CANCELLED")
        self.a = ["u"]
        self.assertEqual(self.run_req("UNDO_LAST").status, "OK")
        self.assertIn("x=1", open(self.p("locked.py")).read())

    def test_restore_single_file(self):
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        r = self.run_req("RESTORE", "=== FILE ===\nPATH: a.py\n=== END ===")
        self.assertEqual(r.status, "OK")
        self.assertIn("x=1", open(self.p("a.py")).read())

    def test_restore_without_backup_stops(self):
        self.assertEqual(self.run_req("RESTORE", "=== FILE ===\nPATH: b.py\n=== END ===").status, "STOPPED")


class T05_Place(Base):
    def body(self, text, **kw):
        h = c.sha256_text(text)
        extra = "".join("%s: %s\n" % kv for kv in kw.items())
        return "=== FILE ===\nPROJECT_PATH: docs/a.md\nKIT_PATH: Docs/a.md\n%sSHA256: %s\n--- CONTENT ---\n%s\n=== END ===" % (extra, h, text)

    def test_place_project_and_kit(self):
        os.makedirs(self.p("Kit"), exist_ok=True)
        r = self.run_req("PLACE", self.body("hello"))
        self.assertEqual(r.status, "OK")
        self.assertTrue(os.path.exists(self.p("docs/a.md")))
        self.assertTrue(os.path.exists(self.p("Kit/Docs/a.md")))

    def test_place_hash_mismatch_writes_nothing(self):
        os.makedirs(self.p("Kit"), exist_ok=True)
        b = self.body("hello").replace("hello", "tampered")
        b = b.replace(c.sha256_text("tampered"), c.sha256_text("hello"))
        self.assertEqual(self.run_req("PLACE", b).status, "STOPPED")
        self.assertFalse(os.path.exists(self.p("docs/a.md")))

    def test_place_identical_is_skipped(self):
        os.makedirs(self.p("Kit"), exist_ok=True)
        self.run_req("PLACE", self.body("hello"))
        r = self.run_req("PLACE", self.body("hello"))
        self.assertEqual(r.status, "OK")
        self.assertIn("2 identical", r.detail)

    def test_place_replacing_code_needs_enter_and_cancel_keeps(self):
        os.makedirs(self.p("Kit"), exist_ok=True)
        w(self.p("x.py"), "old\n")
        b = "=== FILE ===\nPROJECT_PATH: x.py\n--- CONTENT ---\nnew=1\n=== END ==="
        self.a = ["z"]
        self.assertEqual(self.run_req("PLACE", b).status, "CANCELLED")
        self.assertEqual(open(self.p("x.py")).read(), "old\n")

    def test_place_binary_by_hash_from_downloads(self):
        data = bytes(range(256)) * 4
        with open(os.path.join(self.ctx.downloads, "icon.bin"), "wb") as f:
            f.write(data)
        h = hashlib.sha256(data).hexdigest()
        r = self.run_req("PLACE", "=== FILE ===\nPROJECT_PATH: assets/icon.ico\nSOURCE_DOWNLOAD: icon.bin\nSHA256: %s\n=== END ===" % h)
        self.assertEqual(r.status, "OK")
        self.assertEqual(rd(self.p("assets/icon.ico")), data)

    def test_place_binary_not_found(self):
        r = self.run_req("PLACE", "=== FILE ===\nPROJECT_PATH: assets/icon.ico\nSOURCE_DOWNLOAD: nope.bin\nSHA256: %s\n=== END ===" % ("0" * 64))
        self.assertEqual(r.status, "STOPPED")

    def test_place_refuses_env(self):
        r = self.run_req("PLACE", "=== FILE ===\nPROJECT_PATH: .env\n--- CONTENT ---\nA=1\n=== END ===")
        self.assertEqual(r.status, "STOPPED")

    def test_place_output_names_pc_and_roots(self):
        os.makedirs(self.p("Kit"), exist_ok=True)
        self.run_req("PLACE", self.body("hello"))
        self.assertIn(self.d, "\n".join(self.ctx.buf))


class T06_ReadModes(Base):
    def setUp(self):
        super().setUp()
        w(self.p("src/a.py"), "def alpha():\n    return 'needle [x]'\n\ndef beta():\n    return 2\n")
        w(self.p("Debug/hidden.py"), "needle [x]\n")
        w(self.p("Debug_Scripts/kept.py"), "needle [x]\n")

    def test_search_literal_brackets(self):
        self.run_req("SEARCH", "=== FIND ===\nTERM: needle [x]\n=== END ===")
        self.assertIn("src/a.py", "\n".join(self.ctx.buf))

    def test_search_skips_Debug_but_not_Debug_Scripts(self):
        self.run_req("SEARCH", "=== FIND ===\nTERM: needle\n=== END ===")
        text = "\n".join(self.ctx.buf)
        self.assertIn("Debug_Scripts/kept.py", text)
        self.assertNotIn("Debug/hidden.py", text)

    def test_collect_many_reads_one_output(self):
        r = self.run_req("COLLECT", "=== READ ===\nFULL: src/a.py\n=== END ===\n=== READ ===\nFUNC: src/a.py::beta\n=== END ===")
        self.assertEqual(r.status, "OK")
        self.assertIn("2/2 read", r.detail)

    def test_collect_missing_file_is_reported(self):
        r = self.run_req("COLLECT", "=== READ ===\nFULL: nope.py\n=== END ===")
        self.assertEqual(r.status, "STOPPED")

    def test_collect_protected_env(self):
        w(self.p(".env"), "A=1\n")
        r = self.run_req("COLLECT", "=== READ ===\nFULL: .env\n=== END ===")
        self.assertEqual(r.status, "STOPPED")
        self.assertNotIn("A=1", "\n".join(self.ctx.buf))

    def test_collect_blocks_secret_content_and_never_prints_it(self):
        w(self.p("cfg.txt"), "line one\n%s\n" % BOTSTR)
        r = self.run_req("COLLECT", "=== READ ===\nFULL: cfg.txt\n=== END ===")
        self.assertEqual(r.status, "STOPPED")
        self.assertNotIn(BOTSTR, "\n".join(self.ctx.buf))

    def test_collect_partial_lines(self):
        self.run_req("COLLECT", "=== READ ===\nPARTIAL: src/a.py\nLINES: 1-2\n=== END ===")
        self.assertIn("def alpha", "\n".join(self.ctx.buf))

    def test_collect_kit_root(self):
        w(self.p("Kit/00_Common_Instructions/Common_Project_Instructions_v1.0.0.md"), "hello kit\n")
        self.run_req("COLLECT", "=== READ ===\nFULL: 00_Common_Instructions/Common_Project_Instructions_v1.0.0.md\nROOT: KIT\n=== END ===")
        self.assertIn("hello kit", "\n".join(self.ctx.buf))


class T07_MapAndTest(Base):
    def test_map_builds_both_files(self):
        w(self.p("a.py"), "def f():\n    pass\n")
        r = self.run_req("MAP")
        self.assertEqual(r.status, "OK")
        self.assertTrue(os.path.exists(self.p("New_Thread__Bundle/Project_Map_Full.md")))
        self.assertLessEqual(len(open(self.p("New_Thread__Bundle/Project_Map_Summary.md"), encoding="utf-8").read()), 6000)

    def test_test_mode_without_checks_json_does_not_crash(self):
        w(self.p("ok.py"), "x=1\n")
        r = self.run_req("TEST")
        self.assertEqual(r.status, "OK")
        self.assertNotIn("internal error", r.detail)

    def test_test_mode_reports_syntax_error(self):
        w(self.p("bad.py"), "def (:\n")
        self.run_req("TEST")
        self.assertIn("bad.py", "\n".join(self.ctx.buf))

    def test_test_mode_named_check_failure(self):
        w(self.p("Documentation/Checks.json"), json.dumps({"checks": {"boom": {"cmd": ["python", "-c", "raise SystemExit(2)"]}, "fine": {"cmd": ["python", "-c", "pass"]}}, "sets": {"quick": ["fine", "boom"]}}))
        r = self.run_req("TEST")
        self.assertIn("1/2 passed", r.detail)

    def test_test_mode_unknown_set(self):
        w(self.p("Documentation/Checks.json"), json.dumps({"checks": {}, "sets": {"quick": []}}))
        self.assertEqual(self.run_req("TEST", "=== RUN ===\nSET: nope\n=== END ===").status, "STOPPED")

    def test_requests_contain_no_commands(self):
        for mode, spec in c.SPEC.items():
            keys = set(spec[0])
            for bk, bs in spec[1].items():
                keys |= set(bs[0])
            self.assertFalse({"CMD", "COMMAND", "RUN_COMMAND", "SHELL"} & keys, mode)


class T08_Tracker(Base):
    def test_status_change_writes_new_tracker_and_keeps_old(self):
        old = os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))
        r = self.run_req("TRACKER", "=== STATUS ===\nID: X-2\nSTATUS: IN_PROGRESS\nDATE: 14-10-2026\nNOTE: n\n=== END ===")
        self.assertEqual(r.status, "OK")
        now = os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))
        self.assertEqual(len(now), len(old) + 1)
        self.assertTrue(set(old) <= set(now))

    def test_invalid_status_word(self):
        self.assertEqual(self.run_req("TRACKER", "=== STATUS ===\nID: X-2\nSTATUS: DONEISH\nDATE: d\nNOTE: n\n=== END ===").status, "STOPPED")

    def test_unknown_id(self):
        self.assertEqual(self.run_req("TRACKER", "=== STATUS ===\nID: NOPE\nSTATUS: LOCKED\nDATE: d\nNOTE: n\n=== END ===").status, "STOPPED")

    def test_add_item_duplicate_id(self):
        row = "| X-2 | dup | \u23f3 NOT_STARTED | p | d | s |"
        self.assertEqual(self.run_req("TRACKER", "=== ADD_ITEM ===\nROW: %s\n=== END ===" % row).status, "STOPPED")

    def test_add_item_and_amend(self):
        row = "| X-3 | new | \u23f3 NOT_STARTED | p | d | s |"
        r = self.run_req("TRACKER", "=== ADD_ITEM ===\nROW: %s\n=== END ===\n=== AMEND ===\nSECTION: A3\n--- TEXT ---\nnote here\n=== END ===" % row, header_extra="BUMP: minor\n")
        self.assertEqual(r.status, "OK")
        self.assertTrue(any("v1.1.0" in f for f in os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))))

    def test_tracker_log_comes_from_operations_log(self):
        self.run_req("MAP")
        r = self.run_req("TRACKER", "=== LOG ===\n--- TEXT ---\nhello\n=== END ===")
        self.assertEqual(r.status, "OK")


class T09_GuardAndRelay(Base):
    def test_guard_detects_bot_token_but_not_env_reference(self):
        self.assertTrue(c.scan_text("x = '%s'" % BOTSTR))
        self.assertFalse(c.scan_text("tok" + 'en = os.environ["X"]'))

    def test_guard_private_key_and_cloud_key(self):
        self.assertTrue(c.scan_text(PEMLINE))
        self.assertTrue(c.scan_text("k = 'AKIA" + "ABCDEFGHIJKLMNOP'"))

    def test_generic_secret_is_detected(self):
        self.assertTrue(c.scan_text(PWLINE))

    def test_generic_secret_can_never_be_allowlisted(self):
        self.assertTrue(c.scan_text(PWLINE, "cfg.txt", allow=["cfg.txt", "**"]))
        self.assertNotIn("GENERIC_SECRET", c.SOFT)

    def test_email_can_be_allowlisted_for_a_path(self):
        self.assertTrue(c.scan_text(MAILSTR, "x.md"))
        self.assertFalse(c.scan_text(MAILSTR, "x.md", allow=["x.md"]))

    def test_allowlist_does_not_hide_a_token(self):
        self.assertTrue(c.scan_text("t='%s'" % BOTSTR, "x.md", allow=["x.md"]))

    def test_safe_copy_blocks_and_leaves_clipboard_untouched(self):
        self.clip.copy("before")
        self.assertEqual(c.safe_copy(self.ctx, "t='%s'" % BOTSTR), "blocked")
        self.assertEqual(self.clip.paste(), "before")
        self.assertEqual(c.safe_copy(self.ctx, "fine text"), "ok")

    def test_output_with_secret_is_blocked_entirely(self):
        self.clip.copy("before")
        body = "# OUTPUT\n%s\n" % BOTSTR
        out = os.path.join(self.ctx.downloads, "out.md")
        self.assertEqual(c.deliver(self.ctx, out, body), "blocked")
        self.assertEqual(self.clip.paste(), "before")
        self.assertNotIn(BOTSTR, open(out, encoding="utf-8").read())
        self.assertTrue(os.path.exists(self.p("Debug/Blocked_Output/out.md")))

    def test_clean_output_is_copied(self):
        out = os.path.join(self.ctx.downloads, "out2.md")
        self.assertEqual(c.deliver(self.ctx, out, "# OUTPUT\nplain\n"), "ok")
        self.assertIn("plain", self.clip.paste())

    def test_clipboard_mode_never(self):
        self.ctx.cfg["clipboard_mode"] = "never"
        self.clip.copy("before")
        c.deliver(self.ctx, os.path.join(self.ctx.downloads, "o3.md"), "x\n")
        self.assertEqual(self.clip.paste(), "before")

    def test_parts_respect_the_15000_limit(self):
        p = c.build_parts([("a", "", "x" * 20000), ("b", "", "y" * 40000)], 15000)
        self.assertGreater(len(p), 4)
        self.assertTrue(all(len(x) <= 15000 for x in p))
        self.assertIn("RELAY START", p[0])
        self.assertIn("RELAY END", p[-1])

    def test_cap_never_exceeds_15000(self):
        self.ctx.cfg["relay_max_chars"] = 99999
        self.assertEqual(c.relay_cap(self.ctx), 15000)
        self.ctx.cfg["relay_max_chars"] = 9000
        self.assertEqual(c.relay_cap(self.ctx), 9000)

    def relay(self, keys, items=None):
        copied = []

        class C2(Clip):
            def copy(s, x):
                copied.append(x)
                return True
        self.ctx.clip = C2()
        self.a = list(keys)
        items = items or [("big", "", ("line %05d " % 0 + "z" * 2000 + "\n") * 20)]
        res = c.Res()
        c.relay_run(self.ctx, items, res)
        return res, copied

    def test_relay_enter_next_repeat_back(self):
        res, copied = self.relay(["", "", "r", "b", "", "", "", ""])
        self.assertGreaterEqual(len(copied), 4)
        self.assertEqual(copied[1], copied[2])

    def test_relay_quit_cancels(self):
        res, copied = self.relay(["", "q"])
        self.assertEqual(res.status, "CANCELLED")
        self.assertEqual(len(copied), 1)

    def test_relay_q_at_start_copies_nothing(self):
        res, copied = self.relay(["q"])
        self.assertEqual((res.status, len(copied)), ("CANCELLED", 0))

    def test_relay_back_goes_to_previous_part(self):
        res, copied = self.relay(["", "", "b", "q"])
        self.assertEqual(copied[0], copied[2])

    def test_relay_blocks_everything_if_any_item_has_a_secret(self):
        res, copied = self.relay([""], items=[("ok", "", "fine\n"), ("bad", "", "t='%s'\n" % BOTSTR)])
        self.assertEqual(res.status, "STOPPED")
        self.assertEqual(copied, [])

    def test_relay_full_run_state_file(self):
        res, copied = self.relay([""] * 12)
        self.assertEqual(res.status, "OK")
        st = json.load(open(self.p("Debug/relay_state.json")))
        self.assertEqual(st["status"], "complete")

    def test_relay_writes_part_files(self):
        self.relay(["q"])
        self.assertTrue(os.path.exists(self.p("New_Thread__Bundle/Relay_Parts/part_01.txt")))


class T10_Clutter(Base):
    def test_hard_protection_without_any_tracker_list(self):
        for rel in ("Documentation/x.md", "Debug_Scripts/old_Pre_x.py", "Debug/Restore_Maintenance/lock.json"):
            self.assertIsNotNone(c.protected(self.ctx, rel), rel)

    def test_clean_refuses_protected(self):
        w(self.p("Debug_Scripts/a.py"), "x\n")
        r = self.run_req("CLEAN", "=== MOVE ===\nFILE: Debug_Scripts/a.py\nREASON: x\n=== END ===")
        self.assertEqual(r.status, "STOPPED")
        self.assertTrue(os.path.exists(self.p("Debug_Scripts/a.py")))

    def test_clean_moves_and_unclutter_restores(self):
        w(self.p("junk.txt"), "x\n")
        self.assertEqual(self.run_req("CLEAN", "=== MOVE ===\nFILE: junk.txt\nREASON: x\n=== END ===").status, "OK")
        self.assertFalse(os.path.exists(self.p("junk.txt")))
        self.assertEqual(self.run_req("UNCLUTTER", "=== BACK ===\nFILE: junk.txt\n=== END ===").status, "OK")
        self.assertTrue(os.path.exists(self.p("junk.txt")))

    def test_clean_manifest_keeps_earlier_moves(self):
        w(self.p("j1.txt"), "1\n")
        w(self.p("j2.txt"), "2\n")
        self.run_req("CLEAN", "=== MOVE ===\nFILE: j1.txt\nREASON: x\n=== END ===")
        self.run_req("CLEAN", "=== MOVE ===\nFILE: j2.txt\nREASON: x\n=== END ===")
        man = json.load(open(self.p("Clutter/002/manifest.json")))
        self.assertEqual(len(man), 2)

    def test_delete_only_inside_clutter_and_needs_y(self):
        w(self.p("Clutter/002/z.txt"), "x\n")
        self.a = [""]
        self.assertEqual(self.run_req("CLEAN", "=== DELETE ===\nFILE: Clutter/002/z.txt\n=== END ===").status, "CANCELLED")
        self.assertTrue(os.path.exists(self.p("Clutter/002/z.txt")))
        self.a = ["y"]
        self.assertEqual(self.run_req("CLEAN", "=== DELETE ===\nFILE: Clutter/002/z.txt\n=== END ===").status, "OK")
        self.assertEqual(self.run_req("CLEAN", "=== DELETE ===\nFILE: src/other.txt\n=== END ===").status, "STOPPED")

    def mk_old_tracker_world(self):
        d = self.p("Documentation/BlueprintTracker_&_ContinuationPrompt")
        w(os.path.join(d, "TST__004__01-02-2026__10-00-AM__1__B_v1.0.0.md"), TRACKER.replace("this thread = 002", "this thread = 004"))
        old = self.p("stale_Pre_x.py")
        w(old, "x\n")
        t = time.mktime((2025, 1, 1, 0, 0, 0, 0, 0, 0))
        os.utime(old, (t, t))
        w(self.p("Debug/report.txt"), "r\n")
        os.utime(self.p("Debug/report.txt"), (t, t))
        w(self.p("Debug_Scripts/keep_Pre_y.py"), "k\n")
        os.utime(self.p("Debug_Scripts/keep_Pre_y.py"), (t, t))

    def test_auto_clutter_reports_first_two_runs_then_moves(self):
        self.mk_old_tracker_world()
        c.auto_clutter(self.ctx, 4)
        self.assertTrue(os.path.exists(self.p("stale_Pre_x.py")))
        c.auto_clutter(self.ctx, 4)
        self.assertTrue(os.path.exists(self.p("stale_Pre_x.py")))
        c.auto_clutter(self.ctx, 4)
        self.assertFalse(os.path.exists(self.p("stale_Pre_x.py")))
        self.assertFalse(os.path.exists(self.p("Debug/report.txt")))
        self.assertTrue(os.path.exists(self.p("Debug_Scripts/keep_Pre_y.py")))

    def test_auto_clutter_never_touches_tool_state(self):
        self.mk_old_tracker_world()
        w(self.p("Debug/Ops_State.json"), "{}")
        t = time.mktime((2025, 1, 1, 0, 0, 0, 0, 0, 0))
        os.utime(self.p("Debug/Ops_State.json"), (t, t))
        self.ctx.cfg["auto_clutter_runs_done"] = 5
        c.auto_clutter(self.ctx, 4)
        self.assertTrue(os.path.exists(self.p("Debug/Ops_State.json")))


class GitBase(Base):
    def setUp(self):
        if not HAVE_GIT:
            self.skipTest("git not installed")
        super().setUp()
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
        os.environ.update({k: self.env[k] for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")})
        self.git("init", "-q", "-b", "main")
        w(self.p(".gitignore"), "ignored.txt\nDebug/Backups/\n")
        w(self.p("a.txt"), "one\n")
        w(self.p("locked.py"), "x=1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def git(self, *a):
        r = subprocess.run(["git"] + list(a), cwd=self.d, capture_output=True, text=True, env=self.env)
        return r.stdout.strip()

    def tracked(self):
        return set(self.git("ls-files").split("\n"))


class T11_Lock(GitBase):
    def stage(self, *files):
        return "".join("=== STAGE ===\nFILE: %s\n=== END ===\n" % f for f in files)

    def lock(self, files, tag="v1", push="no", extra=""):
        return self.run_req("LOCK", self.stage(*files), header_extra="TAG: %s\nMESSAGE: lock %s\nPUSH: %s\n%s" % (tag, tag, push, extra))

    def test_stages_only_the_listed_files(self):
        w(self.p("a.txt"), "two\n")
        w(self.p("other.txt"), "untracked\n")
        w(self.p("b.txt"), "new\n")
        r = self.lock(["a.txt", "b.txt"])
        self.assertEqual(r.status, "OK")
        self.assertIn("b.txt", self.tracked())
        self.assertNotIn("other.txt", self.tracked())
        self.assertEqual(self.git("tag"), "v1")
        self.assertEqual(self.git("show", "--stat", "--format=", "HEAD").count("|"), 2)

    def test_no_stage_block_stages_nothing(self):
        w(self.p("other.txt"), "x\n")
        r = self.run_req("LOCK", "", header_extra="TAG: v2\nMESSAGE: m\nPUSH: no\n")
        self.assertEqual(r.status, "STOPPED")
        self.assertNotIn("other.txt", self.tracked())

    def test_refuses_machine_local_files(self):
        w(self.p("app_config.json"), "{}\n")
        w(self.p("Debug/Project_Operations.config.json"), "{}\n")
        for f in ("app_config.json", "Debug/Project_Operations.config.json"):
            self.assertEqual(self.lock([f], tag="t_" + f.replace("/", "_").replace(".", "_")).status, "STOPPED", f)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_refuses_env_database_and_ignored(self):
        w(self.p(".env"), "A=1\n")
        w(self.p("x.db"), "d\n")
        w(self.p("ignored.txt"), "i\n")
        for i, f in enumerate((".env", "x.db", "ignored.txt")):
            self.assertEqual(self.lock([f], tag="r%d" % i).status, "STOPPED", f)

    def test_refuses_file_with_a_secret(self):
        w(self.p("s.txt"), "t='%s'\n" % BOTSTR)
        r = self.lock(["s.txt"])
        self.assertEqual(r.status, "STOPPED")
        self.assertNotIn("s.txt", self.tracked())

    def test_stops_when_index_already_has_staged_files(self):
        w(self.p("pre.txt"), "p\n")
        self.git("add", "pre.txt")
        w(self.p("a.txt"), "changed\n")
        r = self.lock(["a.txt"])
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "1")

    def test_cancel_leaves_everything_uncommitted(self):
        w(self.p("a.txt"), "two\n")
        self.a = ["n"]
        r = self.lock(["a.txt"])
        self.assertEqual(r.status, "CANCELLED")
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "1")
        self.assertEqual(self.git("tag"), "")

    def test_existing_tag_refused(self):
        self.git("tag", "-a", "v1", "-m", "x")
        w(self.p("a.txt"), "two\n")
        self.assertEqual(self.lock(["a.txt"]).status, "STOPPED")

    def test_locked_area_needs_u(self):
        w(self.p("locked.py"), "x=2\n")
        self.a = [""]
        self.assertEqual(self.lock(["locked.py"]).status, "CANCELLED")
        self.a = ["u"]
        self.assertEqual(self.lock(["locked.py"], tag="v9").status, "OK")

    def test_plan_lists_status_and_excluded_changes(self):
        w(self.p("a.txt"), "two\n")
        w(self.p("other.txt"), "x\n")
        self.a = ["n"]
        self.lock(["a.txt"])
        text = "\n".join(self.ctx.buf)
        self.assertIn("Will stage ONLY these 1 file(s)", text)
        self.assertRegex(text, r"\d+ other change\(s\) are NOT included")
        self.assertNotIn("+ other.txt", text)

    def test_push_sends_branch_and_tag_never_force(self):
        bare = os.path.realpath(tempfile.mkdtemp(prefix="po_bare_"))
        try:
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True, env=self.env)
            self.git("remote", "add", "origin", bare)
            self.git("push", "-q", "origin", "main")
            w(self.p("a.txt"), "two\n")
            r = self.lock(["a.txt"], push="yes")
            self.assertEqual(r.status, "OK")
            tags = subprocess.run(["git", "--git-dir", bare, "tag"], capture_output=True, text=True).stdout.split()
            self.assertEqual(tags, ["v1"])
            self.assertEqual(subprocess.run(["git", "--git-dir", bare, "rev-list", "--count", "main"], capture_output=True, text=True).stdout.strip(), "2")
        finally:
            shutil.rmtree(bare, ignore_errors=True)

    def test_push_stops_when_github_is_ahead(self):
        bare = os.path.realpath(tempfile.mkdtemp(prefix="po_bare_"))
        other = os.path.realpath(tempfile.mkdtemp(prefix="po_other_"))
        try:
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True, env=self.env)
            self.git("remote", "add", "origin", bare)
            self.git("push", "-q", "origin", "main")
            subprocess.run(["git", "clone", "-q", bare, other], check=True, env=self.env)
            w(os.path.join(other, "n.txt"), "n\n")
            subprocess.run(["git", "-C", other, "add", "n.txt"], check=True, env=self.env)
            subprocess.run(["git", "-C", other, "commit", "-q", "-m", "remote"], check=True, env=self.env)
            subprocess.run(["git", "-C", other, "push", "-q", "origin", "main"], check=True, env=self.env)
            w(self.p("a.txt"), "two\n")
            self.assertEqual(self.lock(["a.txt"], push="yes").status, "STOPPED")
            self.assertEqual(self.git("rev-list", "--count", "HEAD"), "1")
        finally:
            shutil.rmtree(bare, ignore_errors=True)
            shutil.rmtree(other, ignore_errors=True)

    def test_core_source_has_no_add_all_and_no_hard_reset(self):
        src = open(CORE, encoding="utf-8").read()
        self.assertNotRegex(src, r"""['"]add['"]\s*,\s*['"]-A['"]""")
        self.assertNotIn("reset', '--hard", src.replace('"', "'"))
        self.assertNotIn("--force", src)
        self.assertNotRegex(src, r"""['"]-f['"]""")


class T12_Rollback(GitBase):
    def setUp(self):
        super().setUp()
        self.git("tag", "-a", "base1", "-m", "base")
        w(self.p("a.txt"), "two\n")
        w(self.p("gone.txt"), "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "second")
        self.git("rm", "-q", "gone.txt")
        w(self.p("newer.txt"), "n\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "third")
        self.head = self.git("rev-parse", "HEAD")

    def rollback(self, tag="base1", extra=""):
        return self.run_req("ROLLBACK", extra, header_extra="TAG: %s\n" % tag)

    def test_requires_u_enter_not_plain_enter(self):
        self.a = [""]
        self.assertEqual(self.rollback().status, "CANCELLED")
        self.assertEqual(open(self.p("a.txt")).read(), "two\n")

    def test_restores_changed_file_and_leaves_history_and_newer_files(self):
        self.a = ["u"]
        r = self.rollback()
        self.assertEqual(r.status, "OK")
        self.assertEqual(open(self.p("a.txt")).read().replace("\r\n", "\n"), "one\n")
        self.assertTrue(os.path.exists(self.p("newer.txt")))
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "3")

    def test_working_changes_are_backed_up_and_undo_last_reverses(self):
        w(self.p("a.txt"), "my uncommitted work\n")
        self.a = ["u"]
        self.rollback()
        self.assertEqual(open(self.p("a.txt")).read().strip(), "one")
        self.a = [""]
        self.assertEqual(self.run_req("UNDO_LAST").status, "OK")
        self.assertEqual(open(self.p("a.txt")).read().strip(), "my uncommitted work")

    def test_unknown_tag(self):
        self.assertEqual(self.rollback("nope").status, "STOPPED")

    def test_single_file_subset(self):
        w(self.p("locked.py"), "x=99\n")
        self.a = ["u"]
        self.rollback(extra="=== FILE ===\nPATH: a.txt\n=== END ===")
        self.assertEqual(open(self.p("a.txt")).read().strip(), "one")
        self.assertEqual(open(self.p("locked.py")).read().strip(), "x=99")

    def test_already_matching_reports_nothing_to_do(self):
        self.git("tag", "-a", "now1", "-m", "x")
        r = self.rollback("now1")
        self.assertEqual(r.status, "OK")
        self.assertIn("0/0", r.detail)

    def test_crlf_working_file_keeps_crlf(self):
        with open(self.p("a.txt"), "wb") as f:
            f.write(b"two\r\nmore\r\n")
        self.a = ["u"]
        self.rollback()
        self.assertEqual(rd(self.p("a.txt")), b"one\r\n")


class T13_SelfUpdate(Base):
    TINY_OK = "import sys\nprint('SELFTEST: PASSED 1/1 tests passed')\nsys.exit(0)\n"
    TINY_BAD = "import sys\nprint('SELFTEST: FAILED 0/1')\nsys.exit(1)\n"

    def setUp(self):
        super().setUp()
        self.tool = os.path.join(self.d, "tool")
        os.makedirs(self.tool)
        self.core_copy = os.path.join(self.tool, "4. Project_Operations_Core.py")
        shutil.copy2(CORE, self.core_copy)
        self.mod = load_core(self.core_copy, "po_core_copy")
        self.core = self.mod
        w(self.p("tool/Tests/Project_Operations/test_project_operations.py"), self.TINY_OK)
        self.ctx = self.mod.Ctx(self.p("tool"), kit_root=self.p("Kit"), downloads=self.p("Downloads"), clip=self.clip, input_fn=lambda p="": self.a.pop(0) if self.a else "", out_fn=lambda s: None, quiet=True)
        w(self.p("tool/Documentation/Project_Code.txt"), "TST")
        w(self.p("tool/Documentation/BlueprintTracker_&_ContinuationPrompt/TST__001__01-01-2026__10-00-AM__1__A_v1.0.0.md"), TRACKER)
        self.ctx.stable_wait = 0

    def new_core(self, version="9.9.9"):
        txt = open(self.core_copy, encoding="utf-8", newline="").read().replace("\r\n", "\n")
        return txt.replace('TOOL_VERSION = "2.0.1"', 'TOOL_VERSION = "%s"' % version)

    def fix_sha(self, text):
        t = text.rstrip("\n")
        return "=== FILE ===\nSHA256: %s\n--- CONTENT ---\n%s\n=== END ===" % (c.sha256_text(t + "\n"), t)

    def test_happy_path_swaps_and_keeps_previous(self):
        before = rd(self.core_copy)
        self.a = [""]
        r = self.run_req("SELFUPDATE", self.fix_sha(self.new_core()))
        self.assertEqual(r.status, "OK", r.detail)
        self.assertIn(b'TOOL_VERSION = "9.9.9"', rd(self.core_copy))
        self.assertEqual(rd(os.path.join(self.tool, "4. Project_Operations_Core_prev.py")), before)

    def test_failing_selftest_changes_nothing(self):
        w(self.p("tool/Tests/Project_Operations/test_project_operations.py"), self.TINY_BAD)
        before = sha(self.core_copy)
        self.a = [""]
        r = self.run_req("SELFUPDATE", self.fix_sha(self.new_core()))
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual(before, sha(self.core_copy))

    def test_hash_mismatch(self):
        before = sha(self.core_copy)
        b = self.fix_sha(self.new_core()).replace("SHA256: ", "SHA256: 0")
        self.assertEqual(self.run_req("SELFUPDATE", b).status, "STOPPED")
        self.assertEqual(before, sha(self.core_copy))

    def test_syntax_error(self):
        before = sha(self.core_copy)
        self.assertEqual(self.run_req("SELFUPDATE", self.fix_sha("def (:\nTOOL_VERSION=1")).status, "STOPPED")
        self.assertEqual(before, sha(self.core_copy))

    def test_duplicate_definitions_refused(self):
        before = sha(self.core_copy)
        dup = self.new_core() + "\ndef sha256_bytes(b):\n    return 1\n"
        self.assertEqual(self.run_req("SELFUPDATE", self.fix_sha(dup)).status, "STOPPED")
        self.assertEqual(before, sha(self.core_copy))

    def test_missing_tests_refused(self):
        os.remove(self.p("tool/Tests/Project_Operations/test_project_operations.py"))
        self.assertEqual(self.run_req("SELFUPDATE", self.fix_sha(self.new_core())).status, "STOPPED")

    def test_same_version_is_already_applied(self):
        txt = open(self.core_copy, encoding="utf-8", newline="").read().replace("\r\n", "\n")
        r = self.run_req("SELFUPDATE", self.fix_sha(txt))
        self.assertEqual(r.status, "OK")
        self.assertIn("already", r.detail)

    def test_cancelled_by_jay_changes_nothing(self):
        before = sha(self.core_copy)
        self.a = ["x"]
        self.assertEqual(self.run_req("SELFUPDATE", self.fix_sha(self.new_core())).status, "CANCELLED")
        self.assertEqual(before, sha(self.core_copy))

    def test_undo_last_puts_old_core_back(self):
        before = rd(self.core_copy)
        self.a = [""]
        self.run_req("SELFUPDATE", self.fix_sha(self.new_core()))
        self.a = [""]
        self.assertEqual(self.run_req("UNDO_LAST").status, "OK")
        self.assertEqual(rd(self.core_copy), before)


class T14_NewThread(Base):
    def nt(self, extra_header="", body=""):
        return self.run_req("NEW_THREAD", body, header_extra="NEXT_THREAD: 3\n" + extra_header)

    A1 = "=== SET_A1 ===\n--- TEXT ---\n<!-- CONTINUATION_PROMPT_START -->\nthis thread = 003\nnext unit: x\n<!-- CONTINUATION_PROMPT_END -->\n=== END ===\n"

    def test_full_run_gate_tracker_map_pack_relay(self):
        w(self.p("a.py"), "x=1\n")
        self.a = ["", "", ""]
        r = self.nt(body=self.A1)
        self.assertEqual(r.status, "OK", r.detail)
        self.assertTrue(any("v1.0.1" in f for f in os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))))
        self.assertTrue(os.path.exists(self.p("New_Thread__Bundle/New_Thread_Pack__TST__T003.md")))
        self.assertIn("NEW THREAD PACK", open(self.p("New_Thread__Bundle/Relay_Parts/part_01.txt"), encoding="utf-8").read())

    def test_cancel_at_approval_gate_writes_nothing(self):
        before = sorted(os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt")))
        self.a = ["no"]
        r = self.nt(body=self.A1)
        self.assertEqual(r.status, "CANCELLED")
        self.assertEqual(before, sorted(os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))))
        self.assertFalse(os.path.exists(self.p("New_Thread__Bundle/New_Thread_Pack__TST__T003.md")))

    def test_next_thread_mismatch_stops_before_writing(self):
        before = sorted(os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt")))
        r = self.run_req("NEW_THREAD", self.A1, header_extra="NEXT_THREAD: 7\n")
        self.assertEqual(r.status, "STOPPED")
        self.assertEqual(before, sorted(os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))))

    def test_failing_step_names_the_step(self):
        r = self.run_req("NEW_THREAD", "=== STATUS ===\nID: NOPE\nSTATUS: LOCKED\nDATE: d\nNOTE: n\n=== END ===\n", header_extra="NEXT_THREAD: 3\n")
        self.assertEqual(r.status, "STOPPED")
        self.assertIn("step TRACKER", r.detail)

    def test_pack_over_limit_is_split_and_secret_blocks_relay(self):
        big = "=== RELAY ===\nFILE: big.txt\n=== END ===\n"
        w(self.p("big.txt"), ("line\n" * 6000))
        self.a = ["", "q"]
        r = self.nt(body=self.A1 + big)
        self.assertEqual(r.status, "CANCELLED")
        self.assertTrue(len(os.listdir(self.p("New_Thread__Bundle/Relay_Parts"))) >= 2)
        w(self.p("sec.txt"), "t='%s'\n" % BOTSTR)
        self.a = [""]
        self.clip.copy("untouched")
        r = self.run_req("NEW_THREAD", self.A1 + "=== RELAY ===\nFILE: sec.txt\n=== END ===\n", header_extra="NEXT_THREAD: 3\n", thread="003")
        self.assertEqual(r.status, "STOPPED")
        self.assertNotIn(BOTSTR, self.clip.paste() or "")
        self.assertFalse(any(BOTSTR in open(os.path.join(self.p("New_Thread__Bundle/Relay_Parts"), f), encoding="utf-8").read() for f in os.listdir(self.p("New_Thread__Bundle/Relay_Parts"))))

    def test_bundle_command_does_not_change_the_tracker(self):
        before = sorted(os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt")))
        self.a = ["q"]
        c.cmd_bundle(self.ctx)
        self.assertEqual(before, sorted(os.listdir(self.p("Documentation/BlueprintTracker_&_ContinuationPrompt"))))
        self.assertTrue(os.path.exists(self.p("New_Thread__Bundle/New_Thread_Pack__TST__T002.md")))

    def test_new_thread_with_lock_uses_explicit_files_only(self):
        if not HAVE_GIT:
            self.skipTest("git not installed")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        os.environ.update(env)
        g = lambda *a: subprocess.run(["git"] + list(a), cwd=self.d, capture_output=True, text=True).stdout.strip()
        g("init", "-q", "-b", "main")
        w(self.p(".gitignore"), "Debug/\nNew_Thread__Bundle/\nClutter/\nDownloads/\n")
        g("add", "-A")
        g("commit", "-q", "-m", "base")
        w(self.p("untracked_other.txt"), "x\n")
        self.a = ["", "", "", ""]
        r = self.nt(extra_header="LOCK: yes\nLOCK_MESSAGE: unit locked\nLOCK_TAG: lock-1\nLOCK_PUSH: no\n", body=self.A1)
        self.assertEqual(r.status, "OK", r.detail)
        self.assertEqual(g("tag"), "lock-1")
        self.assertNotIn("untracked_other.txt", g("ls-files"))


class T15_RunnerAndLogs(Base):
    def test_pick_lowest_first_and_skips_done(self):
        self.req("MAP", num=7)
        self.req("MAP", num=3)
        f9 = self.req("MAP", num=9)
        self.assertEqual([x[1] for x in c.pick(self.ctx)], [3, 7, 9])
        w(os.path.join(self.ctx.downloads, c.output_name(os.path.basename(f9))), "done")
        self.assertEqual([x[1] for x in c.pick(self.ctx)], [3, 7])

    def test_cmd_run_runs_lowest_waiting(self):
        self.req("MAP", num=8)
        f2 = self.req("MAP", num=2)
        r = c.cmd_run(self.ctx)
        self.assertEqual(r.status, "OK")
        self.assertTrue(os.path.exists(os.path.join(self.ctx.downloads, c.output_name(os.path.basename(f2)))))

    def test_cmd_run_with_nothing_waiting(self):
        self.assertIsNone(c.cmd_run(self.ctx))

    def test_request_not_run_twice(self):
        f = self.req("MAP", num=4)
        c.run_request(self.ctx, f)
        os.remove(os.path.join(self.ctx.downloads, c.output_name(os.path.basename(f))))
        self.assertIn("already processed", c.run_request(self.ctx, f).detail)

    def test_ops_log_is_written_with_hashes(self):
        w(self.p("a.py"), "x=1\n")
        self.run_req("REPLACE", self.replace_body("a.py", "x=1", "x=2"))
        log = open(self.p("Debug/Ops_Log.md"), encoding="utf-8").read()
        self.assertIn("REPLACE", log)
        self.assertIn("a.py=", log)

    def test_state_records_file_numbers(self):
        self.run_req("MAP", num=12)
        self.assertEqual(self.ctx.state["last_file_number"], 12)

    def test_watcher_single_instance_lock(self):
        wl = c.WatcherLock(self.ctx)
        self.assertFalse(wl.alive())
        w(self.p("Debug/ops.lock"), json.dumps({"pid": 99999999, "beat": time.time()}))
        self.assertTrue(wl.alive())
        w(self.p("Debug/ops.lock"), json.dumps({"pid": 99999999, "beat": time.time() - 100}))
        self.assertFalse(wl.alive())
        w(self.p("Debug/ops.lock"), json.dumps({"pid": 99999999, "beat": time.time()}))
        self.assertEqual(c.cmd_watch(self.ctx), 1)

    def test_run_lock_blocks_parallel_run(self):
        w(self.p("Debug/ops_run.lock"), "1")
        f = self.req("MAP")
        self.assertEqual(c.run_request(self.ctx, f).status, "STOPPED")

    def test_stable_file_detects_missing_and_stable(self):
        p = self.p("g.txt")
        w(p, "a")
        self.assertTrue(c.stable_file(p, 0))
        self.assertFalse(c.stable_file(self.p("nofile"), 0))


class T16_Preflight(Base):
    def test_gitignore_gaps_reported_never_edited(self):
        w(self.p(".gitignore"), "venv/\n")
        before = sha(self.p(".gitignore"))
        self.run_req("PREFLIGHT")
        self.assertEqual(before, sha(self.p(".gitignore")))
        self.assertIn("report only", "\n".join(self.ctx.buf))

    def test_missing_tool_file_is_a_problem_with_ai_prompt(self):
        r = self.run_req("PREFLIGHT")
        self.assertIn("PREFLIGHT:", r.detail)
        self.assertTrue(os.path.exists(self.p("Debug/AI_Prompt_Generate_Missing.txt")))

    def test_repairs_missing_tool_from_kit_and_creates_folders(self):
        w(self.p("Kit/Scripts/Project_Operations/4a. New_Thread__Bundle.bat"), "@echo off\n")
        self.run_req("PREFLIGHT")
        self.assertTrue(os.path.exists(self.p("4a. New_Thread__Bundle.bat")))
        self.assertTrue(os.path.isdir(self.p("Documentation/Help_Source")))

    def test_preflight_runs_before_other_modes(self):
        self.run_req("MAP")
        self.assertTrue(os.path.exists(self.p("Debug/AI_Prompt_Generate_Missing.txt")))


class T17_MenuCalibrateVSCode(Base):
    def test_menu_quit_and_unknown(self):
        self.a = ["9", "q"]
        self.assertEqual(c.cmd_menu(self.ctx), 0)
        self.assertIn("unknown choice", "\n".join(self.ctx.buf))

    def test_menu_status(self):
        self.a = ["8", "q"]
        c.cmd_menu(self.ctx)
        self.assertIn("project code: TST", "\n".join(self.ctx.buf))

    def test_menu_preflight_and_run(self):
        self.a = ["5", "1", "q"]
        c.cmd_menu(self.ctx)
        self.assertIn("no waiting request", "\n".join(self.ctx.buf))

    def test_calibration_sample_is_exact_size(self):
        for n in (15000, 8000, 4000):
            s = c.calib_sample(n)
            self.assertEqual(len(s), n)
            self.assertTrue(s.endswith("END-OF-CALIBRATION-%d" % n))

    def test_calibration_accepts_first_size(self):
        self.a = ["y"]
        self.assertEqual(c.cmd_calibrate(self.ctx), 0)
        self.assertEqual(json.load(open(self.p("Debug/Project_Operations.config.json")))["relay_max_chars"], 15000)

    def test_calibration_steps_down(self):
        self.a = ["n", "y"]
        c.cmd_calibrate(self.ctx)
        self.assertEqual(json.load(open(self.p("Debug/Project_Operations.config.json")))["relay_max_chars"], 12000)

    def test_calibration_quit_saves_nothing(self):
        self.a = ["q"]
        self.assertEqual(c.cmd_calibrate(self.ctx), 1)
        self.assertFalse(os.path.exists(self.p("Debug/Project_Operations.config.json")))

    def test_vscode_task_installed_only_after_enter(self):
        self.a = ["x"]
        self.assertFalse(c.install_vscode_task(self.ctx))
        self.assertFalse(os.path.exists(self.p(".vscode/tasks.json")))
        self.a = [""]
        self.assertTrue(c.install_vscode_task(self.ctx))
        data = json.load(open(self.p(".vscode/tasks.json")))
        self.assertEqual(data["tasks"][0]["runOptions"]["runOn"], "folderOpen")
        self.assertEqual(data["tasks"][0]["command"], "4b. Watch_Requests.bat")

    def test_vscode_task_merges_and_backs_up_existing(self):
        w(self.p(".vscode/tasks.json"), json.dumps({"version": "2.0.0", "tasks": [{"label": "mine", "type": "shell", "command": "x"}]}))
        self.a = [""]
        c.install_vscode_task(self.ctx)
        data = json.load(open(self.p(".vscode/tasks.json")))
        self.assertEqual([t["label"] for t in data["tasks"]], ["mine", "Project_Operations Watcher"])
        self.assertTrue(any(f.startswith("tasks.json.bak_") for f in os.listdir(self.p("Debug/Backups"))))

    def test_vscode_task_invalid_json_untouched(self):
        w(self.p(".vscode/tasks.json"), "// comment\n{}")
        before = sha(self.p(".vscode/tasks.json"))
        self.assertFalse(c.install_vscode_task(self.ctx))
        self.assertEqual(before, sha(self.p(".vscode/tasks.json")))

    def test_vscode_task_idempotent(self):
        self.a = [""]
        c.install_vscode_task(self.ctx)
        h = sha(self.p(".vscode/tasks.json"))
        self.assertTrue(c.install_vscode_task(self.ctx))
        self.assertEqual(h, sha(self.p(".vscode/tasks.json")))


class T18_CoreHealth(unittest.TestCase):
    def test_core_parses_and_has_no_duplicate_definitions(self):
        tree = ast.parse(open(CORE, encoding="utf-8").read())
        cnt = collections.Counter(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
        self.assertEqual({k: v for k, v in cnt.items() if v > 1}, {})

    def test_core_has_no_undefined_names(self):
        import builtins
        tree = ast.parse(open(CORE, encoding="utf-8").read())
        defined = set(dir(builtins)) | {"__file__"}
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                defined.add(n.name)
            elif isinstance(n, ast.arg):
                defined.add(n.arg)
            elif isinstance(n, ast.Import):
                defined |= {(a.asname or a.name).split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                defined |= {a.asname or a.name for a in n.names}
            elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                defined.add(n.id)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                defined.add(n.name)
        loads = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        self.assertEqual(sorted(loads - defined), [])

    def test_core_is_standard_library_only(self):
        tree = ast.parse(open(CORE, encoding="utf-8").read())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module.split(".")[0])
        std = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else mods
        self.assertEqual(sorted(mods - std), [])

    def test_all_clipboard_writes_go_through_the_guard(self):
        src = open(CORE, encoding="utf-8").read()
        lines = [l for l in src.split("\n") if "clip.copy(" in l]
        allowed = ("def safe_copy", 'return "ok" if ctx.clip.copy(text)', "probe", "if ctx.clip.copy(probe)")
        bad = [l for l in lines if not any(a in l for a in allowed)]
        self.assertEqual(bad, [])

    def test_tool_version_matches(self):
        self.assertEqual(c.TOOL_VERSION, "2.0.1")

    def test_launchers_force_utf8(self):
        found = 0
        for name in ("4. Project_Operations.bat", "4a. New_Thread__Bundle.bat", "4b. Watch_Requests.bat", "4c. Test_And_Check.bat"):
            p = os.path.join(PROJECT_ROOT, name)
            if os.path.isfile(p):
                found += 1
                t = open(p, encoding="utf-8", errors="replace").read()
                self.assertIn("PYTHONUTF8=1", t, name)
                self.assertIn("chcp 65001", t, name)
        p = os.path.join(PROJECT_ROOT, "4. Project_Operations.ps1")
        if os.path.isfile(p):
            self.assertIn("PYTHONUTF8", open(p, encoding="utf-8", errors="replace").read())
        if not found:
            self.skipTest("launchers not next to the tests (running from a temporary folder)")

    def test_windows_launchers_use_crlf(self):
        for name in ("4. Project_Operations.bat", "4b. Watch_Requests.bat", "4c. Test_And_Check.bat", "4a. New_Thread__Bundle.bat"):
            p = os.path.join(PROJECT_ROOT, name)
            if os.path.isfile(p):
                b = rd(p)
                self.assertNotIn(b"\n", b.replace(b"\r\n", b""), name)


PUSH_SCAN = [r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b", r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{36,}", r"github_pat_[A-Za-z0-9_]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
             r"""(?i)(api[_-]?key|secret|token|passwd|password)\s*[:=]\s*["'][^"'\s]{8,}["']"""]


class T21_ShippedFilesAreClean(unittest.TestCase):
    """The tool's own files must pass the Clipboard Guard and the push-script secret scan, or LOCK / COLLECT / push would refuse them."""

    def files(self):
        out = []
        for rel in ("4. Project_Operations_Core.py", "4. Project_Operations.bat", "4. Project_Operations.ps1", "4a. New_Thread__Bundle.bat", "4b. Watch_Requests.bat",
                    "4c. Test_And_Check.bat", "2. Push_To_GitHub.ps1", "Tests/Project_Operations/test_project_operations.py",
                    "Debug_Scripts/Untrack_Accidental_Debug_Files_v1.0.0.py", "Install_Project_Operations.py", "MANIFEST.json",
                    "Docs/Project_Operations/Project_Operations_Features_v2.0.0_Spec.md", "Docs/Project_Operations/Project_Operations_Workflow_Steps_v1.0.0.md",
                    "Documentation/Help_Source/Project_Operations/Project_Operations_Features_v2.0.0_Spec.md",
                    "Documentation/Help_Source/Project_Operations/Project_Operations_Workflow_Steps_v1.0.0.md"):
            p = os.path.join(PROJECT_ROOT, *rel.split("/"))
            if os.path.isfile(p):
                out.append((rel, p))
        return out

    def test_clipboard_guard_finds_nothing_in_the_tools_own_files(self):
        files = self.files()
        self.assertTrue(files)
        for rel, p in files:
            text = open(p, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
            self.assertEqual(c.scan_text(text, os.path.basename(rel)), [], rel)

    def test_push_script_secret_patterns_find_nothing_in_the_tools_own_files(self):
        for rel, p in self.files():
            for n, line in enumerate(open(p, encoding="utf-8", errors="replace").read().split("\n"), 1):
                for rx in PUSH_SCAN:
                    self.assertIsNone(re.search(rx, line), "%s line %d" % (rel, n))


def _find_dir(env, rel):
    for d in (os.environ.get(env, ""), os.path.join(PROJECT_ROOT, *rel.split("/"))):
        if d and os.path.isdir(d):
            return d
    return None


INSTALLER = _find_dir("PO_INSTALLER_DIR", "Debug/Installers/Project_Operations_v2.0.1")
if INSTALLER and not os.path.isfile(os.path.join(INSTALLER, "Install_Project_Operations.py")):
    INSTALLER = None


class T19_Installer(unittest.TestCase):
    def setUp(self):
        if not INSTALLER:
            self.skipTest("installer folder not found")
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="po_inst_"))
        self.kit = os.path.join(self.root, "KIT")
        self.proj = os.path.join(self.root, "proj")
        os.makedirs(os.path.join(self.proj, "Documentation"))
        os.makedirs(self.kit)
        self.manifest = json.load(open(os.path.join(INSTALLER, "MANIFEST.json"), encoding="utf-8"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_inst(self, *extra, inp="", folder=None):
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, os.path.join(folder or INSTALLER, "Install_Project_Operations.py"), "--root", self.proj, "--kit", self.kit] + list(extra),
                              input=inp, capture_output=True, text=True, env=env, timeout=180, encoding="utf-8", errors="replace")

    def test_manifest_hashes_match_every_shipped_file(self):
        for e in self.manifest["files"]:
            self.assertEqual(hashlib.sha256(rd(os.path.join(INSTALLER, *e["src"].split("/")))).hexdigest(), e["sha256"].lower(), e["src"])

    def test_manifest_has_no_pycache_or_stub_docs(self):
        for e in self.manifest["files"]:
            self.assertNotIn("__pycache__", e["src"])
            self.assertFalse(e["src"].endswith(".pyc"))
            if e["src"].lower().endswith(".md"):
                self.assertGreater(os.path.getsize(os.path.join(INSTALLER, *e["src"].split("/"))), 1200, e["src"])

    def test_every_tool_file_is_in_the_manifest(self):
        names = {e["src"] for e in self.manifest["files"]}
        for need in ("4. Project_Operations_Core.py", "4. Project_Operations.bat", "4. Project_Operations.ps1", "4a. New_Thread__Bundle.bat", "4b. Watch_Requests.bat", "4c. Test_And_Check.bat", "Tests/Project_Operations/test_project_operations.py"):
            self.assertIn(need, names)

    def test_dry_run_changes_nothing(self):
        r = self.run_inst("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.proj, "4. Project_Operations_Core.py")))

    def test_fresh_install_places_everything_with_hashes(self):
        r = self.run_inst("--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for e in self.manifest["files"]:
            for base, rel in e["targets"]:
                dst = os.path.join(self.proj if base == "P" else self.kit, *rel.split("/"))
                self.assertTrue(os.path.exists(dst), dst)
                self.assertEqual(hashlib.sha256(rd(dst)).hexdigest(), e["sha256"].lower(), dst)

    def test_second_install_is_idempotent(self):
        self.run_inst("--yes")
        r = self.run_inst("--yes")
        self.assertEqual(r.returncode, 0)
        self.assertIn("identical", r.stdout)

    def test_replaced_file_is_backed_up_first(self):
        w(os.path.join(self.proj, "4. Project_Operations_Core.py"), "old core\n")
        self.run_inst("--yes")
        found = []
        for dp, dn, fn in os.walk(os.path.join(self.proj, "Debug", "Backups")):
            found += [os.path.join(dp, f) for f in fn if f.startswith("4. Project_Operations_Core.py")]
        self.assertTrue(found)
        self.assertEqual(open(found[0]).read(), "old core\n")

    def test_without_yes_a_replace_needs_enter(self):
        w(os.path.join(self.proj, "4. Project_Operations_Core.py"), "old core\n")
        r = self.run_inst(inp="n\n")
        self.assertEqual(open(os.path.join(self.proj, "4. Project_Operations_Core.py")).read(), "old core\n")
        self.assertNotEqual(r.returncode, 0)

    def test_config_and_project_code_never_clobbered(self):
        os.makedirs(os.path.join(self.proj, "Debug"))
        w(os.path.join(self.proj, "Debug", "Project_Operations.config.json"), json.dumps({"kit_root": "Z:/mine", "downloads": "Z:/dl", "relay_max_chars": 9000}))
        w(os.path.join(self.proj, "Documentation", "Project_Code.txt"), "KEEP\n")
        self.run_inst("--yes")
        cfg = json.load(open(os.path.join(self.proj, "Debug", "Project_Operations.config.json")))
        self.assertEqual(cfg["kit_root"], "Z:/mine")
        self.assertEqual(cfg["relay_max_chars"], 9000)
        self.assertEqual(open(os.path.join(self.proj, "Documentation", "Project_Code.txt")).read(), "KEEP\n")

    def test_new_config_gets_kit_root_only_when_missing(self):
        self.run_inst("--yes")
        cfg = json.load(open(os.path.join(self.proj, "Debug", "Project_Operations.config.json")))
        self.assertEqual(os.path.normcase(cfg["kit_root"]), os.path.normcase(self.kit))

    def test_existing_different_help_doc_is_kept(self):
        d = os.path.join(self.proj, "Documentation", "Help_Source", "Project_Operations")
        os.makedirs(d)
        name = [e["src"].split("/")[-1] for e in self.manifest["files"] if e["src"].lower().endswith(".md")][0]
        w(os.path.join(d, name), "my own words, not a known stub\n" * 60)
        self.run_inst("--yes")
        self.assertIn("my own words", open(os.path.join(d, name)).read())

    def test_known_old_stub_hashes_are_recorded(self):
        e = [x for x in self.manifest["files"] if x["src"].lower().endswith(".md") and x.get("known_old_sha256")][0]
        self.assertTrue(all(len(h) == 64 for h in e["known_old_sha256"]))

    def test_tampered_source_file_refused(self):
        tmp = os.path.join(self.root, "copy")
        shutil.copytree(INSTALLER, tmp)
        with open(os.path.join(tmp, "4a. New_Thread__Bundle.bat"), "ab") as f:
            f.write(b"echo tampered\r\n")
        r = self.run_inst("--yes", folder=tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.proj, "4. Project_Operations_Core.py")))

    def test_refuses_folder_without_documentation(self):
        shutil.rmtree(os.path.join(self.proj, "Documentation"))
        self.assertNotEqual(self.run_inst("--yes").returncode, 0)

    def test_installed_core_runs_and_reports_version(self):
        self.run_inst("--yes")
        r = subprocess.run([sys.executable, os.path.join(self.proj, "4. Project_Operations_Core.py"), "version"], capture_output=True, text=True, env=dict(os.environ, PYTHONUTF8="1"))
        self.assertEqual(r.stdout.strip(), "2.0.1")

    def test_installed_copy_passes_its_own_selftest(self):
        self.run_inst("--yes")
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        env.pop("PO_INSTALLER_DIR", None)
        r = subprocess.run([sys.executable, os.path.join(self.proj, "4. Project_Operations_Core.py"), "selftest"], capture_output=True, text=True, env=env, timeout=600, encoding="utf-8", errors="replace")
        self.assertIn("SELFTEST: PASSED", r.stdout, r.stdout[-800:])


HELPER = _find_dir("PO_HELPER_DIR", "Debug_Scripts")
if HELPER and not os.path.isfile(os.path.join(HELPER, "Untrack_Accidental_Debug_Files_v1.0.0.py")):
    HELPER = None
ACCIDENTAL = ["Debug/Home_Sync_ReadOnly_Report.txt", "Debug/Narrow_Cleanup_Report.txt", "Debug_Scripts/Narrow_Git_Cleanup_v1.0.0.bat", "Debug_Scripts/Narrow_Git_Cleanup_v1.0.0.py"]


class T20_UntrackHelper(unittest.TestCase):
    def setUp(self):
        if not HELPER or not HAVE_GIT:
            self.skipTest("helper or git not available")
        self.d = os.path.realpath(tempfile.mkdtemp(prefix="po_h_"))
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com", PYTHONUTF8="1")
        self.g("init", "-q", "-b", "main")
        w(os.path.join(self.d, ".gitignore"), "venv/\n")
        for f in ACCIDENTAL + ["keep.txt", "Debug/Other_Report.txt"]:
            w(os.path.join(self.d, *f.split("/")), "content of %s\n" % f)
        self.g("add", "-A")
        self.g("commit", "-q", "-m", "base")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def g(self, *a):
        return subprocess.run(["git"] + list(a), cwd=self.d, capture_output=True, text=True, env=self.env).stdout.strip()

    def helper(self, *extra, inp=""):
        return subprocess.run([sys.executable, os.path.join(HELPER, "Untrack_Accidental_Debug_Files_v1.0.0.py"), "--root", self.d] + list(extra), input=inp, capture_output=True, text=True, env=self.env, timeout=120, encoding="utf-8", errors="replace")

    def test_dry_run_changes_nothing(self):
        before = self.g("rev-parse", "HEAD")
        r = self.helper("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(before, self.g("rev-parse", "HEAD"))
        self.assertIn("Debug/Narrow_Cleanup_Report.txt", self.g("ls-files"))

    def test_untracks_exactly_the_four_files_keeps_local_copies_and_no_history_rewrite(self):
        before = self.g("rev-parse", "HEAD")
        r = self.helper("--yes", "--no-push")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tracked = set(self.g("ls-files").split("\n"))
        for f in ACCIDENTAL:
            self.assertNotIn(f, tracked)
            self.assertTrue(os.path.exists(os.path.join(self.d, *f.split("/"))), f)
        for f in ("keep.txt", "Debug/Other_Report.txt", ".gitignore"):
            self.assertIn(f, tracked)
        self.assertEqual(self.g("rev-list", "--count", "HEAD"), "2")
        self.assertEqual(self.g("rev-parse", "HEAD~1"), before)
        self.assertEqual(self.g("show", "--stat", "--format=", "HEAD").count("|"), 5)
        self.assertEqual(self.g("status", "--short"), "")

    def test_ignore_rules_added_so_a_later_add_all_cannot_bring_them_back(self):
        self.helper("--yes", "--no-push")
        self.g("add", "-A")
        self.assertEqual(self.g("diff", "--cached", "--name-only"), "")

    def test_refuses_when_index_already_has_staged_files(self):
        w(os.path.join(self.d, "pre.txt"), "p\n")
        self.g("add", "pre.txt")
        before = self.g("rev-parse", "HEAD")
        r = self.helper("--yes", "--no-push")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(before, self.g("rev-parse", "HEAD"))
        self.assertIn("Debug/Narrow_Cleanup_Report.txt", self.g("ls-files"))

    def test_cancel_changes_nothing(self):
        before = self.g("rev-parse", "HEAD")
        r = self.helper("--no-push", inp="n\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(before, self.g("rev-parse", "HEAD"))

    def test_second_run_is_a_noop(self):
        self.helper("--yes", "--no-push")
        n = self.g("rev-list", "--count", "HEAD")
        r = self.helper("--yes", "--no-push")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(n, self.g("rev-list", "--count", "HEAD"))

    def test_helper_source_has_no_force_reset_or_add_all(self):
        src = open(os.path.join(HELPER, "Untrack_Accidental_Debug_Files_v1.0.0.py"), encoding="utf-8").read()
        self.assertNotIn("--force", src)
        self.assertNotIn("--hard", src)
        self.assertNotRegex(src, r"""['"]-A['"]""")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    r = unittest.TextTestRunner(verbosity=1).run(suite)
    passed = r.testsRun - len(r.failures) - len(r.errors) - len(r.skipped)
    print("SELFTEST: %s %d/%d tests passed (%d skipped)" % ("PASSED" if r.wasSuccessful() else "FAILED", passed, r.testsRun - len(r.skipped), len(r.skipped)))
    sys.exit(not r.wasSuccessful())
