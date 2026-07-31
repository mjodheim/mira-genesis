# Hypothèses scientifiques

Chaque état indique aussi sa **provenance** : `vérifiable` si le protocole figé, le code
et le run scellé existent dans ce dépôt, `héritée` si l'affirmation repose sur M001–M011,
dont aucune archive n'est versionnée (voir [`archives/README.md`](archives/README.md)).

## H1 — Séparation fonctionnelle

Une compétence peut être représentée indépendamment des poids et de l'architecture qui l'ont acquise.

**État :** validée uniquement pour les compétences séquentielles finies de M001–M011.
**Provenance :** héritée, non vérifiable ici. Partiellement ré-établie par M013e, qui
migre exactement une compétence héritée sans oracle de tâche.

## H2 — Réincarnation hétérogène

Un même passeport peut être exécuté par plusieurs physiques computationnelles sans perdre son comportement.

**État :** validée dans le contrat fini de M010.
**Provenance :** héritée. Ré-établie de façon vérifiable par M013e sur trois familles de
machines booléennes opaques.

## H3 — Plasticité portable

Une compétence réincarnée peut recevoir un delta portable et évoluer nativement dans chaque substrat.

**État :** validée **structurellement**, non tenue **quant à l'efficacité**.
**Provenance :** vérifiable. M014b a transporté et exécuté exactement le mécanisme de
plasticité, 36/36, mais l'avantage en nombre de requêtes n'a pas survécu au décalage de
distribution. Transporter une politique n'implique pas transporter son efficacité.

## H4 — Morphogenèse autonome

Un organisme peut construire son propre corps à partir d'un contrat, de primitives et d'un budget, sans compilateur spécialisé.

**État :** validée dans le domaine fini.
**Provenance :** vérifiable. M012b, évaluation scellée 36/36 et reproduction indépendante.

## H5 — Continuité cognitive riche

La mémoire, la stratégie d'apprentissage, les incertitudes et les compétences peuvent survivre ensemble à un changement de substrat.

**État :** non validée. Objet de M015, **reportée** derrière M017 et M018.
**Motif du report :** transporter la mémoire d'un organisme à catalogue fermé
étendrait latéralement un paradigme dont le cœur n'est pas établi.

## H7 — Langage auto-extensible

Un organisme dont le vocabulaire de départ ne contient que des atomes peut absorber
les compositions récurrentes de son environnement, et en tirer un pouvoir expressif
qu'il n'avait pas.

**État :** non validée, objet de M017, en développement.
**Provenance :** vérifiable. Le banc de développement montre 0/42 pour le catalogue
fermé, 34/42 pour la recherche ouverte à coût constant, 37/42 pour l'organisme
auto-extensible dont le coût médian tombe de 4 222 à 43 nœuds. Aucun résultat
canonique n'est revendiqué : le protocole n'est pas figé.

H7 n'est pas une hypothèse nouvelle du projet — c'est la reconnaissance que M017
figurait déjà dans la feuille de route, et qu'elle y était mal placée.

## H6 — Auto-métamorphose

Un organisme peut diagnostiquer une limite de son propre corps, proposer des descendants, les évaluer sur des tests cachés et migrer vers une meilleure incarnation.

**État :** non validée. Objet de M018, **bloquée par H7** : un organisme qui ne peut
pas étendre son langage ne peut pas se décrire un corps que ses primitives ne savent
pas écrire.
