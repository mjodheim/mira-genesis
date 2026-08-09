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

### Resolution of the M020 negative-constant defect

Repaired by making the reader, not the writer, treat a `-<int>` expression as one constant
target. `_negative_int_literal` is now consulted by both `_TargetCollector` and
`_IndexedNodeTransformer`, so a patch replaces the whole negation instead of the literal
nested inside it.

Constant patches are idempotent for every sign, the AST no longer grows under repeated
negative patches, the effective behaviour no longer alternates, and a body whose outputs
leave the declared state range is now rejected by the reachability evaluator rather than
silently accepted.

The repair moves all four recorded M033 digests, because `ConstantRewriteTool.propose`
filters on `value != current` and previously read a negative constant as positive. Every
search in the construction stack was therefore carrying phantom candidates that could only
stack negations. Removing them lowers candidate medians by 3 to 7 per cent.

**No finding changed.** All paired outcomes reproduce identically across the two kernel
generations. The generation-1 artifacts are kept and scoped rather than re-run, per D015.

`tests/test_m020_negative_constant_defect.py`, which pinned the defective behaviour so a
fix could not land unnoticed, has been retired and replaced by
`tests/test_m020_negative_constant_round_trip.py`, which guards the repair.

## M017 — The confirmation is complete only inside the language it confirms

Found while writing the sealed generator that §10 of the frozen protocol requires before
hashing. Not found by the test suite, the isolation audit or the six development gates.

### The observation

On an out-of-language negative control derived from a head the development bench had never
used, the self-extending organism announced `program_identified`. The target has 7 states,
the source 6, the announced solution 6. The solution is not equivalent: the two are
separated by `(0, 0, 1, 0, 0, 0)`.

That is two §7 falsifiers at once — a false success, and a missed abstention on a negative
control — and it leaves §3.2 unmet.

### The cause

`_confirm` states its own completeness bound: the structural language does not create
states, so a target cannot have more states than the source. The W-method suite is built
against that bound and is complete for every target *inside* the language.

`make_out_of_language_target` is defined by adding a state. The control therefore sits
outside the bound by construction, and §3.2 asks the organism to reject targets its own
confirmation cannot see.

| Confirmation bound | Suite | Detects the mismatch |
|---|---:|---|
| source states (current) | 34 words | no |
| source states + 1 | 69 words | yes |

### Why development passed

Gate 5 was declared passed on **two** out-of-language controls, both of which abstain. An
independent sweep of 24 controls yields **2 false successes**, an escape rate near 8 per
cent. Two clean controls occur about 85 per cent of the time. The bench was not unlucky; it
was too small to see the escape.

This is the third time the same shape appears in M017. The first was a probabilistic
confirmation drawing 96 long words while claiming to cover the distinguishing bound. The
second was the W-method applied to an unminimised hypothesis. Both were announced correct
and both produced a false success. D010 exists because of this failure mode, and it
recurred inside the experiment that was about to be frozen against it.

### Consequence

The freeze is blocked. Gate 5 is re-opened. Raising the bound to `source + 1` restores
detection at roughly double the suite, but it also changes query cost, which §2 measures —
so the bound is a protocol parameter that must be signed with the thresholds rather than
adjusted after an observation.

Pinned by `tests/test_m017_confirmation_bound.py`, which reproduces the case from a fixed
head and records that the development controls do not expose it.

## M035 — a selector was named for a mechanism it did not implement

Found by external review of the M037 pull request, not by the test suite, the integrity
audit or any experiment control. All of them passed over it.

### What was claimed

`minimal_criterion_survivors` was documented as a minimal criterion — "keep everyone above
a bar, not the best few" — and justified by M021's measurement, which scored the minimal
criterion at 750 per mille against 416 for novelty, 312 for quality-diversity and 0 for the
direct objective.

M037's own report then asserted that "a minimal criterion admits or rejects; it does not
rank".

### What the code did

```
qualified.sort(key=lambda pair: (-score, structural_cost, digest))
return [org for org, _ in qualified[:capacity]]
```

It admitted on a threshold, then ranked the admitted by descending agreement, preferred
the smaller body on a tie, and truncated. **The documentation asserted the opposite of the
implementation**, in the same file that criticised elitist truncation.

Adding deduplication in M037 did not remove this: the distinct bodies were still ordered
by `(-score, structural_cost, digest)`.

### What M021 actually measured

`rank_by_minimal_criterion` in `m021_measures.py` filters on viability
(`ledger.solved > 0`), ranks the viable by **novelty**, ranks the rejected by energy, and
lets `Population.select` truncate. Its 750 per mille belongs to *viability, then novelty,
then truncation*, and its report already warns it is not a claim about the general family.

M035 implemented none of that. The citation was not merely imprecise: it attributed a
figure to a mechanism that was never run.

### A second dependency the review also caught

Deduplication kept whichever organism the loop met first for each body digest. Two
organisms can share a body and differ in ancestry, generation and mutation counts, so
permuting the population changed the surviving *lineage* while leaving the surviving
*bodies* identical. The invariant test written alongside compared digests only, and passed
while the defect was present.

### Consequence

Three selectors are now named apart. `thresholded_elitist_truncation` keeps M035's
historical 6/12. `viability_then_novelty` keeps M021's 750 per mille. The corrected rule,
`population_floor_admission_with_body_diversity`, inherits neither and has not been
measured on a sealed block.

The threshold is also named for what it is: the current population's minimum, recomputed
each generation, able to fall. A comment claiming it "rises only when the whole population
clears it" was false; no previous threshold was ever stored.

This is the same methodological shape as M014b, M017's confirmation bound and M033's
degenerate controls: the mechanism held, and the description of it did not.

## M048 — two qualification runs failed before the migration qualified

The M048 qualification history is append-only. Neither failing commit was rerun; each was
corrected in a new commit, and both negative verdicts remain part of the record.

### First verdict — run `31046715149`, number 402, commit `616f316`

`FAILED`. Repository integrity and the M048 checkpoint path exposed two defects together:
an orphan import, and a schema mismatch between `causal_journal` and `native_journal`. The
migration code could write a journal entry that the native reader could not interpret.

### Second verdict — run `31054844770`, number 403, commit `839883d`

`FAILED` again after the schema correction. The suite now reached the checkpoint contract
and exposed a missing public `combined_digest` field. The first correction was real and
incomplete: fixing the schema simply let the tests advance far enough to find the next
defect.

### Resolution — run `31061450556`, number 404, commit `0dfd822`

`PASSED` on the pinned Node.js 20 target runtime across the Python 3.11 and 3.13 matrix,
with repository integrity and no rerun.

### Lesson

The two failures are the causal history that localised the defects *before* qualification,
not noise to be discarded once the third run went green. A qualification suite that only
ever reports its final state cannot show that it was the checkpoint contract, and not the
migration semantics, that was wrong the second time.

## M050 — the declared grammar and the positive fixture disagreed

### Verdict — run `31083479890`, number 410, commit `3bc3b50`

`FAILED` in both Python matrices while repository integrity passed. Five M050 tests failed
because the positive fixture required both the `absolute` and `unique` input primitives,
while the frozen three-stage grammar permits exactly one input primitive.

### What was corrected, and what was not

The correction changed only the public and hidden probes. It added no primitive, did not
enlarge the search budget, did not weaken validation and did not rerun the failing commit.
Run `31087299169`, number 413, commit `c75e9e70`, then passed with 822 tests on each
Python version.

### Lesson

The defect was in the experiment's own fixture, not in the mechanism under test. The
temptation in that situation is to widen the grammar until the fixture passes, which would
have silently changed what M050 claims. Fixing the probe instead keeps the frozen grammar
as the object of study.

## M053 — a CI failure that carries no scientific information

### What happened

The first CI attempt on the M053 pull request, run `31118366409`, failed during *Set up
job* with `Failed to resolve action download info. Error: Service Unavailable` while
resolving GitHub Actions downloads. `Tests (Python 3.11)` never started. `Repository
integrity` and `Tests (Python 3.13)` were cancelled in cascade, and the companion
`Attribution policy` run `31118366475` was cancelled with them.

### Why it is recorded here but is not a negative verdict

No M053 code executed. The run reports the availability of GitHub's action registry, not
anything about endogenous language extension. Recording it as a preserved negative
qualification verdict would put a fact about a third-party service into the causal history
of the experiment, and would later read as evidence that the construction had been tested
and found wanting.

The distinction has to be drawn explicitly, because the append-only rule that makes M048
and M050 trustworthy also makes it tempting to append everything. An append-only history is
only useful if each entry states what was actually observed.

M053 therefore remains `PROPOSED — UNQUALIFIED`, with zero qualification attempts that
reached a verdict.

## M048 — the replay claim holds only inside one process

Found while making a successor experiment's manifest reproducible, not by the test suite, the
integrity audit or the qualifying CI run. All of them passed over it.

### What was claimed

`experiments/M048/PROTOCOL.md` §Replay requires the run to "reproduce the exact final native
state digest". `experiments/M048/DEVELOPMENT_RESULT.md` recorded "exact artifact replay of
migration, accepted learning, rollback and terminal evidence", unqualified.

### What holds

Two runs of `run_m048_native_runtime_migration` in the same environment produce different
`final_state_digest` and different `post_migration_checkpoint`. The manifest is not
byte-identical across processes.

The manifest's own `replay_identical` field is not false. It compares two runs inside a single
process, where the volatile value is constant. The claim in the prose is what over-reaches.

### Mechanism

`metamorphosis/m048_native_lineage.py` computes

    validation_digest = _digest(b"m048-native-validation-v1\x00", selection)

over the mapping returned by `_validate`, and that mapping carries `worker_pid` — the pid of
the disposable Node validation process. The pid changes per process, so `validation_digest`
changes, and the change propagates into the patch registry record, the native journal, the
causal memory and the final state digest.

Neutralising `worker_pid` alone restores full manifest reproducibility. It is the sole cause,
and the defect is therefore bounded and identifiable.

### Why it survived two corrections aimed at it

The M048 development history contains `M048: remove volatile process identity from manifest`
and `M048: keep manifest identity deterministic across runtime processes`. Both removed the pid
from the manifest's top level. Neither removed it from the value the manifest's digests are
derived from, so the visible field disappeared while the dependency remained.

### Blast radius

No recorded value is invalidated. No literal M048 state digest appears in its result, its
protocol or the project registers; only commit SHAs are cited. `_native_body_digest` reproduces
exactly across processes, so the accepted body keeps a stable identity. The migration, the
preserved capabilities, the post-migration learning and the rollback are unchanged.

### Lesson

This is M014c recurring, and the repository already knew the shape: `PROJECT_STATE.yaml`
records `immediate_replay_byte_identical_within_each_runtime` separately from
`separately_archived_cross_runtime_manifest_comparison` for M044 and M046. M048 was written
without that distinction, and the distinction is exactly what it needed.

An identity that is computed over a mapping should be computed over the fields that carry
meaning, not over whatever the producer happened to return. `worker_pid` is evidence that a
disposable process ran; it is not part of what was decided.

### Resolution

`_decided` now removes the environmental fields from a validation selection before it is
digested. The manifest is byte-identical across processes, verified by a permanent test that
spawns a separate interpreter and compares. Recorded as D018.

Exactly two fields move: `final_state_digest` and `post_migration_checkpoint`. Thirty-nine are
unchanged, including every scientific outcome — retained-capability passes, tool reuse after
migration, the adopted version, the selected template, the forced-fault restoration, the
terminal action and the replay flag. **No finding changed**, and that is pinned by a test that
runs the lineage under both digest rules and asserts the moved set is exactly those two fields.

Following D015, M048 artifacts now belong to a digest generation, and the qualifying run
`31061450556` is not re-executed. It exercised the science; the science is untouched.

## M061 — the manifest asserted what the builder contradicted

Found by an external review of PR #90, reading the manifest against the code it describes. Not
found by the sixteen permanent tests, the repository-integrity audit or the green CI run on the
experiment commit. All of them passed over it.

### What was claimed

`m061_discovered_structure.py` recorded two fields:

    "copy_loop_uses_only_discovered_instructions": True,
    "structural_instructions_authored": False,

`experiments/M061/DEVELOPMENT_RESULT.md` said the copy loop was built "from discovered
instructions alone", and its protocol's anti-cheating clause forbade the loop using "an
instruction the scans did not recover".

### What held

`build_copy_loop` took three opcodes from the resolution and wrote seven in by hand:

| Written in | Byte |
|---|---|
| `block` | `0x02` |
| `loop` | `0x03` |
| `br` | `0x0c` |
| `local.set` | `0x21` |
| `i32.le_s` | `0x4d` |
| `i32.add` | `0x6a` |
| `i32.sub` | `0x6b` |

The loop computed correctly and recovered its phrase. The measurement of *how* it was built was
false.

### Mechanism

The scans resolved five instructions. The loop needed twelve. The gap was filled at the point of
emission, in a byte literal inside a `bytes([...])` call, where no resolver and no test looked.
The manifest field was a constant written a few lines below the builder that contradicted it.

The tests asserted `value["copy_loop_uses_only_discovered_instructions"] is True`, which is true
whenever the constant is `True`. See **D020**.

### What the correction found

`i32.le_s` is `0x4c`. The hand-written loop had `0x4d`, the **unsigned** comparison. Nothing
caught it because the loop counter never goes negative, so the two opcodes agree on every value
the loop ever produces. M060's emitter had it right; the defect was local to M061.

The scan that replaced the literal named `0x4c` from behaviour and contradicted the author. A
latent defect in the authored code was found by the procedure built to reproduce it.

### Blast radius

No other recorded value is invalidated. M060's authored instruction set is unaffected and was
independently correct. The copy loop's computed output — the recovered phrase — was always
genuine; only the provenance claim was false.

The false manifest reached `main` in merge `1c7cceb`, because the correction was pushed after
PR #90 merged. It is corrected by PR #91.

### Resolution

Six of the seven are now discovered, through three additional scaffolds scanned in a second
stage that bootstraps on the first stage's integer scan. `block` and `loop` remain authored and
are named in `copy_loop_authored_elements`, at the same level as what was found. The boolean
reads `False`. The protocol's anti-cheating clause now names this failure mode explicitly.

### Lesson

The experiment whose subject was honesty about what a scan found shipped a false statement about
what a scan found, and its own falsifiers were arranged so that they could not notice. Writing
about rigour is not the same as being subject to it. **D020** states the rule this produced.

## M062 — the first region scaffold could not transport its witness value

Found by `test_a_branch_makes_block_and_loop_observably_different` before the complete M062
development lineage ran.

### Defect

The candidate opener was followed by the empty blocktype `0x40`. The branch placed `7` on the
stack and targeted depth zero; code after the region then attempted to add one. An empty-result
region cannot transport `7`, so WebAssembly correctly refused the `0x02` witness. The scan would
therefore have reported no exit-region candidate if its witness guard had not stopped it.

### Resolution

The region probe now declares the `i32` result blocktype `0x7f`. The exit-region branch transports
`7` and returns `8`; the repeat region restarts and does not terminate. The blocktype is explicitly
listed in M062's presupposed floor because it is authored. The resolver was not loosened.

### Status

Instrument defect found before the full development result, not a scientific verdict and not a
qualification attempt. The failing permanent test remains the regression guard.

## M064 — a fixture guessed two intermediate module sizes

The first complete four-bank whole-WebAssembly test invocation finished every scientific run and
emitted all four manifests. Nineteen tests passed. One assertion expected the three selected
module sizes to be `1903, 1970, 2037`; the emitted modules were `1887, 1962, 2037`.

The failure was in the fixture, not the engine or decision rule: the test values had been inferred
from the final size instead of read from the completed evidence. Hidden quality, survivor counts,
imports, archive, rollback, memory and replay all passed. The assertion was corrected to the
observed identities without changing code generation, task cases, thresholds, budgets or the
protocol. A clean rerun is required before M064 may be frozen.

## M064 — frozen qualification exposed checkout-dependent hashes and a false rollback proof

Exact parent `ec92af78b57203d32c2ee504db91b4166ec83fdf` failed GitHub run
`31281234286`, attempt 1. Python 3.11 passed 1,084 tests and failed one in 1,037.15 seconds;
Python 3.13 passed 1,084 and failed one in 1,094.43 seconds. Both observed Git's LF bytes for
`m048_native_lineage.py` while the frozen commitment named the Windows CRLF checkout bytes.
Integrity and attribution passed. No canonical marker was created.

The same pull request review found three defects before arming: the marker could be updated and
run again, a workflow rerun could recreate the first artifact, and the rollback receipt compared
the untouched `before` copy to its own previously calculated bytes and digest. The first two are
governance defects. The third invalidates the claimed rollback falsifier and, under D023, requires
M065. M064 remains preserved as a negative pre-canonical qualification.

During the M065 portability correction, two focused fixture invocations and the first complete
rerun still computed temporary M064/M065 source expectations from raw CRLF bytes. The scientific
M065 tests all passed; the complete run reached 1,100 passes and one fixture failure. Each fixture
was changed only to hash LF-normalised temporary bytes. The final complete rerun passed 1,101 tests
in 1,762.37 seconds.
