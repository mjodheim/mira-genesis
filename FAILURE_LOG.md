# Journal des échecs et corrections

## M004 — Échec partiel

- La preuve exhaustive avait été comptée dans le budget d’expérience de Genesis.
- Certaines restructurations composées étaient fonctionnellement équivalentes à une mutation simple.
- Correction : séparation stricte organisme/évaluateur et protocole M005.

## M012 — Évaluation contaminée

- Plusieurs graines déclarées réservées à l’évaluation apparaissaient dans les tests.
- Statut : `INCONCLUSIVE — CONTAMINATED`.
- Correction : M012b avec cas générés seulement après création du SHA immuable.

## M013 / M013b — Contaminations successives

- Des passeports, machines ou contrôles réservés avaient été exécutés pendant le développement.
- Statut : `INCONCLUSIVE — CONTAMINATED`.

## M013c — Commit de reproduction incomplet

- Le commit annoncé ne contenait pas son protocole figé.
- Statut : `INCONCLUSIVE — NON REPRODUCIBLE AT ANNOUNCED COMMIT`.

## M013d — Échec du critère de baseline en développement

- Aucun run canonique scellé n’a été ouvert.
- Le contrôle non canonique donnait 36/36 migrations exactes à Genesis.
- La baseline fixe sans sondage obtenait 12/36, au-dessus du maximum préenregistré de 8/36.
- Statut : `FAILED — DEVELOPMENT BASELINE CRITERION`.
- Correction : M013e utilise un avantage relatif préenregistré sur la meilleure baseline sans information.

## M014 — Arrêt préventif

- Le protocole initial a été stoppé avant évaluation lorsque ses prérequis ont été révoqués.
- Statut : `HALTED — NEVER EVALUATED`.
- Remplacement : M014b.

## M014b — Plasticité transportable sans avantage généralisable

- Première évaluation canonique : run `30650363802`, tentative 1, SHA `5a0947afb96d7d59438c222028f2cabb34bc0cd5`.
- La chaîne technique a réussi 36/36 fois : migration de l’ancienne compétence, transport du passeport, identification, consolidation, nouvelle morphogenèse et archive intacte.
- Genesis utilisait 14 requêtes médianes d’identification.
- L* depuis zéro utilisait également 14 requêtes médianes.
- Les baselines aléatoire et sans passeport appris utilisaient chacune 17 requêtes médianes.
- Deux critères figés ont échoué : avantage de 25 % sur L* et avantage de 20 % sur les deux baselines locales.
- Statut : `FAILED — PORTABILITY WITHOUT GENERALIZABLE LEARNING ADVANTAGE`.
- Aucun rerun et aucun assouplissement de seuil ne remplacent ce résultat.

### Leçon scientifique

Le développement avait appris un langage de transformations et un prior utiles sur ses propres distributions, mais cet avantage ne s’est pas maintenu sur la distribution scellée. La portabilité structurelle d’une politique n’implique pas la portabilité de son efficacité.

### Défaut de traçabilité découvert

- La reproduction retrouve tous les résultats scientifiques.
- `consolidation_record_sha256` diffère entre environnements parce qu’il inclut des scores flottants dans la trace.
- Correction obligatoire pour M014c : décisions et hashes fondés sur des nombres quantifiés, entiers ou rationnels canoniques.

### Remplacement

M014c devra apprendre à travers plusieurs distributions, détecter le décalage, adapter son prior sous budget et être comparé au passeport statique M014b en plus des baselines précédentes.

## M014c — Arrêt avant évaluation

- Statut : `HALTED — SUPERSEDED BY M017`. Aucune évaluation canonique n'a été ouverte
  et aucun résultat n'est revendiqué.
- Branche préservée : `research/m014c-distribution-general-plasticity`, tête `fc46005`.
- L'implémentation fonctionnait, les tests passaient, la CI était verte. Le défaut
  était dans ce qui était mesuré.
- `MetaPlasticitySession.identify` énumère strictement `passport.programs` — douze
  programmes structurels écrits à la main. L'adaptation en ligne se réduit à
  repondérer des compteurs de groupe sur ce catalogue fermé.
- Le banc affichait `active_to_scratch_ratio = 0,083`, lisible comme un gain de quinze
  fois. C'est un effet de taille d'automate : L\* paye un coût qui croît avec l'automate,
  Genesis un coût qui croît avec sa bibliothèque de douze entrées. Agrandir les
  automates aurait gonflé le ratio sans rien changer à ce qui avait été appris.
- La comparaison qui portait l'hypothèse était `active_to_static_ratio = 0,88` : douze
  pour cent, sur une fenêtre large de quatre requêtes.
- **C'est la géométrie exacte de l'échec de M014b.** Figer M014c contre L\* aurait
  passé trivialement et répété l'erreur en sens inverse.

### Leçon scientifique

Un catalogue fermé rend indécidable toute expérience sur l'apprentissage : la fenêtre
mesurable est bornée par la taille du catalogue, pas par la capacité de l'organisme.
Voir D009 et D010.

### Remplacement

M017 — langage auto-extensible. Le vocabulaire de départ ne contient que des atomes ;
tout ce qui dépasse l'atome doit être construit, et ce qui est construit peut être
absorbé.

## M017 — Confirmation non fiable, découverte en développement

- Statut : `DEVELOPMENT DEFECT — CORRECTED BEFORE ANY FREEZE`.
- Aucune évaluation canonique n'avait été ouverte. Le défaut est corrigé avant le gel,
  et non découvert après un run irremplaçable.

### Le défaut

La confirmation d'un candidat portait sur tous les mots jusqu'à la longueur 6, plus
**96 mots tirés au hasard** entre 7 et 20. La docstring affirmait que ces mots longs
couvraient la borne de distinction de deux automates.

C'était faux. Quatre-vingt-seize tirages ne couvrent pas 2⁷+…+2²⁰. La garantie était
probabiliste et faible.

### Ce que ça invalide

Le banc de développement M017 rapportait **zéro faux succès sur 42 épisodes**. Ce
n'était pas une garantie mais un tirage favorable. Un balayage plus large, mené pendant
le développement de M018, a produit deux automates à 9 états confirmés identiques que
le mot `(1,0,1,0,1,0,1)` sépare — un mot absent des deux jeux.

**Conséquence :** tous les chiffres de développement M017 — banc principal, dispersion,
transport — avaient été produits sous cette confirmation. Ils ne sont pas
nécessairement faux, mais ils n'étaient plus établis, et ont dû être remesurés.

### La correction, en deux temps

`metamorphosis/conformance.py` : test de conformité par **méthode W**. Pour une
hypothèse minimale à k états et une cible d'au plus k+s états, la suite
`P · (ε ∪ Σ ∪ … ∪ Σˢ) · W` est complète — l'accord sur la suite implique l'équivalence.

**La première correction a échoué, et de la même façon que le défaut d'origine.** Elle
construisait la suite depuis le candidat brut de la recherche, non minimisé, avec une
marge fixée arbitrairement à deux états. Or la méthode W exige une hypothèse minimale :
`characterizing_set` cherchait à séparer des paires d'états équivalents, échouait
silencieusement, et l'ensemble ne caractérisait plus rien. Un second faux succès a
survécu, à l'environnement 6 de l'étude de dispersion.

La version retenue minimise l'hypothèse au lieu de la supposer minimale, et **calcule**
la marge au lieu de la choisir : le langage structurel ne crée aucun état, donc la
cible ne peut pas en compter plus que la source, borne que l'organisme connaît
puisqu'il détient la source.

Le coût ne diverge pas : la suite croît en `|Σ|ˢ · k²`, or `s` décroît quand `k` croît.
Sur un automate à 9 états la suite compte **99 mots contre 160** au jeu probabiliste.
L'ancienne confirmation était donc à la fois plus chère et moins sûre.

### Trois corrections, dont deux fausses

Il a fallu trois versions pour obtenir une confirmation complète, et les deux premières
ont été annoncées comme correctes avant de l'être.

1. **Marge fixe sur hypothèse non minimisée.** Un second faux succès a survécu, à
   l'environnement 6 de l'étude de dispersion.
2. **Couverture d'états au lieu de couverture de transitions.** Pire que le défaut
   d'origine : **10 faux succès sur 73**, avec des témoins de longueur 6 que le jeu
   probabiliste attrapait. La méthode W part d'une couverture de transitions
   `S·(Σ∪{ε})` ; sans elle les transitions sortantes ne sont jamais exercées, et les
   atomes de ce langage sont majoritairement des redirections.
3. **Version retenue** : hypothèse minimisée, couverture de transitions, marge calculée
   depuis le nombre d'états de la source.

Le test censé garder cette propriété n'inversait que des bits d'acceptation et
n'exerçait **aucune redirection** — c'est précisément pourquoi il passait sur une suite
cassée. Réécrit pour engendrer ses différences avec le jeu d'atomes réel, il échoue sur
la version 2 en manquant 14 différences sur 151.

**Conséquence de calendrier :** chaque mesure lancée entre ces versions a tourné sous
une confirmation défectueuse, y compris une remesure du banc M017 annoncée « identique »
qui ne comptait donc pas. Toutes les mesures de M017 et de M018 ont été refaites sous
la version 3.

### Ce que le défaut menaçait, et ce qu'il ne menaçait pas

Distinction à ne pas perdre : **le coût de recherche ne dépend pas de la confirmation**.
Le nombre de programmes évalués est arrêté par le filtre d'empreinte ; seule la facture
d'oracle change quand la confirmation change. Le résultat de tête de M017 —
l'effondrement du coût de 4 222 à 43 nœuds — n'était donc jamais en jeu.

Ce qui l'était, c'est la condition d'admission « zéro faux succès », qui décide si
l'expérience compte pour quelque chose. Une expérience qui mesure bien un coût tout en
acceptant des solutions fausses ne mesure rien.

**Les quatre mesures réexécutées sous la version 3 rendent des chiffres strictement
identiques** :

- banc : 0/34/37 résolus, 4 222 → 43 nœuds médians, 24 macros, 9/9 réincarnations
  exactes, 4/4 abstentions, 0 faux succès ;
- dispersion : rapport apparié 95,32× à 620,14×, médiane 377,20×, 8/8 environnements
  favorables ;
- transport : 0,69× hors distribution, 4/4 paires pénalisées, 118,7× à motifs partagés ;
- M018 : mesuré directement sous la version 3.

Sur ces épisodes, le premier candidat passant le filtre était toujours le bon, ce qui
explique que le coût soit inchangé. Le résultat tient — et il tient désormais parce que
la procédure est complète.

### Leçon

Une condition d'admission n'est pas établie parce qu'un banc la rapporte satisfaite.
Elle l'est quand la procédure qui la vérifie est **complète**. M017 rapportait
« 0 faux succès » avec une procédure incapable de le garantir — ce qui est
exactement le genre d'affirmation que la discipline du dépôt existe pour empêcher.

Que la remesure redonne les mêmes chiffres ne réhabilite pas l'ancienne procédure. Un
résultat juste obtenu par une méthode qui ne peut pas le garantir reste un résultat non
établi ; c'est la distinction que M014b avait déjà payée, et elle se répète ici sur la
vérification plutôt que sur la mesure.

## M018 — Détruire ne restaure pas l'amélioration

- Statut : `DEVELOPMENT — HYPOTHESIS NOT SUPPORTED`. Aucune évaluation canonique.
- La prédiction était écrite avant la mesure. Sa seconde moitié tient, la première —
  celle qui portait l'hypothèse — est fausse.

Trois mécanismes de destruction, référence = l'organisme de M017 qui n'oublie jamais :

| | stable | décalage | transport |
|---|---|---|---|
| `budget` | identique | +3 % | +6 % |
| `utility` | jusqu'à 177× pire | +2 % | +4 % |
| `dissolution` | **350× pire** | −18 % | 0 % |

Aucun n'annule le passif de 0,69× mesuré par M017.

### Pourquoi

1. **L'oubli est réactif.** Un symbole inutile est payé d'avance, à chaque épisode, sur
   chaque nœud. Quand l'organisme sait qu'un macro ne sert pas, il l'a déjà financé ;
   jeter ensuite ne rembourse rien.
2. **La destruction est indiscriminée.** La dissolution ne distingue pas ce qui a cessé
   de servir de ce qui va resservir, et paye 350× cette ignorance.
3. **Le coût d'un macro inutile est réel mais modeste** — le branchement passe de 36 à
   48 symboles et les recherches s'arrêtent souvent tôt.

### Deux lectures, et la seconde ouvre M019

Le résultat ne dit pas que détruire est inutile. Il dit que **détruire est intenable
pour un individu isolé** : la chenille se dissout une fois, et si cela échoue, cette
chenille meurt — pas l'espèce.

Et il désigne une cause plus profonde : le budget de recherche valait 200 000 nœuds et
l'échec ne coûtait rien. **Il n'y avait rien pour quoi être efficace.** C'est ce que
M019 met à l'épreuve.

## M019 — Montage invalide, cause structurelle identifiée

- Statut : `DEVELOPMENT — RIG NOT VALID`. Aucune évaluation canonique, aucune
  conclusion tirée sur l'hypothèse H8.

Trois calibrages, trois dégénérescences, aucune porte de gel franchie :

| Calibrage | Résultat | Morts |
|---|---|---|
| prime 25 000 | énergie doublée, `none` 8/8 | 0 |
| prime 6 000 | profondeur de recherche → 2, macros → 0 | 0 |
| prime 6 000 + report d'énergie | profondeur → 2, macros → 0 | 0 |

Population : 11 épisodes résolus. Contrôle sans sélection : **103**, 18 macros.

### La cause

**Une sélection à horizon court ne peut pas valoriser un investissement dont le
rendement est différé.** Apprendre coûte ~23 000 nœuds pour une prime de 6 000 ; ne pas
essayer coûte 1 296. À la première sélection, l'apprenti est éliminé avant d'avoir pu
rembourser. Le report d'énergie n'y change rien puisqu'il suppose que l'investisseur
survive à cette première coupe.

La sélection a découvert que ne pas essayer coûte moins cher qu'essayer — et elle avait
raison sur l'horizon qu'on lui avait donné.

### Un garde-fou mal choisi

« Mortalité non nulle » signalait mal. Zéro mort n'indiquait pas une rareté trop faible
mais l'inverse : elle mordait assez pour que la stratégie gagnante soit de ne rien
dépenser. Le bon garde-fou était le nombre de macros — nul dans les trois essais.

### Pourquoi l'arrêt

Un quatrième calibrage aurait été de l'ajustement jusqu'à obtenir la réponse voulue.
Trois essais et un invariant nommé suffisent à conclure que **le montage est faux**, non
que l'hypothèse est réfutée.

### Leçon

Une pression de sélection mal formée sélectionne la stagnation. Trop faible, elle ne
trie rien ; trop impatiente, elle élimine l'exploration avant qu'elle ne rapporte.
**L'horizon d'évaluation compte davantage que l'intensité de la pression.**

C'est le piège de M014b sous une autre forme : un critère qui mesure la mauvaise chose
ne devient pas juste en changeant ses seuils.

## M026 — Observed clade guidance did not reveal latent clade value

- Status: `DEVELOPMENT — HYPOTHESIS NOT SUPPORTED`. No canonical evaluation.
- The prediction and 64-seed decision rule were committed before the full run.

The finite positive control contains an exact reversal: the platform scores 0 now but
can reach 6/6 hidden cases; a shortcut scores 1 now but can reach at most 3/6. Despite
that known mismatch, the HGM-inspired clade policy did not beat the DGM-inspired
immediate policy: median paired difference 0 per mille, 4 wins, 59 ties and 1 loss.

The aligned control passed for every reachable state, all selector boundaries excluded
hidden fields, and a full replay was byte-identical. The failure is therefore retained
as a result, not tuned away. Observed clade aggregation cannot value descendants that
the expansion process has not yet exposed. This does not test full HGM because M026
holds its adaptive evaluation scheduler, asynchronous execution and final-selection
rule out of scope.

## M027 — Breadth coverage did not turn a clade mean into a clade maximum

- Status: `DEVELOPMENT — HYPOTHESIS NOT SUPPORTED`. No canonical evaluation.
- The coverage intervention and estimator/policy gates were committed before the full
  run.

Every reachable state through the first reward-bearing depth was present before parent
selection. The hidden signal was therefore observable in all 64 mismatch seeds. Even
so, the clade estimator remained -907 per mille concordant with exact CMP, improved on
immediate performance by only 93 per mille, and produced 64/64 final-quality ties at
zero between HGM-inspired and DGM-inspired guidance.

The failure is not insufficient breadth. Equal evaluation of every clade node estimates
an average dominated by proxy-successful shortcuts, whereas exact CMP is determined by
the rare maximum-quality generic lineage. Full HGM's adaptive evaluation weighting was
deliberately excluded, so the result identifies that mechanism as the next separable
question rather than making a claim about full HGM.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante.

## Principe permanent

Un échec ou une révocation n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.

## M028 — Adaptive evaluation weighted the wrong evidence

- Status: `DEVELOPMENT — HYPOTHESIS NOT SUPPORTED`. No canonical evaluation.
- The unique-task schedule and all six decision gates were committed before the
  64-seed run at `334eec2`.

Adaptive evaluation changed the search but did not support the prediction. Its median
weighted-clade/exact-CMP concordance was -478 per mille, only 40 above uniform and below
the 167-per-mille gate. Median final hidden advantage was zero: 2 wins, 60 ties and 2
losses. Coverage, unique-task, selector-isolation and aligned controls all passed, and
the complete replay was byte-identical.

The diagnostic identifies the mechanism. Individual-performance Thompson sampling
used the same visible development proxy that rewards shortcut lineages. It allocated
34 per mille of non-initial evaluations to high-potential observed nodes, compared with
51 per mille under uniform allocation. Unequal evidence did not soften a mean toward
the hidden maximum; it concentrated confidence on the proxy's preferred descendants.

This is not a failure of adaptive allocation in general or a test of full HGM. It shows
that changing weights without changing the information that produces them cannot
repair this measured proxy reversal. Any successor must justify a distinct routing
signal before observing its full result.

## M029 — Component evidence aligned; adaptive policy gates still failed

- Status: `DEVELOPMENT — ESTIMATOR ALIGNED WITHOUT POLICY ADVANTAGE`.
- The probe definition and complete decision rule were committed before the 64-seed
  run at `7c3eaa2`.

The component suite was exactly disjoint from development and hidden suites and turned
median clade/exact-CMP concordance from -478 to 699 per mille. The full registered
prediction still failed. High-potential allocation shifted by 92 rather than 167 per
mille; paired median final hidden advantage was zero; component adaptive produced
31 wins, 32 ties and 1 loss rather than the required 40 wins.

The pre-declared component-uniform diagnostic was stronger: 50 wins, 14 ties and no
losses against development adaptive. It cannot be promoted to a confirmed result on
the same observed seeds.

Post-hoc diagnostics localise the remaining mismatch. Component-adaptive search made a
median 31 expansions from shortcut-containing parents versus 28 under component
uniform, and only 8 from pure generic parents versus 12. It reached a median maximum
generic count of 3 rather than 4. Component probes detect reusable motifs even in
lineages that have already consumed too much depth on shortcuts.

The next correction must remain separate: confirm uniform component guidance on
untouched seeds, or pre-write a resource-viability signal. Reclassifying the observed
diagnostic as M029's primary result would violate the repository's decision discipline.

### M030 resolution of the diagnostic boundary

M030 chose the first correction without changing either policy implementation. On the
untouched seed block 64–127, component-uniform guidance reproduced with 48 wins,
16 ties and no losses, +1,000 per mille median paired final hidden quality and 662 per
mille clade/exact-CMP concordance. Every pre-written gate passed and the replay was
byte-identical.

This confirms that M029's component information effect was not a favourable draw on
seeds 0–63. It does not reverse M029's failed adaptive-policy verdict: uniform
observation and adaptive concentration remain empirically different interventions.

### M031 resolution of the structural-transport boundary

M031 changed the task generator rather than drawing another same-structure seed block.
Length-three cyclic/permuted triads and two independent scaffolds replaced length-two
pair reversals and one platform. The frozen component-uniform contrast passed every
gate with 737 per mille concordance, +500 per mille median paired hidden quality and a
43/18/3 split. The replay was byte-identical.

This resolves the finite structural-transport question without erasing M029's failure.
The remaining optimisation problem is still resource viability under non-uniform
allocation, not whether the component information exists in these two generators.

## M020 — A negative constant does not survive the patch round trip

Found while attempting to demonstrate Gate 9 (repeated improvement cycles), not by a
failing test. The rewrite kernel has carried this since M020 and every experiment built
on it inherits the defect: M023, M024, M025, M032 and M033.

### Mechanism

`_IndexedNodeTransformer.visit_Constant` writes `ast.Constant(-2)`. `ast.unparse` renders
that as `-2`, and re-parsing `-2` yields `UnaryOp(USub, Constant(2))`, because Python has
no negative integer literal. Every later patch at that index then sees a *positive*
constant nested inside a negation and wraps another one around it.

### Consequences

- a constant patch is **not idempotent** for negative values: applying `constant[0] = -2`
  twice yields `--2`, which evaluates to `+2`;
- the AST grows without bound under repeated negative patches — five applications produce
  `-----2`;
- the effective behaviour alternates between two different functions on successive
  applications;
- the search can reach bodies whose outputs leave the declared state range, such as a
  next-state of `-1` in a two-state machine.

`ConstantRewriteTool.values` includes `-2` and `-1`, so the defective path is inside the
search space of every experiment in the construction stack.

### Blast radius

No recorded result is contaminated. Across the fixed, structural, combined and
body-anchored M033 calibration artifacts, **776 of 776 adopted sources contain no negative
constant**, and all four recorded digests reproduce exactly. The defect is latent in those
runs, not expressed.

It was expressed in the Gate 9 exploration that found it. Both candidate reuse lineages
depended on stacked negations, so that demonstration is **withdrawn** rather than reported
as a Gate 9 result.

### Why this is not fixed in the same change

Correcting `apply_patch` changes which candidate sources are reachable, and therefore may
move recorded calibration digests. Under D003 and the repository's replay discipline, that
is a protocol-owner decision, not a repair to slip into an unrelated commit. The defect is
pinned by `tests/test_m020_negative_constant_defect.py`, which asserts the current
behaviour so that a fix cannot land silently.

### Consequence for Gate 9

Gate 9 remains undemonstrated. The exhaustive finite check found 4 candidate reuse
lineages out of 195 cycle-1/cycle-2 pairs, all of which relied on the defect. Whether
Gate 9's reuse clause is satisfiable on a corrected kernel is now an open question, and it
must be re-run after the fix rather than assumed.
