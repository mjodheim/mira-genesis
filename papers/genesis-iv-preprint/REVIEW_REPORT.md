# Genesis IV hostile-review report

Date: 2026-09-23

Status: internal AI-assisted adversarial review; not independent peer review.

## Verdict

Proceed to preprint with a deliberately narrow central claim: **bounded recursive process improvement across two successive lineage transitions**.

## Main attacks and resolutions

1. **It only stops earlier.** Correct. The real-organism wins are evaluation-efficiency wins after promotion and quality tie. The paper does not call this recursive quality uplift.

2. **G2 hard-codes a threshold.** Partly correct. The >=780 stopping threshold is development-adapted. V19's fresh 24-world holdout tests generalization, but V20 still uses one real A016 state.

3. **G1 did not literally write G2.** Correct literally. An external LLM is the mutation operator. The paper uses lineage-mediated/system-level self-modification.

4. **Temporary Chat isolation is not attestable.** Correct. It is an operator-procedural control.

5. **The hidden evaluator has been queried repeatedly.** Correct external-validity concern. The claim is restricted to one fixed evaluator epoch.

6. **V20 is asymmetric.** Correct by design. The frozen utility rewards lower observation cost only after higher-priority outcomes tie.

7. **There is only one real terminal state.** Correct. No population-level generalization claim is made.

8. **GitHub run IDs are not random beacons.** Correct. The manuscript says prospectively unavailable/run-ID-derived seed.

9. **L3-P is project-defined.** Correct. The paper defines it explicitly and does not present it as a field-wide standard.

10. **V19 could be another replay overfit.** The fresh 24-world one-shot holdout is the direct test; G2 wins all 24. This still does not establish transfer outside that generator.

## Residual work only an external reviewer can close

- independent rerun of the full experiment;
- independent assessment of novelty;
- evaluation of L3-P against alternative RSI taxonomies;
- replication under a new organism/evaluator family.
