# M115 route-selection decision

**Status:** owner-authorized pre-freeze decision, 28 August 2026. No M115 qualifying invocation or carrier bank exists at this point.

M113 and M114 remain closed. Their literal model-identity checks are not edited, reinterpreted or repaired.

## What changed for the successor contract

The preserved DEVELOPMENT matrix requested the dated alias `deepseek/deepseek-v4-flash-0731`. For 12 providers OpenRouter returned the same alias as the served model while its router metadata identified the selected endpoint as the canonical checkpoint `deepseek/deepseek-v4-flash-20260731`. Every predecessor runtime check held except literal equality between those two different names. PR #229 therefore preserved two separate facts rather than normalising strings: `selected_endpoint_exact=false` and `canonical_checkpoint_match=true`.

The owner has now authorized M115/H60 to accept **only that explicitly attested alias -> canonical-checkpoint relation** as the successor identity rule. Unknown aliases, pattern-derived dates, suffix stripping and mutable `latest` aliases remain inadmissible.

This change is prospective. It applies to M115 only.

## Provider selection

The provider is not hand-picked after viewing the matrix. Before the first DEVELOPMENT matrix was executed, `generator-route-development-recommendation-v1` committed the following reliability ordering:

1. 1-day uptime descending;
2. 30-minute uptime descending;
3. p50 latency ascending;
4. stable provider name ascending.

On 28 August 2026 the owner adopted that already-written ordering as the M115 milestone route-selection rule. This adoption happened **after** the DEVELOPMENT matrix was visible, and that temporal fact is recorded rather than hidden; however, the ordering itself is unchanged from the pre-measurement source and no H58/H59/H60 carrier result existed or was observed.

Recomputing eligibility under the new canonical-checkpoint identity boundary and applying the preserved ordering selects **Alibaba**.

Preserved DEVELOPMENT measurements for the selected route:

- 1-day uptime: `99.98945871422205`
- 30-minute uptime: `99.98797932443804`
- p50 latency: `1214`
- catalogue quantization: `unknown`

Quantization and BYOK were explicitly not ranking inputs. The selected route's quantization is therefore recorded as unknown rather than upgraded by inference.

## Scientific boundary

This decision changes no carrier rule, qualification rule, closure rule, scoring rule, delivery retry rule, `P22` computation or generality gate. The carrier-blind scientific target remains the target M113 and M114 never reached because their instruments aborted before bank materialization.

The route decision is not a positive result. H60 remains untested until a frozen M115 instrument materializes a bank and the preregistered downstream sequence is executed.
