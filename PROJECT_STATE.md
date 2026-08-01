# Mira Genesis — État du projet

## Objectif ultime

Construire une intelligence capable d’apprendre dans un substrat A, de découvrir un substrat B inconnu, d’y construire un nouveau corps, puis d’y transférer ses compétences, sa mémoire et sa plasticité afin de continuer à apprendre sans intervention architecturale humaine.

## État au 31 juillet 2026

- Dernière expérience validée : **M013e — migration scellée vers un substrat opaque**, dans son domaine fini
- M012b : **VALIDATED — BOUNDED FINITE DOMAIN**
- M013e : **VALIDATED — BOUNDED FINITE OPAQUE SUBSTRATE**
- M014b : **FAILED — PORTABILITY WITHOUT GENERALIZABLE LEARNING ADVANTAGE**
- M014c : **HALTED — SUPERSEDED BY M017**, jamais évaluée
- M017 : **READY TO FREEZE**, critère devenu directionnel après balayage à 50 environnements
- M018 : **HYPOTHESIS NOT SUPPORTED** — détruire ne restaure pas l’amélioration
- M019 : **RIG NOT VALID** — sélection trop impatiente pour valoriser l’apprentissage
- Expérience suivante : **M019b — sélection à horizon long**
- Statut global : **prototype de recherche borné avec morphogenèse et migration opaque validées, plasticité exacte transportable, avantage d’apprentissage non validé, et croissance du langage en cours de développement**

## Correction de direction — 31 juillet 2026

Toute la chaîne M012b → M014c reposait sur une limite qu’aucun critère ne mesurait :
**l’organisme ne peut exprimer que ce qui lui a été écrit à la main.** L’identification
de M014c énumère strictement douze programmes structurels ; son apprentissage n’est
qu’une repondération de compteurs sur ce catalogue fermé.

M014c est donc arrêtée avant évaluation et remplacée par M017 — langage
auto-extensible — dont le vocabulaire de départ ne contient que des atomes, et où tout
ce qui dépasse l’atome doit être construit puis peut être absorbé. La feuille de route
change d’ordre, pas de noms : M015 et M016 sont reportées derrière M017 et M018.

Voir D009, D010, `ROADMAP.md` et `experiments/M017/`.

## Développement M017

42 épisodes, trois environnements. Le catalogue fermé — la capacité de M014c —
n’en résout **aucun**. La recherche ouverte sans absorption en résout 34, à coût
constant. L’organisme auto-extensible en résout 37, et son coût de recherche médian
passe de 4 222 nœuds sur la première moitié des épisodes à **43** sur la seconde,
tandis que celui de la recherche ouverte reste plat.

Réincarnation 9/9 exacte sur trois familles de machines opaques, archive intacte,
4/4 abstentions sur les contrôles négatifs, zéro faux succès.

**Les six portes de gel sont franchies.** Le protocole complet, seuils compris, attend
une signature humaine dans `experiments/M017/FROZEN_PROTOCOL_017_CANDIDATE.md`. Aucune
évaluation canonique n’est autorisée avant elle : le gel engage des seuils qui ne
bougeront plus, et l’évaluation ne s’exécute qu’une fois.

Deux mesures ont modifié le protocole en cours de route :

- **la statistique décisive initiale a été rejetée par la mesure.** Non appariée :
  2,4× à 605× selon l’environnement. Appariée épisode par épisode : 95× à 620×. La
  dispersion est divisée par trente-huit sans que la médiane bouge ;
- **le langage étendu ne se transporte pas.** Une bibliothèque héritée d’un
  environnement aux motifs disjoints donne 0,69×, strictement pire que pas de
  bibliothèque du tout, quatre fois sur quatre. Ses macros ne s’appliquent jamais et
  gonflent pourtant le facteur de branchement.

La portée revendiquée est donc restreinte d’avance : le langage croît **à l’intérieur**
d’une distribution de transformations, et son avantage ne suit que si l’environnement
d’arrivée partage cette structure.

## Résultat canonique M014b

M014b a transporté un passeport de plasticité sérialisé avec douze compétences héritées vers trois machines opaques scellées. Pour chaque modification comportementale, Genesis ne recevait qu’un oracle de requêtes.

Ce qui a réussi :

- 36/36 chaînes complètes exactes ;
- 12/12 sur chaque machine ;
- ancien et nouveau corps exacts et sérialisables ;
- sémantique des opcodes utilisés correctement découverte ;
- ancien corps préservé octet pour octet ;
- 12/12 contrôles négatifs rejetés ;
- zéro faux succès et zéro mutation d’archive ;
- médiane totale de 44 requêtes, maximum 50.

Ce qui a échoué :

- médiane d’identification Genesis : 14 ;
- apprentissage L* depuis zéro : 14 ;
- requêtes aléatoires : 17 ;
- organisme sans passeport appris : 17.

Genesis n’a donc pas atteint les avantages préenregistrés de 25 % sur L* et 20 % sur les deux baselines locales. Huit critères sur dix passent, mais le statut reste **FAILED**. Aucun seuil n’est modifié et aucun rerun ne remplace la première tentative.

Identité de la preuve :

- SHA évalué : `5a0947afb96d7d59438c222028f2cabb34bc0cd5` ;
- protocole SHA-256 : `215e442435e4f915e647ad1392f1172685f977f758053027adaa687b1126c881` ;
- run GitHub Actions : `30650363802`, tentative 1 ;
- artefact SHA-256 : `0b5cf2df20dc4fc05dba3f1540c6d07c557ebd4c4d963d6e6286d90358a2f28a`.

Une reproduction indépendante a retrouvé toutes les métriques, tous les corps, les critères et la décision. Le hash de consolidation était seul non portable, car il incorporait des scores flottants ; M014c devra utiliser une trace quantifiée ou rationnelle.

## Capacités soutenues dans le domaine fini

- extraction d’un passeport comportemental ;
- morphogenèse autonome depuis un contrat opaque ;
- découverte expérimentale d’un substrat fini inconnu ;
- migration exacte d’une compétence sans oracle de tâche ;
- transport, exécution et consolidation exacte d’un mécanisme de plasticité borné ;
- abstention face aux modifications hors langage ou aux oracles instables.

## Non validé

- avantage d’apprentissage transférable hors distribution de développement ;
- mémoire autobiographique portable ;
- adaptation à une physique continue ou analogique ;
- langage cognitif auto-extensible ;
- auto-métamorphose ouverte.

## Prochaine opération — M014c

M014c ne cherchera pas simplement une meilleure heuristique sur les mêmes cas. Elle devra apprendre une représentation de transformations à travers plusieurs environnements de développement, détecter le décalage de distribution, adapter son prior en ligne sous un budget strict et battre quatre baselines : L* depuis zéro, requêtes aléatoires, absence de passeport et passeport statique M014b.

Le but initial demeure inchangé : apprendre dans un corps A, comprendre un substrat B inconnu, y construire un corps, puis y transférer compétence, mémoire et plasticité afin de continuer à apprendre réellement mieux qu’un organisme vierge.
