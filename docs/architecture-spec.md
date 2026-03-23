# Browser Bridge Spec

_Last updated: 2026-03-20_
_Status: handoff-ready draft_

## 1. Purpose

Browser Bridge is a local-first bridge that lets an agent operate the user's real Chrome/Edge browser through a structured HTTP API, while preserving the user's real login state, cookies, profile, and browsing environment.

Primary goal:
- safe, low-frequency, human-like assistance on real sites

Non-goals:
- bulk crawling
- bot-evasion arms race
- captcha / 2FA bypass
- cloud relay control plane
- autonomous high-risk account actions

## 2. System model

```text
Agent / OpenClaw skill
  -> Browser Bridge HTTP API
    -> Path A: Browser Extension hint / semantic layer
    -> Path B: CDP direct control layer
    -> Path C: Playwright attach layer
```

## 3. Design constraints

- Real browser only: Chrome / Edge
- Prefer host Mac real browser over synthetic container identity
- Local-first only
- High-risk actions require human confirmation
- Extension is enhancement, not sole control plane
- Playwright may only attach to existing browser, not launch a new automation identity

## 4. Core components

### 4.1 CDP HTTP client
Responsibilities:
- call `/json/version`, `/json/list`, `/json/new`, `/json/activate`
- inject required `Host: 127.0.0.1:9333` header when accessing host browser through OrbStack

### 4.2 CDP WebSocket client
Responsibilities:
- `Runtime.evaluate`
- `Page.captureScreenshot`
- DOM-driven read / click / fill helpers

### 4.3 Bridge service
Responsibilities:
- normalize targets / pages
- expose HTTP API
- collect readiness probes
- merge extension hints with CDP fallback

### 4.4 Extension layer
Responsibilities:
- page semantic observation
- site-specific adapters
- active page reports to bridge
- high-frequency site hints (currently X)

### 4.5 Playwright attach layer
Responsibilities:
- robust complex interactions
- locator / wait / form flows
- future heavier workflows

## 5. Current API surface

### Base bridge
- `GET /health`
- `GET /version`
- `GET /tabs`
- `POST /open`
- `POST /activate`
- `GET /wait`
- `GET /page-info`
- `GET /page-content`
- `GET /probe-readiness`
- `POST /read-page`
- `POST /screenshot`
- `GET /query`
- `POST /click`
- `POST /fill`

### Extension integration
- `POST /extension/report`
- `GET /extension/state`

### Playwright
- `POST /playwright/connect`
- `POST /playwright/disconnect`
- `GET /playwright/pages`
- `POST /playwright/click`
- `POST /playwright/fill`
- `POST /playwright/evaluate`
- `GET /playwright/wait-selector`

## 6. Readiness model

The bridge must not rely on blind sleep as primary strategy.

Readiness signals are layered:

### Generic readiness
- `document.readyState`
- URL / title stability
- body text length threshold
- optional selector presence

### Site-specific readiness
- per-site adapters may provide semantic readiness
- current adapter: `x`

### Network-aware readiness
- intended signal: recent request quiet period
- current state: request probe is wired into extension reports and X readiness scoring; still needs longer real-session validation

## 7. Site adapter model

Adapter abstraction should support:
- `match()`
- `collect()`
- semantic page classification
- primary content extraction
- site-specific readiness

Current adapters:
- `generic`
- `x`

Current X-oriented skill wrapper:
- `skills/x-assistant` (search / home feed / single post scripts)

## 8. Safety boundary

Bridge must hard-stop or require explicit confirmation before:
- login / logout
- 2FA / MFA
- captcha challenges
- password / email / phone changes
- payment / transfer
- content publishing / deletion
- third-party authorization

Current status:
- documented as policy
- not yet fully enforced in route-level code

## 9. Known limitations

- Extension install / reload still requires human browser-side action
- X adapter can extract primary content and timeline lists, but can still carry timeline / metadata noise on edge pages
- request probe and `signals.network` exist in reports, but stability across long sessions and all X page variants is not fully verified
- current skill wrapper is X-focused; a unified bridge-level skill suite contract is not finalized
- no stable deployment/service model yet

## 10. Handoff note

This project is now beyond raw prototype stage. Another agent should not start by coding blindly. It should:
1. read this spec
2. read `browser-bridge-plan.md`
3. read `browser-bridge-task-board.md`
4. read `browser-bridge-acceptance.md`
5. inspect current code only after understanding architecture and current gaps
