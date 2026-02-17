# OpsConductor‑Pulse — Software Strategy, Gap Analysis, and Development Priorities
**Date:** 2026-02-12  
**Scope:** United States market focus (regions, compliance posture, go‑to‑market assumptions).  
**Source of truth for “current state”:** the repo snapshot provided in `/mnt/data/opsconductor-pulse-main/opsconductor-pulse-main/` (docs + compose + services).

---

## 0) What this document is (and is not)

### This document **is**
- A durable “north star” strategy that formalizes **vision, intent, direction, and the plan** to evolve OpsConductor‑Pulse into an AWS‑IoT‑inspired, modular, scalable architecture.
- A **gap analysis**: where you are today vs. the architecture you want to mimic.
- A **high‑level priority plan** (epics) that you can turn into a tactical, step‑by‑step execution plan next.

### This document **is not**
- A detailed sprint plan, Jira ticket dump, or a vendor‑locked architecture.
- A promise that AWS “leaf” IoT products will remain available (some are being retired); the strategy explicitly avoids that dependency.

---

## 1) Context: “AWS IoT is shutting down stuff — what does that mean for us?”

AWS has announced end‑of‑support / end‑of‑life for some higher‑level IoT products, including:
- **AWS IoT Events** — end of support **May 20, 2026**, and stopped onboarding new customers **May 20, 2025**. citeturn0search1turn0search7  
- **AWS IoT Analytics** — end of support **December 15, 2025**, and stopped onboarding new customers **July 24, 2024**. citeturn0search2  
- **Fleet Hub (IoT Device Management feature)** — discontinued **October 18, 2025**. citeturn0search0turn0search3  

**Interpretation for Pulse (US‑market SaaS):**
- AWS is still an excellent **infrastructure** provider for IoT workloads (compute, storage, streaming, security primitives, managed DBs, etc.).
- But if your product vision is “a simpler, turnkey, lower‑cost version” of the retired higher‑level offerings, you should treat AWS’s retired feature‑sets as **design references**, not dependencies.

**Decision statement (Recommendation):**  
Build Pulse so it can run:
1) **self‑hosted / customer‑hosted**,  
2) **Pulse‑hosted in AWS** (default), and optionally  
3) **hybrid** (edge gateway + cloud).  
**Confidence:** 0.92 (high confidence: matches your cost/velocity needs, avoids vendor risk; primary uncertainty is operational overhead as you scale).

---

## 2) Product vision (formalized)

### 2.1 Vision
OpsConductor‑Pulse is a **fleet operations** and **event intelligence** platform for infrastructure devices (sensors, gateways, UPS/utility telemetry, environmental monitors, etc.), designed to:
- **Ingest** telemetry/events reliably over constrained networks (LTE‑M, NAT’d sites, intermittent connectivity).
- Maintain a trustworthy “device twin” / operational state model (“what is true right now?”).
- Detect and explain **events** (failure states, patterns, thresholds, health anomalies).
- Route actions to **customer workflows** (webhooks, email, ticketing, future integrations).
- Provide a **polished, cohesive** customer experience (not “cobbled together”), even though it’s built from modular components.

### 2.2 What “mimic AWS IoT” means for Pulse (the right way)
We mimic:
- The **architecture pattern** (planes, contracts, routing, “twin” state, jobs, rules, auditability).
- The **product surfaces** (connectivity, registry, device mgmt, state, rules, alerting, UI).

We do **not** mimic:
- AWS service names, console UX, or their internal implementation choices that don’t benefit your target market.

**Decision statement (Recommendation):**  
Adopt an AWS‑IoT‑inspired “product module map” for Pulse that customers recognize *as a coherent product*, while internally keeping components replaceable.  
**Confidence:** 0.88 (high confidence in clarity + modularity; medium risk of over‑engineering if not time‑boxed).

---

## 3) Architectural north star (target reference architecture)

### 3.1 Planes (the conceptual model)
This matches the structure you already started documenting in your repo:

1) **Device Plane**  
Devices publish telemetry/events, receive commands, and report status.

2) **Ingestion & Routing Plane**  
Authenticates devices, validates envelopes, applies rate limits, persists telemetry, and routes events to downstream processors.

3) **State Plane (“Device Twin”)**  
Maintains durable device state:
- **reported** (what device last said),
- **desired** (what cloud wants),
- **delta** (difference), plus
- metadata/versioning for correctness.

(This mirrors AWS Device Shadow semantics.) citeturn1search1turn1search2

4) **Rules & Eventing Plane**  
Evaluates rules, patterns, and state machines to generate alerts/incidents (your “IoT Events‑lite”).

5) **Actions / Delivery Plane**  
Routes alerts to integrations (webhook/email today, more later).

6) **Experience Plane (UI/API)**  
Customer portal, operator portal, APIs, and realtime updates.

7) **Ops Plane**  
Observability, audit, tenancy enforcement, quotas, billing entitlements.

### 3.2 “Modules” (product surfaces)
Use stable internal contracts so each module can be replaced (self‑hosted vs AWS later):

- **Pulse Connect:** device connectivity (MQTT/HTTP), auth, topic conventions
- **Pulse Registry:** tenant/site/device inventory + provisioning
- **Pulse State:** device twin + health + last‑seen, heartbeat, rollups
- **Pulse Stream:** telemetry storage + query API
- **Pulse Rules:** rules, detectors, workflows (event intelligence)
- **Pulse Actions:** connectors + delivery pipeline
- **Pulse Fleet:** fleet UI + dashboards + map + drill‑downs
- **Pulse Ops:** audit, quotas, SLOs, billing hooks, admin tooling

**Decision statement (Recommendation):**  
Make this module map the canonical structure for docs, repo layout, service boundaries, and UI navigation labels.  
**Confidence:** 0.86 (high clarity benefits; some renaming/refactor effort required).

---

## 4) Current state (what you have right now)

Based on your repo docs and docker compose, you already have a strong “modular services” shape:

### 4.1 Implemented capabilities (high value)
- **Multi‑service architecture** with clear roles (ingest, evaluator, dispatcher, delivery worker, webhook receiver, UI/API, provision API, device simulator).  
- **MQTT ingestion** (Mosquitto) and a dedicated ingestion service (`ingest_iot`).  
- **TimescaleDB** for telemetry + retention/compression policies.
- **Alerting pipeline**: evaluator → dispatcher → delivery worker with routing + integrations.
- **Tenant enforcement** with **RLS** patterns (docs and migrations show the intent and plumbing).
- **Keycloak OIDC/PKCE** SPA auth; customer vs operator routes separated.
- **Subscription entitlements** and multi‑subscription migrations exist in DB migrations (foundation for SaaS packaging).

### 4.2 “Monolith risk” reality check
Your system is **not** a monolith in the classic sense—your Compose stack is already decomposed.  
However, there is still **responsibility density** in the UI/API service (it hosts routes, websockets, and some ingest‑adjacent code paths), which is fine for MVP but needs clear boundaries for scale.

**Decision statement (Recommendation):**  
Treat the current system as a **modular monolith at the domain level** (contracts first), even if you keep multiple containers. Only split further when scale or ownership demands it.  
**Confidence:** 0.84 (reduces churn; risk is delayed scaling work if growth spikes).

---

## 5) Gap analysis: where you are vs. AWS‑IoT‑style target

### 5.1 Capability map (Pulse vs AWS‑IoT concepts)

**A) Device registry & identity**
- **Current:** `device_registry` exists; provisioning API supports activation code → token issuance; ingestion validates tokens.  
- **Target:** add strong device identity story (certs, rotation, revocation, policy).  
- **Gap:** certificate‑grade security + standardized “thing” policy model.

**B) Device twin (“shadow”) semantics**
- **Current:** `device_state.state JSONB` exists; heartbeat/online states exist.  
- **Target:** explicit **desired/reported/delta**, versioning, metadata timestamps (AWS shadow model). citeturn1search1turn1search2  
- **Gap:** the semantics are not explicit, so automation and command/control will be harder.

**C) Rules engine (“IoT Events‑lite”)**
- **Current:** evaluator supports thresholds/health checks; rules tables exist (`alert_rules`) and schema is evolving.  
- **Target:** composable rules + state machines + “detectors” with explainability and test fixtures.  
- **Gap:** rule authoring model, deterministic evaluation, and versioned rollouts.

**D) Actions & delivery**
- **Current:** webhooks + email integrations + route filtering + min severity.  
- **Target:** richer connectors, retries/DLQ, idempotency, per‑tenant quotas.  
- **Gap:** operational hardening and connector expansion.

**E) Fleet operations UI (“Fleet Hub‑lite”)**
- **Current:** customer portal exists; map/dashboard components exist in frontend dependencies.  
- **Target:** first‑class fleet views: thing search, groupings, remote actions, audit trail.  
- **Gap:** fleet indexing/search + UX for device operations.

**F) Cloud‑ready scaling & portability**
- **Current:** docker compose; can run on a single host; services already containerized.  
- **Target:** “lift” to AWS with minimal changes (ECS/RDS/ALB), then optional swap‑ins (IoT Core, Kinesis/MSK).  
- **Gap:** IaC, environment separation, secrets, and deployment automation.

### 5.2 “How close are we?”
You are **closer than you think** to the *architecture pattern*:
- Your services correspond cleanly to the AWS mental model: ingest, store, evaluate, deliver, UI/console, provisioning, and identity.  
- The largest gaps are **(1) device twin semantics**, **(2) a durable rules/workflow model**, and **(3) fleet UX + indexing**.

**Decision statement (Recommendation):**  
Define “Pulse v1” as **Shadow + Rules + Fleet‑lite** on top of your existing ingestion/storage/delivery pipeline, not a wholesale rewrite.  
**Confidence:** 0.90 (high confidence: aligns to your current codebase strengths; main risk is hidden coupling between UI/API and ingest paths).

---

## 6) Cloud provider strategy (US‑only focus)

### 6.1 Recommended provider for launch: **AWS**
Reasons (US market):
- Strong enterprise familiarity and procurement comfort.
- Mature building blocks for your target architecture (RDS, ECS, KMS, CloudWatch, managed streaming, etc.).
- Direct alignment with the AWS‑IoT‑inspired architecture you want to mimic.

**But:** avoid direct dependency on retired AWS IoT “leaf” products (Events/Analytics/Fleet Hub). Use primitives instead. citeturn0search1turn0search2turn0search0

**Decision statement (Recommendation):**  
Launch Pulse hosted on AWS (us‑west‑2 or us‑east‑1) using **ECS + RDS (Postgres/Timescale) + ALB + S3/CloudFront**, keeping Mosquitto initially.  
**Confidence:** 0.83 (good fit; uncertainty: cost curve and ops overhead vs. a single‑VM MVP).

### 6.2 “Build on my own systems now, migrate later” (the practical path)
You can keep developing on your own systems and still stay AWS‑portable by enforcing:
- container boundaries
- environment variables for infra endpoints
- one “platform interface” layer per external dependency (MQTT broker, secrets, object store, queue)

**Decision statement (Recommendation):**  
Create a small “platform adapter” layer (interfaces) so local implementations (Mosquitto/Postgres) can be swapped for AWS services later.  
**Confidence:** 0.78 (useful; risk: too abstract too early—keep it thin and focused).

---

## 7) “Can we fully simulate AWS IoT Core locally?”

**Short answer:** you can simulate the *architecture and contracts* locally, but you generally can’t fully emulate the AWS IoT Core managed MQTT broker behavior 1:1.

Practical options:
- **Local contract simulation**: Mosquitto + your own auth/rules/shadow services (what you already have).
- **LocalStack partial emulation**: LocalStack supports **IoT Data plane APIs** (e.g., get/update/delete thing shadow), but that’s not the same as fully emulating the managed broker + rules engine end‑to‑end. citeturn2search6
- **Hybrid integration tests**: keep local dev fast; run periodic CI tests against a real AWS sandbox account for the “AWS adapter”.

Edge option for hybrid deployments:
- AWS Greengrass supports local MQTT brokers and a bridge to AWS IoT Core (useful for “gateway” concepts). citeturn2search0turn2search1

**Decision statement (Recommendation):**  
Treat “AWS IoT simulation” as **contract simulation locally + real AWS sandbox validation**, not full local emulation.  
**Confidence:** 0.89 (high confidence; uncertainty: how far you want to go with automated AWS integration testing early).

---

## 8) Strategy: how we pivot without churn (the plan)

### 8.1 Guiding principles (non‑negotiables)
1) **Contracts > code**: stabilize message envelopes, event types, and APIs before major refactors.  
2) **Tenant safety by default**: RLS + immutable tenant context + audited operator bypass.  
3) **Replaceability**: no “deep lock‑in” to a broker, queue, or cloud provider.  
4) **Polished UX**: productize the experience with consistent naming + navigation that mirrors the module map.  
5) **Cost‑aware scaling**: start minimal; scale components only when metrics force you to.

**Decision statement (Recommendation):**  
Adopt a formal “Pulse Envelope v1” (for MQTT + HTTP ingest + internal events) and treat it as a versioned API.  
**Confidence:** 0.87 (high leverage; risk: initial refactor touches multiple services).

---

## 9) High‑level development priorities (epics)

Below are the epics that convert “AWS‑IoT‑style architecture” into concrete build steps.  
Each epic includes: goal, key deliverables, acceptance criteria, and a confidence score.

### P0 — Stabilize contracts & reduce coupling
**Goal:** make future work predictable by locking down contracts and eliminating hidden coupling.

- **P0.1 Pulse Envelope v1 (MQTT/HTTP/internal)**
  - Deliverables: JSON schema, version field, canonical topic mapping, error taxonomy.
  - Acceptance: ingest accepts v1; evaluator/dispatcher consume v1; rejects are categorized.
  - **Confidence:** 0.86 (clear benefit; some coordinated changes required).

- **P0.2 Service boundary cleanup (UI/API vs ingest)**
  - Deliverables: decide which service owns HTTP ingest; deprecate duplicate paths.
  - Acceptance: one canonical ingest path; UI service only proxies/reads.
  - **Confidence:** 0.74 (likely valuable; uncertainty: current usage patterns in your stack).

### P1 — Device Twin (Shadow‑lite) as a first‑class feature
**Goal:** unlock command/control, better rules, better UI consistency.

- **P1.1 Explicit `desired/reported/delta` model**
  - Deliverables: schema update + APIs; versioning and timestamps; update semantics.
  - Acceptance: UI can display desired vs reported; delta triggers can exist.
  - **Confidence:** 0.81 (strong payoff; risk: migration complexity).

- **P1.2 Twin update routes**
  - Deliverables: secure APIs for apps to set desired state; devices set reported state.
  - Acceptance: all state transitions audited; RLS enforced.
  - **Confidence:** 0.79 (depends on auth plumbing and UI needs).

### P2 — Rules & Eventing (“IoT Events‑lite”)
**Goal:** replace “hardcoded evaluator logic” with a scalable rules model.

- **P2.1 Rules DSL v1 (simple, testable)**
  - Deliverables: threshold + heartbeat + pattern rules; rule unit tests with fixtures.
  - Acceptance: rules run deterministically; can be enabled/disabled; produce explainable output.
  - **Confidence:** 0.77 (medium complexity; high payoff).

- **P2.2 Detector state machines (optional v1.5)**
  - Deliverables: detector instances, states, transitions, timers, and outputs.
  - Acceptance: supports “stuck in alarm”, “flapping suppression”, and “maintenance mode”.
  - **Confidence:** 0.68 (useful; risk: scope creep—time‑box).

### P3 — Fleet UX (“Fleet Hub‑lite”)
**Goal:** customer sees Pulse as a cohesive product, not components.

- **P3.1 Fleet Indexing + Search**
  - Deliverables: search by device/site/tag; groupings; status filters.
  - Acceptance: <1s query for typical tenant sizes; consistent drill‑downs.
  - **Confidence:** 0.72 (implementation depends on data volume assumptions).

- **P3.2 Remote actions UX (Shadow‑backed)**
  - Deliverables: “set desired” actions, maintenance mode, acknowledge flows.
  - Acceptance: all actions visible in audit log; rollback supported.
  - **Confidence:** 0.70 (depends on P1).

### P4 — Cloud‑portable deployment (AWS default)
**Goal:** launch in US regions with credible reliability without blowing upfront costs.

- **P4.1 Minimal AWS landing zone (IaC)**
  - Deliverables: Terraform (or CDK) for VPC, ECS, RDS, ALB, logs, secrets.
  - Acceptance: one‑click deploy to dev/stage/prod; config via env/secrets only.
  - **Confidence:** 0.75 (straightforward but time‑consuming).

- **P4.2 Frontend hosting (S3 + CloudFront)**
  - Deliverables: build pipeline; versioned assets; proper caching/invalidations.
  - Acceptance: HTTPS, SPA routing, and auth callbacks work.
  - **Confidence:** 0.82 (common pattern; low risk).

### P5 — Optional AWS IoT Core adapter (future scale)
**Goal:** keep Mosquitto for MVP, but be ready to swap in AWS IoT Core later.

- **P5.1 Device auth strategy (custom authorizer or cert model)**
  - Deliverables: adapter design; mapping of Pulse tokens/certs to AWS policies.
  - Acceptance: device can connect via AWS IoT Core using Pulse provisioning.
  - **Confidence:** 0.63 (AWS integration complexity; depends on device firmware constraints). citeturn1search5turn1search4turn1search1

---

## 10) Risk register (top items)

1) **Over‑modularization early** (churn / slow velocity)  
   - Mitigation: contracts first, time‑box abstractions, keep adapters thin.  
   - **Confidence:** 0.80 (known failure mode; mitigation is standard).

2) **Device twin semantics migration pain**  
   - Mitigation: additive schema; dual‑write/dual‑read during migration; feature flags.  
   - **Confidence:** 0.73 (depends on data volume and current UI usage).

3) **Cost surprises in AWS**  
   - Mitigation: start minimal (single tenant/stage), instrument cost drivers, set quotas.  
   - **Confidence:** 0.76 (cost control is doable; discipline required).

---

## 11) What you should do next (tactical plan precursor)

This is what the next document should expand into step‑by‑step tasks:

1) Lock **Pulse Envelope v1** + topic conventions  
2) Decide canonical **ingest ownership** (one path)  
3) Implement **Shadow‑lite** (desired/reported/delta)  
4) Refactor evaluator into **Rules DSL v1**  
5) Productize **Fleet Hub‑lite** UI with indexing + search  
6) Create **AWS MVP deploy** (IaC) that runs the same containers

**Decision statement (Recommendation):**  
Start the tactical plan by writing the Pulse Envelope spec and shadow semantics first; everything else gets easier after that.  
**Confidence:** 0.88 (high leverage; lowest regret foundation).

---

## Appendix A — Mapping AWS IoT concepts to Pulse components (reference)

- AWS IoT Core MQTT broker → Mosquitto today; optional AWS adapter later  
- Thing registry → `device_registry`  
- Device Shadow → `device_state` + future desired/reported/delta model citeturn1search1turn1search2  
- Rules engine → Pulse Rules (future)  
- IoT Events‑style detectors → Pulse detector state machines (future) citeturn0search1  
- Fleet Hub‑style console → Pulse Fleet UI citeturn0search0turn0search3  

---

## Appendix B — Notes on “US‑only focus”
- Choose AWS regions that match your target customers and latency (commonly us‑west‑2 / us‑east‑1).
- Keep logs/telemetry in‑region by design; avoid cross‑region replication until required.
- Treat FedRAMP/GovCloud as out of scope unless you explicitly target that market.

