# Browser Bridge Open Items

_Last updated: 2026-03-19_
_Status: active_

## Product / architecture

### 1. Skill wrapper
- raw bridge exists, but OpenClaw-facing skill suite does not yet exist
- needs façade design and user-facing contract

### 2. Deployment model
- still unresolved: manual start vs long-running service vs managed service wrapper
- current practical mode: manual local process

### 3. Runtime safety enforcement
- safety boundary is documented
- code-level hard stops / confirmations are not fully implemented yet

## Bridge / API

### 4. API stability contract
- current API is usable, but still evolving
- need decision on what becomes stable external contract vs internal-only route

### 5. Open URL semantics
- currently opens a new target/tab
- may later need explicit “navigate existing tab” semantics

### 6. Activate semantics
- CDP activate is not guaranteed to equal desktop foreground focus
- may need optional stronger focus path later

## Extension / site adapters

### 7. X adapter precision
- current extraction works, but still includes metadata / page noise
- `tweetTextFound` can remain false while fallback still succeeds
- gate detection is conservative and may over-fire

### 8. Request-aware readiness
- architecture exists
- signal still not fully reliable in final adapter output
- should remain observational only; no page request replacement

### 9. Next adapter choice
- recommended next site: GitHub
- not started yet

## Operations

### 10. Edge launch ergonomics
- still manual
- may later need helper script / alias / startup wrapper
