# Baseline persistence fix v0.1.0
Approved direction by Jay 08-11-2026, option 1. Implementation pending local tests and live confirmation; not locked.
Startup previously fetched five-day baseline into RAM only. Chart merges RAM and SQLite; popup reads SQLite, exposing real historical gaps.
New worker fills only absent closed UTC-aligned 1m/5m/15m rows from the already fetched baseline. Derived 15m needs all three 5m source timestamps. Existing rows stay unchanged under the store lock. No setup notifications or history replay. Closed by time does not certify exchange settlement.
Before first insertion per store instance, SQLite backup creates Debug/Backups/baseline_before_fill_*.db. Failure prevents fill; startup reports failure rather than silently proceeding. No extra HTTP requests; local backup and inserts add disk/time cost at startup. Never delete backups without Jay approval.
Scope is returned five-day baseline, not all historical gaps or automatic recovery after arbitrary network failure. Verify diagnostic before/after; investigate remaining gaps. Six isolated regression tests cover forming exclusion, existing-value preservation, backup ordering/reuse, partial derived exclusion, complete derived acceptance/alignment, and backup failure. Jay must run full suite and live checks before locking.

