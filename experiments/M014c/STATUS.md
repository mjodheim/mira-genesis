# M014c — Statut

- Statut scientifique : `HALTED — SUPERSEDED BY M017`
- Évaluation canonique : **jamais ouverte**
- Résultat revendiqué : **aucun**
- Branche préservée : `research/m014c-distribution-general-plasticity`, tête `fc46005`

## Ce qui a été construit

Un passeport de méta-plasticité structurelle, une session d'adaptation en ligne à
compteurs entiers, un moteur d'adaptation persistant sur substrat opaque, et un banc
de développement à profils générés. Les tests passaient, la CI était verte.

## Pourquoi l'expérience est arrêtée

Elle n'a pas échoué : elle mesurait la mauvaise chose.

`MetaPlasticitySession.identify` énumère strictement `passport.programs` — douze
programmes structurels écrits à la main. Tout l'apprentissage consiste à repondérer
des compteurs de groupe sur ce catalogue fermé. L'organisme ne peut rien exprimer
qu'on ne lui ait donné.

Le banc de développement affichait `active_to_scratch_ratio = 0,083`, ce qui se lit
comme un gain de quinze fois. C'en est un effet de taille d'automate : les DFA
hors distribution portent 7 à 10 états, donc L\* depuis zéro paye un coût qui croît
avec l'automate, tandis que Genesis paye un coût qui croît avec sa bibliothèque de
douze programmes. Agrandir les automates aurait gonflé le même ratio sans rien changer
à ce que le passeport avait appris.

La comparaison qui portait réellement l'hypothèse était l'adaptatif contre son propre
jumeau non adaptatif : `active_to_static_ratio = 0,88`. Douze pour cent, sur une tâche
dont l'optimum théorique est proche de quatre requêtes et la sélection aléatoire à
huit — une fenêtre large de quatre requêtes.

**M014b a échoué sur exactement cette géométrie** : une marge préenregistrée de 25 %,
mesurée sur une échelle trop grossière pour séparer le signal du bruit. Figer M014c
contre L\* aurait passé trivialement et répété l'erreur en sens inverse.

## Ce qui est repris

La partie du langage structurel qui n'appartient à aucune expérience — rôles, atomes,
application, formes canoniques — a été extraite dans `metamorphosis/structural.py` et
sert de socle à M017. Le passeport, la session et la politique de requêtes propres à
M014c n'ont pas été repris : ils encodent le catalogue fermé qui motive l'arrêt.

Conformément à D007, le code de M014c ne reste pas dans l'arbre de travail. La branche
`research/m014c-distribution-general-plasticity` le conserve intact, et le présent
enregistrement n'est jamais supprimé.

## Remplacement

**M017 — Langage auto-extensible.** Voir `experiments/M017/`.
