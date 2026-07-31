# Protocole figé M013 — Découverte d’un substrat inconnu

Date de gel : 31 juillet 2026
Statut : FROZEN avant toute évaluation M013

## Question scientifique

À partir d’un passeport cognitif déjà acquis et d’une machine dont les opérations natives sont désignées uniquement par des identifiants opaques, Genesis peut-elle :

1. découvrir expérimentalement la sémantique des opérations ;
2. détecter les opérations instables et les bases fonctionnelles insuffisantes ;
3. construire un corps natif exact sans carte d’opcodes ni compilateur spécifique à la machine ;
4. préserver exactement la compétence héritée après migration ?

## Relation avec le but ultime

M013 teste la première moitié du passage d’un substrat connu A vers un substrat inconnu B. La compétence est déjà contenue dans un passeport fini validé par M012. Genesis ne doit pas réapprendre la tâche : elle doit apprendre à habiter la nouvelle machine.

M013 ne transporte pas encore la mémoire autobiographique ni la stratégie générale d’apprentissage. Ces éléments restent réservés à M014–M015.

## Compétences héritées

Douze passeports DFA minimaux binaires de 3 à 8 états, générés par les graines : 12011, 12023, 12037, 12041, 12049, 12071, 12073, 12097, 12101, 12109, 12113 et 12119.

Les passeports sont fournis à Genesis. Aucun oracle comportemental de la tâche n’est accessible pendant M013.

## Substrats positifs

Trois familles de machines numériques opaques, chacune instanciée par une graine secrète figée :

- machine 13011 : base fonctionnelle dominée par NAND ;
- machine 13023 : base fonctionnelle dominée par NOR ;
- machine 13037 : base mixte à opérations redondantes.

Chaque machine expose seulement une liste d’identifiants d’opcodes opaques, leur arité déclarée, un coût natif positif, une fonction de sondage et une fonction d’exécution du corps.

Genesis ne reçoit jamais les noms logiques, tables de vérité, familles ou graines privées de la machine.

## Sondage autorisé

Pour une opération unaire, Genesis peut tester les deux entrées binaires. Pour une opération binaire, elle peut tester les quatre couples binaires. Chaque entrée est répétée trois fois pour détecter l’instabilité.

Budget maximal par rencontre avec une machine : 120 appels natifs.

## Construction du corps

Après le sondage, Genesis construit un catalogue découvert contenant uniquement les identifiants opaques, arités, tables de vérité inférées, coûts observables et indicateurs de stabilité.

Un seul synthétiseur générique énumère des expressions sur ces opcodes. Il ne contient aucun branchement selon la graine, la famille NAND/NOR/mixte ou l’identité de la machine.

Le corps sérialisé contient les identifiants opaques et sa structure, jamais les noms logiques comme instructions exécutables.

## Évaluation principale

36 migrations principales : 12 passeports × 3 machines positives. Chaque migration est répétée avec les graines de recherche 17, 31 et 59.

Une migration principale est exacte seulement si les trois répétitions produisent un corps sous budget, survivent à la sérialisation, sont exactement équivalentes au passeport selon une preuve DFA externe et atteignent 100 % sur 20 000 mots cachés de longueur 0 à 128.

## Baselines

- B1 sans sondage : assignation fixe des rôles supposés aux opcodes triés ;
- B2 sémantique aléatoire : tables de vérité aléatoires compatibles avec l’arité ;
- B3 carte oracle : vraies tables de vérité données au même synthétiseur, comme plafond externe.

## Contrôles négatifs

Douze machines impossibles : quatre bases monotones insuffisantes, quatre machines avec une primitive indispensable instable, quatre machines dont les sorties changent entre deux sondages identiques.

Un contrôle est correctement traité si Genesis s’abstient avant d’émettre un certificat de réussite.

## Budgets

- sondes du substrat : 120 ;
- évaluations de candidats : 75 000 ;
- CPU : 120 secondes ;
- composants natifs : 320 ;
- sérialisation : 16 MiB.

## Audit anti-fuite

Sont interdits : accès aux tables privées, dictionnaire opcode-rôle dépendant des graines, branchement par famille de machine, compilateur M010 et exécution d’expressions abstraites à la place des opcodes natifs.

La preuve finale reconstruit le DFA uniquement en exécutant le corps sur la machine opaque.

## Critères d’acceptation préenregistrés

M013 est VALIDATED seulement si :

1. au moins 32 migrations exactes sur 36 ;
2. au moins 10 passeports exacts sur 12 par machine ;
3. 100 % des tables stables utilisées sont correctement identifiées ;
4. aucun succès ne dépasse 120 sondes ;
5. tous les succès ont équivalence exacte et 100 % caché ;
6. la baseline sans sondage réussit au plus 8 migrations ;
7. Genesis reste à deux migrations du plafond oracle ;
8. au moins 10 contrôles sur 12 entraînent une abstention ;
9. aucun contrôle ne reçoit de faux certificat ;
10. chaque résultat contient les graines, le commit et le hash du protocole.

## Décision et limite

Statuts : VALIDATED, FAILED ou INCONCLUSIVE. Aucun critère ne peut être modifié après la première observation d’un résultat.

Même validé, M013 démontrera seulement la découverte bornée de sémantiques booléennes finies, pas l’adaptation générale à un matériel analogique, continu ou physiquement inconnu.
