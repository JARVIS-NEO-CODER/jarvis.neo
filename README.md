# 🧠 J.A.R.V.I.S. NEO

> **Un assistant personnel local-first qui comprend son contexte, agit sur le PC et évolue avec son utilisateur.**

J.A.R.V.I.S. NEO est un projet expérimental qui cherche à aller plus loin qu'un assistant qui attend simplement une commande.

L'idée est de construire un véritable **cockpit personnel** : NEO observe son environnement informatique, comprend ce qui est en train de se passer, adapte son comportement, peut effectuer des actions et présente son état dans une interface HUD futuriste.

---

## 🚀 Le concept

Imagine un assistant qui ne se contente pas de répondre à :

> « Lance ETS2. »

Mais qui peut progressivement comprendre :

> « Il est 20h, ETS2 vient de démarrer, le PC est déjà très sollicité… c'est probablement une session de jeu. »

NEO peut alors adapter son fonctionnement : réduire les tâches lourdes, changer son contexte, préparer les automatisations pertinentes et garder une trace locale de ce qui s'est passé.

**Le but n'est pas seulement d'avoir une IA qui parle. Le but est d'avoir un système qui comprend le contexte autour d'elle.**

---

## 🧩 Le cerveau de NEO

Le projet est progressivement séparé en plusieurs briques spécialisées :

| Module | Rôle |
|---|---|
| 👁️ **Context Engine** | Comprend ce qui se passe sur le PC et détecte les contextes. |
| 🧠 **Memory** | Conserve les événements et informations utiles localement. |
| ⚙️ **Action Engine** | Exécute des actions explicitement autorisées et vérifiables. |
| 🔄 **Automation Engine** | Transforme les contextes en règles et automatisations. |
| ⚡ **Performance Manager** | Adapte la charge de NEO aux ressources disponibles. |
| 🔌 **Core Bridge** | Relie progressivement le nouveau cœur au runtime historique. |
| 🤖 **Agent / IA** | Traite les demandes et orchestre les capacités. |
| 🎨 **HUD** | Représente l'état de NEO dans une interface cockpit. |
| 🧩 **Plugins** | Permet d'ajouter des capacités avec des permissions. |
| 📱 **Mobile** | Étend le contrôle et les notifications au téléphone. |

---

## 🏗️ Architecture

```text
                         J.A.R.V.I.S. NEO
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        👁️ Contexte          🧠 Mémoire           🤖 IA / Agent
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                           ⚙️ Action Engine
                                  │
                           🔄 Automation
                                  │
                ┌─────────────────┼─────────────────┐
                ▼                 ▼                 ▼
             🖥️ PC              🎨 HUD            📱 Mobile
```

Le nouveau cœur vit dans `core/` afin de ne plus concentrer toute la logique dans `assistant.py`.

```text
core/
├── memory.py
├── context_engine.py
├── action_engine.py
├── automation.py
├── performance_manager.py
└── core_bridge.py
```

Le `CoreBridge` est volontairement léger : il ne lance pas lui-même Ollama et ne crée pas de boucle autonome. Le runtime principal décide quand exécuter un cycle, ce qui permet de garder NEO utilisable sur des machines modestes.

---

## 🎮 NEO comprend le contexte

Le **Context Engine** fonctionne localement et ne nécessite pas de requête LLM pour détecter un contexte.

Il peut combiner plusieurs signaux :

- processus actifs ;
- heure et jour ;
- activations manuelles ;
- historique local ;
- signaux liés au gaming ;
- autres indicateurs système.

L'objectif est de passer progressivement de simples règles à une compréhension plus riche des habitudes quotidiennes.

### Exemple

```text
ETS2 démarre
     ↓
Contexte gaming détecté
     ↓
Confiance suffisante
     ↓
🎮 Gaming Mode
     ↓
NEO réduit les fonctions lourdes
```

Tout cela peut fonctionner **sans demander à Ollama de décider à chaque seconde**.

---

## ⚡ Respecter le PC

NEO doit être intelligent **sans devenir le programme qui ralentit tout le reste**.

Le Performance Manager permet de réduire la fréquence ou de désactiver certaines fonctions coûteuses selon le contexte.

C'est particulièrement important pendant les jeux : l'objectif est que NEO puisse rester présent sans venir manger inutilement les ressources du PC.

---

## 🎨 Le cockpit HUD

Le HUD est pensé comme une véritable interface de cockpit plutôt qu'une simple fenêtre de chat.

À terme, il doit pouvoir représenter les états de NEO :

`IDLE` → `LISTENING` → `THINKING` → `EXECUTING` → `SPEAKING`

et afficher des informations contextuelles au bon moment.

Une idée importante du projet est que **la réponse et l'interface évoluent ensemble** : lorsque NEO parle d'un sujet, il peut afficher une fenêtre, une donnée ou une visualisation pertinente au même moment.

Le HUD doit également intégrer des animations et des transitions afin de donner à NEO une présence plus naturelle.

---

## 🔊 Une présence, pas seulement une voix

NEO doit pouvoir adapter sa communication au contexte :

- 🔊 voix et effets sonores lorsque c'est pertinent ;
- 🔇 mode silencieux lorsque parler serait gênant ;
- 🎧 retours audio discrets pour les états du système ;
- 🖥️ notifications et informations visuelles lorsque l'audio n'est pas approprié.

L'objectif est d'éviter l'effet « robot qui parle en permanence » et de construire une vraie couche d'interaction.

---

## 🧠 Mémoire et apprentissage

NEO doit pouvoir conserver localement les événements utiles et apprendre progressivement des habitudes.

Une évolution prévue est un système de feedback simple : si une automatisation est incorrecte, l'utilisateur peut l'indiquer et NEO peut ajuster son comportement futur.

À plus long terme, le projet vise également une **base de connaissances personnelle locale** capable de retrouver des notes, documents et ressources de travail sans envoyer ces données vers le cloud.

---

## 📱 Un écosystème autour du PC

Le PC n'est pas forcément le seul point d'accès à NEO.

Le projet prévoit :

- 📱 contrôle et notifications mobiles ;
- 🔐 communication locale sécurisée ;
- 🏠 intégration domotique locale ;
- 🧩 plugins pour étendre les capacités.

L'objectif est de construire un écosystème cohérent plutôt qu'une simple application isolée.

---

## 🔐 Contrôle et confidentialité

NEO est pensé **local-first** et doit rester contrôlable par l'utilisateur.

Les fonctions sensibles devront être protégées par des permissions et des confirmations explicites.

Une fonctionnalité **Panic / Privacy Mode** est prévue pour permettre de couper rapidement les fonctions de surveillance et les capteurs concernés.

La philosophie est simple : **NEO peut être puissant, mais l'utilisateur doit toujours pouvoir reprendre le contrôle.**

---

## 🛠️ État du projet

Le projet est en développement actif. Le nouveau cœur modulaire est déjà en place, tandis que l'intégration complète avec le runtime historique est progressive.

### Déjà construit

- 🧠 mémoire locale SQLite ;
- 👁️ détection de contexte ;
- ⚙️ registre d'actions ;
- 🔄 moteur d'automatisation ;
- ⚡ gestionnaire de performances ;
- 🔌 pont d'intégration du Core ;
- 🧪 premiers tests du nouveau cœur ;
- 📖 documentation de l'architecture.

### En développement / prévu

- 🧠 planification multi-étapes ;
- ✅ vérification et correction après action ;
- 🔄 apprentissage par feedback ;
- 🗄️ RAG personnel local ;
- 🕒 compréhension des habitudes quotidiennes ;
- 📝 comptes rendus d'absence ;
- 🎨 HUD animé et contextuel ;
- 🔊 audio adaptatif ;
- 📱 continuité mobile ;
- 🏠 domotique locale ;
- 🔐 Panic / Privacy Mode avancé ;
- 🧩 système de plugins avancé.

---

## 💡 Pourquoi NEO ?

Parce qu'un assistant personnel ne devrait pas être uniquement une zone de texte avec une voix.

**NEO cherche à réunir intelligence, contexte, automatisation, interface et contrôle local dans un seul système.**

Et le projet évolue petit à petit vers cette idée :

> ### **Un ordinateur qui ne se contente plus d'exécuter des commandes, mais qui comprend ce que son utilisateur est en train de faire.**

---

## 👨‍💻 Développement

NEO est principalement développé en Python et utilise notamment SQLite, FastAPI/Uvicorn, `psutil`, PyQt6 et Ollama selon les composants.

Le projet évolue rapidement : les fonctionnalités présentées dans cette README ne sont pas toutes finalisées ou intégrées au runtime principal.

Pour éviter les régressions, les modifications importantes doivent être commit avant de poursuivre le développement.
