# Unified Auth — Infrastructure Cost Impact

**Feature:** unified-auth (PR 1 library + PRs 2–6 consumer adoption & migration)
**Guiding doc:** `Skawr/.kiro/steering/skawr-pricing-steering.md`
**Date:** July 2026

## TL;DR

**Estimated added monthly cost: ~$0 incremental** on the current Contabo VPS baseline (~$25–30/mo). Unified auth adds *identity* rows (users, enrollments, sessions, stores), not *product* rows — and per steering rule #1, **product count is the cost driver, not auth or search volume**. No OpenSearch threshold moves, no new metered third-party costs, no new services.

The first threshold that unified-auth storage could theoretically approach is ~10M+ users (tens of GB), which is far beyond any near-term scale and would still be dwarfed by the analytics `events` table that independently drives the ClickHouse migration decision.

---

## 1. PostgreSQL Storage Growth

Postgres remains the single data store (per steering). New/changed tables:

| Table | Rows | Approx bytes/row | Notes |
|-------|------|------------------|-------|
| `product_enrollments` | ~2 per user | ~100 B + index | (user_id, product) unique |
| `connected_stores` | 1 per SaaS merchant | ~2–4 KB | encrypted OAuth tokens + settings JSON |
| `user_sessions` (enhanced) | ~2–5 per user | +~600 B (device/ip/product) | cleaned on refresh, bounded by active devices |
| `subscription_tier_audit` | few per user/yr | ~60 B | append-only |
| `api_keys` (+4 columns) | existing | negligible | user_id, product, resource_id, resource_type |
| `organizations` / `organization_members` / `user_identity_providers` | 0 | 0 | dormant until features activate |

### Estimate per 1,000 users

Assuming 1,000 users, ~200 of which are SaaS merchants with 1 connected store each:

| Component | Calculation | Size |
|-----------|-------------|------|
| Enrollments | 1,000 × 2 × 200 B | ~0.4 MB |
| Connected stores | 200 × 3 KB | ~0.6 MB |
| Sessions | 1,000 × 3 × 600 B | ~1.8 MB |
| Tier audit | 1,000 × 2 × 60 B | ~0.12 MB |
| **Total** | | **~3 MB / 1,000 users** |

**Scaling:** 100K users ≈ ~300 MB. For comparison, the analytics `events` table reaches millions of rows and is the actual storage/scaling driver. Unified auth storage stays **negligible** relative to events at every realistic scale.

**Portability:** All new tables use portable column types (UUID, String, Boolean, DateTime, JSON, Text) — no Postgres-specific types — consistent with the steering requirement to keep the schema ClickHouse-portable. (Auth tables would remain in Postgres even after a ClickHouse read-path migration for events.)

---

## 2. Compute / Latency

| Operation | DB cost | Frequency | Impact |
|-----------|---------|-----------|--------|
| `verify_token_for_product()` | **0 queries** (reads JWT claim) | every API request (hot path) | **Zero** — the key design win |
| Enrollment lookup on token issuance | 1 indexed query | login / signup / refresh (infrequent) | Minimal |
| Resource resolver (indexer) | 1–2 indexed queries (on user_id) | requests needing resource context | Minimal, indexed |
| Session cleanup on refresh | 1 DELETE | per refresh (~every 15 min/session) | Minimal |
| Session validation (optional) | 1 indexed lookup, Redis-cacheable | refresh | Minimal |

The `product_enrollments` claim is embedded in the JWT, so **the hot path (every authenticated read) does zero extra DB work**. Extra queries only occur on the low-frequency auth lifecycle events (login, refresh). This keeps CPU/RAM impact within existing VPS headroom.

---

## 3. Encryption Overhead

`connected_stores` OAuth tokens are encrypted at rest with Fernet (`SKAWR_AUTH_STORE_ENCRYPTION_KEY`). Encrypt/decrypt is in-process, microsecond-scale, and only runs during OAuth flows (install, token refresh) — not on the search or analytics hot paths. **Negligible.**

---

## 4. One-Time Migration Cost

Three standalone scripts (`migrate_analytics_users.py`, `migrate_saas_apiclients.py`, `migrate_marketplace_supabase.py`):

- Batch reads + inserts against the existing shared Postgres — **no extra infrastructure**.
- At current scale (a handful of SaaS clients + hundreds/low-thousands of analytics users), each script runs in **seconds to a few minutes**.
- Idempotent (UUID-based dedup) — safe to re-run; failed runs don't require provisioning.
- Runs within the VPS's existing headroom; recommend running during low-traffic window as a courtesy, but no capacity change needed.

---

## 5. Threshold Checks (per steering)

| Threshold | Moved by unified auth? |
|-----------|------------------------|
| OpenSearch node class (product count) | **No** — auth adds no products/indices |
| Single-client 200K+ products alert | **No** — unrelated to identity |
| VPS baseline (~$25–30/mo) | **No change** |
| Redis | Already running; optional session cache adds no new cost |
| Embedding cost (Fireworks) | **$0** — auth never triggers embeddings |

Per steering rule #1, tier upgrades and infra scaling gate on **indexed product count**. Unified auth adds identity rows only, so it contributes **zero** to the cost driver.

---

## 6. Third-Party / Metered Costs

- **Embeddings (Fireworks):** $0 — untouched.
- **Email:** No new volume beyond existing transactional auth emails (password reset placeholder). Notification volume is driven by the payment feature, not auth.
- **Polar.sh payment fees:** Out of scope for this feature — tracked in the `saas-payment-integration` spec. (For reference, those are ~5% + $0.50/tx on the MoR model, but they scale with revenue, not infra.)

---

## 7. Future AWS Baseline

When the AWS migration happens (~$180–200/mo baseline per steering):

- **RDS storage:** unified auth adds ~MBs–hundreds of MBs — negligible against the RDS instance already sized for events.
- **No new services:** no queue, no warehouse, no additional Fargate tasks, no OpenSearch nodes attributable to auth.
- **Incremental AWS cost of unified auth: ~$0.**

---

## Summary

| Dimension | Incremental cost |
|-----------|------------------|
| VPS (current) | **~$0/mo** |
| Postgres storage | ~3 MB / 1,000 users (negligible) |
| Compute / latency | Minimal (hot path is DB-free) |
| One-time migration | No new infra; minutes of runtime |
| OpenSearch / embeddings | $0 |
| AWS (future) | ~$0 incremental |

**Threshold crossing:** No unified-auth-driven threshold is crossed within any realistic near-term user count. Auth storage would only become a first-order concern at ~10M+ users, at which point the events table (not auth) already dictates the platform's scaling strategy.
