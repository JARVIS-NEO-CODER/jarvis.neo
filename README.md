# 🧠 J.A.R.V.I.S. NEO

> **Un assistant personnel local-first qui comprend son contexte, agit sur le PC et évolue avec son utilisateur.**

> [!WARNING]
> 🔴 **OLLAMA DOIT ÊTRE INSTALLÉ SÉPARÉMENT SUR LE PC.**
>
> J.A.R.V.I.S. NEO n'embarque pas le moteur Ollama ni les modèles dans son `.exe`. Il faut installer Ollama séparément et télécharger au moins un modèle local avant le premier lancement.

---

## 🔐 Mode Sentinelle

Le mot de passe du **Mode Sentinelle** est :

```text
SENTINEL-NEO-2026
```

Ce code sert uniquement au verrouillage du mode Sentinelle dans NEO. Il ne doit pas être considéré comme un secret cryptographique ou une protection de compte.


## 🚀 Installation rapide depuis zéro

Cette section est le parcours à suivre sur un PC Windows fraîchement installé. **Si tu ne connais pas le projet, commence ici et suis les étapes dans l'ordre.**

### 1. Prérequis

NEO est prévu en priorité pour **Windows 10/11**.

Il est recommandé d'avoir :

- un PC 64 bits ;
- 8 Go de RAM minimum, 16 Go recommandés ;
- un microphone si tu veux utiliser la voix ;
- une connexion Internet pour installer les composants et utiliser les fournisseurs cloud ;
- suffisamment d'espace disque pour Ollama et le modèle local.

> ⚠️ NEO peut fonctionner avec une machine modeste, mais les modèles IA locaux peuvent être lourds. Plus le modèle est grand, plus la consommation de RAM/CPU augmente.

### 2. Installer Python

Si tu utilises le projet depuis ses sources, installe **Python 3.11**.

Pendant l'installation de Python, active l'option :

**Add Python to PATH**

Puis ouvre un nouveau terminal et vérifie :

```powershell
python --version
```

Tu dois obtenir une version Python 3.11.x.

Si `python` n'est pas reconnu, Python n'est pas correctement installé ou n'est pas présent dans le PATH.

### 3. Télécharger J.A.R.V.I.S. NEO

Tu peux utiliser la version `.exe` fournie par le projet ou récupérer le code source depuis GitHub.

Pour une installation depuis les sources :

```powershell
git clone https://github.com/JARVIS-NEO-CODER/jarvis.neo.git
cd jarvis.neo
```

Si Git n'est pas installé, installe Git pour Windows puis recommence cette étape.

### 4. 🔴 Installer Ollama

**Ollama n'est PAS inclus dans J.A.R.V.I.S. NEO.**

Installe Ollama séparément sur le PC, puis vérifie qu'il fonctionne :

```powershell
ollama --version
```

Ensuite, télécharge le modèle local recommandé par la configuration de NEO :

```powershell
ollama pull llama3.2:3b
```

Vérifie ensuite que le modèle est disponible :

```powershell
ollama list
```

Tu dois voir `llama3.2:3b` dans la liste.

> 💡 Si tu choisis un autre modèle, assure-toi qu'il correspond au modèle configuré dans NEO. Les modèles de vision sont séparés du modèle conversationnel.

### 5. Installer les dépendances

Depuis le dossier du projet :

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si `requirements.txt` n'existe pas dans la version que tu as téléchargée, **arrête-toi ici** : la distribution que tu utilises n'est pas correctement préparée pour cette méthode d'installation. N'installe pas une liste de paquets trouvée au hasard sur Internet.

### 6. Configurer NEO

Lance NEO une première fois. Les paramètres permettent notamment de configurer :

- le fournisseur IA ;
- la clé API Groq si tu utilises Groq ;
- le modèle cloud ;
- le modèle Ollama ;
- le mode de fallback lorsque le quota cloud est atteint ;
- le délai d'attente ;
- le démarrage automatique de Windows.

🔐 **Ne mets jamais ta clé API Groq directement dans le code source ou dans un dépôt GitHub.** Utilise les paramètres prévus par NEO.

### 7. 🚀 Premier lancement depuis les sources

Dans le dossier du projet :

```powershell
python assistant.py
```

Si Windows affiche une erreur indiquant qu'un module Python manque, vérifie d'abord que l'étape 5 a été effectuée dans le même environnement Python.

### 8. 📦 Utiliser la version `.exe`

Si tu disposes de `JARVIS_NEO.exe`, tu n'as normalement pas besoin de lancer `assistant.py`.

Cependant, **l'installation d'Ollama reste nécessaire** si ta configuration utilise le moteur local.

Lance simplement :

```text
JARVIS_NEO.exe
```

Au premier démarrage, vérifie que :

1. le HUD apparaît ;
2. NEO indique correctement son fournisseur IA ;
3. Ollama est détecté si le mode local est utilisé ;
4. le microphone fonctionne si la voix est activée ;
5. une demande simple reçoit une réponse.

### 9. 🎙️ Tester la voix

Si la voix est activée, vérifie que Windows voit correctement ton microphone.

Commence par une commande simple. Par exemple :

```text
Jarvis, quelle heure est-il ?
```

Une fois la session vocale commencée, les demandes de suivi peuvent être effectuées sans répéter le mot d'activation pendant la courte fenêtre de conversation prévue par NEO.

### 10. 🧪 Vérification finale

Une installation est considérée comme fonctionnelle lorsque :

- [ ] NEO démarre sans erreur bloquante ;
- [ ] le HUD fonctionne ;
- [ ] le fournisseur IA affiché correspond réellement au fournisseur utilisé ;
- [ ] Ollama répond si le mode local est choisi ;
- [ ] le modèle configuré est installé ;
- [ ] une conversation simple fonctionne ;
- [ ] la voix fonctionne si elle est activée ;
- [ ] une action demandée est vérifiée avant d'être annoncée comme terminée ;
- [ ] le fallback cloud/local fonctionne lorsque sa condition est déclenchée.

---

## 🛠️ Dépannage rapide

### `python` n'est pas reconnu

Réinstalle Python 3.11 en activant **Add Python to PATH**, puis ouvre un nouveau terminal.

### `ollama` n'est pas reconnu

Ollama n'est pas installé ou son installation n'est pas disponible dans le PATH. Installe Ollama séparément, puis ouvre un nouveau terminal.

### Le modèle Ollama est introuvable

Vérifie :

```powershell
ollama list
```

Puis installe le modèle attendu, par exemple :

```powershell
ollama pull llama3.2:3b
```

### NEO utilise un autre fournisseur que prévu

Ouvre les paramètres et vérifie le fournisseur sélectionné, le modèle et le mode de fallback. Le HUD doit refléter l'état réel du fournisseur utilisé.

### Groq ne fonctionne plus après plusieurs requêtes

Le quota ou une limite du fournisseur peut avoir été atteint. Vérifie la configuration du fallback. NEO peut basculer vers Ollama ou vers le mode Simple selon le choix enregistré.

### Le microphone ne fonctionne pas

Vérifie dans **Paramètres Windows → Système → Son → Entrée** que le bon microphone est sélectionné et autorisé.

### NEO ralentit le PC

Les modèles locaux peuvent consommer beaucoup de CPU/RAM. Utilise un modèle plus léger, réduis les fonctions lourdes et vérifie le mode Performance/Gaming lorsque tu joues.

---

## ❓ FAQ

### Est-ce qu'Ollama est inclus dans NEO ?

**Non.** Ollama doit être installé séparément sur le PC. Les modèles sont eux aussi téléchargés séparément.

### Est-ce qu'une clé Groq est obligatoire ?

**Non**, si tu utilises uniquement un modèle local avec Ollama. Une clé Groq est nécessaire pour utiliser le fournisseur Groq.

### Est-ce que NEO envoie toutes mes conversations dans le cloud ?

Non par principe : NEO est conçu selon une approche **local-first**. Les requêtes envoyées à un fournisseur cloud dépendent du fournisseur et de la configuration choisie.

### Puis-je jouer pendant que NEO fonctionne ?

Oui, mais la charge dépend des fonctions activées et du modèle utilisé. Le projet prévoit une gestion des performances afin de limiter les fonctions coûteuses lorsque le PC est fortement sollicité.

---

## 🧩 Le concept

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
- 📖 documentation de l'architecture ;
- 🤖 pont Groq ↔ Ollama avec fallback ;
- 🧩 Agent avec vérification des actions ;
- 🎨 HUD discret en arrière-plan ;
- 🪟 démarrage automatique Windows configurable.

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
