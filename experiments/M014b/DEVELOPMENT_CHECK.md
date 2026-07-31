# M014b — Development check

Status: **development only, not scientific evidence**.

GitHub Actions run: `30640903561`.

- tests: 7 passed;
- exact principal chains: 36/36;
- per opaque machine: 12/12, 12/12, 12/12;
- median active identification calls: 16;
- median independent confirmation calls: 31;
- median total update calls: 47;
- maximum total update calls: 60;
- random-policy successes: 12/12, median identification 28;
- no-learned-passport successes: 12/12, median identification 26;
- scratch L* successes: 12/12, median membership queries 32.5;
- correct negative abstentions: 12/12;
- serialized plasticity passport: 715 bytes;
- learned schema prior: acceptance flip 0.5, transition redirect 1/3, combined local edit 1/6.

These measurements were used only to pre-register realistic M014b thresholds. No canonical nonce or evaluation seed existed during this run. The canonical result must come exclusively from the first PR-opened sealed workflow attempt after the protocol and runner are frozen.
