# Browser Bridge Task Board

_Last updated: 2026-03-19_
_Status: authoritative next-work list_

## Done

### Environment / base architecture
- [x] Validate host Mac Edge CDP route
- [x] Confirm `9333` as working debug port
- [x] Confirm `Host: 127.0.0.1:9333` workaround via OrbStack
- [x] Create project structure under `projects/browser-bridge-project/`

### Bridge core
- [x] HTTP bridge skeleton
- [x] CDP HTTP client
- [x] CDP WebSocket client
- [x] FastAPI migration
- [x] README / requirements / git / GitHub repo

### Core API
- [x] `health`
- [x] `version`
- [x] `tabs`
- [x] `open`
- [x] `activate`
- [x] `wait`
- [x] `page-info`
- [x] `page-content`
- [x] `screenshot`
- [x] `query`
- [x] `click`
- [x] `fill`
- [x] `probe-readiness`
- [x] `read-page`

### Heavy interaction path
- [x] Playwright attach scaffold
- [x] Playwright routes

### Extension integration
- [x] MV3 extension scaffold
- [x] popup health check
- [x] extension -> bridge reporting
- [x] bridge hint-first read path
- [x] site adapter framework
- [x] initial X adapter
- [x] X adapter can become `preferredContentSource=extension`

## In progress / partially complete

### X adapter precision
- [ ] Reduce metadata / stats noise further
- [ ] Better split primary post vs surrounding content
- [ ] Better handling for sensitive-content gates
- [ ] Better handling for reply-heavy pages

### Request-aware readiness
- [ ] Request probe exists in architecture
- [ ] Verify adapter can reliably consume request state
- [ ] Make `signals.network` stable and non-null when expected
- [ ] Use network quiet signal in final readiness scoring, not just placeholder logic

## Not started

### GitHub adapter
- [ ] Detect issue / PR / discussion pages
- [ ] Extract primary issue / PR body
- [ ] Detect comments timeline separately
- [ ] Add GitHub-specific readiness hints

### Skill wrapper
- [ ] Design OpenClaw-facing skill API
- [ ] Wrap bridge into reusable skill entrypoint
- [ ] Separate basic / playwright / safe-auth layers if needed

### Safety enforcement
- [ ] Turn documented high-risk rules into runtime checks
- [ ] Add confirmation gates / deny list for dangerous operations

### Deployment / operations
- [ ] Decide manual vs long-running service model
- [ ] Add start / stop helper scripts if needed
- [ ] Decide host Mac vs NAS long-term deployment target

## Recommended next order

1. Finish X adapter precision
2. Stabilize request-aware readiness
3. Add GitHub adapter
4. Add skill wrapper
5. Add safety enforcement
6. Finalize deployment model
