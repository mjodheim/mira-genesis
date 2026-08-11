# Private R&D operating procedure

**Effective from 12 August 2026 for prospective M086+ core work.**

This procedure operationalises [`IP_PUBLICATION_POLICY.md`](IP_PUBLICATION_POLICY.md). It is meant
to reduce accidental disclosure while keeping the historical public scientific record intact. It is
not a legal opinion and does not guarantee patentability or trade-secret status.

## 1. Separate repository/workspace

Do not develop materially new M086+ enabling core mechanisms on a branch of the public
`mjodheim/mira-genesis` repository. A branch of a public repository is public.

Use a genuinely private repository or a non-public local workspace for private R&D. A practical
layout is:

- `mjodheim/mira-genesis` — public historical/scientific repository through M085 and later
  deliberately published material;
- a separately created private repository such as `mjodheim/mira-genesis-rnd` — unpublished core
  R&D, private invention/disclosure ledger and private experimental branches.

The private repository name should not itself disclose a confidential mechanism.

## 2. Safe bootstrap from the public baseline

When a private GitHub repository has been created, a local bootstrap can start from the current
public baseline while disabling accidental pushes back to the public remote:

```sh
git clone git@github.com:mjodheim/mira-genesis.git mira-genesis-rnd
cd mira-genesis-rnd
git remote rename origin public
git remote set-url --push public DISABLED

git remote add private git@github.com:mjodheim/mira-genesis-rnd.git
git config remote.pushDefault private
git push -u private main
```

The `DISABLED` push URL is a guard against an accidental `git push public`; it is not a security
boundary by itself. Confirm the target repository is private before pushing unpublished work.

After bootstrapping, replace the public-repository agent instructions with private-workspace
instructions that preserve scientific/provenance rules but permit approved private M086+ work. Do not
merge those private instructions back to the public repository unless they reveal nothing enabling.

## 3. Access control

For unpublished R&D:

- keep repository visibility private;
- grant access only to the project owner and services/tools actually needed for development;
- review GitHub App/OAuth access before granting a coding service access to the private repository;
- do not create public forks, public Actions artifacts, public gists or public paste links from private
  source;
- do not copy unpublished task banks or confidential external-maintainer material into the public
  repository;
- keep credentials out of Git and use the repository/service secret store where needed;
- retain enough access/provenance history to support later diligence.

If secrecy is intended to carry commercial value, access-control evidence should be preserved rather
than relying only on a file saying `confidential`.

## 4. AI-provider data controls

Private Git hosting does not make prompts sent to an AI service private by itself. Before sending
material unpublished R&D to Codex, ChatGPT or Claude, check the data controls and contract for the
actual product/account in use.

### OpenAI / Codex

At the 12 August 2026 snapshot, OpenAI states that content from individual services such as ChatGPT
and Codex may be used to train models unless the user opts out. OpenAI documents a ChatGPT account
control named **Improve the model for everyone** and states that opting out applies to new ChatGPT
conversations; OpenAI also documents separate Codex controls for allowing training on full
environments.

For unpublished M086+ R&D on a personal account:

- turn off **Improve the model for everyone** before starting the private work;
- review Codex Settings and disable any separate full-environment training/data-sharing option for the
  private workspace;
- avoid submitting feedback on confidential sessions unless the implications have been reviewed,
  because provider feedback can carry the associated conversation into improvement workflows;
- re-check these controls after material product/account changes.

OpenAI states that its Business, Enterprise, Edu and API offerings are not used for model training by
default. If private R&D becomes commercially significant, a business/API arrangement may therefore
provide a clearer contractual/data-handling boundary than relying only on consumer controls, subject
to the exact agreement actually purchased.

References checked at this snapshot:

- <https://help.openai.com/en/articles/5722486-api-data-usage-policies>
- <https://help.openai.com/en/articles/7730893-data-controls-faq>
- <https://openai.com/business-data/>

### Anthropic / Claude / Claude Code

At the 12 August 2026 snapshot, Anthropic states for consumer Claude Free/Pro/Max products, including
Claude Code used with those accounts, that chats/coding sessions can be used to improve Claude when
the user chooses to allow it, with separate safety-review and explicit-feedback/opt-in cases.
Anthropic states that its commercial offerings do not use inputs/outputs for model training by
default unless the customer explicitly opts in or provides covered feedback/material.

For unpublished M086+ R&D:

- do not enable consumer chat/coding-session model-improvement sharing for the private work;
- avoid feedback submissions that would intentionally send a confidential coding session for
  provider improvement;
- if using Claude Code with an API/commercial organisation, preserve the exact organisation/product
  terms and data-retention configuration used for the material work;
- re-check settings and terms when changing Claude plan, organisation or authentication method.

References checked at this snapshot:

- <https://privacy.anthropic.com/en/articles/10023580-is-my-data-used-for-model-training>
- <https://privacy.anthropic.com/en/articles/7996868-is-my-data-used-for-model-training>

These provider settings reduce disclosure/training risk but do not by themselves establish legal
trade-secret status, patent novelty, copyrightability or freedom to operate.

## 5. Private scientific record

Private does not mean scientifically ungoverned. For each material private experiment:

- freeze the protocol/thresholds before observing the result when the claim requires precommitment;
- keep append-only result/failure records;
- preserve Track A / Track B attribution;
- preserve exact source commit, environment/runtime identity and dependency lock evidence;
- record negative and inconclusive results rather than silently deleting them;
- checkpoint/rollback claims must remain non-tautological and independently evaluable;
- do not call project-authored or project-controlled AI material "independent" evidence.

A private scientific record may later be published, but publication must not rewrite its chronology.

## 6. Private invention/disclosure ledger

Before materially implementing or externally sharing a new enabling mechanism, create a private
entry derived from the public `IP_ASSET_REGISTER.md` with at least:

- asset ID and short non-enabling description;
- date/commit of first material conception/implementation;
- human problem formulation and conception notes;
- AI tools/products/accounts materially involved;
- third-party code/data/model dependencies;
- people/services with access;
- any external disclosure and date;
- intended disposition: patent-first, trade-secret/private, commercial-private, restricted
  publication or public research;
- publication/filing decision and supporting evidence.

Do not put the enabling private ledger entry into the public repository before the publication
classification permits it.

## 7. Public hand-back rule

Nothing from private M086+ work returns to `mjodheim/mira-genesis` merely because it works.
Before a public push/PR:

1. identify exactly what code, protocol, result or description would be disclosed;
2. update the private invention/disclosure record;
3. review third-party and AI-assisted provenance;
4. decide patent/trade-secret/commercial/public treatment;
5. record an explicit publication decision;
6. only then prepare a clean public branch containing the authorised disclosure.

Never merge the private repository wholesale into the public one.

## 8. Commercial/acquisition snapshot

For a future investor, licensee or acquirer, preserve a data-room snapshot containing at least:

- public/private commit boundaries;
- contributor and AI-assistance provenance;
- private repository access history;
- invention/disclosure ledger;
- exact provider terms/account class used for material AI-assisted R&D;
- release-specific SBOM/licence reports;
- trademark/patent filings or documented decisions;
- commercial licences/contracts and encumbrances, if any;
- reproducible scientific evidence and its relationship to proprietary implementation.

This procedure is deliberately stricter than normal hobby-project practice because a future buyer
values a clean explanation of **what is public, what is controlled, who had access, and why the
controlled asset was not accidentally disclosed**.
