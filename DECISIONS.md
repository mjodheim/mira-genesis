# Registre des décisions

## D001 — Le dépôt est la mémoire officielle

La continuité du projet repose sur les fichiers versionnés, pas uniquement sur le contexte conversationnel.

## D002 — Recentrage sur Metamorphosis

Les prototypes V4–V6 restent des bancs sensorimoteurs, mais la recherche principale vise la portabilité et la continuité trans-substrat.

## D003 — Protocoles figés

Toute modification importante après observation d’un résultat crée une nouvelle expérience numérotée.

## D004 — Évaluateur extérieur

Les preuves exhaustives et tests secrets ne sont pas comptabilisés comme expériences accessibles à l’organisme.

## D005 — Pas de revendication d’AGI

Les validations M001–M011 sont limitées aux domaines formels décrits dans leurs protocoles.

## D006 — M012 doit supprimer les compilateurs spécialisés

Le prochain progrès accepté doit concerner la naissance autonome d’un corps, pas un nouvel ajout manuel de backend.

## D007 — L’arbre de travail ne contient que du code vivant

Le code d’une expérience révoquée sort de l’arbre de travail ; son enregistrement
scientifique, lui, reste. L’historique Git est l’archive, et `archives/RETIRED_CODE.md`
en est l’index : chaque retrait cite le commit où le fichier reste consultable.

Motif : la pile héritée M012 / M013b, environ 2 400 lignes, formait un sous-graphe
d’imports entièrement déconnecté et faisait échouer `pytest -q` en important `torch`.
Aucun signal ne le révélait, parce que les workflows scellés n’exécutaient que des
fichiers de test ciblés.

## D008 — Une CI permanente, distincte des évaluations scellées

`.github/workflows/ci.yml` protège l’arbre de travail sur chaque PR et ne produit jamais
de résultat scientifique. Les workflows d’évaluation scellée restent créés par
expérience, exécutés une fois, puis retirés vers `archives/workflows/` : un workflow
canonique consommé ne doit plus être exécutable, sans quoi la règle du run unique ne
tient que par convention.

`scripts/check_repository_integrity.py` rend structurels les trois défauts qui avaient
échappé à la CI : module non importable, module orphelin, dépendance déclarée fantôme.

## D009 — Le prochain progrès accepté doit étendre le langage, pas le catalogue

D006 exigeait de M012 qu'elle supprime les compilateurs spécialisés. La même exigence
s'applique un cran plus haut : **un progrès qui consiste à mieux choisir dans un
catalogue écrit à la main n'est pas un progrès.**

M012b, M013e, M014b et M014c partagent une limite qu'aucun de leurs critères ne
mesurait. `MetaPlasticitySession.identify` énumère strictement douze programmes
structurels ; tout l'apprentissage repondère des compteurs sur ce catalogue fermé.
L'organisme ne peut rien exprimer qu'on ne lui ait donné, et M014c aurait mesuré la
qualité de cette repondération, pas la croissance d'une capacité.

M014c est donc arrêtée avant évaluation, comme M014 l'avait été, et remplacée par
M017 — langage auto-extensible. La feuille de route change d'ordre, pas de noms :
M015 et M016 sont reportées parce qu'elles étendraient latéralement un paradigme dont
le cœur n'est pas établi.

## D010 — Une grandeur mesurée doit avoir une plage dynamique

M014b comparait 14 requêtes à 14 requêtes, sur une fenêtre large de quatre requêtes,
avec une marge préenregistrée de 25 %. Aucun résultat n'y était décidable : le critère
mesurait du bruit d'échantillonnage.

Toute expérience ultérieure doit donc établir, **avant de figer son protocole**, que
la grandeur choisie varie sur plusieurs ordres de grandeur entre les organismes
comparés, et que la marge retenue dépasse la dispersion entre environnements.

Corollaire : une baseline structurellement incapable est un contrôle, pas un critère.
Le catalogue fermé échoue 0/42 en développement M017 ; figer un seuil contre lui
passerait trivialement. Le critère doit opposer deux organismes de capacité identique
au premier épisode, que seul le mécanisme testé sépare ensuite.

## D011 — Le projet suit ce que ses échecs ont désigné

Quatre expériences ont échoué — M014b, M017 sur son seuil, M018, M019 — et **aucune
n'a échoué dans l'organisme**. À chaque fois, ce qu'on construisait tenait ; c'est la
façon de juger si c'était mieux qui a cédé.

La question centrale du dépôt devient donc : **quand une mesure-proxy cesse-t-elle de
suivre ce qu'elle prétend suivre, et sous quelle pression d'optimisation ?**

### Ce que cette décision ne prétend pas

Le problème n'est ni neuf ni vierge. La loi de Goodhart, le *reward hacking*, le
*specification gaming*, la recherche de nouveauté et les algorithmes qualité-diversité
le travaillent depuis longtemps. Toute formulation suggérant que le projet explore un
terrain inoccupé serait fausse, et cette précision fait partie de la décision.

### L'angle réel

Ces travaux opèrent presque tous là où **l'objectif vrai n'est pas vérifiable
exactement** : un *reward hacking* se diagnostique parce qu'un humain trouve le
résultat suspect. Ici, l'équivalence comportementale de deux automates finis se prouve.

Le dépôt peut donc montrer **où exactement** une mesure décroche, plutôt que constater
qu'un résultat semble faux. C'est un banc d'essai décidable pour la conception de
mesures, et c'est une contribution modeste et défendable.

### Conséquences

- `MEASURES.md` devient un registre de premier rang, à côté de `FAILURE_LOG.md` ;
- la ligne métamorphose n'est pas abandonnée : elle a produit le domaine décidable, les
  deux validations scellées et les six cas de divergence. Elle devient le **support**
  de la question plutôt que la question ;
- M017 reste à figer, ses résultats étant acquis et son critère assaini.
