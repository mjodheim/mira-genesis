# Mira Genesis — État du projet

## Objectif ultime

Construire une intelligence capable d’apprendre dans un substrat A, de découvrir un substrat B inconnu, d’y construire un nouveau corps, puis d’y transférer ses compétences, sa mémoire et sa plasticité afin de continuer à apprendre sans intervention architecturale humaine.

## État au 31 juillet 2026

- Dernière expérience validée : **M013e — migration scellée vers un substrat opaque**, dans son domaine fini
- M012 : **INCONCLUSIVE — CONTAMINATED**
- M012b : **VALIDATED — BOUNDED FINITE DOMAIN**
- M013 / M013b : **INCONCLUSIVE — CONTAMINATED**
- M013c : **INCONCLUSIVE — NON REPRODUCTIBLE AU COMMIT ANNONCÉ**
- M013d : **FAILED — DEVELOPMENT BASELINE CRITERION**, aucun run canonique
- M013e : **VALIDATED — BOUNDED FINITE OPAQUE SUBSTRATE**
- Ancien M014 : **HALTED — prerequisites revoked, never evaluated**
- Expérience suivante : **M014b — plasticité portable scellée**
- Statut global : **prototype de recherche borné avec chaîne d’évaluation scellée et reproductible**

## Résultat M013e

M013e a reçu douze compétences héritées et trois machines dont les opérations étaient désignées uniquement par des identifiants opaques. Les compétences, machines, contrôles et suites cachées ont été générés après création du SHA immuable, lors du premier run `pull_request/opened`.

Genesis a :

- sondé les opérations dans un budget de 120 appels ;
- identifié exactement les sémantiques stables utilisées ;
- exclu les opérations instables ;
- vérifié la suffisance fonctionnelle ;
- construit des corps contenant uniquement les identifiants opaques et leur structure ;
- préservé exactement la compétence sans oracle de tâche ni carte d’opcodes.

Résultats :

- 36/36 migrations principales exactes ;
- 108/108 exécutions exactes ;
- trois machines à 12/12 ;
- plafond oracle 36/36 ;
- 84 sondes médianes, 96 maximum sur 120 ;
- baseline fixe sans sondage 0/36 ;
- baseline aléatoire 1/36 ;
- avantage de 35 migrations sur la meilleure baseline sans information ;
- 12/12 contrôles négatifs rejetés ;
- zéro faux succès ;
- dix critères préenregistrés passés.

Identité de la preuve :

- SHA évalué : `e309169b4edf8a508ec60990e68ba079fd032f2c` ;
- protocole SHA-256 : `e29f024e3cc04ebd18ebd9484d499bdfbf1d98a3fbe0beb9c0ec318c8c394c5f` ;
- run GitHub Actions : `30637689966`, tentative 1 ;
- artefact SHA-256 : `47888734b6c88ef5811e086bac71bbcfd8e6c14f676824eb5d6597475c7742c6`.

Une reproduction indépendante avec la nonce publiée a produit exactement le même contenu scientifique après exclusion du temps d’exécution et des métadonnées d’environnement.

## Capacités désormais soutenues dans le domaine fini

- extraction d’un passeport comportemental ;
- construction autonome d’un corps depuis un contrat opaque ;
- migration exacte vers plusieurs substrats finis ;
- découverte expérimentale bornée des opérations d’un substrat opaque ;
- détection de bases insuffisantes ou instables ;
- migration d’une compétence héritée sans oracle de tâche ni compilateur spécifique.

## Non validé

- transport d’une méthode d’apprentissage générale ;
- poursuite d’un apprentissage nouveau après migration ;
- mémoire autobiographique portable ;
- adaptation à une physique continue ou analogique ;
- langage cognitif auto-extensible ;
- auto-métamorphose ouverte.

## Prochaine opération — M014b

L’ancien protocole M014 a été stoppé avant évaluation lorsque ses prérequis ont été révoqués. M014b repartira proprement avec de nouveaux cas scellés.

M014b devra transporter avec la compétence un passeport de plasticité sérialisable : espace d’hypothèses, politique active de requêtes, représentation de l’incertitude et règle de consolidation. Après migration vers une machine opaque M013e, Genesis devra apprendre une modification comportementale inconnue avec peu de requêtes, produire un nouveau corps natif exact et préserver l’ancien corps archivé.

Le but initial demeure inchangé : apprendre dans un corps A, comprendre un substrat B inconnu, y construire un corps, puis y transférer compétence, mémoire et plasticité afin de continuer à apprendre.
