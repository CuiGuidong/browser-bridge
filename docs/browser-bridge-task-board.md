# Browser Bridge Task Board

_Last updated: 2026-03-20_
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
- [x] Reduce metadata / stats noise further
- [x] Better split primary post vs surrounding content
- [x] Better handling for sensitive-content gates
- [x] Better handling for reply-heavy pages
- [ ] Continue reducing timeline noise and empty-fragment cases on edge pages

### Request-aware readiness
- [x] Request probe exists in architecture
- [x] Verify adapter can reliably consume request state
- [x] Make `signals.network` stable and non-null when expected
- [x] Use network quiet signal in final readiness scoring, not just placeholder logic
- [ ] Long-session validation across X home/search/post variants

## Completed since 2026-03-20

### X Smart Search & Timeline Support
- [x] Upgrade X adapter (`content.js`) to extract structured timeline lists
- [x] Update `read_page` in Bridge to support "Light Scroll" for timelines
- [x] Build OpenClaw Skill Wrapper (`x-assistant`) for search/feed/read-post workflows
- [x] Add feed-mode detection (`for_you` / `following`) with Chinese/English tab compatibility
- [x] Default home feed behavior: read both streams with configurable target count
- [x] Add low-frequency scroll/read pacing and bounded rounds for risk control
- [x] Prefer same-domain tab reuse before opening new tabs to reduce tab/memory growth

## Not started

### GitHub adapter
- [ ] Detect issue / PR / discussion pages
- [ ] Extract primary issue / PR body
- [ ] Detect comments timeline separately
- [ ] Add GitHub-specific readiness hints

### Skill wrapper
- [ ] Design unified OpenClaw-facing bridge skill API (not only X)
- [ ] Wrap bridge into reusable multi-site skill entrypoint
- [ ] Separate basic / playwright / safe-auth layers if needed

### Safety enforcement
- [ ] Turn documented high-risk rules into runtime checks
- [ ] Add confirmation gates / deny list for dangerous operations

### Deployment / operations
- [ ] Decide manual vs long-running service model
- [ ] Add start / stop helper scripts if needed
- [ ] Decide host Mac vs NAS long-term deployment target

## Recommended next order

1. Harden X extraction quality and long-session readiness stability
2. Add GitHub adapter
3. Generalize skill wrapper from X-only to bridge-level suite
4. Add safety enforcement
5. Finalize deployment model
