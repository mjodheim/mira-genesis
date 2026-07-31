# Reproductibilité

## Reproduire l'arbre de travail

1. Python 3.11 ou plus récent.
2. `pip install -e ".[dev]"`.
3. `pytest -q` — la suite complète doit passer.
4. `python scripts/check_repository_integrity.py` — importabilité, absence de module
   orphelin et cohérence des dépendances déclarées.

Ces quatre étapes sont exactement celles exécutées par `.github/workflows/ci.yml` sur
chaque pull request, en Python 3.11 et 3.13.

## Reproduire un résultat canonique

Chaque résultat canonique est identifié dans `results/<ID>.md` par :

- le SHA du commit évalué, immuable ;
- le SHA-256 du protocole figé ;
- l'identifiant et le numéro de tentative du run GitHub Actions ;
- le SHA-256 de l'artefact de preuve.

La reproduction se fait à partir du nonce publié, en repartant du commit évalué :

```bash
git checkout <SHA évalué>
python scripts/run_<ID>_evaluation.py --help
```

La recette CI exacte de chaque évaluation scellée déjà consommée est conservée dans
`archives/workflows/`. Ces workflows sont volontairement rendus non exécutables : la
règle « un seul run canonique, jamais rejoué » interdit de les relancer.

## Contenu attendu d'un futur résultat

Tout nouveau résultat doit contenir la graine, le commit Git, le hash du protocole et
une trace de décision portable bit à bit. M014b a montré qu'un hash de consolidation
incorporant des scores flottants n'est pas reproductible d'un environnement à l'autre :
les décisions et les hashes doivent reposer sur des entiers ou des rationnels canoniques.

## Périmètre

Les scripts présents dans `scripts/` correspondent aux expériences **M012b et
suivantes**. Aucun code M001–M011 n'existe dans ce dépôt ; voir `archives/README.md`.
