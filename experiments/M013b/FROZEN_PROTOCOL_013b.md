# Protocole figé M013b — Découverte d’un substrat inconnu

Date de gel : 31 juillet 2026
Statut : FROZEN avant toute observation des nouvelles graines
Remplace : M013, contaminé pendant les tests d’implémentation

## Motif du remplacement

Les tests d’implémentation de M013 ont exécuté les graines de passeport 12011, 12023 et 12037 ainsi que les machines 13011, 13023 et 13037 avant l’évaluation formelle. Ces graines ne sont plus considérées comme cachées. Aucun résultat M013 ne peut donc recevoir le statut VALIDATED.

M013b conserve la question, les budgets, les baselines et les critères de M013, mais utilise exclusivement de nouvelles graines jamais exécutées avant ce gel.

## Question scientifique

À partir d’un passeport cognitif déjà acquis et d’une machine dont les opérations natives sont désignées uniquement par des identifiants opaques, Genesis peut-elle découvrir expérimentalement leur sémantique, détecter les substrats insuffisants ou instables, puis construire un corps natif exact sans carte d’opcodes ni compilateur spécifique ?

## Passeports cachés M013b

13211, 13217, 13229, 13241, 13249, 13259, 13267, 13291, 13309, 13313, 13327 et 13331.

Ils contiennent 3 à 8 états minimaux sur alphabet binaire. Aucun oracle comportemental de la tâche n’est accessible pendant la migration.

## Machines positives cachées

13411, 13423 et 13437. Les familles ne sont pas révélées au code Genesis. Chaque machine expose uniquement des identifiants opaques, arités, coûts, sondes et exécution.

## Graines de recherche

67, 83 et 101.

## Sondage

Toutes les entrées binaires d’un opcode sont répétées trois fois. Budget maximal : 120 appels par rencontre. Une opération non reproductible est marquée instable et exclue.

## Construction et preuve

Genesis infère un catalogue fonctionnel, synthétise un corps composé d’opcodes opaques et le sérialise. L’évaluateur reconstruit le DFA exclusivement en exécutant ce corps sur la machine. La table privée ne sert qu’à auditer l’exactitude des sémantiques déclarées, jamais à construire le corps.

## Évaluation

36 migrations principales : 12 passeports × 3 machines, chacune répétée avec les trois graines de recherche. Chaque succès doit être exactement équivalent et obtenir 100 % sur 20 000 mots cachés de longueur 0 à 128.

## Baselines

Sans sondage avec rôles fixes, sémantiques aléatoires, et carte oracle comme plafond externe.

## Contrôles négatifs

Douze nouvelles machines impossibles, graines privées 13500 à 13511 : quatre bases stables monotones insuffisantes, quatre bases dont la primitive indispensable est instable, quatre bases à sorties non reproductibles.

## Budgets

120 sondes, 75 000 candidats, 120 secondes CPU, 320 composants et 16 MiB sérialisés.

## Critères d’acceptation inchangés

1. au moins 32 migrations exactes sur 36 ;
2. au moins 10 sur 12 par machine ;
3. toutes les tables stables utilisées correctement identifiées ;
4. aucun succès au-delà de 120 sondes ;
5. équivalence exacte et 100 % caché pour tous les succès ;
6. baseline sans sondage à au plus 8 sur 36 ;
7. résultat à deux migrations au plus du plafond oracle ;
8. au moins 10 abstentions correctes sur 12 ;
9. aucun faux succès négatif ;
10. traçabilité complète graines, commit et hash.

## Limite

M013b reste un test fini de sémantiques booléennes opaques. Il ne représente pas encore un matériel continu ou une physique inconnue.
