# M019 — Protocole de développement (brouillon)

**Statut : BROUILLON — évaluation canonique interdite.**

## Hypothèse

Sous rareté réelle, une population sélectionnée sur son efficacité découvre des
stratégies d'usage du langage qu'une conception à la main n'atteint pas.

## Prédiction, écrite avant la mesure

> La population convergera vers `budget`, seul mécanisme sans revers en régime stable
> dans M018, et vers des seuils d'absorption bas. `dissolution` disparaîtra.
> **Si `none` domine, c'est que la rareté n'est pas assez mordante et le montage est à
> refaire avant d'en conclure quoi que ce soit.**

La dernière phrase est la plus importante : elle distingue à l'avance un résultat d'un
artefact de calibrage.

## Le montage

- **énergie = budget de recherche.** Un organisme appauvri cherche moins loin ;
- **classement par énergie restante**, pas par nombre de succès ;
- **population de 10**, moitié la plus riche conservée, moitié remplacée par des
  descendants mutés ;
- **survivants remis à niveau** à chaque génération : on sélectionne une stratégie, pas
  une avance accumulée ;
- **l'environnement change une fois**, à mi-parcours. Stable, l'absorption paierait
  toujours et l'oubli n'aurait aucun rôle ; changeant à chaque génération, aucune
  absorption ne paierait jamais.

## Calibrage, et pourquoi il a dû être refait

Le premier essai fixait la prime à 25 000 pour une dotation de 150 000. Résultat :
**zéro mort, énergie doublée, `none` vainqueur 8/8**.

La condition d'invalidation écrite d'avance s'appliquait donc, et le diagnostic était
objectif — une population qui ne perd personne et double son énergie n'est pas sous
contrainte. Une prime très supérieure au coût d'une résolution bon marché rend toute
bibliothèque, même encombrée, sans conséquence.

Le second calibrage — prime 6 000, dotation 200 000, plafond 60 000 — fait mordre
l'arithmétique :

| | coût | bilan |
|---|---|---|
| résolution par macro | ~43 nœuds | **+5 957** |
| résolution macro + atome | ~1 700 nœuds | +4 300 |
| résolution en profondeur 3 | ~23 000 nœuds | **−17 000** |
| abstention | 60 000 nœuds | **−60 000** |

Un organisme doit amortir chaque apprentissage coûteux par plusieurs résolutions bon
marché, et une bibliothèque qui gonfle le facteur de branchement ampute réellement la
prime.

**Le plafond doit dépasser 46 656** — l'espace complet de profondeur 3. Un premier
réglage à 45 000 rendait le montage dégénéré : aucun organisme sans macro applicable ne
pouvait achever une recherche, la population entière s'abstenait dès le changement
d'environnement, et la sélection n'avait plus rien à trancher.

## Contrôle

Un organisme seul, sans sélection, sous la même rareté, portant le génome par défaut de
M017 — absorption au seuil 2, aucun oubli — face aux mêmes épisodes. Sans lui, on ne
saurait pas si la population gagne parce qu'elle sélectionne ou simplement parce
qu'elle est dix.

## Conditions d'admission

1. **Zéro faux succès**, quelles que soient la rareté et la mortalité. Mourir est
   permis ; mentir non.
2. Toute solution annoncée est exactement équivalente, vérifiée par le test de
   conformité complet de `conformance.py`.
3. Trace entièrement entière.

## Portes de gel

1. la rareté doit **mordre** : mortalité non nulle et énergie qui ne diverge pas ;
2. la composition finale de la population doit différer de sa composition initiale de
   façon reproductible sur plusieurs lignées indépendantes ;
3. la comparaison décisive et sa marge doivent respecter D010 — plage dynamique
   établie, dispersion entre lignées mesurée, seuil dérivé et non ajusté ;
4. un balayage large, l'échantillon initial étant petit. **M017 a montré que huit
   environnements donnaient un minimum optimiste d'un facteur dix** ;
5. audit d'isolation.

## Ce que M019 ne prétendra pas

Une population qui optimise dans un espace fini finira par le saturer. Il n'y a pas de
croissance ouverte dans des automates de 4 à 10 états, et le vocabulaire atomique reste
écrit à la main : M019 sélectionne la manière de s'en servir, pas l'invention de
primitives nouvelles.

M019 teste si la **sélection** est le mécanisme manquant. C'est une condition de
l'auto-métamorphose, pas l'auto-métamorphose.
