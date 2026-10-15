# Black Halo: vrais tests de requêtes

Ces tests complètent les tests unitaires. Ils ne les remplacent pas.

## 1. Test d'une vraie requête avec le modèle local

Prérequis :
- Python et les dépendances du projet installés ;
- Ollama lancé ;
- le modèle choisi téléchargé localement (par défaut `qwen2.5:7b`).

Depuis la racine du dépôt :

```bash
python scripts/live_agent_smoke.py
```

Avec un autre modèle :

```bash
python scripts/live_agent_smoke.py --model llama3.2:3b
```

Le script envoie une vraie demande à l'agent, qui doit créer puis relire `live_check.txt`. Les outils exposés sont volontairement limités à la lecture, l'écriture et la liste de fichiers dans un dossier temporaire isolé. Aucun outil de shell, navigateur, suppression ou réseau n'est donné au modèle. Le résultat affiche l'état final, les appels d'outils et le contenu réellement lu. Le test échoue si le fichier n'existe pas, si son contenu est incorrect ou si l'agent ne termine pas correctement.

Le test utilise le vrai modèle local et le vrai agent, mais **pas l'interface graphique complète**. Un échec peut venir du modèle, de sa disponibilité ou du comportement de l'agent : lire le rapport avant de conclure.

## 2. Test manuel sur le PC Windows

À réaliser dans l'application réelle, car GitHub Actions ne peut pas confirmer le comportement du HUD sur le PC de l'utilisateur.

- [ ] Envoyer une demande simple et vérifier le résultat concret.
- [ ] Demander une action multi-étapes et vérifier chaque étape.
- [ ] Demander une action impossible et vérifier que BH annonce l'échec sans inventer de réussite.
- [ ] Refuser une confirmation et vérifier que l'action sensible ne s'exécute pas.
- [ ] Vérifier que l'état du HUD suit réellement l'écoute, l'action, l'attente, la réussite ou l'échec.
- [ ] Relancer BH et vérifier qu'il démarre sans erreur.
- [ ] Noter le modèle utilisé, le temps de réponse, les erreurs et les ressources CPU/RAM observées.

Ne jamais utiliser un test réel pour supprimer des fichiers importants, modifier des réglages sensibles ou lancer des commandes dangereuses. Utiliser des fichiers de test jetables et vérifier les effets réels plutôt que de se fier uniquement au texte de réponse.

## 3. Interprétation

- **Tests unitaires verts** : les règles de code testées passent.
- **Test live vert** : une vraie requête du modèle local a réussi dans le bac à sable.
- **Test manuel Windows validé** : le parcours testé fonctionne dans l'application réelle sur ce PC.

Aucun de ces niveaux ne garantit à lui seul que toutes les demandes possibles fonctionneront. Les rapports doivent conserver les échecs au lieu de les masquer.
