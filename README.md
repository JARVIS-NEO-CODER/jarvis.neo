# J.A.R.V.I.S. NEO

> Assistant personnel local-first, modulaire et orienté contexte.

J.A.R.V.I.S. NEO est un projet expérimental d'assistant personnel pour PC. L'objectif est de dépasser le simple assistant à commandes : NEO doit pouvoir comprendre le contexte, apprendre des habitudes, exécuter des actions composées et rester contrôlable par l'utilisateur.

## Vision

NEO est organisé autour de plusieurs briques :

- **Context Engine** — observation locale légère et détection de contextes/habitudes.
- **Action Engine** — exécution d'actions autorisées avec cooldown et journalisation.
- **Automation Engine** — déclencheurs, conditions et workflows réversibles.
- **Performance Manager** — adaptation de la charge de NEO au contexte détecté, notamment le gaming.
- **Memory / Store** — événements et souvenirs persistants.
- **Core Bridge** — point d'intégration progressif entre le nouveau Core et l'ancien runtime.
- **Agent** — traitement d'instructions et orchestration des capacités.
- **HUD** — interface cockpit et représentation de l'état de NEO.
- **Plugins** — extension des capacités avec permissions.
- **Mobile** — contrôle et notifications via le réseau local.
- **Security / Privacy** — permissions, appareils autorisés et futurs mécanismes de coupure d'urgence.

## Architecture actuelle

Le nouveau cœur est regroupé dans `core/` afin d'éviter de concentrer toute la logique dans `assistant.py`.

```text
J.A.R.V.I.S. NEO
│
├── assistant.py              # runtime historique / interface actuelle
│
└── core/
    ├── memory.py             # stockage et historique local
    ├── context_engine.py     # détection du contexte
    ├── action_engine.py      # actions autorisées
    ├── automation.py         # règles et automatisations
    ├── performance_manager.py # adaptation de la charge
    └── core_bridge.py        # raccord progressif avec assistant.py
```

Le `CoreBridge` reste volontairement léger : il ne démarre pas de thread autonome et ne déclenche pas Ollama de lui-même. Le runtime principal décide quand exécuter un cycle, ce qui permet de limiter la consommation sur les machines peu puissantes.

## Context Engine

Le moteur fonctionne localement et ne fait pas d'appel LLM pour détecter le contexte. Il peut observer des processus autorisés, détecter des signaux de gaming, tenir compte de l'heure et du jour, apprendre à partir des activations manuelles, enregistrer les événements dans SQLite et produire un niveau de confiance pour un contexte.

La base est stockée localement et l'état courant peut être conservé pour permettre à NEO de reprendre son contexte après un redémarrage.

## Action Engine

`core/action_engine.py` fournit un registre d'actions explicites. Il ne lance pas arbitrairement des commandes shell : les actions doivent être enregistrées dans le moteur.

L'action `gaming_mode` est prévue pour appeler le processeur NEO avec `active le mode gaming` lorsque le contexte gaming atteint un niveau de confiance suffisant. Un cooldown évite les déclenchements répétés.

## Performance et gaming

Le **Performance Manager** permet de définir des profils de charge afin que les fonctions lourdes de NEO puissent être réduites lorsque le PC est déjà sollicité.

L'objectif est notamment d'éviter que la surveillance permanente, la vision ou les appels IA ne consomment inutilement des ressources pendant un jeu comme ETS2.

Les décisions de performance restent locales et ne nécessitent pas de requête Ollama.

## Philosophie de sécurité

NEO doit rester **local-first**, explicite et réversible autant que possible.

Les futures fonctionnalités de surveillance, vision, mémoire et domotique devront être désactivables et protégées par des permissions claires. Les actions sensibles devront demander une confirmation avant exécution.

## Prochaines étapes

### Intelligence
- planification multi-étapes ;
- vérification des actions ;
- correction après échec ;
- mémoire contextuelle ;
- RAG personnel local ;
- apprentissage par feedback.

### Contexte
- habitudes quotidiennes ;
- détection gaming / travail / étude / création ;
- comptes rendus d'absence ;
- contexte multi-signal.

### Interface
- HUD cockpit complet ;
- états `IDLE`, `LISTENING`, `THINKING`, `EXECUTING`, `SPEAKING`, `SENTINEL` ;
- timeline d'actions ;
- feedback rapide ;
- animations et fenêtres contextuelles synchronisées avec les réponses vocales.

### Audio
- sound design contextuel ;
- voix adaptative ;
- mode silencieux selon le contexte.

### Écosystème
- application mobile ;
- canal local chiffré ;
- domotique locale ;
- système de plugins avancé.

### Confidentialité
- Panic / Privacy Mode ;
- arrêt immédiat des capteurs ;
- stockage local protégé ;
- contrôles de rétention des historiques.

## Développement

Le projet est principalement Python et utilise notamment SQLite, FastAPI/Uvicorn, `psutil`, PyQt6 et Ollama selon les composants installés. Certains modules sont optionnels et doivent rester capables de fonctionner lorsque leurs dépendances ne sont pas disponibles.

**Important :** le projet évolue rapidement. Avant une modification importante, créer un commit afin de pouvoir revenir en arrière facilement.
