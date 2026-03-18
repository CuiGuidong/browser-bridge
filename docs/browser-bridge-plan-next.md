# Browser Bridge Plan (Execution Reset)

_Last updated: 2026-03-19_
_Status: execution-oriented handoff plan_

## Why this file exists

Older docs explain why the project exists and how the architecture was chosen.
This file explains what the *next developer* should do from the current state, without needing old conversation context.

## Current project state

The project is no longer at pure Phase 2 skeleton stage.
It already has:
- functioning bridge
- FastAPI surface
- CDP direct path
- Playwright attach scaffold
- extension reporting path
- site adapter framework
- X adapter with hint-first reading

So the next developer should not restart from skeleton thinking.

## Immediate objective

Turn the current useful prototype into a stable handoff-quality system by focusing on quality and completeness, not breadth.

## Recommended workstream

### Workstream 1: X adapter polish
Goal:
- cleaner primary content extraction
- better separation of main post vs surrounding page noise
- better gate / warning detection

### Workstream 2: request-aware readiness stabilization
Goal:
- make request probe readable from adapter path reliably
- expose useful network quiet signal in adapter reports
- keep it observational only; never replace site requests

### Workstream 3: second site adapter
Recommended target:
- GitHub
Reason:
- strong user value
- page structure is more stable than many consumer SPAs
- good test of adapter generality

### Workstream 4: skill wrapper and integration
Goal:
- make Browser Bridge callable as an OpenClaw skill suite
- provide a stable façade over the raw bridge API

### Workstream 5: safety and deployment
Goal:
- convert safety policy into runtime behavior
- clarify how bridge should be started and kept available

## What not to do next

- do not restart architecture debate from zero
- do not add many random site adapters before polishing X and one more stable site
- do not over-focus on network interception sophistication before primary content extraction quality is good
- do not launch autonomous login / payment / high-risk action support

## Suggested first task for new agent

If a new agent is asked to continue immediately, start with:
1. inspect current X adapter extraction quality
2. reduce X primary text noise further
3. verify whether request probe state can be surfaced non-null
4. document findings in dev log and acceptance doc
