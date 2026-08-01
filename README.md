# Mira Genesis

**Quand une mesure-proxy cesse-t-elle de suivre ce qu'elle prétend suivre, et sous
quelle pression d'optimisation ?** Mira Genesis pose cette question dans un domaine où
la vérité terrain est **décidable**, donc où la réponse se prouve au lieu de s'estimer.

## Comment le projet en est arrivé là

Le dépôt a d'abord été consacré à la **métamorphose cognitive trans-substrat** :
séparer une compétence de son corps computationnel, la transporter, la réincarner dans
un substrat dont la sémantique est inconnue, et y préserver sa plasticité. Cette ligne
a produit deux validations scellées — M012b et M013e — puis quatre échecs.

Aucun de ces quatre échecs n'était dans l'organisme.

| | Ce qui a cassé |
|---|---|
| M014b | seuil de 25 % sur une fenêtre large de 4 requêtes |
| M017 | seuil de 10× dérivé d'un cas typique pris pour une borne |
| M018 | aucune conséquence à l'inefficacité, donc rien à optimiser |
| M019 | horizon de fitness plus court que la période de remboursement |

Quatre fois, ce qu'on construisait tenait ; c'est la façon de juger si c'était mieux
qui a cédé. Le projet suit désormais ce que ses propres échecs ont désigné.

## Ce que ce dépôt apporte, et ce qu'il n'invente pas

Le problème n'est ni neuf ni vierge : la loi de Goodhart, le *reward hacking*, le
*specification gaming*, la recherche de nouveauté et les algorithmes qualité-diversité
le travaillent depuis longtemps, avec des réponses partielles.

Mais ces travaux opèrent presque tous là où **l'objectif vrai n'est pas vérifiable
exactement**. Un *reward hacking* se diagnostique parce qu'un humain trouve que le
résultat a l'air faux ; la nouveauté s'évalue à ce qui paraît intéressant ; les
descripteurs comportementaux sont choisis à la main.

Ici, l'équivalence comportementale de deux automates finis se **prouve**. On peut donc
montrer *où exactement* une mesure décroche, au lieu de constater qu'un résultat semble
faux. C'est un banc d'essai pour la conception de mesures — pas une tentative de
résoudre ce que d'autres n'ont pas résolu.

Le catalogue est dans [`MEASURES.md`](MEASURES.md), et chaque cas se rejoue :

```bash
python scripts/reproduce_measure_failures.py
```

## État actuel

| | |
|---|---|
| Validations scellées | **M012b** morphogenèse autonome, **M013e** migration vers substrat opaque |
| Prêt à figer | **M017** — langage auto-extensible, critère devenu directionnel |
| Non soutenu | **M018** — détruire ne restaure pas l'amélioration |
| Montage invalide | **M019** — sélection trop impatiente pour valoriser l'apprentissage |
| Domaine | automates finis déterministes, alphabet binaire, 4 à 10 états |
| Substrats | machines booléennes opaques : opcodes sans sémantique déclarée, découverts par sondage |

Laboratoire de recherche borné. Ne démontre ni AGI, ni conscience, ni auto-amélioration
ouverte. Les affirmations reposant sur M001–M011 ne sont **pas vérifiables dans ce
dépôt** : voir [`archives/README.md`](archives/README.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pytest -q
```

Vérifications structurelles :

```bash
python scripts/check_repository_integrity.py
```

```bash
python scripts/audit_m017_isolation.py
```

## Organisation

- `MEASURES.md` — catalogue des mesures qui ont divergé, avec vérité terrain
- `FAILURE_LOG.md` — échecs et contaminations, jamais supprimés
- `metamorphosis/` — noyau expérimental, un préfixe de module par expérience
- `scripts/` — bancs de développement, évaluations canoniques, audits, garde-fous
- `experiments/<ID>/` — protocole figé, protocole lisible et statut de chaque expérience
- `results/<ID>.md` et `results/<ID>_raw/` — résultats canoniques et preuves brutes
- `tests/` — tests de développement, exécutés par la CI sur chaque PR
- `archives/` — index des retraits de code, workflows scellés consommés, tags d'archive
- `.github/workflows/ci.yml` — la seule CI permanente

## Règle scientifique

Une expérience reçoit exactement l'un de ces statuts : `VALIDATED`, `FAILED` ou
`INCONCLUSIVE`.

1. Le protocole est figé et haché avant toute observation de résultat.
2. L'évaluation canonique s'exécute une fois, en CI, sur un commit immuable.
3. Aucun rerun ne remplace une première tentative, aucun seuil n'est assoupli après coup.
4. Les échecs et contaminations sont conservés, jamais supprimés.

Voir [`PROJECT_STATE.md`](PROJECT_STATE.md), [`ROADMAP.md`](ROADMAP.md),
[`MEASURES.md`](MEASURES.md), [`FAILURE_LOG.md`](FAILURE_LOG.md) et
[`DECISIONS.md`](DECISIONS.md).
