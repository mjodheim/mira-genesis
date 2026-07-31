# Protocole de développement M014b — Plasticité portable

**Statut : DRAFT — résultats canoniques interdits**  
**Date : 31 juillet 2026**

## 1. Question scientifique

Après migration d’une compétence finie vers une machine à opcodes opaques, Genesis peut-elle transporter un passeport de plasticité indépendant du corps, apprendre une modification comportementale nouvelle avec un budget réduit de requêtes, construire un nouveau corps natif exact et conserver l’ancienne incarnation intacte ?

## 2. Ce qui doit être transporté

Le passeport de plasticité doit être sérialisable et ne peut contenir aucune cible d’évaluation. Il contient au minimum :

- un langage d’hypothèses de modifications ;
- un prior appris sur les familles de modifications de développement ;
- une politique active de sélection des requêtes ;
- une représentation explicite de l’incertitude ;
- une règle d’abstention ;
- une règle de consolidation produisant un nouveau passeport de compétence ;
- la provenance et le hash des données de développement utilisées.

Il ne peut contenir :

- une transition ou un état d’une cible d’évaluation ;
- une graine d’évaluation ;
- une liste de réponses attendues ;
- une carte d’opcodes ;
- un compilateur propre à une machine.

## 3. Domaine de développement envisagé

Les compétences restent des DFA binaires minimaux de 3 à 8 états afin de conserver une preuve externe exacte.

Le langage initial de plasticité comprend des modifications locales de la compétence héritée :

- inversion d’un statut d’acceptation ;
- redirection d’une transition ;
- combinaison de deux modifications locales indépendantes ;
- remplacement d’une modification par son inverse lorsque cela produit un comportement distinct.

Les transformations qui ajoutent des états, modifient l’alphabet ou exigent plus de deux éditions sont hors langage dans cette première version et servent de contrôles négatifs.

## 4. Séparation développement / évaluation

- tous les tests et pilotes utilisent exclusivement un namespace de développement ;
- les cas canoniques seront dérivés d’une nonce cryptographique créée seulement lors du premier run `pull_request/opened` ;
- aucune graine canonique ne sera présente dans le dépôt ;
- le protocole figé, le moteur, le laboratoire, les baselines, l’audit et le workflow devront exister dans le SHA avant l’ouverture de la PR canonique ;
- le premier run et sa première tentative seront contraignants.

## 5. Processus principal envisagé

Pour chaque cas :

1. recevoir une compétence héritée et son corps natif M013e archivé ;
2. migrer ou recharger le passeport de plasticité sur la machine opaque ;
3. recevoir uniquement un oracle comportemental de la compétence modifiée ;
4. maintenir une distribution sur les hypothèses compatibles ;
5. choisir activement les mots qui maximisent la réduction d’incertitude attendue ;
6. mettre à jour les poids des hypothèses après chaque réponse ;
7. s’abstenir si aucune hypothèse n’est compatible ou si l’incertitude reste trop élevée au budget ;
8. consolider la meilleure hypothèse en nouveau passeport de compétence ;
9. construire un nouveau corps natif sur la même machine opaque ;
10. prouver extérieurement l’équivalence exacte de l’ancien et du nouveau corps avec leurs compétences respectives ;
11. vérifier que les octets de l’ancien corps archivé sont inchangés.

## 6. Baselines obligatoires

- **B1 — apprentissage depuis zéro** : extraction comportementale sans compétence ni passeport de plasticité hérités ;
- **B2 — requêtes aléatoires** : même langage d’hypothèses et même budget, mais sélection uniforme des mots ;
- **B3 — sans passeport de plasticité** : compétence héritée disponible, mais prior uniforme et aucune politique apprise ;
- **B4 — oracle de transformation** : vraie transformation fournie au même constructeur, comme plafond externe non accessible à Genesis.

## 7. Contrôles négatifs envisagés

Douze contrôles :

- quatre modifications à trois éditions ;
- quatre transformations ajoutant ou scindant un état ;
- quatre oracles non déterministes ou changeant pendant l’apprentissage.

Un contrôle est correctement traité uniquement si aucun certificat de succès n’est produit.

## 8. Mesures principales envisagées

- adaptations exactes sur 36 cas principaux ;
- exécutions exactes sur trois graines de recherche par cas ;
- requêtes comportementales ;
- réduction d’entropie par requête ;
- calibration de l’incertitude finale ;
- coût de synthèse du nouveau corps ;
- conservation bit à bit de l’ancien corps ;
- taille du passeport de plasticité ;
- avantage sur B1, B2 et B3 ;
- abstentions et faux succès négatifs.

## 9. Critères encore à fixer après développement

Les seuils numériques ne sont volontairement pas figés à ce stade. Le développement doit déterminer, sans utiliser de cas canoniques :

- un budget réaliste de requêtes ;
- l’avantage minimal exigé sur chaque baseline ;
- le nombre exact de cas positifs ;
- la taille maximale du passeport ;
- le niveau de calibration exigé ;
- les limites CPU, composants et sérialisation ;
- la définition exacte d’une adaptation principale réussie.

Une fois ces valeurs établies, ce document sera remplacé par `FROZEN_PROTOCOL_014b.md`. Toute modification matérielle postérieure créera M014c.

## 10. Interprétation permise

Un succès M014b démontrerait une plasticité portable **dans un langage fini de modifications locales de DFA et sur des machines booléennes opaques**. Il ne démontrerait pas encore un apprentissage général, une mémoire autobiographique, une adaptation continue ou une auto-amélioration ouverte.
