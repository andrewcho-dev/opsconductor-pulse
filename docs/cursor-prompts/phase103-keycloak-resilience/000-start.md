# Phase 103 — Keycloak Resilience

## Goal

Harden the JWT/JWKS validation path so that a Keycloak restart or brief
outage does not take down the UI service. Currently, if Keycloak is
unreachable the JWKS fetch fails and every authenticated request returns 503.

The fix:
1. Cache the JWKS in memory with a configurable TTL (default 10 minutes).
2. On JWKS fetch failure, serve from cache if available (stale-while-revalidate).
3. Add a background refresh task so the cache is proactively updated.
4. Log JWKS refresh outcomes as structured JSON.

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-jwks-cache.md` | JWKS cache module with TTL + stale fallback |
| `002-auth-integration.md` | Wire cache into existing JWT validation |
| `003-verify.md` | Simulate Keycloak outage, confirm auth still works from cache |
