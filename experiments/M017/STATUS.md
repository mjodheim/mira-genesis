# M017 — Statut

- Protocole : **BROUILLON DE DÉVELOPPEMENT**
- Résultats canoniques autorisés : **NON**
- Graines d'évaluation scellée : **aucune**
- Langage structurel séquentiel : **implémenté**
- Bibliothèque auto-extensible et règle d'abstraction : **implémentées**
- Réincarnation sur substrat opaque : **implémentée**, 9/9 exactes
- Tests de développement : **10 passants**, dans une suite de 29
- Statut scientifique : `DEVELOPMENT — LANGUAGE GROWTH BENCHMARKING`

## Portes de gel

| # | Porte | État |
|---|---|---|
| 1 | Désigner la comparaison décisive avant toute nouvelle observation | **franchie** — [`PRE_REGISTRATION_DRAFT.md`](PRE_REGISTRATION_DRAFT.md) |
| 2 | Établir que la marge dépasse la dispersion entre environnements | en cours — `scripts/run_m017_dispersion.py` |
| 3 | Justifier budget et profondeur par l'hypothèse, non par la marge produite | à faire |
| 4 | Transporter la bibliothèque vers un environnement scellé aux motifs inédits | à faire |
| 5 | Contrôles négatifs adverses et changement brutal de distribution | à faire |
| 6 | Audit d'isolation des sources et trace entièrement entière | à faire |

Aucune pull request canonique ne peut être ouverte avant que ces portes soient
franchies. Voir [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md).

## Risque à ne pas perdre de vue

Le banc de développement montre un effondrement du coût de recherche d'un facteur
cent. La tentation sera de figer un seuil contre le **catalogue fermé**, qui échoue
0/42 : ce critère passerait trivialement et ne mesurerait rien d'autre que le fait,
déjà connu, qu'un catalogue de douze programmes n'exprime pas une trajectoire de trois
atomes.

La comparaison qui porte l'hypothèse est l'auto-extensible **contre la recherche
ouverte**, sur la décroissance du coût au fil des épisodes — deux organismes de
capacité identique au premier épisode, que seule l'absorption sépare ensuite.

C'est la faute exacte de M014b, en sens inverse : un seuil calé sur une baseline qui
ne mesure pas ce que l'expérience prétend établir.
