# M018 — Protocole de développement (brouillon)

**Statut : BROUILLON — évaluation canonique interdite.**

## Hypothèse

Un organisme qui ne peut qu'accumuler finit par se ruiner. La capacité de **détruire**
ce qu'il a appris n'est pas un raffinement de l'apprentissage : c'en est une condition.

## Prédiction, écrite avant la mesure

Reproduite telle qu'elle a été formulée, avant d'avoir lancé quoi que ce soit :

> `(1)` et `(2)` réduiront le passif sans l'annuler, `(3)` l'annulera mais coûtera cher
> sur les environnements stables. **S'il n'y a pas de coût à la dissolution, c'est que
> la mesure est mal construite.**

Le dernier membre de phrase est le plus important. Une mesure où l'oubli ne coûte rien
serait une mesure insensible, pas un bon résultat.

## Trois régimes, parce que l'hypothèse y prédit des signes opposés

| Régime | Ce qui s'y passe | Signe attendu |
|---|---|---|
| **stable** | les motifs ne changent pas | l'oubli **coûte** : il jette ce qui allait resservir |
| **décalage** | la distribution bascule sur des motifs disjoints | l'oubli **gagne** : les anciens macros sont du coût pur |
| **transport** | l'organisme démarre avec une bibliothèque étrangère | l'oubli doit **annuler** le passif de 0,69× de M017 |

Un mécanisme qui gagnerait dans les trois régimes serait suspect : il n'y aurait alors
aucun arbitrage, et l'accumulation n'aurait jamais eu de raison d'exister.

## Ce qui est mesuré

Le nombre de programmes évalués avant de trouver — le même entier que M017, sur la même
plage de quatre ordres de grandeur. La référence est toujours `NoForgetting`,
c'est-à-dire l'organisme de M017. Les rapports sont exprimés en centièmes entiers ;
au-dessus de 100, l'oubli gagne.

## Conditions d'admission

Jeter ne doit jamais dégrader l'exactitude, seulement le coût.

1. **Zéro faux succès** dans tous les régimes et pour toutes les politiques.
2. Toute solution annoncée est exactement équivalente à la cible.
3. Trace de décision entièrement entière — la dissolution divise les compteurs par
   deux en division entière, aucun flottant n'entre dans une décision.

## Ce que l'organisme n'a pas le droit de savoir

Il **ne lit jamais ce que fait un macro**. Son registre ne contient qu'un nombre
d'usages et un âge. C'est la contrainte qui rend le problème représentatif : un
organisme qui manipule du code que personne ne comprend doit juger sur l'usage, jamais
sur la sémantique.

Un test le verrouille : le registre ne doit contenir que ces deux champs.

## Portes de gel

Le protocole ne pourra être figé qu'après :

1. la mesure des trois régimes, et la vérification que **les signes attendus
   apparaissent** — en particulier que la dissolution coûte en régime stable ;
2. la désignation de la comparaison décisive et de sa marge, selon D010 : plage
   dynamique établie, dispersion entre paires mesurée, seuil dérivé plutôt qu'ajusté ;
3. l'extension aux environnements dont la distribution bascule plusieurs fois, et non
   une seule ;
4. un audit d'isolation, sur le modèle de `audit_m017_isolation.py`.

## Ce que M018 ne prétendra pas

Un organisme qui jette des macros ne se métamorphose pas. Il élague un vocabulaire dont
les atomes restent écrits à la main, dans un domaine booléen fini, avec un moteur de
recherche qu'il ne peut pas modifier.

M018 mesure une **condition** de l'auto-métamorphose, pas l'auto-métamorphose. Le pas
suivant est que la politique elle-même — ordre d'énumération, profondeur, seuil
d'absorption, budget — devienne un objet que l'organisme réécrit.
