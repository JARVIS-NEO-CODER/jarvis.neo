# J.A.R.V.I.S. NEO Mobile

Application mobile cross-platform (Expo / React Native) destinée à piloter J.A.R.V.I.S. NEO.

## Flux
1. Installer l'application.
2. Saisir l'IP/nom local et le port du PC (8890 par défaut).
3. Appuyer sur « Générer un code » côté PC.
4. Entrer le code à 6 chiffres dans l'app.
5. L'application conserve le token localement et ouvre le WebSocket.

## Protocole NEO Mobile v1

HTTP:
- `POST /api/pair-code` → `{code, expires_in}`
- `POST /api/pair` body `{code,name}` → `{device_id,token}`
- `GET /api/system`
- `GET /api/devices`
- `POST /api/command` body `{token,command,confirmed}`
- `POST /api/agent` body `{instruction,confirmed}`
- `POST /api/agent/stop`
- `GET /api/events`

WebSocket:
- `ws://HOST:8890/ws?token=TOKEN`
- client → `{type:"ping"}`
- client → `{type:"command",id,command,confirmed}`
- server → `{type:"event",event:"notification",payload:{...}}`
- server → `{type:"response",id,ok,result}`
- server → `{type:"status",payload:{...}}`

Le serveur doit valider le token avant toute commande. Les actions sensibles doivent conserver le mécanisme de confirmation de J.A.R.V.I.S.

> Pour un usage hors réseau local, ne pas exposer directement le port 8890 sur Internet : utiliser un tunnel/VPN sécurisé et HTTPS/WSS.
