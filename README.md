# Mira Genesis

Mira Genesis est un projet expérimental consacré à la **métamorphose cognitive trans-substrat** : séparer une compétence de son corps computationnel, la transporter, la réincarner dans un substrat dont la sémantique est inconnue, et y préserver sa capacité à continuer d'apprendre.

Objectif à long terme : un organisme qui apprend dans un corps A, découvre seul les règles d'un substrat B inédit, s'y construit un corps, y transfère compétence, mémoire et plasticité, puis apprend une tâche nouvelle plus vite qu'un organisme vierge — sans qu'un humain redessine son architecture.

## État actuel

| | |
|---|---|
| Dernière expérience validée | **M013e** — migration scellée vers un substrat opaque, domaine fini |
| Dernier échec canonique | **M014b** — plasticité transportable sans avantage d'apprentissage généralisable |
| Expérience arrêtée | **M014c** — jamais évaluée ; elle mesurait un catalogue fermé |
| Expérience active | **M017** — langage auto-extensible, branche `research/m017-self-extending-language` |
| Domaine validé | automates finis déterministes sur alphabet binaire, 4 à 10 états |
| Substrats validés | machines booléennes opaques : opcodes sans sémantique déclarée, tables de vérité découvertes par sondage |

Les résultats constituent un laboratoire de recherche borné. Ils ne démontrent ni AGI, ni conscience, ni auto-amélioration ouverte. Les affirmations reposant sur M001–M011 ne sont **pas vérifiables dans ce dépôt** : voir [`archives/README.md`](archives/README.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pytest -q
```

Vérifier en plus l'intégrité structurelle du dépôt :

```bash
python scripts/check_repository_integrity.py
```

## Organisation

- `metamorphosis/` — noyau expérimental, un préfixe de module par expérience (`m012b_*`, `m013e_*`, `m014b_*`)
- `scripts/` — exécutions de développement, évaluations canoniques, audits d'isolation, garde-fous
- `experiments/<ID>/` — protocole figé, protocole lisible et statut de chaque expérience
- `results/<ID>.md` et `results/<ID>_raw/` — résultats canoniques et preuves brutes
- `tests/` — tests de développement, exécutés par la CI sur chaque PR
- `archives/` — index des retraits de code et workflows scellés consommés
- `.github/workflows/ci.yml` — la seule CI permanente

## Règle scientifique

Une expérience reçoit exactement l'un de ces statuts : `VALIDATED`, `FAILED` ou `INCONCLUSIVE`.

1. Le protocole est figé et haché avant toute observation de résultat.
2. L'évaluation canonique s'exécute une fois, en CI, sur un commit immuable.
3. Aucun rerun ne remplace une première tentative, aucun seuil n'est assoupli après coup.
4. Les échecs et contaminations sont conservés, jamais supprimés.

Voir [`PROJECT_STATE.md`](PROJECT_STATE.md), [`ROADMAP.md`](ROADMAP.md), [`FAILURE_LOG.md`](FAILURE_LOG.md) et [`DECISIONS.md`](DECISIONS.md).
