# J.A.R.V.I.S. NEO Mobile

Application mobile cross-platform (Expo / React Native) destinée à piloter J.A.R.V.I.S. NEO sur le réseau local.

## Première connexion

1. Lancer J.A.R.V.I.S. NEO sur le PC.
2. Dans le HUD PC, cliquer sur **📱 MOBILE**.
3. Relever l'adresse IP, le port `8890` et le code d'appairage affichés.
4. Dans NEO Mobile, saisir l'adresse IP, le port et le code, puis appuyer sur **APPARIER**.
5. Le téléphone conserve son token localement et se reconnecte automatiquement après une coupure réseau ou un redémarrage du PC.

## Fonctionnalités synchronisées

- Dashboard système : CPU, RAM, disque, batterie.
- État IA : fournisseur et modèle.
- États micro, voix, écoute et traitement.
- Commandes PC via l'API authentifiée.
- Flux d'événements en temps réel via WebSocket.
- Reconnexion automatique.
- Historique d'événements côté mobile.
- Plusieurs appareils autorisés côté PC.
- Tokens persistants et appairage à code unique avec expiration.

## Protocole NEO Mobile v1

HTTP sur le LAN :
- `POST /api/pair` → `{code,name,device_id?}` → `{device_id,token}`
- `GET /api/system?token=TOKEN`
- `GET /api/devices?token=TOKEN`
- `POST /api/command` → `{token,command,confirmed}`
- `POST /api/agent` → `{token,instruction,confirmed}`
- `POST /api/agent/stop` → `{token}`
- `GET /api/events?token=TOKEN`

WebSocket :
- `ws://HOST:8890/ws?token=TOKEN`
- client → `{type:"ping",token,id}`
- client → `{type:"status",token,id}`
- client → `{type:"sync",token,id}`
- client → `{type:"command",token,id,command,confirmed}`
- server → `{type:"status",payload:{...}}`
- server → `{type:"state",state:{...}}`
- server → `{type:"event",event,payload,ts}`
- server → `{type:"response",id,ok,result}`

Le serveur valide le token avant toute lecture protégée ou commande. Les actions sensibles doivent conserver le mécanisme de confirmation de J.A.R.V.I.S.

La passerelle est prévue pour le **réseau local**. Pour un accès hors réseau local, ne pas exposer directement le port `8890` sur Internet : utiliser ultérieurement un tunnel/VPN sécurisé avec HTTPS/WSS.
