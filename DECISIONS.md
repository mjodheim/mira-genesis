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
