# Genesis IV reproducibility

## Evidence repository

The scientific evidence is in mjodheim/mira on research/genesis-dream-replay.

The publication package does not regenerate hidden organism observations. It verifies preserved one-shot records.

## V19/V20 independent audit

The post-result audit script experiment/free_metamorphosis/v20/reproduce_l3p_audit.py reconstructs the V19 holdout from its frozen seed construction, reloads exact G1/G2 policy sources, recomputes replay reports, reconstructs A016 policy decisions, rereads immutable V20 physical results, and recomputes terminal utilities.

The successful audit records:

- holdout 24 / 0 / 0 wins/losses/ties;
- mean core delta +75.25;
- mean represented-request delta -1.0416666666666665;
- G1 A016 parents v8-node-015-913198e1c00a and v8-node-014-2334b1dcc01a;
- G2 A016 parents: none;
- V20 utilities G1=(0,0,-2), G2=(0,0,0).

## V15 direct cross-check

A separate post-result cross-check rereads all six immutable V15 physical observation records and verifies:

- both G0/G1 round-one public projections match pairwise;
- G0 round-two results are neutral at quality 953;
- G0 terminal utility is (0,0,-4);
- G1 terminal utility is (0,0,-2).

A later wrapper intended to combine the whole chain in one GitHub Actions job failed before runner assignment on the observed reruns. It is not represented as a successful scientific execution. The successful V19/V20 audit and separately recorded V15 cross-check are the publication evidence.

## One-shot boundaries

Do not redraw a completed holdout seed and call it the same experiment.

Do not regenerate V20 hidden-evaluator observations. The preserved lab records are canonical.

## External replication

There is no independent external replication. Public-artifact reproduction by the same project is not peer review.
