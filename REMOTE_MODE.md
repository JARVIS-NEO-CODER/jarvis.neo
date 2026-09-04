# JARVIS NEO Remote Mode

Remote Mode connects the JARVIS NEO Mobile app to the PC over the Internet without exposing the PC's local WebSocket port.

Architecture:

`Mobile (4G/5G) -> WSS relay -> outbound WSS tunnel -> JARVIS NEO PC`

The PC opens the outbound connection. Port `8890` remains a LAN-only service and is never published by Remote Mode.

## Relay deployment

The relay is in `remote_relay/` and requires Python 3.11+, FastAPI and Uvicorn. A Dockerfile is provided.

Example:

```bash
cd remote_relay
docker build -t jarvis-neo-relay .
docker run --rm -p 8080:8080 -e PORT=8080 jarvis-neo-relay
```

For production, put the relay behind a TLS reverse proxy and use a public `wss://` URL. Do not use plain `ws://` on the Internet.

The relay is intentionally stateless: it stores no JARVIS account data, tokens or conversation data. It only holds live WebSocket connections in memory.

## PC configuration

Set the relay URL before starting JARVIS NEO:

`JARVIS_REMOTE_RELAY_URL=wss://your-relay.example/ws`

On first startup the PC creates a random Remote Node ID and tunnel secret in:

`~/.jarvis_neo/remote.json`

The launcher logs the Node ID when the outbound tunnel is enabled. Keep the generated file private.

## Mobile configuration

The mobile app must first be paired with the PC on the local network so it has the normal device token. Then open:

`Devices -> JARVIS NEO PC -> Mode Remote 4G / 5G`

Enter:

1. the relay `wss://...` URL;
2. the PC Remote Node ID shown by JARVIS NEO.

Save, then connect. The mobile client authenticates through the existing per-device PC token after the relay attaches it to the PC tunnel.

## Security model

- Protocol is fixed to `jarvis-neo/1`.
- Relay accepts only WSS-compatible client URLs from the application.
- PC tunnel authentication uses a random secret.
- Mobile access is authenticated by the existing device-bound PC token.
- Tokens are never placed in discovery packets.
- The PC's LAN port 8890 is not opened by Remote Mode.
- The relay enforces a 64 KiB frame limit and rejects invalid protocol/roles.
- High-risk PC actions remain blocked behind the existing local-confirmation policy.

## Current scope

Remote Mode currently transports the existing JARVIS NEO protocol: authentication, state/sync, ping, events and allowlisted actions. Remote desktop/video streaming is intentionally not included yet because it needs a separate low-latency media/input transport.

A real Internet end-to-end test still requires a deployed TLS relay plus one running PC and one physical Android/iOS device. The repository CI validates the code contracts and build/analyzer checks, but cannot prove a real cellular path by itself.
