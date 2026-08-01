# M017 — Statut

- Protocole : **BROUILLON DE DÉVELOPPEMENT**
- Résultats canoniques autorisés : **NON**
- Graines d'évaluation scellée : **aucune**
- Langage structurel séquentiel : **implémenté**
- Bibliothèque auto-extensible et règle d'abstraction : **implémentées**
- Réincarnation sur substrat opaque : **implémentée**, 9/9 exactes
- Tests de développement : **11 passants**, dans une suite de 30
- Statut scientifique : `DEVELOPMENT — LANGUAGE GROWTH BENCHMARKING`

## Portes de gel

| # | Porte | État |
|---|---|---|
| 1 | Désigner la comparaison décisive avant toute nouvelle observation | **franchie** — [`PRE_REGISTRATION_DRAFT.md`](PRE_REGISTRATION_DRAFT.md) |
| 2 | Établir que la marge dépasse la dispersion entre environnements | **franchie** — appariée : 95× à 620×, seuil proposé 10× |
| 3 | Justifier budget et profondeur par l'hypothèse, non par la marge produite | **franchie** — [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) |
| 4 | Transporter la bibliothèque vers un environnement aux motifs inédits | **franchie** — et elle oblige à restreindre la portée |
| 5 | Décalage brutal de distribution après absorption | **franchie** — dégradation sans faux succès |
| 6 | Audit d'isolation des sources et trace entièrement entière | **franchie** — `scripts/audit_m017_isolation.py` |

**Les six portes sont franchies**, et elles l'ont été deux fois : une première sur une
confirmation non fiable, une seconde après correction.

La confirmation tirait 96 mots longs au hasard en affirmant couvrir la borne de
distinction de deux automates. Elle ne la couvrait pas. Le « zéro faux succès sur
42 épisodes » était un tirage favorable, pas une garantie : deux automates à 9 états
confirmés identiques sont séparés par `(1,0,1,0,1,0,1)`.

`metamorphosis/conformance.py` la remplace par un test de conformité complet — méthode
W sur hypothèse minimisée, couverture de transitions, marge calculée depuis le nombre
d'états de la source. Il a fallu trois versions, dont deux annoncées correctes à tort ;
voir `FAILURE_LOG.md`.

**Les quatre mesures refaites sous cette confirmation rendent des chiffres strictement
identiques.** Le coût de recherche ne dépend pas de la confirmation ; ce qui en
dépendait, c'est la condition d'admission, désormais réellement établie.

Le protocole complet, seuils compris, est dans
[`FROZEN_PROTOCOL_017_CANDIDATE.md`](FROZEN_PROTOCOL_017_CANDIDATE.md). Il n'est **pas
figé** : le gel engage des seuils qui ne bougeront plus et ouvre une évaluation
canonique qui ne s'exécute qu'une fois. Cette signature est humaine.

## Ce que la porte n°2 a déjà appris

La première statistique décisive — deux médianes agrégées séparément — a été
**rejetée par la mesure**. Sur huit environnements l'avantage allait de 2,4× à 605×,
et le facteur de confusion a été identifié : le coût de l'organisme auto-extensible
est bimodal, environ 42 nœuds sur un motif pur, environ 1 800 lorsqu'un atome de bruit
impose la profondeur 2. La médiane basculait selon le tirage.

Appariée épisode par épisode, la même mesure donne 95× à 620× : **la dispersion est
divisée par trente-huit sans que la médiane bouge**. Le seuil proposé, 10×, est dérivé
de l'arithmétique des espaces de recherche — environ 500× attendus — et non de
l'échantillon.

La porte n°6 a de même trouvé un défaut réel : `m017_engine` importait le laboratoire.

## Coût de l'absorption, à ne pas dissimuler

Sur le pire épisode isolé, l'organisme auto-extensible est **35 % plus lent** : ses
macros gonflent le facteur de branchement sans jamais s'appliquer. Cela concerne 8
épisodes tardifs sur 49. Une garde par test de signe est préenregistrée pour qu'une
règle d'absorption dégénérée ne puisse pas passer.

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
