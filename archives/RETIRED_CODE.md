# Code retiré de l'arbre de travail

Principe : un enregistrement scientifique n'est jamais supprimé, mais le code d'une
expérience révoquée n'a pas à rester dans l'arbre de travail. L'historique Git est
l'archive ; ce fichier est l'index qui rend le retrait traçable.

## Retrait R001 — pile héritée M012 / M013b

- Date : 31 juillet 2026
- Dernier commit contenant ces fichiers : `26c86711714c7c09cd4881acb13231b146f48498`
- Récupération : `git show 26c8671:<chemin>`

| Fichier retiré | Lignes | Raison |
|---|---|---|
| `metamorphosis/core.py` | 483 | Pile DFA + extracteur L\* héritée, remplacée par `m012b_dfa.py` ; seule source d'import de `torch` |
| `metamorphosis/morphogenesis.py` | 684 | Synthétiseur hérité, remplacé par `m012b_basis/_body/_expr/_primitives` |
| `metamorphosis/unknown_substrate.py` | 302 | Migration M013b, remplacée par `m013e_runtime.py` et `m013e_engine.py` |
| `metamorphosis/opaque_machine_lab.py` | 184 | Banc de machines opaques M013b, remplacé par `m013e_lab.py` |
| `scripts/run_m012_development.py` | 54 | Expérience M012, statut `INCONCLUSIVE — CONTAMINATED` |
| `scripts/run_m012_evaluation.py` | 303 | Expérience M012, statut `INCONCLUSIVE — CONTAMINATED` |
| `scripts/run_m013b_evaluation.py` | 199 | Expérience M013b, statut `INCONCLUSIVE — CONTAMINATED` |
| `tests/test_morphogenesis.py` | 138 | Ne couvrait que la pile héritée |
| `tests/test_unknown_substrate.py` | 71 | Ne couvrait que la pile héritée |
| `metamorphosis/m013e.py` | 13 | Façade de ré-export sans consommateur ; M014b et M014c importent directement `m013e_engine`, `m013e_lab` et `m013e_runtime` |

Total : environ 2 400 lignes, soit près de 30 % du dépôt.

### Justification

1. Aucun module vivant (`m012b_*`, `m013e_*`, `m014b_*`, `m014c_*`) n'importait cette pile.
   Le graphe d'imports formait un sous-graphe entièrement disjoint.
2. Les seules expériences qui l'utilisaient sont M012 et M013b, toutes deux classées
   `INCONCLUSIVE — CONTAMINATED`, sans résultat revendiqué.
3. `metamorphosis/core.py` importait `torch`, ce qui faisait échouer la collecte de
   `pytest -q` — la commande documentée dans le README et dans `docs/REPRODUCIBILITY.md` —
   sur toute installation ne disposant pas de PyTorch.

### Chaîne de preuve préservée

Les enregistrements scientifiques restent intacts et ne sont pas modifiés :

- `FAILURE_LOG.md` — contaminations M012 et M013 / M013b ;
- `results/M012.md`, `results/M012_raw/`, `results/M013b.json`, `results/M013b.md` ;
- `experiments/M012/`, `experiments/M013/`, `experiments/M013b/`.

`results/M012.md` cite `tests/test_morphogenesis.py` comme preuve de la contamination par
graines d'évaluation. Ce fichier reste consultable à `git show 26c8671:tests/test_morphogenesis.py`.

## Retrait R002 — workflows d'évaluation scellée terminés

- Date : 31 juillet 2026
- Dernier commit contenant ces fichiers : `26c86711714c7c09cd4881acb13231b146f48498`
- Copie lisible conservée dans `archives/workflows/`

| Workflow retiré de `.github/workflows/` | Raison |
|---|---|
| `m012b-sealed-evaluation.yml` | Run canonique consommé ; la branche déclencheuse `research/m012b-sealed-morphogenesis` n'existe plus |
| `m013e-sealed-evaluation.yml` | Run canonique consommé ; branche déclencheuse supprimée |
| `m014b-sealed-evaluation.yml` | Run canonique consommé ; branche déclencheuse supprimée |
| `validate-m013b.yml` | Marqueur `workflow_dispatch` sans effet, remplacé par `FAILURE_LOG.md` |

Ces trois workflows scellés étaient conditionnés par `github.head_ref`. Comme leurs branches
sont supprimées, ils ne pouvaient plus s'exécuter : ils ajoutaient trois vérifications
`skipped` à chaque pull request, sans jamais rien évaluer.

La règle « un seul run canonique, jamais rejoué » implique qu'un workflow scellé consommé
ne doit plus être exécutable. Sa valeur est documentaire, pas opérationnelle : les copies
de `archives/workflows/` conservent la recette exacte, et la preuve reste attachée aux runs
GitHub Actions et aux hashes d'artefacts publiés dans `results/`.

## Retrait R003 — workflows de jalons restés exécutables

- Date : 23 août 2026
- Retrait réalisé dans : PR #187 (historique Git de la réorganisation)
- Copies exactes conservées dans `archives/workflows/`
- Total : 25 workflows retirés de la surface GitHub Actions active

### M017 à M066

Dix-neuf workflows de développement ou canoniques appartenant aux jalons M017, M019,
M021, M022, M026–M033, M042 et M064–M066 restaient sous `.github/workflows/` alors que
leurs jalons étaient historiques. Leur contenu a été déplacé byte-for-byte dans
`archives/workflows/` : la recette reste lisible et versionnée mais n'est plus une
surface d'exécution permanente.

### M092

Les six workflows M092 (`adoption-qualification-rehearsal`, `canonical-search`,
`canonical-transport-rehearsal`, `independent-reproduction`,
`reproduction-transport-rehearsal` et `runtime-envelope`) ont également été archivés.
Le registre public classe M092 `Aborted without verdict`; conserver ses workflows armés dans
GitHub Actions ne représentait donc plus l'état scientifique actuel.

Après R003, `.github/workflows/` ne contient plus que l'intégration continue permanente et
la politique d'attribution. Le cycle de vie est désormais documenté dans
`docs/REPOSITORY_ARCHITECTURE.md` et vérifié par `scripts/audit_repository_layout.py`.

## Retrait R004 — Dockerfile sans entrée d'exécution supportée

- Date : 23 août 2026
- Retrait réalisé dans : PR #187 (le fichier reste consultable dans l'historique Git)
- Fichier retiré : `Dockerfile`

Le Dockerfile installait le paquet puis déclarait `ENTRYPOINT ["mira-run"]`. La configuration
`pyproject.toml` actuelle n'installe aucune commande `mira-run`, et `mira_core/agent.py` expose
la bibliothèque `MiraAgent` sans fonction CLI `main`. L'image construite ne disposait donc pas
de l'exécutable qu'elle annonçait comme point d'entrée.

Le fichier copiait en outre `scripts/` et `experiments/` dans une image présentée comme runtime,
ce qui mélangeait sans contrat explicite code réutilisable et matériel de recherche. Aucune
commande Docker supportée n'est documentée dans le README actuel.

Plutôt que de maintenir une image qui se construit mais ne démarre pas correctement, le Dockerfile
est retiré. Si un conteneur runtime redevient un produit supporté, il devra être réintroduit avec
une CLI réellement définie, un smoke test d'image et une frontière explicite entre runtime et
matériel scientifique.
