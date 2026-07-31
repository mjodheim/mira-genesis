# Reproductibilité

1. Utiliser Python 3.11 ou plus récent.
2. Installer avec `pip install -e ".[dev]"`.
3. Exécuter `pytest -q`.
4. Chaque script dans `scripts/` correspond aux expériences historiques M001–M011.
5. Les résultats canoniques sont dans `results/`; l’archive complète historique est dans `archives/`.
6. Les futurs résultats doivent contenir la graine, le commit Git et le hash du protocole.
