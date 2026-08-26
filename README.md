# J.A.R.V.I.S. NEO

> Assistant personnel local-first, modulaire et orienté contexte.

J.A.R.V.I.S. NEO est un projet expérimental d'assistant personnel pour PC. L'objectif est de dépasser le simple assistant à commandes : NEO doit pouvoir comprendre le contexte, apprendre des habitudes, exécuter des actions composées et rester contrôlable par l'utilisateur.

## Vision

NEO est organisé autour de plusieurs briques :

- **Context Engine** — observation locale légère et détection de contextes/habitudes.
- **Action Engine** — exécution d'actions autorisées avec cooldown et journalisation.
- **Agent** — traitement d'instructions et orchestration des capacités.
- **Memory / Store** — événements et souvenirs persistants.
- **HUD** — interface cockpit et représentation de l'état de NEO.
- **Plugins** — extension des capacités avec permissions.
- **Mobile** — contrôle et notifications via le réseau local.
- **Security / Privacy** — permissions, appareils autorisés et futurs mécanismes de coupure d'urgence.

## Architecture actuelle

```text
Utilisateur
    │
    ▼
  Agent
    │
    ├──────────► Actions
    │
    ├──────────► Plugins
    │
    └──────────► Assistant / IA

Context Engine
    │
    ├── événements locaux
    ├── habitudes
    └── contexte détecté
             │
             ▼
       Action Engine
             │
             ▼
        NEO / HUD
```

## Context Engine

`context_engine.py` fonctionne localement et ne fait pas d'appel LLM. Il peut observer des processus autorisés, détecter des signaux de gaming, tenir compte de l'heure et du jour, apprendre à partir des activations manuelles, enregistrer les événements dans SQLite et produire un niveau de confiance pour un contexte.

La base est stockée dans `neo_context.db` à côté du projet et un état courant est écrit dans `neo_context_state.json`.

## Action Engine

`action_engine.py` fournit un registre d'actions explicites. Il ne lance pas arbitrairement des commandes shell : les actions doivent être enregistrées dans le moteur.

L'action `gaming_mode` est prévue pour appeler le processeur NEO avec `active le mode gaming` lorsque le contexte gaming atteint un niveau de confiance suffisant. Un cooldown évite les déclenchements répétés.

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
- feedback rapide.

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

Le projet est principalement Python et utilise notamment SQLite, FastAPI/Uvicorn et `psutil` selon les composants installés. Certains modules sont optionnels et doivent rester capables de fonctionner lorsque leurs dépendances ne sont pas disponibles.

**Important :** le projet évolue rapidement. Avant une modification importante, créer un commit afin de pouvoir revenir en arrière facilement.
