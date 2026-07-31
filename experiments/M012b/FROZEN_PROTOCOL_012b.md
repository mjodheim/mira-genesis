# Protocole figé M012b — Morphogenèse autonome à cas scellés

**Statut : FROZEN avant toute évaluation canonique**  
**Date de gel : 31 juillet 2026**  
**Remplace : M012, révoquée pour contamination des graines d’évaluation**

## Question scientifique

À partir d’un contrat comportemental opaque, d’un catalogue déclaratif de primitives natives et d’un budget, Genesis peut-elle découvrir les états utiles puis construire un corps natif exact sans recevoir le DFA cible ni un compilateur propre au catalogue ?

## Correction centrale par rapport à M012

Aucune graine d’évaluation n’existe dans le dépôt, les tests ou le code de développement avant l’évaluation.

Le premier workflow GitHub Actions déclenché par l’ouverture de la pull request M012b :

1. génère une seule nonce cryptographique de 256 bits avec le générateur système ;
2. dérive de cette nonce douze graines de cibles, trois graines de recherche et douze graines de tests cachés ;
3. exécute immédiatement l’évaluation ;
4. publie la nonce, les graines, les résultats complets et leurs empreintes dans un artefact GitHub horodaté.

La première exécution, tentative `1`, déclenchée par l’action `pull_request: opened`, est la seule exécution canonique. Une relance, une nouvelle nonce ou une modification après ouverture invalide M012b et impose une nouvelle expérience numérotée.

## Domaine

- alphabet binaire `{0, 1}` ;
- douze langages réguliers déterministes ;
- automates minimaux de 3 à 8 états ;
- trois catalogues déclaratifs : logique directe, tissu NAND et tissu NOR ;
- trois répétitions de recherche par cible et catalogue ;
- 36 naissances principales et 108 exécutions.

Les catalogues contiennent uniquement des identifiants de primitives, arités, tables de vérité et coûts. Le même moteur découvre une base NOT/AND/OR et construit les corps sans branchement sur l’identité du catalogue.

## Interface autorisée

Genesis reçoit uniquement :

- une fonction de requête d’appartenance sur des mots binaires ;
- un catalogue déclaratif ;
- les budgets ;
- une graine de recherche.

Genesis ne reçoit pas :

- la graine de la cible ;
- le DFA, ses transitions ou ses états ;
- les mots de validation cachés ;
- un compilateur spécifique à un catalogue ;
- la nonce avant le lancement canonique.

## Budgets par exécution

- 20 000 requêtes comportementales ;
- 50 000 évaluations de candidats ;
- 120 secondes CPU ;
- 256 composants natifs ;
- 16 MiB sérialisés ;
- 8 états découverts au maximum.

## Validation externe

Pour chaque corps déclaré réussi :

1. sérialisation et rechargement ;
2. reconstruction d’un DFA uniquement par exécution native du corps ;
3. équivalence exacte avec la cible ;
4. 10 000 mots cachés de longueur 0 à 128 ;
5. contrôle indépendant de la taille et des budgets.

## Baseline

Un plafond oracle reçoit directement le DFA cible mais utilise le même synthétiseur générique et les mêmes catalogues. Il ne fait pas partie de Genesis. L’écart maximal admis est de deux naissances principales.

## Contrôles négatifs

Douze contrôles :

- six contrats non déterministes, qui doivent être rejetés lors de l’audit de cohérence ;
- six catalogues monotones incomplets, incapables de produire une négation, qui doivent provoquer une abstention.

Aucun contrôle négatif ne peut recevoir un corps ou un certificat de réussite.

## Critères d’acceptation préenregistrés

M012b est `VALIDATED` seulement si les dix conditions passent :

1. au moins 32 naissances principales exactes sur 36 ;
2. au moins 10 cibles exactes sur 12 dans chaque catalogue ;
3. tous les succès revendiqués sont exactement équivalents et à 100 % sur le caché ;
4. au moins 96 exécutions exactes sur 108 ;
5. écart au plafond oracle inférieur ou égal à deux naissances ;
6. 12 abstentions négatives correctes sur 12 ;
7. zéro faux succès négatif ;
8. tous les succès respectent les budgets ;
9. l’audit d’isolement des cas et du code passe ;
10. la traçabilité du premier run contient commit, protocole, run GitHub, nonce et graines révélées.

Un seul échec entraîne `FAILED`, jamais « presque validé ».

## Portée permise

Un succès démontrerait une morphogenèse autonome bornée sur des compétences régulières finies et des primitives booléennes déclarées. Il ne démontrerait pas encore la compréhension d’un substrat inconnu, le transfert de mémoire, la plasticité générale ou une AGI.
