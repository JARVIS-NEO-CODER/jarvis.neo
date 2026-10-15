# Black Halo Roadmap

## Direction produit

Black Halo doit être un assistant personnel du quotidien, utilisable pour une raison concrète à la fois, à la manière d'un Google Home, avec en plus la capacité d'agir sur le PC et d'aider sur des tâches complexes. L'interface doit rester rapide, utile et adaptée à la machine de l'utilisateur.

## Priorités

### 1. Fiabiliser l'agent et ses actions
- [ ] Vérifier le parcours complet demande → plan → outils → résultat → HUD.
- [ ] Empêcher toute annonce de réussite sans preuve réelle d'exécution.
- [ ] Améliorer la récupération après une erreur sans répéter inutilement la même action.
- [ ] Valider le fonctionnement de bout en bout dans l'application, au-delà des tests automatisés.

### 2. HUD dynamique piloté par l'IA
- [ ] Laisser l'IA décider quels boutons, commandes, panneaux et informations afficher selon la demande, le contexte et les préférences de l'utilisateur.
- [ ] Permettre à l'interface de réorganiser, afficher ou masquer ses éléments en direct.
- [ ] Permettre à l'IA de proposer ou composer de nouvelles commandes à partir des capacités réellement disponibles, plutôt que de se limiter à un menu figé.
- [ ] Garder les fonctions essentielles faciles à retrouver et permettre à l'utilisateur de garder le contrôle.
- [ ] Refléter l'état réel de BH dans le HUD : écoute, réflexion, action, attente, réussite ou erreur.
- [ ] Apprendre les préférences au fil de l'usage, sans supposer qu'elles sont permanentes.
- [ ] Respecter les permissions et confirmations configurées pour les actions sensibles.

### 3. Utilité quotidienne
- [ ] Rendre les demandes courantes rapides à lancer par la voix ou par le HUD.
- [ ] Ajouter des actions PC concrètes et vérifiables, selon les permissions disponibles.
- [ ] Construire une mémoire utile du contexte, des préférences et des projets de l'utilisateur.
- [ ] Permettre des tâches en arrière-plan et des rappels lorsqu'ils sont réellement configurés.
- [ ] Prévoir des niveaux d'autonomie configurables, sans contourner les autorisations.

### 4. Performance et robustesse
- [ ] Garder une consommation CPU/RAM adaptée aux PC modestes.
- [ ] Tester les parcours principaux, les erreurs d'outils et les changements d'état du HUD.
- [ ] Distinguer clairement les capacités disponibles, indisponibles et non encore implémentées.

## État du travail

Dernier commit suivi : `f2a83f09a19658a44ce52b7b2dc44e3881f293e8` — correction empêchant l'agent de déclarer une tâche terminée sans résultat d'outil réussi vérifiable. Les workflows GitHub Actions observés sur ce commit étaient verts, mais cela ne remplace pas une validation manuelle de bout en bout dans l'application.
