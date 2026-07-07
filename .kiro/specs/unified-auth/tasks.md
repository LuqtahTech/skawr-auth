# Implementation Plan: Unified Auth

## Overview

This implementation plan transforms skawr-auth from a shared-code library into a shared-identity library. Work is structured around 6 PRs (with PR 1 split into 1a/1b/1c) reflecting the deployment order: schema first, then backend logic, then frontend, then consumer adoption, then migrations, then cleanup.

Each top-level task maps to a PR. Sub-tasks are independently reviewable, testable units ordered by dependency within the PR.

## Tasks

- [x] 1. PR 1a: Schema + Models (skawr-auth repo)
  - [x] 1.1 Create Alembic migration: add subscription_tier to users + make password_hash nullable
    - Add nullable `subscription_tier` column (String(20)) to users table
    - Alter `password_hash` column to nullable=True (for OAuth-only users)
    - _Requirements: 1.5, 15.3_

  - [x] 1.2 Create Alembic migration: product_enrollments table
    - Create `product_enrollments` table with id, user_id, product, role, is_active, enrolled_at, revoked_at
    - Add unique constraint on (user_id, product)
    - Add index on user_id
    - _Requirements: 2.1_

  - [x] 1.3 Create Alembic migration: connected_stores table
    - Create `connected_stores` table with all columns from design (platform, platform_store_id, OAuth tokens, subscription state, settings, legacy_client_id)
    - Add unique constraints on (platform, platform_store_id) and legacy_client_id
    - _Requirements: 11.3_

  - [x] 1.4 Create Alembic migration: enhance user_sessions table
    - Add `device` (String 512), `ip_address` (String 45), `product` (String 50) columns
    - Add `expires_at` (DateTime timezone-aware) column
    - _Requirements: 5.1_

  - [x] 1.5 Create Alembic migration: extend api_keys table
    - Add `resource_id` (UUID, nullable, indexed) and `resource_type` (String 50, nullable) columns
    - Add composite index on (user_id, product)
    - _Requirements: 7.1_

  - [x] 1.6 Create Alembic migration: organizations + organization_members tables (dormant)
    - Create `organizations` table (id, name, owner_user_id FK)
    - Create `organization_members` table (id, organization_id FK, user_id FK, role)
    - _Requirements: 8.1, 8.2_

  - [x] 1.7 Create Alembic migration: user_identity_providers table (dormant)
    - Create table with id, user_id FK, provider, provider_user_id, linked_at
    - Add unique constraint on (provider, provider_user_id)
    - _Requirements: 9.1_

  - [x] 1.8 Create Alembic migration: subscription_tier_audit table
    - Create table with id, user_id FK (indexed), old_tier, new_tier, changed_at
    - _Requirements: 15.5_

  - [x] 1.9 Update User model: add subscription_tier column and make password_hash nullable
    - Extend `create_user_models()` factory to include `subscription_tier` column
    - Change `password_hash` nullable=True
    - Add relationships: enrollments, sessions, connected_stores
    - _Requirements: 1.5, 15.3_

  - [x] 1.10 Create ProductEnrollment model
    - New file `models/enrollment.py` with factory pattern
    - Define columns, unique constraint, relationship to User
    - _Requirements: 2.1_

  - [x] 1.11 Create ConnectedStore model
    - New file `models/connected_store.py` with factory pattern
    - Define all columns from design, relationship to User
    - _Requirements: 11.3_

  - [x] 1.12 Enhance UserSession model
    - Add device, ip_address, product, expires_at columns to existing session model
    - _Requirements: 5.1_

  - [x] 1.13 Extend APIKey model with resource_id and resource_type
    - Add resource_id (UUID, nullable) and resource_type (String 50, nullable)
    - Add composite index on (user_id, product)
    - _Requirements: 7.1_

  - [x] 1.14 Create Organization + OrganizationMember models (dormant)
    - New file `models/organization.py`
    - Define both models with relationships
    - _Requirements: 8.1, 8.2_

  - [x] 1.15 Create UserIdentityProvider model (dormant)
    - New file `models/identity_provider.py`
    - _Requirements: 9.1_

  - [x] 1.16 Create SubscriptionTierAudit model
    - New file `models/subscription_tier_audit.py`
    - _Requirements: 15.5_

  - [ ]* 1.17 Write tests for model instantiation and constraint enforcement
    - Test ProductEnrollment unique constraint on (user_id, product)
    - Test ConnectedStore unique constraint on (platform, platform_store_id)
    - Test User.subscription_tier accepts valid values
    - Test password_hash nullable works for OAuth-only users
    - _Requirements: 1.5, 2.1_

- [x] 2. Checkpoint - Ensure schema and models are correct
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. PR 1b: Backend Logic (skawr-auth repo)
  - [x] 3.1 Implement environment config standardization (_get_secret_key with priority chain)
    - Create/update `utils/config.py` with `_get_secret_key()` function
    - Priority: SKAWR_AUTH_SECRET_KEY → SECRET_KEY → JWT_SECRET_KEY → DEFAULT_SECRET_KEY
    - _Requirements: 4.3, 13.2_

  - [x] 3.2 Implement JWT dual-auth: detect_token_format()
    - Add `detect_token_format(payload: dict) -> str` to `utils/auth.py`
    - Returns "unified", "legacy_indexer", or "legacy_analytics"
    - Raises ValueError for unrecognizable format
    - _Requirements: 13.3, 13.4_

  - [x] 3.3 Implement verify_token_for_product() with all three format handling
    - Unified format: check product_enrollments claim for product role
    - Legacy analytics: treat as enrolled everywhere with "member" role (90-day window)
    - Legacy indexer: resolve client_id → connected_store → user, return "admin"
    - Check SKAWR_AUTH_LEGACY_TOKEN_DEADLINE for legacy token rejection after deadline
    - _Requirements: 4.4, 4.5, 4.6, 13.3, 13.4_

  - [x] 3.4 Extend create_access_token to include product_enrollments and email in claims
    - Add `product_enrollments` list and `email` to JWT payload
    - Maintain existing claims (sub, type, iat, exp) unchanged
    - _Requirements: 4.1, 4.2, 13.7_

  - [x] 3.5 Implement enrollment service (services/enrollment.py)
    - `get_or_create_enrollment(db, user_id, product, default_role)`
    - `get_user_enrollments(db, user_id)`
    - `revoke_all_enrollments(db, user_id)` — atomic with user deactivation
    - `restore_all_enrollments(db, user_id)` — restore prior roles
    - `assign_role(db, user_id, product, role, actor_role)` — 403 if actor not admin
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6, 3.2, 3.3_

  - [x] 3.6 Implement session service (services/sessions.py)
    - `create_session(db, user_id, token_hash, device, ip, product, expires_at)`
    - `list_user_sessions(db, user_id)` — non-expired, excludes token_hash
    - `revoke_session(db, user_id, session_id)` — returns False if not found/not owned
    - `revoke_all_sessions(db, user_id)` — returns count
    - `cleanup_expired_sessions(db, user_id)` — removes expired
    - `is_session_valid(db, token_hash)` — checks Postgres (optional Redis cache)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 3.7 Implement resource resolver (utils/resource_resolver.py)
    - `get_current_user_resources(db, user_id, product)` → UserResources dataclass
    - `get_current_user_or_legacy_client(request, credentials, db)` → UnifiedUser | LegacyClient
    - Handle all three token formats in the resolver
    - _Requirements: 6.2, 13.3_

  - [x] 3.8 Implement guest claim flow (services/guest_claim.py)
    - `claim_guest_account(db, legacy_client_id, email, password_hash, name)`
    - Check email uniqueness, create user, enrollment, connected_store
    - Re-associate SearchIndex and APIKey rows
    - Handle merge case (email already exists)
    - _Requirements: 11.4, 11.5_

  - [x] 3.9 Implement sync/async dual dependency factories
    - `create_get_current_user_dependency_sync(user_model, db_dependency, product)` for indexer
    - `create_get_current_user_dependency_async(user_model, db_dependency, product)` for analytics
    - Both validate product enrollment if product is specified
    - _Requirements: 13.2, 3.4_

  - [x] 3.10 Implement CORS helper (utils/cors.py)
    - `get_allowed_origins()` reading from SKAWR_AUTH_ALLOWED_ORIGINS env var
    - Default origins per environment (local, production)
    - _Requirements: 6.2, 14.1_

  - [x] 3.11 Implement subscription tier internal endpoint
    - `PUT /internal/subscription-tier/{user_id}` authenticated via service-level API key
    - Record old/new tier + timestamp in subscription_tier_audit
    - _Requirements: 15.4, 15.5_

  - [x] 3.12 Implement role dependency (utils/roles.py)
    - `Product` enum (analytics, search_saas, client_dashboard, admin_dashboard, marketplace)
    - `Role` enum (admin, member, viewer)
    - `require_product_role(product, min_role)` — FastAPI dependency factory
    - _Requirements: 3.1, 3.4, 3.5_

  - [ ]* 3.13 Write property tests for token format detection
    - **Property 25: Legacy token backward compatibility** — legacy tokens without product_enrollments grant member role everywhere
    - **Property 26: New token structural backward compatibility** — new tokens keep sub/email/iat/exp in standard positions
    - **Property 11: Invalid token rejection** — expired, bad signature, or missing claims → None
    - Generate random valid/invalid payloads using Hypothesis strategies
    - **Validates: Requirements 4.5, 13.3, 13.4, 13.7**

  - [ ]* 3.14 Write property tests for enrollment service
    - **Property 3: Enrollment uniqueness constraint** — duplicate (user_id, product) rejected
    - **Property 4: Auto-enrollment on first product access** — no enrollment → creates member
    - **Property 5: Enrollment deactivation/reactivation round trip** — revoke_all → restore_all = original state
    - **Property 6: Role assignment isolation across products** — changing role in X doesn't affect Y
    - **Property 7: Non-admin role assignment rejection** — non-admin assigning role → 403
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6, 3.2, 3.3**

  - [ ]* 3.15 Write property tests for session management
    - **Property 12: Session listing excludes expired and hides sensitive data** — only non-expired, no token_hash
    - **Property 13: Session revocation invalidates refresh token** — revoked → rejected
    - **Property 14: Cross-user session revocation returns 404** — user A can't revoke user B's session
    - **Property 15: Logout-everywhere invalidates all sessions** — all N sessions invalid after
    - **Property 17: Token refresh cleans expired sessions** — expired records removed on refresh
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**

  - [ ]* 3.16 Write property tests for API key scoping
    - **Property 19: API key limit enforcement** — 11th key rejected
    - **Property 20: API key product scope enforcement** — key for X rejected at Y
    - **Property 21: API key permission enforcement** — missing permission → 403
    - **Validates: Requirements 7.1, 7.3, 7.5, 7.6**

  - [ ]* 3.17 Write property tests for token claims and verification
    - **Property 8: Token claims completeness** — issued token has sub, email, product_enrollments, type, iat, exp
    - **Property 9: Token verification returns correct role** — verify_token_for_product returns matching role
    - **Property 10: Unenrolled product access denied without session invalidation** — returns None, sessions preserved
    - **Validates: Requirements 4.1, 4.2, 4.4, 4.6, 6.1, 6.2**

- [x] 4. Checkpoint - Ensure backend logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. PR 1c: Frontend (skawr-auth repo)
  - [x] 5.1 Update TypeScript types (ProductEnrollment, ConnectedStore, etc.)
    - Add interfaces: ProductEnrollment, ConnectedStore, UserSession (extended), APIKey (extended)
    - Add Product and Role enums
    - _Requirements: 2.1, 4.1_

  - [x] 5.2 Extend AuthClient with product-aware login and enrollment methods
    - Add `product` param to `login()` method
    - Add `getEnrolledProducts(): ProductEnrollment[]` — decode from current token
    - Add `hasProductAccess(product: string): boolean`
    - _Requirements: 6.1, 6.2, 14.1_

  - [x] 5.3 Create ProductSwitcher component
    - Display enrolled products, highlight current product
    - `onSwitch` callback for navigation
    - Accessible (keyboard navigable, ARIA labels)
    - _Requirements: 14.3_

  - [x] 5.4 Create SharedLoginPage component
    - Accept `config`, `redirectProduct`, `onSuccess` props
    - Shared login/signup form that works across all products
    - Post-login redirect to originating product or default dashboard
    - _Requirements: 14.1, 14.2, 6.4_

  - [ ]* 5.5 Write tests for frontend components and auth state
    - Test ProductSwitcher renders enrolled products correctly
    - Test SharedLoginPage form submission and redirect behavior
    - Test AuthClient.getEnrolledProducts() decodes token correctly
    - Test AuthClient.hasProductAccess() returns correct boolean
    - _Requirements: 14.1, 14.3_

- [x] 6. Checkpoint - Ensure PR 1 (a/b/c) is complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. PR 2: skawr-analytics — Adopt Unified Auth
  - [ ] 7.1 Update skawr-auth dependency version in requirements.txt
    - Pin to the version that includes unified auth features
    - _Requirements: 13.2_

  - [ ] 7.2 Wire product enrollment into auth.py (add product="analytics")
    - Update `create_get_current_user_dependency` call to pass `product="analytics"`
    - Use the async factory variant
    - _Requirements: 2.2, 3.4_

  - [ ] 7.3 Update token issuance to include product_enrollments in claims
    - Ensure login/signup endpoints issue tokens with product_enrollments claim
    - Query user's enrollments before token creation
    - _Requirements: 4.1, 6.1_

  - [ ] 7.4 Update Dockerfile SKAWR_AUTH_REF + add SKAWR_AUTH_SECRET_KEY env var
    - Update git ref for skawr-auth clone in Dockerfile
    - Add SKAWR_AUTH_SECRET_KEY to docker-compose.yml and .env.example
    - _Requirements: 4.3_

  - [ ]* 7.5 Write tests: login → token contains enrollments, existing endpoints still work
    - Test login response includes product_enrollments in token
    - Test existing /auth/me, /projects, /analytics endpoints work unchanged
    - Test backward compat: old tokens (without enrollments) still accepted
    - _Requirements: 13.1, 13.2, 4.1_

- [ ] 8. PR 3: skawr-backend — Indexer Dual-Auth + Dashboard
  - [ ] 8.1 Add skawr-auth as dependency to indexer
    - Add skawr-auth to requirements.txt / pyproject.toml
    - Import models and utilities needed for dual-auth
    - _Requirements: 13.2_

  - [ ] 8.2 Implement dual-auth in get_current_client() using resource resolver
    - Replace existing get_current_client with `get_current_user_or_legacy_client()`
    - Handle unified tokens (new) → resolve user directly
    - Handle legacy indexer tokens (old) → resolve via client_id → connected_store → user
    - Keep both paths working simultaneously
    - _Requirements: 13.3, 13.4_

  - [ ] 8.3 Update token_service to issue unified tokens for NEW logins
    - New login/signup flows issue tokens with product_enrollments claim
    - Ensure search_saas enrollment exists for user before token creation
    - _Requirements: 4.1, 2.2_

  - [ ] 8.4 Keep legacy token acceptance for existing sessions
    - Existing refresh tokens continue to work
    - Legacy tokens are accepted and resolved through dual-auth path
    - _Requirements: 13.3, 13.4_

  - [ ] 8.5 Update dashboard-client auth context for unified token format
    - Parse product_enrollments from JWT in frontend auth context
    - Show user's role and enrolled products in dashboard UI
    - _Requirements: 6.2, 14.3_

  - [ ] 8.6 Add SKAWR_AUTH_SECRET_KEY env var to docker-compose and config
    - Add to docker-compose.yml, .env.example
    - Update config loading to use _get_secret_key() priority chain
    - _Requirements: 4.3_

  - [ ]* 8.7 Write tests: dual-auth (both token formats work), API key + resource binding
    - Test: unified token → resolves user + connected_stores
    - Test: legacy indexer token → resolves via client_id → user
    - Test: API key with resource_id → only bound resource accessible
    - Test: API key without resource_id → all user's resources accessible
    - _Requirements: 13.3, 13.4, 7.3_

- [ ] 9. Checkpoint - Ensure consumer adoption PRs pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. PR 4: Migration Scripts (skawr-auth repo)
  - [ ] 10.1 Create common migration utilities module
    - Idempotency helpers (UUID-based dedup check)
    - Conflict logging (email, source product, action taken)
    - Summary reporting (total processed, migrated, skipped, enrollments created)
    - DB connection management (source + target)
    - _Requirements: 10.4, 10.5, 10.7, 11.6_

  - [ ] 10.2 Implement migrate_analytics_users.py
    - Copy users preserving all columns (id, email, password_hash, name, company, email_verified, is_active, created_at, updated_at)
    - Create ProductEnrollment (product=analytics, role=admin) for each
    - Re-associate projects and API keys
    - Handle duplicate email conflicts (log + skip)
    - Output summary report
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ] 10.3 Implement migrate_saas_apiclients.py
    - Create unified user for each APIClient with non-null email
    - Create ProductEnrollment (product=search_saas, role=admin)
    - Create connected_store records (Salla/Shopify data migration)
    - Set connected_store.legacy_client_id = APIClient.id
    - Re-associate SearchIndex and APIKey rows to new user_id
    - Handle email conflicts (merge into existing user)
    - Skip guest APIClients (null email), log skipped IDs
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ] 10.4 Implement migrate_marketplace_supabase.py
    - Export Supabase users → create unified user records
    - Handle OAuth-only users (no password_hash)
    - Create ProductEnrollment (product=marketplace, role=member)
    - Handle email conflicts (add enrollment to existing user)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]* 10.5 Write tests for migration scripts (fixture datasets + idempotency)
    - **Property 22: Migration data preservation** — all source columns preserved in target
    - **Property 23: Migration idempotency** — running N times = same result as once
    - **Property 24: Migration conflict merge behavior** — duplicate email → merge, not duplicate
    - Test analytics migration against fixture dataset
    - Test SaaS migration with guest clients (skipped) and email conflicts (merged)
    - Test Supabase migration with OAuth-only users
    - Verify summary report output
    - **Validates: Requirements 10.1-10.7, 11.1-11.6, 12.1-12.4**

- [ ] 11. Checkpoint - Ensure migration scripts are correct
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. PR 5: skwar-web-mvp — Unified Auth Frontend
  - [ ] 12.1 Replace guest AuthProvider with @skawr/auth-frontend AuthProvider
    - Remove Supabase auth references
    - Configure AuthProvider with apiBaseUrl pointing to unified auth endpoints
    - _Requirements: 14.1_

  - [ ] 12.2 Configure apiBaseUrl for unified auth endpoints
    - Set base URL for auth API calls
    - Ensure token refresh and session management work with unified endpoints
    - _Requirements: 6.4, 6.7_

  - [ ] 12.3 Add marketplace enrollment flow (auto-enroll on first access)
    - On first authenticated access, check for marketplace enrollment
    - If missing, auto-create enrollment via API
    - _Requirements: 2.2, 14.4_

  - [ ]* 12.4 Write tests: login/signup flow works, marketplace routes accessible
    - Test login redirects to correct product page
    - Test signup creates user with marketplace enrollment
    - Test protected marketplace routes are accessible after enrollment
    - _Requirements: 14.1, 14.2, 2.2_

- [ ] 13. PR 6: Legacy Cleanup (Day 91) (skawr-auth repo)
  - [ ] 13.1 Remove detect_token_format legacy branches
    - Remove "legacy_indexer" and "legacy_analytics" handling from detect_token_format
    - Only "unified" format accepted; all others raise ValueError
    - _Requirements: 13.4_

  - [ ] 13.2 Remove SECRET_KEY and JWT_SECRET_KEY aliases from _get_secret_key
    - Only SKAWR_AUTH_SECRET_KEY is supported
    - Remove fallback chain
    - _Requirements: 4.3_

  - [ ] 13.3 Remove backward compat for tokens without product_enrollments
    - verify_token_for_product rejects tokens missing product_enrollments claim
    - Remove 90-day grace period logic
    - _Requirements: 13.4_

  - [ ] 13.4 Update documentation and MIGRATION_GUIDE.md
    - Document that legacy tokens are no longer accepted
    - Update PUBLISHING_GUIDE.md with new version notes
    - _Requirements: 13.4_

  - [ ]* 13.5 Write tests: verify legacy tokens are now rejected
    - Test legacy analytics tokens → rejected
    - Test legacy indexer tokens → rejected
    - Test unified tokens → still work correctly
    - _Requirements: 13.4_

- [ ] 14. Estimate infrastructure cost impact of unified auth
  - Produce a written cost estimate (in the repo, e.g. `docs/COST_IMPACT.md`) covering the added infrastructure footprint of this feature across all implemented and pending tasks. Use `Skawr/.kiro/steering/skawr-pricing-steering.md` as the guiding/steering doc.
  - **PostgreSQL storage growth**: estimate added rows/bytes for the new tables (`product_enrollments`, `connected_stores`, `subscription_tier_audit`, extended `user_sessions`, `api_keys` columns, dormant `organizations`/`organization_members`/`user_identity_providers`). Postgres remains the single data store per steering — quantify growth per 1K users and confirm it stays negligible vs event-table volume.
  - **Compute / latency**: estimate extra per-request DB work (enrollment lookup on token issuance, `verify_token_for_product` is DB-free, resource resolver queries for indexer, session cleanup on refresh). Note that JWT `product_enrollments` claim avoids a per-request enrollment query for most reads.
  - **Encryption overhead**: note the Fernet encrypt/decrypt cost for `connected_stores` OAuth tokens (negligible, in-process).
  - **One-time migration cost**: estimate runtime + DB load of the three migration scripts against production data volumes; confirm they run within the VPS's headroom and require no extra infra.
  - **Threshold checks**: confirm this feature does NOT move any OpenSearch scaling threshold (it adds no products/indices) and does NOT change the ~$25–30/mo VPS baseline. Product count is the cost driver per steering rule #1 — unified auth adds identity rows, not product rows, so cost impact should be near-zero.
  - **Third-party**: confirm no new metered third-party costs (no Fireworks embeddings, no email volume beyond existing). Flag the upcoming Polar.sh fees as out-of-scope (tracked in saas-payment-integration).
  - Output a summary line: estimated added monthly cost (expected: ~$0 incremental on current VPS) and the user-count at which any threshold would be crossed.
  - _Steering: Skawr/.kiro/steering/skawr-pricing-steering.md_

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each PR-level task is independently deployable and reviewable
- PR 1a → 1b → 1c must be sequential (schema before logic before frontend)
- PR 2 and PR 3 can proceed in parallel after PR 1b is merged
- PR 4 depends on PR 2 + PR 3 being deployed (migration needs real data targets)
- PR 5 can proceed after PR 1c (uses published frontend package)
- PR 6 is scheduled for Day 91 after initial deployment
- Property-based tests use Hypothesis (Python) and fast-check (TypeScript)
- Each migration script is idempotent — safe to re-run
- Checkpoints ensure incremental validation between PR boundaries

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8"] },
    { "id": 1, "tasks": ["1.9", "1.10", "1.11", "1.12", "1.13", "1.14", "1.15", "1.16"] },
    { "id": 2, "tasks": ["1.17"] },
    { "id": 3, "tasks": ["3.1", "3.10", "3.12"] },
    { "id": 4, "tasks": ["3.2", "3.4"] },
    { "id": 5, "tasks": ["3.3", "3.5", "3.6"] },
    { "id": 6, "tasks": ["3.7", "3.8", "3.9", "3.11"] },
    { "id": 7, "tasks": ["3.13", "3.14", "3.15", "3.16", "3.17"] },
    { "id": 8, "tasks": ["5.1"] },
    { "id": 9, "tasks": ["5.2"] },
    { "id": 10, "tasks": ["5.3", "5.4"] },
    { "id": 11, "tasks": ["5.5"] },
    { "id": 12, "tasks": ["7.1", "8.1"] },
    { "id": 13, "tasks": ["7.2", "7.3", "8.2", "8.3"] },
    { "id": 14, "tasks": ["7.4", "8.4", "8.5", "8.6"] },
    { "id": 15, "tasks": ["7.5", "8.7"] },
    { "id": 16, "tasks": ["10.1"] },
    { "id": 17, "tasks": ["10.2", "10.3", "10.4"] },
    { "id": 18, "tasks": ["10.5"] },
    { "id": 19, "tasks": ["12.1", "12.2"] },
    { "id": 20, "tasks": ["12.3"] },
    { "id": 21, "tasks": ["12.4"] },
    { "id": 22, "tasks": ["13.1", "13.2", "13.3"] },
    { "id": 23, "tasks": ["13.4"] },
    { "id": 24, "tasks": ["13.5"] },
    { "id": 25, "tasks": ["14"] }
  ]
}
```
