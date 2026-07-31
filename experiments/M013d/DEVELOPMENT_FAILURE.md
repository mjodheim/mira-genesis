# M013d — Development failure

Fixed development nonce: `00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff`.

Observed development results:

- Genesis: 36/36 exact principal migrations;
- oracle ceiling: 36/36;
- no-probe fixed-role baseline: 12/36;
- random-semantics baseline: 0/36;
- negative controls: 12/12 abstentions;
- failed criterion: `no_probe_baseline_at_most_8_of_36`.

Interpretation: with only three machines, one fixed opaque ordering happened to align with a usable assumed basis. The absolute threshold was therefore too sensitive to small-sample machine permutations. M013e requires a substantial margin over the strongest zero-information baseline instead of an absolute baseline score.
