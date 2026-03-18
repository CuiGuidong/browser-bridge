# README FIRST — Browser Bridge Handoff

_Last updated: 2026-03-19_
_Status: primary entrypoint for any new developer / agent_

## Stop: read this before touching code

If you are a new developer or agent taking over this project, do **not** start by reading random source files or replaying old chat context.

Read in this order:

1. `docs/README-FIRST-HANDOFF.md`  ← you are here
2. `docs/browser-bridge-spec.md`
3. `docs/browser-bridge-plan.md`
4. `docs/browser-bridge-plan-next.md`
5. `docs/browser-bridge-task-board.md`
6. `docs/browser-bridge-acceptance.md`
7. `docs/browser-bridge-progress.md`
8. `docs/browser-bridge-open-items.md`
9. `docs/browser-bridge-dev-log.md`

Only then read code.

---

## What this project is

Browser Bridge is a local-first bridge that lets an agent operate the user's **real Chrome / Edge browser** through HTTP APIs, while preserving the user's real browser profile, cookies, and login state.

This is **not** a generic bot framework and **not** a headless scraping platform.

Primary idea:
- use the user's real browser identity safely
- combine multiple execution paths:
  - Path A: browser extension semantic hints
  - Path B: CDP direct control
  - Path C: Playwright attach

---

## Current reality of the codebase

Do not treat this repo as “still only a Phase 2 skeleton”.
That is outdated.

Current codebase already includes:
- FastAPI bridge
- CDP HTTP + WebSocket clients
- core page interaction APIs
- readiness probe and `read-page`
- Playwright attach scaffold
- MV3 browser extension
- extension -> bridge reporting
- site adapter framework
- initial X adapter
- hint-first reading where extension content can be preferred over raw CDP content

So this is now a **working prototype with architecture**, not just an initial scaffold.

---

## What is already working

### Confirmed working
- host Mac real Edge CDP connection
- OrbStack/OpenClaw -> host Mac connectivity
- `Host: 127.0.0.1:9333` workaround
- open / activate / tabs / page-info / page-content / screenshot / query / click / fill / wait
- readiness probe
- `read-page`
- extension reporting to bridge
- X page semantic extraction via extension
- `preferredContentSource=extension` on supported X page

### Confirmed partially working
- request-aware readiness architecture exists
- request signal path is not yet fully stable in adapter output
- X adapter works but still contains some metadata / timeline noise

---

## What is **not** done yet

1. OpenClaw skill wrapper
2. runtime safety enforcement for dangerous actions
3. deployment/service model finalization
4. GitHub adapter
5. reliable request-aware network signal in adapter reports
6. higher-quality X main-post extraction

---

## What not to do

- do not restart architecture discussion from zero
- do not throw away extension path because one signal is imperfect
- do not overbuild a network interception platform before fixing content extraction quality
- do not implement autonomous high-risk flows
- do not assume old docs mentioning “Phase 2” reflect current repo state

---

## Recommended next work order

1. polish X adapter extraction quality
2. stabilize request-aware readiness signal
3. implement GitHub adapter
4. design and implement OpenClaw skill wrapper
5. add runtime safety gates
6. decide deployment/service model

---

## File map

### Core code
- `bridge/app/server.py` — FastAPI routes and extension state merge path
- `bridge/app/cdp_service.py` — main bridge service / readiness logic
- `bridge/app/cdp_client.py` — CDP HTTP access
- `bridge/app/cdp_ws_client.py` — CDP WebSocket access
- `bridge/app/playwright_client.py` — Playwright attach scaffold

### Extension
- `extension/background.js` — background relay / bridge reporting
- `extension/content.js` — page observation, X extraction, reporting
- `extension/site-adapters.js` — earlier adapter scaffold reference (keep aligned or refactor; current content script owns more of the logic)
- `extension/manifest.json` — MV3 manifest

### Docs
- `browser-bridge-spec.md` — system spec
- `browser-bridge-task-board.md` — actionable queue
- `browser-bridge-acceptance.md` — acceptance contract
- `browser-bridge-plan-next.md` — execution reset plan
- `browser-bridge-progress.md` — current state summary
- `browser-bridge-open-items.md` — unresolved items
- `browser-bridge-dev-log.md` — development history

---

## Notes on old docs

Some older docs are still useful as historical context, especially:
- `browser-bridge-plan.md`
- `browser-bridge-retrospective-2026-03-12.md`

But at least one file is now historical rather than operational:
- `browser-bridge-phase-2.md`

That file describes an earlier execution stage and should no longer be used as the primary starting point for new development.

---

## Handoff instruction

If you are another agent taking over:
- use docs as source of truth first
- inspect code second
- update docs when changing architecture, task order, or acceptance conditions
- prefer small, reviewable commits
- keep the user-facing control role separate from implementation role
