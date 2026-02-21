State of the codebase after the code review remediation batch (phases 193–202).

Short answer: no, not perfect. Better — meaningfully better — but there's a clear tier of remaining work.

## What we actually fixed

The critical and high severity findings from the code review are resolved:
- Secrets are no longer committed with weak defaults — services fail fast if env vars are missing
- CSRF cookie is httpOnly, CORS has no wildcard, WebSocket auth uses tickets not JWT-in-URL
- MQTT TLS enabled, weak EMQX defaults removed
- NATS race condition gone, audit logger lock contention fixed, bare excepts replaced with structured logging
- Operator DB role is now split — BYPASSRLS is no longer paired with full schema write access
- Admin key comparison is timing-safe, MQTT password no longer passed as a subprocess argument
- N+1 queries fixed in evaluator hot path, batch writer buffer is bounded
- Frontend WebSocket messages validated at runtime with Zod, as-any casts removed from AlertRuleDialog
- RLS inventory is complete: 61 PROTECTED / 21 EXEMPT / 0 GAP
- Test collection is clean, coverage gate passes at 31.21%

## What is still broken or unfinished

**Test suite — 442 unit tests hitting a real database**
These tests are marked @pytest.mark.unit but they make real asyncpg connections. They fail with InvalidPasswordError because no database is running in the unit test environment. They were failing before we started — the boto3 crash was hiding them. This needs a dedicated phase to either properly mock the DB connections or reclassify them as integration tests.

**MyPy baseline**
We made MyPy blocking in CI. Whether that was done via a clean run or a baseline file, the actual number of type errors in the codebase is unknown. If a baseline was used, that baseline represents technical debt we haven't looked at.

**The WS ?token= legacy fallback**
Still in the code with a dated deprecation comment. Not removed. Will become permanent if no one schedules phase 203.

**Frontend observability**
The logger utility created in phase 202 is a no-op in production. There is no error tracking service (Sentry, Datadog, etc.) wired up. Frontend errors are invisible in production right now.

**Frontend accessibility**
The code review found ~39 aria attributes across 176+ components. That is very low. No remediation was planned or executed.

**Performance testing**
Benchmarks exist in the CI pipeline but results are uploaded without comparison to a baseline. A 2x performance regression would not fail any CI gate.

**The 10 microservices outside ui_iot**
evaluator_iot, ingest_iot, ops_worker and others now have coverage measurement enabled with a 30% starting threshold. But the actual tests for those services are thin. We set the floor — we haven't built the tests yet.

**Stripe integration**
Phase 133 added Stripe. No code review was done on the billing/webhook path. Stripe webhook signature verification, idempotency handling, and subscription state transitions were not audited.

**Carrier/Hologram integration**
Same situation — added in a prior phase, not audited as part of this review.

## Priority order for what comes next

1. Fix the 442 unit tests (mock DB or reclassify) — this is blocking meaningful unit test signal
2. Remove WS ?token= fallback — phase 203, short phase
3. Frontend error tracking — pick a provider and wire up the logger
4. Stripe/webhook security audit — payment paths deserve their own review pass
5. Accessibility audit — not urgent but real gap
6. Performance baseline — make benchmark comparisons meaningful

## Bottom line

The attack surface is significantly reduced. The most exploitable issues are closed. What remains is test quality debt, observability gaps, and two integrations that haven't been reviewed. Not perfect — but the foundation is solid enough to build on.
