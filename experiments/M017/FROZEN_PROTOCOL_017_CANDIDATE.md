# M017 — Protocole candidat au gel

**Statut : CANDIDAT — RETIRÉ DE LA SIGNATURE. Chiffres en cours de remesure.**

> **Défaut trouvé après rédaction de ce document.** La confirmation d'un candidat
> tirait 96 mots longs au hasard en affirmant couvrir la borne de distinction de deux
> automates. Elle ne la couvrait pas. Le « zéro faux succès sur 42 épisodes » du §3
> était un tirage favorable, pas une garantie : deux automates à 9 états confirmés
> identiques se sont révélés séparés par `(1,0,1,0,1,0,1)`.
>
> Tous les chiffres de ce document ont été produits sous cette confirmation. Ils ne
> sont pas nécessairement faux, mais ils ne sont plus établis.
>
> Correction : `metamorphosis/conformance.py`, test de conformité par méthode W,
> complet tant que la cible ne dépasse pas l'hypothèse de plus de deux états — et plus
> court que le jeu qu'il remplace, 99 mots contre 160. Voir `FAILURE_LOG.md`.
>
> **Ce document ne doit pas être signé avant que les trois mesures aient été refaites.**

Les six portes de développement avaient été franchies. Ce document est le protocole
complet, seuils compris. **Il attend une remesure, puis une signature humaine.**

Le gel est irréversible dans son esprit : une fois haché, aucun seuil ne bouge, et
l'évaluation canonique ne s'exécute qu'une fois, sans rejeu. C'est pourquoi il n'a pas
été franchi automatiquement.

---

## 1. Hypothèse

Dans un environnement dont la structure compositionnelle se répète, un organisme qui
absorbe ses motifs récurrents dans son vocabulaire acquiert un pouvoir expressif qu'il
n'avait pas, et voit son coût de recherche s'effondrer. Un organisme à catalogue fermé
ne peut pas le suivre. Un organisme qui compose sans jamais absorber ne s'améliore pas
avec le temps.

## 2. La comparaison décisive — une seule

> Médiane, sur les épisodes tardifs d'un environnement scellé, du rapport apparié
> entre le coût de recherche de la recherche ouverte et celui de l'organisme
> auto-extensible, mesuré sur le même épisode.

**Seuil : ≥ 10× dans chaque environnement scellé.** Jamais en moyenne.

**Garde par test de signe :** dans chaque environnement, l'organisme auto-extensible
doit être plus rapide sur strictement plus de la moitié des épisodes tardifs appariés.

### D'où viennent ces deux nombres

Ils sont dérivés de l'arithmétique des espaces de recherche, pas de l'échantillon.

Un macro comprime un motif de trois atomes en un symbole, rencontré en profondeur 1
parmi environ 45 symboles. Sans macro, il faut balayer la profondeur 3 sur 36 atomes,
soit 46 656 trajectoires, environ la moitié en médiane. Rapport attendu ≈ **500×**.

Le seuil de 10× est donc un ordre de grandeur sous la prédiction théorique, et un
ordre de grandeur sous le minimum observé en développement (95×).

La garde est à une demie parce que c'est le point neutre d'un test de signe. Sans
elle, une règle d'absorption dégénérée — qui avalerait tout — pourrait satisfaire la
médiane tout en dégradant la majorité des épisodes.

## 3. Conditions d'admission

Non satisfaites, l'expérience est nulle quel que soit le coût de recherche.

1. **Zéro faux succès.** Toute solution annoncée est exactement équivalente à la cible.
2. **Abstention sur tout contrôle négatif** : cible hors langage, oracle instable.
3. **Réincarnation exacte** de l'ancien et du nouveau corps sur substrat opaque.
4. **Archive intacte** octet pour octet.
5. **Trace de décision entièrement entière**, vérifiée par `audit_m017_isolation.py`.
6. **Isolation** : le code de l'organisme n'atteint aucun nom du laboratoire.

## 4. Rapporté, jamais décisif

| Grandeur | Pourquoi elle ne décide pas |
|---|---|
| catalogue fermé, capacité de M014c | Structurellement incapable, 0/42 en développement. Un seuil calé sur lui passerait trivialement. |
| épisodes résolus par le seul auto-extensible | Réel, mais son ampleur dépend du budget, qui est un paramètre. |
| longueur de description médiane | Suit mécaniquement l'absorption. |
| nombre de macros absorbés | Mesure l'activité de la règle, pas son utilité. |
| **transport vers un autre environnement** | Voir §6. |

## 5. Coût de l'absorption — rapporté explicitement

Mesuré en développement :

- pire épisode isolé : **0,74×**, l'organisme auto-extensible est 35 % plus lent ;
- épisodes tardifs plus lents : **8 sur 49**, soit 16 %.

Un macro qui ne s'applique pas coûte quand même : il élargit le facteur de
branchement. C'est le problème d'utilité des macro-opérateurs. Il est minoritaire et
compensé, mais il doit figurer au résultat.

## 6. Portée — ce que M017 ne revendiquera pas

**Le langage étendu ne se transporte pas.**

| Bibliothèque héritée | Gain médian | Paires |
|---|---|---|
| motifs partagés | 118,7× | 3/4 aident |
| motifs disjoints | **0,69×** | **4/4 nuisent** |

Une bibliothèque héritée d'un environnement aux motifs différents est strictement pire
que pas de bibliothèque du tout, sur les quatre paires mesurées, dans une fourchette
serrée de 0,65 à 0,75.

M017 revendiquera donc une croissance du langage **à l'intérieur** d'une distribution
de transformations, et rien de plus. C'est la leçon de M014b — transporter un
mécanisme ne transporte pas son avantage — portée dans le protocole avant le gel, au
lieu d'être découverte après une évaluation canonique.

M017 ne démontre pas davantage : ni mémoire autobiographique, ni physique continue,
ni invention de rôle nouveau, ni choix de son propre corps. Le langage reste borné à
quatre rôles et deux formes d'atome, sur un domaine booléen fini. **M017 est la
première marche vers H6, pas H6.**

## 7. Ce qui falsifierait M017

Énoncé avant l'évaluation :

- un seul environnement scellé sous 10× ;
- un seul environnement où la garde par test de signe échoue ;
- un seul faux succès ;
- une seule abstention manquée sur un contrôle négatif ;
- un seul corps reconstruit inexact, ou une archive modifiée.

Aucun rerun ne remplace la première tentative. Aucun seuil n'est assoupli après
observation.

## 8. Procédure d'évaluation scellée

1. Créer la branche de recherche et son workflow scellé, déclenché sur `opened` d'une
   pull request vers `main`, gardé par `head_ref`.
2. Le workflow extrait le head immuable, installe par le manifeste, exécute les tests,
   puis `audit_m017_isolation.py`, **avant** l'évaluation.
3. Les environnements scellés ne sont engendrés qu'à partir du nonce dérivé du SHA du
   head, donc après l'existence de ce head.
4. Un seul run. L'artefact et son SHA-256 sont publiés dans `results/M017.md`.
5. Le workflow part ensuite dans `archives/workflows/`, conformément à D008.

## 9. Reproduction des preuves de gel

Run GitHub Actions `30669588931`, `workflow_dispatch` sur
`research/m017-freeze-gates`, job `freeze-evidence`.

**Chaque nombre est identique** entre l'exécution locale (Windows, Python 3.14) et
la CI (Ubuntu, Python 3.11) : les huit environnements de dispersion et les quatre
paires de transport, ligne à ligne, y compris les valeurs par environnement.

C'est la vérification directe que la correction imposée par M014b tient. Le
`consolidation_record_sha256` de M014b différait d'un environnement à l'autre parce
qu'il incorporait des scores flottants : le résultat scientifique se reproduisait, sa
preuve non. M017 ne décide que sur des entiers, et cela se constate plutôt que se
postule.

## 10. Ce qui reste à faire avant de figer

- [ ] Relecture et signature humaine des seuils du §2.
- [ ] Écriture du générateur scellé et de son dérivateur de nonce.
- [ ] Écriture du workflow d'évaluation scellée.
- [ ] Hachage SHA-256 de ce document, reporté dans `results/M017.md`.

Tant que la première case n'est pas cochée, aucune de celles qui suivent ne doit
l'être.
