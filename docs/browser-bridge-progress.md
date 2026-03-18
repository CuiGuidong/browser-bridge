# Browser Bridge Progress

_Last updated: 2026-03-19_
_Status: active handoff summary_

## Current state summary

Project state is **beyond skeleton**.
A new developer should treat it as a working prototype with multiple interaction paths already implemented.

## Completed

### Phase 1: environment validation
- Real Edge on host Mac validated
- CDP reachable from OrbStack/OpenClaw
- `9333` confirmed usable
- `Host: 127.0.0.1:9333` workaround validated

### Phase 2: base bridge
- Python bridge skeleton implemented
- FastAPI migration completed
- Core endpoints implemented:
  - `health`
  - `version`
  - `tabs`
  - `open`
  - `activate`
  - `wait`
  - `page-info`
  - `page-content`
  - `screenshot`
  - `query`
  - `click`
  - `fill`
- Git initialized and project published to GitHub

### Phase 3-ish capability expansion already done
Even though older docs still emphasize Phase 2, the codebase has already moved forward:
- Playwright attach path added
- readiness probe added
- smart `read-page` added
- browser extension scaffold added
- extension -> bridge reporting added
- site adapter framework added
- X adapter added
- bridge now supports hint-first reading where extension hints are available

## Current architecture reality

```text
Agent / future skill
  -> Browser Bridge FastAPI
    -> Path A: extension hints / semantic adapters
    -> Path B: CDP direct control
    -> Path C: Playwright attach
```

## Validated behaviors

- real X page can be opened in the user's real browser
- bridge can wait for asynchronous page readiness
- bridge can extract page content and screenshot after readiness
- extension can report page semantic state to bridge
- on supported X page, `read-page` can prefer extension-derived content over raw CDP content

## Current gaps

- request-aware readiness signal is not yet fully stable in adapter output
- X primary content extraction still includes some metadata / noise
- no GitHub adapter yet
- no OpenClaw skill wrapper yet
- safety policy is documented but not fully enforced in runtime code
- deployment/service model remains undecided

## Handoff recommendation

A new developer should next read:
1. `browser-bridge-spec.md`
2. `browser-bridge-plan.md`
3. `browser-bridge-plan-next.md`
4. `browser-bridge-task-board.md`
5. `browser-bridge-acceptance.md`

Do **not** continue from old chat memory first. Continue from docs + repo state first.
