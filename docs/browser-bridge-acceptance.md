# Browser Bridge Acceptance

_Last updated: 2026-03-19_
_Status: draft acceptance contract_

## Acceptance philosophy

Acceptance should prove real capability on the user's real browser, not mocked success.

A capability is only accepted when it is:
- observable
- repeatable
- tied to a concrete real-page workflow
- documented with expected result and failure mode

## A. Environment acceptance

### A1. Host browser connectivity
Pass when:
- `/json/version` is reachable through bridge client
- `Browser` version is returned
- `Host` header workaround is documented and functioning

### A2. Target listing
Pass when:
- `GET /tabs` returns real browser tabs
- tab IDs and URLs are visible

## B. Core bridge acceptance

### B1. Open and activate
Pass when:
- `POST /open` creates a real new tab
- `POST /activate` focuses target in CDP sense

### B2. Read page basics
Pass when:
- `GET /page-info` returns title/url
- `GET /page-content` returns visible text
- `POST /screenshot` returns usable image bytes

### B3. DOM interaction
Pass when:
- `GET /query` returns element summaries
- `POST /click` can trigger a real navigation or page change
- `POST /fill` can update a real input

## C. SPA readiness acceptance

### C1. Generic readiness
Pass when:
- `GET /probe-readiness` can mark a non-trivial SPA page ready without blind fixed sleep as sole criterion

### C2. Smart read path
Pass when:
- `POST /read-page` returns content after readiness probing
- repeated runs produce stable output on the same page

## D. Extension acceptance

### D1. Extension reporting
Pass when:
- extension is installed
- `/extension/state` receives live reports from browser pages

### D2. Hint-first path
Pass when:
- `POST /read-page` returns `preferredContentSource=extension` on supported site
- bridge still falls back to CDP on unsupported or missing extension signal

## E. X adapter acceptance

### E1. Page classification
Pass when extension report contains:
- `site = x`
- `isTweetDetail = true` on tweet page
- `articleFound = true` once content is ready

### E2. Primary content extraction
Pass when:
- `primaryText` contains the main post body
- output is materially cleaner than raw `document.body.innerText`
- bridge selects extension content as preferred source

### E3. Regression boundary
Current known non-blockers:
- some metadata / engagement counts may remain
- `tweetTextFound` may be false if fallback extraction still works

## F. Playwright acceptance

Pass when:
- bridge can connect Playwright to existing browser
- a selector-based click/fill succeeds on a real page where CDP path would be more brittle

## G. Handoff acceptance for another agent

The project is handoff-ready when a new agent can:
1. read docs only
2. identify current architecture
3. identify known gaps
4. identify recommended next task order
5. continue without replaying old chat history

## Current acceptance snapshot

### Accepted now
- host browser connectivity
- core bridge API
- CDP page reading and screenshot
- basic interaction path
- smart read path
- extension reporting
- hint-first extension read on X
- Playwright attach scaffold

### Not fully accepted yet
- request-aware readiness signal stability
- X adapter precision polish
- GitHub adapter
- skill wrapper
- runtime safety enforcement
- deployment/service model
