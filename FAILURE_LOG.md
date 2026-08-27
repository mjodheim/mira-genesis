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

## M065 — all-ref marker history blocked the canonical run before selection

Exact M065 parent `b1489d7a3a264de8a9e783eb139dafe28732b040` passed qualification run
`31286019961`, attempt 1. The marker-only commit
`a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57` then triggered canonical workflow run
`31287477458`, attempt 1. Guard job `93178824313` failed with “marker is not its first and only
path-history occurrence”. The first-result and independent-reproduction jobs were skipped. No bank
was selected and no artifact was created.

The frozen workflow used `git rev-list --all` after a depth-zero checkout. GitHub's clone contained
both the squash-merged `main` marker commit and the pull-request branch commit that introduced the
same path. The guard treated this lateral ref as canonical history and counted two occurrences,
although `main` contained exactly one.

The run is preserved as M065's negative canonical guard qualification and is not rerun. D025
requires canonical identity to follow `git rev-list --first-parent HEAD`. M066 applies only that
governance correction and changes no scientific engine, bank, budget, threshold, arm or rule.

During M066 development, an initial local test command was terminated by the terminal's 120-second
command timeout before pytest emitted a verdict. It was rerun with a suitable development-only
window; the final strengthened campaign passed all eleven tests in 202.78 seconds. This local process timeout created no canonical
observation and changed no frozen input.

## M070 — external Unicode and process-tree transport failed before task completion

M070 froze exact agent design `41ebe791605f55e7a44df8f0939d730139cf219a`, then blindly
selected two Terminal-Bench 2 tasks from a pinned 89-task inventory. Both official Harbor trials
completed with reward `0.0`; both `nop` controls also scored `0.0`. Harbor recorded no exception,
retry or replacement.

The frozen `CodexExecBackend` used `subprocess.run(..., text=True)` without an explicit encoding.
Python 3.14.6 selected Windows `cp1252`. A true non-breaking hyphen (`U+2011`) in a later prompt
raised `UnicodeEncodeError` in the stdin writer thread. Timeout killed the `.cmd` wrapper but not
its `node`/`codex` descendants, which retained the pipe and delayed return. After the configured
180 seconds had elapsed, only those verified orphan descendants were stopped so the existing
decision could record `ModelBackendError`; no decision was retried.

M070 therefore fails its preregistered 1/2 threshold. The result is not reclassified as an
infrastructure pass and the two selected tasks cannot become M071's fresh evidence. Explicit UTF-8
transport, whole-process-tree timeout enforcement and permanent non-ASCII/descendant regressions
are mandatory before a new freeze.

## M069 — a falsifier audited the learner's text instead of the interface (found after M071)

This defect was found by review after M069 had been qualified and merged, and after M071 closed.
The frozen evaluator imports each candidate with `exec_module` in the process that holds `TASKS`,
so every hidden case is resident in memory while candidate code runs. The policy owns `write_text`
and the public evaluator is registered with output exposed, so a candidate printing
`sys.modules["__main__"].TASKS` would have carried hidden cases back through admitted actions
alone.

M069 falsifier 10 checks that the learner's *source* does not read the evaluator implementation. It
audits the wrong object: it constrains the text that was written rather than what the interface
permits. No reported M069 falsifier established non-reachability.

The recorded rewards do not move. The frozen learner at `c603dd5` is auditable and does not exploit
the leak, so the task outcomes remain useful diagnostics. They cannot retain a positive scientific
qualification by inspection of one benign artifact: the setup failed the declared interface-level
falsifier. The distinction matters because M061 already cost this project a false manifest that its
own sixteen tests could not see.

Full record in `experiments/M069/EVALUATOR_ISOLATION_DISCLOSURE.md`. No frozen M069 artifact was
rewritten. M069 is now post-hoc disqualified as a positive development result by the evaluator-
isolation falsifier. Successor evaluators must execute candidate code in a separate process that
never holds hidden evidence.

## M074 development — live BusyBox absence code contradicted the stub expectation

The first real-container probe of the M074 development bank returned `127` for missing `python3` in
the digest-pinned Alpine image. The draft probe had declared `1` as its only absence code. The new
calibration core correctly classified `127` as `INCONCLUSIVE`, leaving that task unlabelled and
failing the bank instead of manufacturing evidence of absence.

No protocol was frozen, no model was called and no scientific result existed. The probe contract
was corrected to the live BusyBox behavior, then all six labels and the complete 12-episode dry run
passed. The failed development observation is retained here because it demonstrates why unexpected
non-zero codes must never default to `ABSENT`.

## M074 scientific — the model acted through every impossible-task budget and never refused

M074 protocol commit `28ddd8b` passed exact first CI before execution. Its single paired campaign
completed all twelve episodes with no inconclusive probe, drift, replay mismatch, backend/body
fault, retry or replacement. All six feasible arm episodes passed external evaluation and no
impossible episode did.

The performance hypothesis nevertheless failed. On all three impossible tasks, arm A emitted four
`act` decisions and zero `refuse` decisions. It searched alternative interpreters after return code
127, attempted permission or privileged fallbacks after write failures, and attempted alternate
read/chmod paths on the unreadable manifest. Both arms exhausted twelve impossible-task steps;
terminal refusal saved none. Arm A true-refusal rate and margin were both 0.0.

The current model request reports observations and recent ledger evidence but not an explicit
remaining-step budget or a task-agnostic belief that repeated failures target the same required
capability. This is a diagnosis, not a post-hoc excuse or proof of cause. M074 remains negative and
cannot be rerun. D039 requires any successor to develop explicit epistemic/budget state on a
separate bank and freeze before private independently maintained cross-domain evaluation.

## M075 development — explicit context improved stopping but missed a visible final barrier

M075 committed its public protocol before any call and completed all twelve ordered model episodes
without defect, retry, replacement or resume. The epistemic condition refused two of three
capability-absent tasks and falsely refused none, while the independent baseline refused none. It
also submitted all three feasible workspaces instead of repeating successful commands.

The remaining miss matters. On `write-receipt-readonly`, the fourth request truthfully reported
three consecutive non-zero commands, zero successful commands, a permission/immutability barrier
and one decision left. The model still attempted another write and exhausted the budget. Exact
script diversity also failed to expose that the four syntactically different commands were
effect-equivalent attempts against the same immutable workspace.

This is not a protocol defect and is not silently repaired. The public bank is contaminated and
the baseline/context samples are independent, so the aggregate improvement is diagnostic rather
than causal or scientific. D041 preserves the counterexample, closes tuning on this bank and
requires a pre-private causal-control and sealed-bank review.

## M084 rehearsal — the induction manufactured a false refusal from one-sided evidence

M084's organism learns which carriers a substrate silently discards and induces the **shortest**
prefix separating them from the carriers it has seen hold a value. Shortest rather than longest,
because the longest common prefix of two names observed in one stage carries that stage's tag and
would transfer to nothing.

The rule is unsound when only one side has been observed. With no durable carrier recorded yet, every
prefix trivially separates, so the shortest is one character: `sealed-a1` induced `s`, which also
rejects `secure-a1`. The organism then found no admissible carrier and **refused a reachable goal**
in the browser and desktop stages of the first rehearsal — a false refusal manufactured by the
induction rather than by the substrate.

Stage 0 hid it. There the organism still verifies at the end of the stage, so an affordance probe had
already supplied a durable observation before it diagnosed anything, and the predicate came out `sea`
as intended. From stage 1 onward it verifies per goal and the diagnosis arrives first. A defect that
appears only after a body transformation changes the order of events is exactly the kind that a
single-stage experiment cannot see.

Nothing was materialized. The rehearsal ran on a throwaway salt with no bank bound and no result
preserved, precisely so that the recorded run could be attempt 1. Amendment A1 makes the predicate
name the observed carriers exactly until the evidence is two-sided; A2 records a verified carrier as
durable evidence, which is what makes the evidence two-sided in the first place. No threshold, salt
or goal grammar changed.

The clause that caught it is P2, the zero-false-refusal requirement. It was written into the frozen
protocol as a control against over-eager refusal by the *substrate*; it caught over-eager refusal by
the organism's own inference instead. See D050.

## M085 wiring control — it passed while exercising none of the path it existed to exercise

The M085 shim drives M084's organism through a domain contract an outside maintainer can satisfy. A
wiring control was written alongside it, on a toy in-memory domain sharing no vocabulary with M084,
to prove the contract is satisfiable from outside before a real bank arrives.

The first version reported success: three of three reachable goals reached, the unreachable one
refused, no false refusal. It had also run **zero diagnostic probes and zero repair cycles**.

Its carrier costs were derived from a modulo of the slot index, `1 + index % 4`. That made the
discarding slot cost 4 while a durable alternative in the same group cost 1, so the cost-minimising
planner routed around the trap and never met a silently discarded write. The control was exercising
the planner and the evaluator and nothing else — not the verification, not the diagnosis, not the
repair, not the induction from a failure. Every one of those is the part M085 exists to carry into
another domain.

The costs are now stated explicitly with the discarding slot cheapest in its group, which is the
property M084's own bank was built around and which the control had quietly dropped. The control now
fails if it runs fewer than one probe and one repair cycle, and a regression asserts that the trap is
the cheapest carrier of its group.

This is the fourth entry in this series where a green result would have been hollow, after M080's
tautological rollback check, M082's harness-held browser state and M083's assumed window origin. It
is the first where the hollow thing was a *control* rather than an experiment, which is worse in one
respect: a control is what the project points at when asked whether the instrument works.

## M047 — a synthesized tool named `max` shadows the builtin its own expression needs

Found while building M086, in a module qualified since M047 and unchanged here.

`render_tool_module(tool_name, expression_id)` emits a function named after the operation and a body
using the matching Python builtin. For `tool_name='max'` and `expression_id='maximum'` it produces:

```python
def max(arguments):
    if not arguments:
        raise ValueError('tool_requires_arguments')
    return max(arguments)
```

The module-level `def max` shadows the builtin, so the call recurses into itself until the sandbox
kills it. The same shape would apply to a tool named `sum` with the `sum` expression, and to `min`
with `minimum`; none of those canonical operations exists today, so `max` is the only reachable case.

M047 never hit it: its synthesized tool was `tool_mean`, whose expression uses `sum` and `len` rather
than `mean`, and no accepted cycle ever routed `max`.

**It is not repaired.** Changing that renderer would change the source bytes of every synthesized
tool, and therefore M047's accepted body digests and its preserved result. M086 avoided the collision
instead: its routeless operation is `mean` in both limitations and never `max`, which is recorded as
amendment A2 before the bank was bound.

A successor that needs a `max` tool must fix the renderer in an experiment that re-derives M047's
digests, not in passing.

## M086 construction — a bank whose repair revealed a new fault, and a greedy tie-break that locked it in

The first M086 development limitation aliased an unknown token onto an operation that had no route.
Repairing the alias therefore moved the failure rather than removing it: the token now parsed, and
immediately failed at execution with a missing route it had previously hidden.

Worse, several candidates passed the same single case, and the cycle's tie-break took the first of
them. It chose an alias onto the wrong canonical operation — arithmetically wrong but passing the one
public case it was scored on — and the next cycle could diagnose nothing, because a wrong answer that
executes produces no error stage at all.

The arm reported no adopted meta-transformation and no solved limitation, which looked like a clean
negative for H32. It was a property of the bank.

Both limitations now pair an unparseable token whose canonical operation **already has a route** with
a separately unroutable operation, so a repair cannot reveal a new fault. Recorded as amendment A2
before the bank was bound. The lesson is the one M080, M082, M083 and the M085 wiring control each
recorded in their own way: the run completed, nothing raised, and the number meant something other
than what it appeared to mean.

## M086-A — a threshold that could not fail, and a digest bound to bytes that are not in the repository

Four defects, found by review after CI was green and after the registers had recorded a qualified
positive result. All four are confirmed at the exact head.

**The verdict tested six of ten conditions.** The frozen protocol lists P1 through P10. `evaluate()`
computes P1 through P6. P7 (causal chain), P8 (rollback), P9 (leak boundary) and P10 (differential
equivalence) never enter it. P9 and P10 are checked by the independent checker, so a reviewer running
it would see them pass — but nothing they could report would turn the verdict negative. P7 and P8 are
checked nowhere.

**P8 has no implementation.** The protocol requires a forced fault during meta-adoption and a
byte-identical restore compared against an independently recorded digest. No fault is injected, no
pre-adoption checkpoint is taken, no rollback runs. The condition was written into the protocol,
counted among the ten, and never built.

**The recorded protocol digest binds bytes that do not exist in git.** `RESULT.json` records
`c0eeeffe…`, which matches the CRLF working-tree copy of `PROTOCOL.json`. The committed blob hashes
to `49583ae9…`. This is M064's disqualifying defect returning verbatim — "the frozen hash was
checkout-dependent" — in a repository where a fix for exactly this class has been sitting on an
unmerged branch since M085.

**The holdout predated the search that must not have seen it.** `HOLDOUT_PUBLIC` and `HOLDOUT_HIDDEN`
are module-level constants in the same module and process as the meta-search, and the runner
enumerates over the holdout before any arm executes. The structural check verified that one function
does not name them, which is an argument about source text where the protocol promised an ordering.

**The replay covered 3 of 14 fields per arm.** The mechanism digests, the adopted and rejected
primitives, the adopted labels, the candidate and cycle counts and the entire causal journal were
preserved and never re-derived.

The common thread is not carelessness about the science but about the *instrument*: each defect makes
some part of the frozen contract unenforceable while leaving every visible signal green. CI passed
because the checker is not in the test suite and no regression asserted the binding, the threshold
coverage or the chronology. M086-B makes each of P1–P10 computed and decisive, implements P8 with a
real fault, separates holdout materialization into its own process and commit, and digests the whole
arm record so an omission cannot hide.

## M086-B — the bank drew a limitation no mechanism could repair

M086-B's first and only scientific attempt is negative, and the negative says nothing about H32.

The salt drew a development limitation whose routeless operation is `add`. The mechanism behaved
exactly as designed: widening the hypothesis schema diagnosed both implicated modules and generated
nine candidates, and adding composition generated twenty, including precisely the right one. Every
candidate that routes `add` is then refused by the sandbox before it executes:

```
RuntimeError: duplicate tool registration: add
```

`tool_core` already registers `add`. A synthesized `tool_add` registers it a second time and the body
is rejected. No mechanism — starting, widened, composed, or any of the ten combinations — could have
repaired that limitation, so the meta-search returned empty and five of the ten conditions failed for
one reason: there was nothing to adopt.

The defect is in the grammar. `ROUTELESS_CANDIDATES` was chosen by asking whether M047's tool
renderer had a correct *expression* for each operation — `sum` does compute `a + b` — and not whether
the tool *name* was already taken. `mean` is repairable; `add` is not; the salt chose `add`.

The bank is materialized and the result is preserved rather than redrawn. Fixing the grammar and
drawing again on the same protocol would be the result-saving retry that disqualified nothing here
only because nothing positive was claimed; it remains forbidden. A corrected grammar needs a new
protocol, a new salt and a new experiment.

Two things are worth separating. This is the **third** consecutive attempt at the meta-mechanism
question to fail for an instrument reason rather than a scientific one — M086-A's threshold could not
fail, M086-B's bank could not be repaired. But the failure modes are not equivalent: M086-A reported
*positive* while four of ten conditions sat outside the verdict, and M086-B reported *negative* with
all ten computed and a table naming exactly which failed. The corrections the disqualification
mandated did their job; they simply revealed a different defect one layer down.

There is also a smaller lesson about reasoning from availability. Both M086 banks were built by
checking that a repair *existed in principle* — an expression that computes the right value, an alias
that parses — without checking that the repair could be *installed*. The sandbox's registration rule
is not in the renderer's signature, and neither bank consulted it.

## M086-C — the mechanism generated the right candidate and then chose the wrong one

M086-C is the first attempt in this line to put H32 at genuine risk, and the hypothesis came out
unsupported. Nine of the ten
conditions passed. P2 failed.

The lineage met a limitation its mechanism could not express, rejected seven meta-transformations,
adopted `widen_hypothesis`, survived a forced fault with a byte-identical restore, and on the holdout
emitted a patch the starting mechanism could never have produced. The patch was
`synthesize_tool:mean:midpoint`, and it is wrong.

The holdout drew `mean 1 2 3` as its public case. That is an arithmetic sequence, so the midpoint and
the mean coincide at 2.0 and two candidate expressions pass the public evidence. The cycle takes the
first in the frozen expression order, which is `midpoint`. The evaluator's hidden cases —
`mean 3 4 6` and `mean 2 3 8`, where midpoint gives 4.5 and 5.0 against a true mean of 4.33 — reject
it.

The protocol named this before the run: it stated the arithmetic condition under which both
expressions pass, named `midpoint` as the one the frozen order would take, and said P2 could
therefore fail on a bank where everything else succeeded. The predicted falsifier fired.

What it exposes is not the limitation the experiment was designed around. Every meta-primitive acts
on the hypothesis schema or the rule set; none acts on the **selection rule**, the greedy
first-past-the-post over public score that decides which generated candidate is adopted. That rule is
frozen and human-authored, and it is what failed. Three attempts have now treated "the mechanism that
produces transformations" as diagnosis plus generation; this result says the pair is incomplete,
because a mechanism that generates a correct candidate and then picks a wrong one is not helped by
generating more.

Making selection mutable is a candidate successor and is not added here. It would immediately meet
the harder version of the same problem: choosing well among candidates that all fit the public
evidence requires evidence the lineage does not have, which is where M078's refusal work already sits.

## M076-M083 — the checkout-dependent hash defect recurred on a Windows clone

> **Recorded 2026-08-11 on the side-car branch `claude/dreamy-swanson-d63fc5`; merged into this log
> 2026-08-20.** The operative repair — `.gitattributes` marking the digest-bearing artifacts by
> naming convention — landed on `main` as `531a447` on 2026-08-12, but this account of *why* it was
> needed did not travel with it, and the branch was never merged. The entry below is the
> contemporaneous text from commit `9e0bff7`, unaltered. Two things were found when porting it and
> are recorded rather than silently fixed: the source commit's subject line says "M076-M084" while
> its heading says "M076-M083", and the checkers it actually names are M077 through M083; and the
> restoration itself went unrecorded in the registers for eight days.

Every independent checker from M077 through M083 failed on a fresh Windows checkout with
`protocol bytes no longer match the recorded commitment`, and the M082/M083 checkers additionally
reported that the browser and desktop image recipes had changed after their banks were bound. No
protocol, result, bank or recipe had in fact changed. `.gitattributes` marked only the M074/M075
artifacts and `results/artifacts/*.json` as `-text`, so Git applied end-of-line conversion to every
newer digest-bearing file on checkout. `git show HEAD:experiments/M083/PROTOCOL.json` hashed to the
recorded `8419f6d8...`; the CRLF working-tree copy hashed to `6479b4c2...`.

This is the same defect class that already disqualified M064, where the frozen commitment named the
Windows CRLF checkout bytes while CI observed Git's LF bytes. M064's correction normalised the
fixtures that computed hashes; it did not make the stored artifacts themselves conversion-immune,
so each experiment frozen afterwards silently reacquired a checkout-dependent hash. The recurrence
was invisible on the machine that recorded the results, because there the working-tree bytes and
the committed bytes agree.

The correction is a checkout-portability fix only. `.gitattributes` now marks the digest-bearing
artifacts by naming convention rather than by individual path, so that a later experiment adopting
the convention is covered before it freezes anything. No recorded digest, protocol content or
result content was recomputed or rewritten: the working-tree files were re-materialised from the
existing blobs and now hash to the commitments already on record.

One trap is worth recording for successors. `git add --renormalize .` is the documented repair, but
run on a tree whose files are already CRLF it stages those CRLF bytes as the new blob content under
the fresh `-text` rule — which would have rewritten every frozen digest in exactly the direction the
fix exists to prevent. The artifacts must be restored from the committed blobs instead, and the
digests verified against the recorded commitments afterwards rather than recomputed from them.

**What the eight-day gap cost, and what it did not.** Nothing in the scientific record was altered:
the affected commitments were verified *against* the recorded digests, never recomputed *from* the
restored files, so no result changed value. What was lost is auditability in the interval — a
reviewer cloning the repository between the freeze of M077 and `531a447` would have found eight
independent checkers failing, with no entry anywhere explaining that the cause was a checkout
artifact rather than a broken commitment. M086-A then reproduced the same defect class in a new
experiment during that interval. The lesson is not about EOL conversion, which is now handled by
convention; it is that a repair landed as a one-line infrastructure commit leaves no trace a
reviewer can follow, and this project's evidence is exactly the trace.

## M095 — Negative structural qualification: local satisfaction did not compose

Attempt 1 ran once on 22 August 2026 from clean commit `951c7c2`, after H40, the protocol and the
nine-entry structural population were frozen. It used zero model and network calls. All three
zero-inner-demand witnesses remained negative, but none of the six demand-bearing worlds
execution-confirmed B after A. The checker reports eight of eleven conditions passed; P3, P5 and P6
failed, and P7 replayed every entry exactly.

A was found in all six positive worlds. Its mapping satisfied the locally observed required keys but
also emitted extra keys. B embedded that complete mapping inside an exact nested contract, so every
structural survivor disagreed with the caller at execution. Status: **NEGATIVE QUALIFIED RESULT —
H40 REFUTED, NO RETRY, NO POST-VERDICT REPAIR.** See D064 and
`experiments/M095/POST_VERDICT_ANALYSIS.md`.

## M102 pre-freeze — the first owner-review candidate allowed runtime substitution

The first M102 owner-review candidate (`ce585aa2…`) recorded CPython 3.11.16 and SQLite 3.53.1, but
its builder derived those identities from whichever interpreter invoked it. The Python 3.13 CI
matrix therefore constructed a different candidate and exposed the mismatch. This was not a
qualification result: `PROTOCOL.json` did not exist, the canonical attempt was not armed, and the
qualification population had never been scientifically executed.

The builder now fails closed unless both exact canonical identities are present. The independent
boundary audit checks that both candidate and final builders enforce the gate, and a regression test
mutates the observed runtime identity. The first candidate remains in Git history as superseded;
candidate `4549f17f…` replaces it for owner review. The frozen population digest remains
`3d6785dd…` and no reroll occurred.

## M102 post-result — two pre-run lifecycle assertions rejected the preserved result

After the unique canonical result and independent positive report were committed, the first targeted
repository test run returned 47 passes and two failures. Both failing tests still asserted that
`experiments/M102/RESULT.json` did not exist. That assertion was valid only during pre-freeze
development and became false precisely because the authorized attempt had been preserved. No P1-P15
condition failed, no result or checker byte changed, and no qualification reran.

The lifecycle tests now verify the immutable attempt-1 raw/result digests and positive checker
digest, and DEVELOPMENT rehearsals snapshot both artifacts before execution and require exact bytes
afterwards. This is a post-result repository-lifecycle correction, not a repair to H47 or D071. The
first red targeted run remains disclosed here rather than being described as an initially green
post-result suite.

## M103 pre-freeze development — stable projection retained named producer PIDs

The first two non-canonical M103 development rehearsals passed P1-P14 but disagreed on their stable
evidence digests, so P15 remained false. A recursive diff isolated exactly three process-ephemera
fields: `s_prime_producer_pid`, `d_producer_pid` and `e_producer_pid`. The projection already removed
the generic `pid` and `process_pids` keys but did not apply M099's intended suffix rule to named
producer fields.

No M103 protocol was frozen and no canonical result existed. The pre-freeze instrument now excludes
every key ending in `_pid` or `_pids` recursively, in both runner and independent checker. The raw
evidence retains all producer identifiers for process-boundary inspection; only the declared stable
projection removes them. A corrected development replay is required before freeze.

## M103 pre-freeze adversarial audit — six additional false-positive paths

The pre-freeze red team found six further defects or underpowered controls after the initial PID
projection failure: an all-features host switch made S-prime state nearly decorative; the
more-budget arm did not actually repeat work; S0 closure was certified only by the runtime being
tested; M101/M102 retention was partly structural rather than behavioral; the producer module named
the exact four-token winning subset; and zero external-call counters were not themselves decisive.

All were corrected before any `PROTOCOL.json` or canonical result existed. The feature interpreter
now executes four separable steps; the control repeats the complete S0 image 32 times; an independent
closure checker imports no M103 runtime/search; a separate execution-only predecessor capsule runs
seven fresh M100-M102 probes; the accepted subset constant is absent from the producer runtime; and
P1/P14/P15 require isolation/import/call-counter evidence. The complete disclosure and residual
claim ceiling are in `experiments/M103/ADVERSARIAL_REVIEW.md`. No qualification population was
redrawn and no scientific attempt was consumed.

## M103 pre-freeze full-suite checkpoint — repository integration registers were incomplete

The first complete post-candidate local suite returned 2,895 passes, 12 expected skips and three
failures. All three were repository-integrity guards: the copied `m103_runtime` capsule alias and
the local `tests` namespace were absent from dependency classification; the three executable M103
author scripts were not classified as entry points; and candidate source commit `48be7c06…` was
cited but not yet recorded in `docs/COMMIT_CITATIONS.json`.

No M103 behavioral test or P1-P15 condition failed. The integrity checker now recognizes explicit
M103 capsule/local-test aliases and `author_` entry points. Annotated provenance tag
`provenance/m103-owner-review-source-v1` preserves the cited source commit, and the citation manifest
records it. This occurred before protocol acceptance, freeze or canonical execution.

## M103 pre-freeze CI checkpoint — the first owner-review candidate was checkout-dependent

The first PR CI run returned 2,897 passes, 11 expected skips and two failures on Python 3.11. One
failure was a correct fail-closed refusal: GitHub's CPython 3.11.16 shipped SQLite 3.45.1 rather than
the canonical SQLite 3.53.1, but the test had incorrectly expected candidate construction to
succeed. The second failure was decisive for the candidate itself: its predecessor checker raw hash
named the CRLF Windows working-tree copy (`aadf6971…`), while CI measured the unchanged committed LF
blob (`5a35f161…`). Further inspection found the same portability defect in retained M100/M101 source
bindings. The M0* attribute convention no longer matched milestone names beginning at M100.

No final `PROTOCOL.json`, result or checker existed, and the qualification population had not run.
The first candidate `0a74e8f2…` is therefore superseded before acceptance. M100+ JSON artifacts and
all M103-bound capsule sources now have explicit stable-byte attributes; `.gitattributes` is itself
bound; builders require a clean worktree; and non-canonical CI verifies refusal rather than trying to
construct a different candidate. The population was not altered or redrawn. A replacement owner-
review candidate must be built from the canonical runtime and pass both CI platforms before freeze.

## M103 freeze checkpoint — two pre-freeze lifecycle assertions rejected the accepted protocol

After owner acceptance materialized the final protocol but before its commit or tag, the first
targeted lifecycle run returned 25 passes and two failures. Both assertions still described the
pre-freeze state: one required `PROTOCOL.json` to be absent, and the other invoked the fully
authorized materialization path expecting a missing protocol file. The latter would become unsafe
once the tag existed because a test could consume the unique scientific attempt.

No qualification process started and `RESULT.json`/`CHECK_REPORT.json` remained absent. The tests
now require the exact accepted protocol while preserving absent evidence, and exercise only denied
authorization combinations. They never invoke `authorized_by_owner=True` with the unique-attempt
acknowledgement. This is a lifecycle/safety correction before the freeze commit, not evidence for
H48 and not a consumed attempt.

## M103 canonical attempt 1 — frozen checker entry point could not import replay

The owner-authorized runner executed exactly once on 24 August 2026 from
`experiment/m103-frozen-protocol-v1`. It exited zero and materialized result `d2ace036…`, stable
evidence `6a11fff9…`. The result was committed and tagged before analysis.

The first checker command used the frozen repository script entry point:

`python scripts/check_m103_result.py --replay --write`

It exited 3 with `ModuleNotFoundError: No module named 'scripts'`. When Python executes a file under
`scripts/` directly, that directory is `sys.path[0]`; the replay-only import
`from scripts import run_m103_qualification` therefore cannot resolve the package from the
repository root. The pre-freeze tests imported the checker as a module and never exercised the exact
direct-script replay/write command, so they missed the defect. No `CHECK_REPORT.json` exists.

The frozen verdict rule makes any false or uncomputed predicate negative. P15 was not computed, so
M103 attempt 1 is negative even though the runner itself completed. The result is not relabelled as
positive and the checker is not retried through `python -m`. Exact process output and bindings are
preserved in `experiments/M103/CHECKER_FAILURE.json` (raw SHA-256 `fbc09a6c…`). D072 closes M103;
a clean-entry-point correction and entirely fresh population belong to M104.

### Post-result lifecycle suite

The first targeted repository run after D072 returned 21 passes and seven failures. Two assertions
still required `RESULT.json` to be absent; three pre-freeze integrity tests tried to reconstruct a
pool whose author deliberately refuses once a result exists; and two candidate/audit tests reached
the same closed authoring path. One surviving test also executed `run_experiment()` twice on the
already exposed M103 pool under the label DEVELOPMENT replay. Those executions wrote no artifact,
cannot rescue P15 and are not additional canonical attempts, but calling them after closure was the
wrong lifecycle behavior and is disclosed here.

Post-result tests now bind the immutable protocol, result and checker-failure hashes, require the
report to remain absent, verify denied authorization leaves result bytes untouched, and explicitly
forbid calling the closed runner/checker. They do not modify or re-execute M103 science.

The first lifecycle correction run returned 25 passes and two test-only failures: one guard called a
hash helper from the runner although that helper belongs to the runtime, and one tried to exercise
the candidate builder from the intentionally dirty correction worktree, so its clean-tree refusal
preceded the expected post-result refusal. The guards now use the standard-library hash and inspect
the two frozen refusal branches statically; neither failure touched an experiment artifact.

## M104 pre-freeze candidate A1 — absolute checkout path entered the commitment

The first M104 candidate (`e528f564…`, raw `f972c1cb…`) passed the direct-script import test but
embedded the full Windows repository root from that preflight report. A protocol accepting it would
have bound checkout identity rather than the portable fact being tested. No M104 qualification
experiment, result, report or final protocol existed.

The exact candidate is preserved at tag `provenance/m104-superseded-candidate-a1`. It is superseded,
not amended into the accepted candidate. The preflight now emits only
`repository_root_resolved: true`; `.gitattributes` explicitly fixes every M104 bound source/prose
path to LF or byte-exact JSON and is itself part of the bound apparatus. A new clean-source candidate
is required.

### M104 pre-freeze candidate A2 — clean-tree and source-commit rules were mutually exclusive

Replacement candidate `62ab21c5…` removed the absolute path and matched every bound Git blob, but
the final builder could not legally consume it. The candidate was created untracked from its clean
source commit; finalization then required a clean worktree and `HEAD` equal to that source commit.
Leaving the candidate untracked violated cleanliness, while committing it changed `HEAD`.

No owner acceptance, final protocol, qualification run, result or report existed. The exact A2
candidate is preserved at `provenance/m104-superseded-candidate-a2`. The corrected chronology is:
clean source commit, generated candidate, candidate-only commit, owner acceptance, final protocol,
then a freeze commit/tag directly above the candidate commit. The builder now verifies the parent,
the candidate-only path census and exact committed candidate blob.

### M104 pre-freeze candidate A3 — full source SHA violated the citation register

Candidate `6b17901b…` satisfied portability and candidate-only commit validation, but repository
integrity failed because its full source commit SHA was not in `docs/COMMIT_CITATIONS.json`. Placing
that SHA in the source commit itself is circular. No protocol acceptance or qualification occurred.

Tag `provenance/m104-superseded-candidate-a3` preserves A3. The replacement uses annotated source
and candidate refs: construction, finalization and canonical preflight each resolve the ref and
verify the exact parent relation. This keeps the commitment reachable and avoids weakening the
commit-citation guard.

### M104 pre-freeze candidate A4 — freeze parent did not imply unchanged apparatus

Candidate `9f6e1b42…` resolved annotated source/candidate refs correctly, but the canonical runner
verified only the freeze tag, parent and clean worktree. A freeze commit could therefore contain
`PROTOCOL.json` plus a changed runner/checker and still pass those checks. No owner acceptance,
protocol freeze or qualification occurred.

Tag `provenance/m104-superseded-candidate-a4` preserves it. The replacement preflight recomputes the
raw pool/candidate, every M104 apparatus member, both inherited M103 binding groups and their set
digests, then requires the freeze commit to change exactly one path: the final protocol.

### M104 pre-freeze candidate A5 — inherited runner and fixtures were not bound

Candidate `3d765cd5…` recomputed every M104 file and both selected M103 groups, but M104's wrapper
executes `scripts/run_m103_qualification.py`, whose runner and fixture bindings live in M103's
`apparatus` group. Omitting that group meant a causal dependency could drift without invalidating
the M104 candidate. No acceptance, final protocol or qualification occurred.

Tag `provenance/m104-superseded-candidate-a5` preserves it. The replacement must bind the exact
causal inherited orchestration bytes as well as M103 `mechanism` and `checker`.

The first correction checkpoint then returned nine passes and one targeted failure before any new
candidate was generated. Binding the full M103 `apparatus` group also bound `.gitattributes`, whose
bytes legitimately changed when M104 registered its own paths. The test exposed an overbroad notion
of causal inheritance, not a qualification failure. The corrected set names only the M103 runner,
two fixtures and M102 result/checker bytes actually read, plus the unchanged M103 mechanism/checker
groups. The red checkpoint is preserved here rather than described as green.

### M104 pre-freeze candidate A6 — replay did not seal the result commit boundary

Candidate `99cb23f5…` sealed the protocol-only freeze but the independent checker did not require the
preserved first-result commit to be a direct RESULT-only child of that freeze. A changed runner or
checker could therefore accompany the result and influence replay. No owner acceptance, final
protocol or qualification occurred.

Tag `provenance/m104-superseded-candidate-a6` preserves it. The replacement freezes the first-result
tag and makes the checker verify tag, parent, path census, committed result bytes, clean tree, raw
pool/candidate and every current causal file binding before replay.

### M104 pre-freeze candidate A7 — checker trusted protocol and pool digest fields

Candidate `4f30459f…` made replay history exact, but the checker did not recalculate the protocol and
pool payload digests before comparing their recorded fields to the result. The runner already did,
but that is not an independent check. No acceptance, final protocol or qualification occurred.

Tag `provenance/m104-superseded-candidate-a7` preserves it. The replacement checker independently
recomputes protocol, candidate and pool identities; fixes the expected pool and M103 identities;
and reconstructs the annotated source/candidate/freeze/result history before any replay.

### M104 pre-freeze candidate A8 — runner trusted fields the checker would only reject post-result

Candidate `46393b91…` closed the independent checker boundary, but the pre-run runner did not itself
prove that all final bindings and history were the exact owner-accepted candidate. A manually
divergent yet internally hashed freeze could therefore consume the sole attempt before the checker
failed closed. No acceptance, final protocol or qualification occurred.

Tag `provenance/m104-superseded-candidate-a8` preserves it. The replacement runner independently
reconstructs candidate identity and equality, fixed group membership, annotated ancestry, path
censuses and committed bytes before qualification.


## Attributes files are frozen apparatus, and three protocols have been broken by that — M105, M106, M107

Milestones from M100 on bind their apparatus by SHA-256 over working-tree bytes, so any bound source
without an explicit `text eol=lf` attribute is checked out with CRLF on Windows and its digest stops
reproducing. The remedy each milestone reached for was an attributes entry. That remedy does not
compose, because an attributes file is itself a bound member of whichever protocol reached for it
first.

- **M105 is broken and stays broken.** Its frozen protocol binds the root `.gitattributes`, which
  M106 later appended to. Four of M105's bound members no longer reproduce on `main`:
  `.gitattributes`, `experiments/M105/README.md`, `tests/test_m105_pre_freeze_audit.py` and
  `tests/test_m105_qualification_runner.py`. M105 is a permanently negative checker-instrument
  result under **D074** and may not be re-frozen, so this is recorded rather than repaired.
- **M106 was broken by M113 and is repaired.** M113's first commit appended its entries to the root
  file, and `test_the_bound_apparatus_still_matches_its_frozen_bytes` and
  `test_canonical_entrypoint_is_gated_by_the_final_freeze` failed from that commit onward. The root
  file is restored to its frozen bytes.
- **M107 was then broken by the repair, and is repaired.** M107 had created
  `metamorphosis/.gitattributes`, `scripts/.gitattributes` and `tests/.gitattributes` precisely so
  that later milestones would not edit the root — and bound all three. Moving M113's entries there
  broke `test_canonical_entrypoint_is_gated_by_the_final_freeze` for M107 instead. Git reads one
  attributes filename per directory, so there is no fourth location.

**What replaces it.** M113 declares only `experiments/M113/.gitattributes`, which no protocol binds,
and its tested system is bound by a **declared per-member digest mode** — `lf_normalized` for every
source member, an undeclared mode refused — as M110 and M111 bind theirs. A digest mode composes
across freezes because it lives in the binding rather than in a shared file. A successor that binds
source bytes should use it and should not reach for an attributes entry.

None of this was visible in `git status`, in M113's own suite, or in its boundary audit. All three
were found by running the whole suite.

## M113's generator phase cannot be run from the session that holds its authorization

Recorded 26 August 2026, after the M113 apparatus merged and the analysis plan was frozen.

The owner's consolidated authorization covers the whole M113 chronology, and names the generator
path explicitly: a local Hermes client, stateless and blind, over OpenRouter, to one exact
DeepSeek model on one exact pinned provider with fallbacks and retries disabled. It permits a
**transport** fallback -- a minimal local HTTP client in place of Hermes -- and it permits no
substitution of model or provider whatsoever: if the frozen provider cannot serve the frozen
request, that is an instrument failure and the experiment stops.

Three conditions were checked in the execution environment before any freeze, and each is
independently fatal to a single blind qualifying invocation:

- **no Hermes client is present.** The owner's Hermes is configured on their own machine. This is a
  freshly provisioned remote container holding a clean clone and no user configuration;
- **no OpenRouter credential is present.** There is no such variable in the environment and no
  configuration file carrying one anywhere readable;
- **`openrouter.ai` is refused by egress policy.** The request fails at the proxy with a 403 on the
  CONNECT tunnel, before TLS. The proxy's own documentation states that this class is an
  organization policy denial, to be reported rather than retried or routed around.

The authorized transport fallback does not lift this. It replaces Hermes with a direct HTTP client
against the same endpoint, and the endpoint is what is unreachable.

**Why nothing was substituted.** The session holding the authorization knows Genesis, H58 and
M107-M113, so it is disqualified as the generator by the authorization's own terms and may never
produce the carriers itself. Reaching for a different model, a different provider, an auto-router or
a locally hosted emitter would each answer a different question than the one M113 asks, and the
blind bank is the entire instrument. A bank this project generated would not be a blind bank; it
would be M112's carrier authorship returned under a new name.

**What this is not.** It is not a negative result for H58, which remains untested. It is not the
`human_maintained_sealed_bank` external blocker, which is a different and larger thing that nothing
in this repository can lift. It is an environment blocker of the same kind as the Docker daemon
already recorded for M113's isolated invocation: the experiment is designed, frozen where it can be
frozen, and waiting on an instrument.

**What was done instead.** The first owner gate, freezing the analysis plan, does not depend on the
generator and was consumed: the plan is frozen as the candidate unchanged, at commitment
`66003159...`, before any carrier exists. Auditing the model-network boundary that the generator
phase would cross then found the twelfth pre-freeze defect -- `P15` reading counters the runner
wrote as literals, and a generation ledger declared and never read -- both repaired, each pinned by
a regression test. The remaining five gates need the instrument.

## M113's single qualifying invocation returned HTTP 429, and no bank exists

Recorded 27 August 2026.

The generator identity was frozen at spec commitment
`c0f13b698034ed8cbe147ff79512e8522594ac6b691d0cde1f806bc407cfd17a` — `deepseek/deepseek-v4-flash-0731`
served by Morph at bf16, twenty-four carriers requested, one invocation permitted, retries forbidden
at eight named layers. The freeze was committed and pushed before the invocation so the order is
verifiable from the history rather than asserted afterwards.

One physical request was made at **2026-08-27T07:27:49Z**. It returned **HTTP 429**.

**This is an instrument failure, not a negative result for H58.** The distinction matters more than
the outcome. A negative result is a measurement — the machinery ran against a bank and did not do
what the hypothesis predicted. Nothing ran. The generator was never reached, no carrier was ever
produced, and `P22` was not computed or approached. Anyone reading this record later must not be
able to mistake an unreached instrument for a tested hypothesis.

**The attempt is not repeated.** The frozen rule permits one physical request and no retry, for any
status, at any layer. The ledger records attempt 1 with outcome `aborted` and no payload digest, and
the shared contract draws the only conclusion available from it: *the frozen spec has materialized 0
banks; exactly one is required*. Spec `c0f13b69…` can never authorize a bank. Whether M113 is
re-frozen under a new generator spec is the owner's decision and was not taken here.

**The risk was known and the trade was made deliberately.** The pre-freeze transport probe against
Morph needed two attempts; the first returned 429 `service_overloaded` from
`upstream_provider_shared_pool` with `is_byok` false. That was recorded before the freeze, together
with the observation that the same condition would end the milestone for a reason with no scientific
content. The owner declined the BYOK remedy on the ground that a new credential path could alter the
served identity after the instrumental choice had been frozen, accepted the successful probe as
sufficient pre-freeze validation, and authorized the invocation with the risk understood. Recording
this is not an apportioning of blame; it is the difference between a milestone that was unlucky and
one that was careless, and the record should be able to tell them apart.

**Two client defects, both found by the failure and neither before it.** The first live qualifying
invocation was also the first exercise of the failure path.

- The ledger outcome was written as `failed`, which the shared closed vocabulary
  (`materialized`, `failed_structural_validation`, `failed_isolation`, `aborted`) does not contain.
  The phase machine caught it on read-back. The correct word is `aborted`. The encoding was
  corrected; the facts were not touched.
- The failure response was discarded. Only the status code survives for the attempt that matters.
  The development probe's 429 named its cause, and that cause is deliberately **not** carried across
  to this attempt: it was a different request at a different time, and borrowing it would be
  inventing evidence this attempt did not leave.

Both are repaired with regression tests, and a failed attempt now preserves its full response.

**What stands.** The analysis plan remains frozen and untouched at `66003159…`. The generator spec
remains frozen. M107–M112 are unaffected. No generality gate moved. H58 is exactly as untested as it
was before the invocation.

## M113's protocol counted one thing where there were two, and M114 separates them

Recorded 27 August 2026, after M113 closed. The entry above stands unchanged; this one is about the
protocol, not the attempt.

M113's rule was "one physical request, no retry, at any layer". Read as a scientific constraint it is
exactly right: one draw from the generator, so nothing can be drawn twice and the better draw kept.
But the rule was written over the *transport*, and the transport is not where the constraint lives.
It conflated two quantities that only coincide while the network cooperates:

    how many times the instrument may reach for the generator
    how many times the generator may produce a bank

The 429 spent the second budget without ever spending the first. The milestone ended on a fact about
a queue in a shared upstream pool, with the model never reached — and the protocol had no vocabulary
in which to say so, because it had only one counter.

**Why this is a defect in the protocol and not in the outcome.** M113's record is correct: the
attempt happened, it aborted, no bank exists, H58 is untested. Nothing about it is repaired,
reinterpreted or completed, and `tests/test_m113_record_is_closed.py` pins its digests so that stays
true. What is defective is that the *only* protocol available made an unreachable generator
indistinguishable, in budget terms, from a generator that answered. That is a measurement instrument
that cannot report its own failure mode, and it is the same shape as M112's cardinality defect and
M086-A's unfailable threshold: a quantity that agreed with the thing it was supposed to constrain.

**What replaces it.** `metamorphosis/m114_delivery.py` gives the two quantities separate names —
`delivery_attempt` and `bank_materialization` — and separate budgets: at most 3 of the first for at
most 1 of the second. The scientific constraint is untouched and is now stated where it belongs, on
materializations. The transport constraint is stated on attempts, and is deliberately the narrowest
window that addresses what happened: an explicit HTTP 429, no completion of any kind, no evidence the
model executed, the byte-identical frozen body, a fixed pre-registered 60-second wait. Three capacity
rejections are `instrument-aborted`, which is still not a result about the hypothesis.

**The failure mode the repair could itself introduce, and what refuses it.** A milestone permitted
three attempts is a milestone that could draw until something passes. So every ambiguity resolves to
a *terminal* outcome rather than a retryable one — a timeout after transmission, a lost connection, a
429 that nonetheless carried a completion, a response that decoded to something that is not an object
— and no scientific outcome is ever retried, `P22` false included. The conservative mistake costs one
unused attempt. The opposite would permit a second draw against a model that may already have
produced one, and no downstream check could ever recover the difference. The checker recomputes every
one of those rules from the attempt sequence rather than reading the ledger's own summary, and the two
verdicts M114 adds are strictly subtractive: neither can turn a negative into a positive.

**When the separation was decided.** After M113's instrument failure, before any M114 bank existed,
and with no observation of H58 or H59 whatsoever — M113's request never reached the model and M114
has not made one. It was never part of M113 and is never described as though it had been. The four
statements are booleans in `m114_carrier_bank.FILIATION` that M114's frozen plan must reproduce
exactly or fail validation.
