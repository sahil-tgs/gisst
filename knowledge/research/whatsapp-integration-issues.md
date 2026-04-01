# WhatsApp Integration Issues — 2026-04-01

## Problem
All versions of @whiskeysockets/baileys (v6.7.21, v6.17.16, v7.0.0-rc.9, GitHub master) fail to connect to WhatsApp. The connection dies at the protocol handshake with status 405 (Method Not Allowed) or 428 (Precondition Required). The QR code event never fires. This happens on both Bun and Node.js.

## Root Cause
WhatsApp frequently updates their Web protocol. Baileys reverse-engineers this protocol and breaks when WhatsApp pushes updates. As of 2026-04-01, all published versions appear broken.

## Alternatives Investigated
1. **whatsapp-web.js** — Uses Puppeteer to run actual WhatsApp Web in headless Chrome. More resilient to protocol changes since it's the real client. Needs Chromium installed. v1.34.6 available on npm.
2. **WhatsApp Cloud API** — Official Meta API. User's Facebook account is suspended, blocking this path.
3. **Telegram Bot API** — Could pivot to Telegram as the initial channel (was Phase 0 in the README). Official API, no reverse engineering, stable.

## Decision Needed
- Try whatsapp-web.js (needs Chromium, heavier but more stable)
- Pivot to Telegram for prototype (simplest, most stable, official API)
- Wait and try Baileys again later
