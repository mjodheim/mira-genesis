# M065 — corrected development result

## Verdict

**Positive in four-bank development; not canonical.**

M065 reran every precommitted bank with the unchanged M064 tasks, controls, budgets, thresholds,
substrates and candidate language. The complete lineage again accepted three rewrites, reached
version twelve, passed 68/68 retained cases and 18/18 hidden observations. Fresh-on-B,
unchanged-parent-migrated and learned-state-ablated again accepted zero rewrites and passed 0/18.

## Corrected rollback evidence

For every bank, the forced transaction now records and verifies all of the following:

- the corrupt staged state has a digest different from the returned state;
- the returned state is a newly deserialised object, not the saved input object;
- that object passes the complete state audit;
- its canonical bytes and state digest equal the pre-fault commitment;
- retained behaviour passes after restoration;
- deterministic replay repeats the same corrected fault and reaches the exact final digest.

Seven M065 tests passed across all four banks in the first corrected campaign. The only failure in
the combined 12-test invocation was an M064 portability fixture that still computed its expected
hash from raw Windows CRLF; the M065 scientific tests all passed. That fixture was corrected and
the five M064 portable-identity tests then passed in 0.19 seconds.

The first complete M065 repository rerun passed 1,100 tests and exposed one remaining M064 guard
fixture with the same raw-CRLF expectation. After normalising that fixture only, the clean
complete rerun passed **1,101 tests in 1,762.37 seconds**. Twenty focused M064/M065 guard and
freeze tests also pass together in 0.27 seconds.

## Scope

M065 does not make the compiler, block structure, task families or evidence endogenous. It
supports only the same bounded completion claim as M064, now with a non-tautological rollback
falsifier and a non-replayable canonical first-result path. It grants no repository, network,
credential, deployment or production authority.

## Remaining gates

1. pass all focused M065 guard/freeze tests and the complete repository suite;
2. qualify the exact frozen parent on Python 3.11 and 3.13 without rerun;
3. merge a first-history marker-only commit bound to that parent;
4. preserve the first result and byte-identical independent reproduction;
5. publish the bounded final verdict.
