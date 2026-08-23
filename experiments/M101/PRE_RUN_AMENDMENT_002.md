# M101 pre-run amendment 002 — stable fresh-process identity

**Date:** 2026-08-23  
**Timing:** after the v2 protocol tag; before any armed M101 run, qualification evidence or result  
**Disposition:** accepted evidence-stability correction; both earlier tags remain preserved

## Trigger

The complete repository suite on the exact v2 freeze commit observed one repeated Windows process
identifier among sequential M101 development invocations. Every invocation had been launched by a
separate synchronous `subprocess.run` call, the prior child had terminated before the next launch,
all children ran with isolated Python, and no project module or repository search path entered the
capsules. Windows legitimately recycled the numeric PID after process death.

The operational check `all_processes_distinct` therefore encoded an invalid platform assumption. It
could turn genuine process death followed by a fresh process into a false failure, and the occurrence
of PID recycling is nondeterministic across stable replay. PIDs were already frozen as recursively
projected process ephemera; the retained distinctness assertion contradicted that policy.

## Correction

The chronology now assigns deterministic invocation ordinals after collecting the runtime rows and
retains these scientific facts:

1. the exact number of fresh runtime invocations;
2. a complete unique contiguous ordinal sequence;
3. a source-audited synchronous `subprocess.run` launch with `-I`, capsule working directory and no
   process reuse API for every invocation;
4. termination-before-next-launch from the synchronous call boundary;
5. per-child isolated-mode, import-census and repository-search-path evidence; and
6. PID presence, while the PID values themselves remain recursively projected ephemera.

The checker still requires exactly 42 runtime invocations for the frozen fifteen-world chronology
and now requires ordinals 1 through 42 plus every isolation and source-launch fact above.

## Scientific invariants

This amendment does not weaken P12: it replaces an operating-system-number uniqueness proxy with
direct evidence for the pre-registered requirement that each step occur in a newly launched process
after the prior producer/consumer terminates. It changes no question, claim, decisive-condition text,
falsifier, world, case, expected value, runtime mechanism, capsule, acquisition language, search
bound, budget, stable-projection key set or verdict rule.

The frozen qualification population remained unexecuted by the M101 mechanism,
`experiments/M101/RESULT.json` did not exist, the armed runner was never invoked, and D070 remained
unfilled. The v1 and v2 tags remain immutable refused pre-run records. The corrected authoritative
freeze uses `experiment/m101-frozen-protocol-v3`.
