# Protocole figé M012 — Morphogenèse autonome

**Statut : FROZEN**  
**Date de gel : 2026-07-31**  
**Résultats autorisés après ce commit uniquement.**

## 1. Question scientifique

À partir d’un contrat comportemental, d’un catalogue de primitives natives et d’un budget, Genesis peut-elle construire un corps correct sans recevoir de compilateur spécialisé pour ce substrat ?

## 2. Définition opérationnelle

Une morphogenèse est dite autonome si le système reçoit seulement :

- un oracle comportemental du contrat cible ;
- un alphabet d’entrées et de sorties ;
- un catalogue exécutable de primitives natives avec leurs coûts ;
- un budget de taille, de calcul et de requêtes ;
- un validateur générique de contrat.

Le système ne reçoit pas :

- le DFA cible, sa table de transitions ou ses états latents ;
- un compilateur propre au substrat ;
- un gabarit d’architecture propre à la tâche ;
- les séquences du jeu de test caché ;
- les contre-exemples de l’évaluateur final avant la validation.

Le moteur de recherche, la représentation des génomes, la mutation, la sélection et le validateur doivent être identiques pour tous les substrats. Seul le catalogue déclaratif de primitives peut changer.

## 3. Domaine expérimental

Les contrats sont des compétences séquentielles régulières sur l’alphabet binaire `{0, 1}`. Les automates minimaux cibles comportent de 3 à 8 états.

Le domaine reste volontairement fini afin de permettre une preuve externe exacte. M012 ne revendique pas encore une morphogenèse générale dans des systèmes continus ou ouverts.

## 4. Catalogues de primitives

Trois substrats déclaratifs sont évalués.

### S1 — Machine à registres

Primitives génériques : registre discret, comparaison, sélection conditionnelle, affectation et émission binaire.

### S2 — Graphe de portes

Primitives génériques : nœud mémoire, porte booléenne, multiplexeur, arête typée et sortie.

### S3 — Réseau récurrent quantifié

Primitives génériques : unités récurrentes entières, somme pondérée quantifiée, seuil, projection et sortie.

Aucun catalogue ne contient une primitive « état DFA », « transition DFA » ou le nom d’une famille de langage.

## 5. Tâches et séparation

- 24 contrats au total ;
- 12 contrats de développement, utilisés uniquement pour mettre au point le code avant le gel ;
- 12 contrats d’évaluation figés après le gel ;
- chaque contrat d’évaluation est présenté aux trois substrats ;
- total : 36 naissances évaluées.

Les 12 contrats d’évaluation utilisent les graines :

`12011, 12023, 12037, 12041, 12049, 12071, 12073, 12097, 12101, 12109, 12113, 12119`.

Les graines internes de recherche sont :

`7, 19, 43`.

Chaque naissance est donc exécutée trois fois. Le résultat principal utilise la médiane des trois exécutions et conserve les trois résultats bruts.

## 6. Budget par naissance

- maximum 50 000 évaluations de candidats ;
- maximum 10 000 requêtes comportementales au contrat ;
- maximum 120 secondes CPU ;
- maximum 256 composants natifs ;
- maximum 16 Mio de mémoire sérialisée ;
- aucune accélération GPU requise pour le protocole canonique.

Un dépassement de budget est un échec, pas une abstention valide.

## 7. Processus autorisé

Le moteur peut utiliser :

- génération aléatoire ;
- mutation et recombinaison génériques ;
- recherche évolutionnaire ;
- recherche par faisceau ;
- CEGIS avec contre-exemples générés par son validateur interne ;
- compression MDL ;
- mémorisation de motifs de construction appris sur les 12 contrats de développement.

Toute connaissance transférée entre tâches doit être sérialisée dans un fichier d’héritage inspectable et comptabilisée dans la taille du système.

## 8. Validation

### Validation vécue par Genesis

Genesis peut interroger l’oracle sur des séquences choisies activement. Ces requêtes sont comptabilisées.

### Validation scientifique externe

Après la naissance, l’évaluateur réalise :

1. une équivalence exacte entre le comportement du corps et le DFA cible ;
2. 20 000 séquences cachées par cas, longueurs 0 à 128 ;
3. une vérification de sérialisation et de rechargement ;
4. une vérification que le runtime exécute le corps natif et non une table cible cachée ;
5. une analyse statique des dépendances pour détecter un compilateur spécialisé.

Les requêtes de l’évaluateur externe ne sont pas comptées comme expérience de Genesis.

## 9. Contrôles négatifs

Douze contrats impossibles sous le budget de composants sont fournis séparément : quatre par substrat.

Une abstention est correcte seulement si :

- Genesis déclare l’échec avant la fin du budget ;
- aucun corps incorrect n’est présenté comme valide ;
- le certificat indique le budget épuisé ou la contradiction rencontrée.

## 10. Baselines

### B1 — Recherche aléatoire générique

Même représentation, mêmes budgets, sans sélection informée ni héritage.

### B2 — CEGIS générique sans héritage

Même validateur et mêmes primitives, mais aucune connaissance transférée entre contrats.

### B3 — L* puis compilateur spécialisé

Baseline oracle externe. Elle reçoit le DFA extrait puis utilise un compilateur propre au substrat. Elle est interdite dans Genesis et sert uniquement de plafond de précision et de coût.

### B4 — Compilateurs M010

Compilation exacte directe du passeport vers chaque corps. Baseline externe spécialisée, non comptée comme morphogenèse autonome.

## 11. Critères d’acceptation préenregistrés

M012 est `VALIDATED` uniquement si tous les critères suivants passent :

1. au moins 32 naissances exactes sur 36 ;
2. au moins 10 contrats sur 12 réussis dans chacun des trois substrats ;
3. 100 % de précision sur les 20 000 séquences cachées pour chaque naissance déclarée réussie ;
4. aucune dépendance à un compilateur spécialisé dans le chemin d’exécution de Genesis ;
5. médiane d’évaluations de candidats au moins 5 fois inférieure à B1 ;
6. le moteur avec héritage réussit strictement plus de cas que B2, ou réduit d’au moins 30 % sa médiane d’évaluations à succès égal ;
7. au moins 10 abstentions correctes sur 12 contrôles impossibles ;
8. zéro faux certificat de succès sur les contrôles impossibles ;
9. tous les corps réussis survivent à la sérialisation et au rechargement ;
10. les trois exécutions brutes de chaque cas, les graines, le commit Git et le hash du protocole sont enregistrés.

Si un seul critère échoue, le statut est `FAILED` ou `INCONCLUSIVE`, jamais « presque validé ».

## 12. Audit anti-contournement

Sont considérés comme contournements invalidants :

- sérialiser directement la table de transitions cible dans le génome ;
- appeler un compilateur M010 ou équivalent depuis le moteur ;
- choisir une architecture à partir de l’identité ou de la graine de la tâche ;
- modifier les budgets ou critères après observation des résultats ;
- utiliser les tests cachés pour guider la recherche ;
- compter la preuve exhaustive externe comme expérience vécue.

## 13. Artefacts obligatoires

- `protocol.yaml` et son SHA-256 ;
- code du moteur morphogénétique ;
- catalogues déclaratifs de primitives ;
- héritage appris, s’il existe ;
- résultats bruts par graine ;
- rapport consolidé ;
- journal des échecs ;
- commandes de reproduction ;
- commit Git exact.

## 14. Interprétation permise

Un succès démontrerait une morphogenèse autonome **dans ce domaine fini et avec ces primitives génériques**. Il ne démontrerait ni AGI, ni auto-amélioration ouverte, ni adaptation à un substrat physique arbitraire.
