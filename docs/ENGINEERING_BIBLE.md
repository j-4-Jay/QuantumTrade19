# QuantumTrade19 — Engineering Bible

A permanent reference. Rules A–C are QT19's own locked rules (sourced from `QuantumTrade19_Project_Instructions_v2.md` and the Architecture Blueprint). Rules D–F are workflow/tooling additions. Rule G is universal — reusable for any future software project, not just QT19.

---

## A. Architecture Rules (Non-Negotiable)

- Three tiers, strictly one-directional: Worker Engines → Monitor Engines → Master Engines. Workers never import Workers; Monitors contain zero business logic; Masters never import a Worker directly.
- Every Worker/Monitor/Master gets its own file, folder, tests, and error boundary — a failure in one module must never hamper another.
- All tiers publish/subscribe through one shared internal event bus so future rules can be added without editing locked code.
- The highest-numbered `00_QuantumTrade19_Architecture_Blueprint_vX.md` is always the current authority — never an older version.
- File numbering is contiguous, zero gaps, 01 through 19.
- CoinDCX Futures endpoints only — never spot — for any candle, price, or POI data.
- Engine math always stays UTC-correct; only the display layer may convert to a local timezone.
- Windows is built and fully locked first; macOS reuses identical engine code later, swapping only OS-specific Workers.

## B. Process Rules

- Pipeline for every module, no exceptions: **build → check → debug (if needed) → re-check → lock → proceed**. A module is never "done" until its check gate passes, and the next module never starts before explicit user lock.
- One Monitor Engine (with all its Workers) is built per conversation thread — never two Monitors in the same thread.
- Never keep one giant "current" architecture doc updated live — the final polished blueprint is assembled only after the software is finished, from the versioned build-log record.
- Every lock gets a new, never-retroactively-edited file in `docs/build_log/`, named `vX.Y.Z_ModuleName_Summary.md`.
- Ad-hoc debugging/scratch files go only in `debug_temp/`, never the project root or inside `engines/` — and you're told explicitly which are safe to delete once debugging ends.

### B1. The Lock Checklist

The instant a module, batch, or scope locks, the following deliverables are produced. Not all of them update every time — this is intentional, to avoid noise:

**Always, every single lock, no exceptions:**
1. A new build-log summary: `docs/build_log/vX.Y.Z_ModuleName_Summary.md` (immutable, never edited after creation).
2. A ready-to-paste continuation prompt for the next thread.
3. `docs/CURRENT_STATUS.md` rewritten to reflect the new true state.
4. `docs/build_log/INDEX.md` — one new line appended for the newly locked item.
5. `docs/DELIVERABLES.md` — the relevant module/scope table updated, flipping any items that just went from ❌/⚠️ to ✅. New modules get a brand-new table section appended below the last one; existing rows are only ever edited to flip status, never deleted.

**Only when applicable — skip if nothing changed:**
6. `docs/KNOWN_ISSUES.md` — add a row only if a new defect was discovered during that work; close a row only if one was fixed.
7. `docs/DECISIONS.md` — add a row only if an actual judgment call was made during that work.

**Rarely — only when a genuinely new permanent rule is established or an existing one needs correcting:**
8. `docs/ENGINEERING_BIBLE.md` itself.

Never skip items 1–5. Never pad items 6–8 with a row just to "look complete" — false entries are worse than no entry.

### B2. Trigger Word

**`CHECKPOINT`** is the standing trigger word. Saying it in any thread means: run through the Lock Checklist above.

- If nothing has locked since the last checkpoint: state that plainly, and only touch `CURRENT_STATUS.md` / `DELIVERABLES.md` / `INDEX.md` if the in-progress state has genuinely moved forward since the last check.
- If something has locked (explicitly confirmed by the user, not assumed): run the full checklist, items 1–5 mandatory, 6–8 conditional.

## C. Engineering Standards

- Git-commit immediately after every lock, tagged with module name and version bump.
- Type-hinted signatures and docstrings on every Worker function.
- Secrets only via `keyring`/`.env` — never hardcoded, never committed.
- Any newly-locked Execution capability defaults its Dry-Run toggle to ON until explicitly soak-tested.
- Every check gate includes at least one test using fabricated/mocked data, not only live API calls.
- Per-Worker heartbeat watchdogs with isolated auto-restart — one Worker dying never takes down its Monitor.
- Idempotent event IDs and an immutable audit log across the event bus.
- Mandatory plain-language explainability on every auto-action the software takes.
- Shadow-mode canary rollout before any auto-learned setting goes live.
- Crash-safe checkpointing and manual-confirm gates before any silent update.
- Local-first storage, with optional encrypted backup — never cloud-first for trading data.
- A short weekly rollup note in `docs/build_log/` tracking overall progress against the roadmap.

## D. Continuity Files (Stop Re-Explaining Yourself)

- `docs/CURRENT_STATUS.md` — one living file, overwritten in place, holding only "what's locked / what's in progress / exact next step."
- `docs/DELIVERABLES.md` — the cumulative, module-by-module done/not-done ledger against the blueprint. Never shrinks; only grows or flips status. This is the file to check for "what's actually built vs. planned" at a glance, at any point in the project's life.
- `docs/build_log/INDEX.md` — one line per locked module.
- `docs/KNOWN_ISSUES.md` — every discovered-but-not-yet-fixed defect, tagged to its module.
- `docs/DECISIONS.md` — a running log of judgment calls made mid-build.
- Name every continuation prompt predictably, e.g. `03.1_Batch4_Continuation_Prompt.md`.
- Enrich the Perplexity Project's Custom Instructions field (in Project settings, not a file) with permanent Working Style rules once, so every new thread inherits them automatically.

## E. GitHub / Tooling Notes

- The GitHub connector reliably confirms file existence, size, and commit hash, and lists directories in full — but does not reliably surface actual file *content* back into the conversation for single-file reads, regardless of file size or repo visibility.
- Making the repo public did not immediately fix external URL fetching either — anonymous GitHub API/CDN access can be rate-limited or take time to propagate after a visibility change.
- Until confirmed working, keep pasting real file content directly for any code that needs reading or modifying.

## F. QT19-Specific Data/UX Rules

- Baseline history: every active symbol always keeps a minimum 5-day rolling window of 1m/5m/15m candles, regardless of any other setting.
- Deep history is opt-in per symbol, rate-limit-deprioritized, and must never compete with live-trading API calls for priority.
- POI types are each independently toggleable; PDH/PDL and 4H H/L default ON, everything else defaults OFF.
- 123Bull/123Bear setup logic is locked and lives only in `123Bull_Setup_Master_Prompt.md` / `123Bear_Setup_Master_Prompt.md` — never re-derive or alter this logic ad hoc mid-build.
- Trade Allowed permission blocks only new entries, never touches an already-open trade.
- App Lock freezes only the UI, never any background engine.

## G. Universal Rules (Reusable for Any Future Software Project)

- Separate concerns strictly by layer (data → logic → orchestration → presentation).
- Never let a UI layer talk directly to an external API — always through an internal interface.
- Treat every external data source as untrustworthy until validated — normalize, timestamp, and sanity-check before it enters your system.
- Make time-zone handling a first-class decision on day one — store in UTC, convert only at display.
- Write the test for a bug the moment you understand its root cause, before you write the fix.
- Log enough to diagnose a 3am failure without needing to reproduce it live.
- Default every irreversible or money-moving action to its safest mode until proven safe.
- Keep a one-page "why" document for every non-obvious architectural choice.
- Version and changelog every config schema change.
- Prefer boring, well-understood technology for anything security- or money-adjacent; save novelty for UI/UX.
