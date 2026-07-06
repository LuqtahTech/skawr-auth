# Requirements Document

## Introduction

Skawr Auth currently provides shared authentication CODE (models, routers, utilities) consumed independently by each product. Each product maintains its own `users` table, meaning a user who signs up for Analytics cannot use the same account for the SaaS Dashboard or Marketplace. This spec defines the requirements for expanding skawr-auth into a centralized identity system that provides shared IDENTITY across all Skawr products — Analytics, Search SaaS, Client Dashboard, Admin Dashboard, and Marketplace.

## Glossary

- **Auth_System**: The skawr-auth library and its database schema, responsible for identity management, authentication, and authorization across all Skawr products.
- **Product**: A distinct Skawr application (Analytics, Search SaaS, Client Dashboard, Admin Dashboard, Marketplace) that a user can access.
- **Product_Enrollment**: A record indicating that a user has access to a specific Product, along with their role within that Product.
- **Role**: A named permission level within a Product (e.g., admin, member, viewer).
- **Organization**: A grouping of users who share access to resources within a Product (future-ready concept).
- **JWT_Token**: A JSON Web Token containing standardized claims (sub, product_enrollments, roles) used for authentication across all products.
- **Session**: A refresh token record representing an active login, tied to a user and optionally scoped to a product context.
- **API_Key**: A programmatic access credential (prefix.suffix format) belonging to a user or organization, scoped to a specific Product.
- **Identity_Provider**: An external authentication source (Google, GitHub) that can be linked to a user account for social login.
- **Migration_Tool**: A utility that moves existing user records from product-specific tables into the unified users table without data loss.
- **SSO_Gateway**: The shared authentication flow that allows a user to log in once and access multiple Products without re-authenticating.

## Requirements

### Requirement 1: Shared User Identity

**User Story:** As a Skawr user, I want a single account across all Skawr products, so that I don't need to create separate accounts for Analytics, SaaS, and Marketplace.

#### Acceptance Criteria

1. THE Auth_System SHALL store all user identities in a single `users` table with a UUID primary key shared across all Products (Analytics, SaaS, and Marketplace).
2. WHEN a user registers through any Product, THE Auth_System SHALL create one user record that is queryable and authenticatable from all other Products using the same email and password credentials.
3. IF a user attempts to register with an email address that already exists in the `users` table, THEN THE Auth_System SHALL reject the registration and return an error indicating the email is already in use.
4. THE Auth_System SHALL enforce email uniqueness across all Products such that no two user records share the same email address.
5. THE Auth_System SHALL preserve the existing User model columns (id, email, password_hash, name, company, email_verified, is_active, created_at, updated_at) and extend them without removing existing fields.

### Requirement 2: Product Enrollment

**User Story:** As a Skawr user, I want to be enrolled in specific products, so that each product knows I have access and what role I hold.

#### Acceptance Criteria

1. THE Auth_System SHALL maintain a `product_enrollments` table linking a user to one or more Products with a designated Role per Product, enforcing a unique constraint on the combination of user_id and product such that a user cannot hold more than one enrollment record per Product.
2. WHEN a user presents a valid JWT_Token to a Product for which no Product_Enrollment record exists, THE Auth_System SHALL create a Product_Enrollment record with a default role of "member" before processing the request.
3. THE Auth_System SHALL support the following Products as enrollment targets: analytics, search_saas, client_dashboard, admin_dashboard, marketplace.
4. WHEN a user's `is_active` field is set to false, THE Auth_System SHALL mark all Product_Enrollment records for that user as revoked within the same database transaction, causing all subsequent token validation attempts for that user to fail with a 403 Forbidden response.
5. THE Auth_System SHALL allow a user to hold different Roles in different Products independently.
6. IF a user's `is_active` field is set back to true after deactivation, THEN THE Auth_System SHALL restore the user's previously revoked Product_Enrollment records to their prior roles and active state.

### Requirement 3: Product-Scoped Roles and Permissions

**User Story:** As a product administrator, I want to assign roles within my product, so that users have appropriate access levels without affecting their roles in other products.

#### Acceptance Criteria

1. THE Auth_System SHALL define three per-product roles — admin, member, and viewer — where admin grants full read-write and role-management access, member grants read-write access to product data without role-management, and viewer grants read-only access to product data.
2. WHEN a user with the admin role for a Product assigns a role to another user for that Product, THE Auth_System SHALL store the role in the Product_Enrollment record without modifying enrollments for other Products.
3. IF a user without the admin role for a Product attempts to assign or modify roles for that Product, THEN THE Auth_System SHALL reject the request with a forbidden error indicating insufficient permissions.
4. THE Auth_System SHALL expose a dependency function that resolves the current user's role for a given Product from the JWT_Token claims and returns one of admin, member, or viewer.
5. IF a user lacks a Product_Enrollment for the requested Product, THEN THE Auth_System SHALL return a 403 Forbidden response.

### Requirement 4: Standardized JWT Token Claims

**User Story:** As a backend service developer, I want consistent JWT claims across all products, so that I can validate identity and permissions using the same logic everywhere.

#### Acceptance Criteria

1. THE Auth_System SHALL include the following claims in every access JWT_Token: `sub` (user UUID), `email`, `product_enrollments` (a list where each entry contains a product identifier and the user's role for that product), `type` (set to "access" for access tokens, "refresh" for refresh tokens), and `iat`/`exp` timestamps.
2. WHEN a token is issued, THE Auth_System SHALL set the access token lifetime to 15 minutes and the refresh token lifetime to 30 days.
3. THE Auth_System SHALL sign all JWT_Tokens using HS256 with a single shared SECRET_KEY.
4. WHEN a consuming service validates a JWT_Token, THE Auth_System SHALL provide a utility function that accepts a token and a target product identifier, verifies the token signature and expiration, and returns the user's role for the specified product from the `product_enrollments` claim.
5. IF the utility function receives a token that is expired, has an invalid signature, or is missing required claims, THEN THE Auth_System SHALL return None to indicate validation failure.
6. IF the utility function receives a valid token but the user has no enrollment for the requested product, THEN THE Auth_System SHALL return None to indicate the user lacks access to that product.

### Requirement 5: Unified Session Management

**User Story:** As a Skawr user, I want to view and revoke my active sessions, so that I can maintain control over where I'm logged in.

#### Acceptance Criteria

1. THE Auth_System SHALL record each login as a Session entry containing user_id, a unique session_id (UUID), token_hash, device/user-agent string (maximum 512 characters), IP address (IPv4 or IPv6), the Product from which login originated, created_at timestamp, and expiration timestamp.
2. WHEN a user requests their active sessions, THE Auth_System SHALL return all non-expired Session records for that user across all Products, each including session_id, device/user-agent string, IP address, Product, created_at timestamp, and expiration timestamp, but excluding the token_hash.
3. WHEN a user revokes a specific Session by session_id, THE Auth_System SHALL invalidate that Session's refresh token within the same request-response cycle such that any subsequent use of that refresh token is rejected.
4. IF a user attempts to revoke a Session that does not exist or does not belong to them, THEN THE Auth_System SHALL return a 404 Not Found response without revealing whether the session exists for another user.
5. WHEN a user performs a "logout everywhere" action, THE Auth_System SHALL invalidate all active Sessions for that user across all Products, including the current Session from which the action was initiated.
6. WHEN a token refresh operation occurs, THE Auth_System SHALL remove all expired Session records belonging to the refreshing user.

### Requirement 6: Single Sign-On Across Products

**User Story:** As a Skawr user, I want to log in once and access all my enrolled products without re-authenticating, so that switching between Analytics and the SaaS Dashboard is seamless.

#### Acceptance Criteria

1. WHEN a user authenticates through any Product, THE Auth_System SHALL issue a JWT_Token containing the list of Product identifiers the user is enrolled in, with an access token expiry of 15 minutes and a refresh token expiry of 30 days.
2. WHEN a user navigates from one Product to another Product they are enrolled in, THE Auth_System SHALL validate the existing JWT_Token and grant access without requiring re-authentication.
3. IF a user navigates to a Product they are not enrolled in, THEN THE Auth_System SHALL deny access and return an error response indicating insufficient product enrollment, without invalidating the existing session.
4. THE Auth_System SHALL provide a shared login endpoint that accepts an optional product parameter, and upon successful authentication SHALL redirect the user to the specified Product's entry page, or to a default product selection view if no product parameter is provided.
5. WHEN a user logs out from one Product, THE Auth_System SHALL revoke only the session associated with that Product, preserving active sessions in other Products.
6. IF a user selects a "logout from all products" option during logout, THEN THE Auth_System SHALL revoke all active sessions associated with that user across all Products.
7. IF the access token expires while a user is navigating between Products, THEN THE Auth_System SHALL attempt a silent token refresh using the refresh token and, if successful, complete the navigation without requiring re-authentication.

### Requirement 7: API Key Unification

**User Story:** As a developer integrating with Skawr, I want all my API keys to be tied to my unified account and scoped to specific products, so that I can manage programmatic access centrally.

#### Acceptance Criteria

1. THE Auth_System SHALL associate every API_Key with a user_id (owner) and a product scope (one of the Product identifiers defined in Product_Enrollment), and SHALL enforce a maximum of 10 API_Keys per user per Product.
2. THE Auth_System SHALL retain the existing prefix.suffix key format (8-character prefix for display, SHA-256 hashed suffix for storage) and the base permission set of track and query.
3. WHEN an API_Key is used for authentication, THE Auth_System SHALL verify that the key's product scope matches the Product identifier of the service handling the request, and SHALL reject the request if they do not match.
4. THE Auth_System SHALL store permissions on each API_Key as a list of string identifiers, supporting both the base permissions (track, query) and product-specific permissions defined per Product, and SHALL reject at creation time any permission string not recognized by the target Product's permission set.
5. IF an API_Key is used against a Product it is not scoped to, THEN THE Auth_System SHALL deny access with an error indicating the key is not authorized for the requested Product.
6. IF an API_Key is valid and product-scoped correctly but lacks a permission required by the endpoint being accessed, THEN THE Auth_System SHALL deny access with an error indicating insufficient permissions.

### Requirement 8: Organization and Team Support (Future-Ready)

**User Story:** As a SaaS client with a team, I want multiple users to manage the same search indices and analytics projects, so that my team can collaborate under one account.

#### Acceptance Criteria

1. THE Auth_System SHALL define an `organizations` table with id (UUID), name, and owner_user_id.
2. THE Auth_System SHALL define an `organization_members` table linking users to organizations with a role (owner, admin, member).
3. WHEN an Organization exists, THE Auth_System SHALL allow API_Keys and Product_Enrollments to be scoped to the Organization rather than an individual user.
4. THE Auth_System SHALL allow the Organization feature to remain dormant (no organizations created) without affecting single-user functionality.

### Requirement 9: OAuth2 and Social Login (Future-Ready)

**User Story:** As a Skawr user, I want to log in with Google or GitHub, so that I can avoid managing another password.

#### Acceptance Criteria

1. THE Auth_System SHALL define a `user_identity_providers` table linking a user to one or more Identity_Providers with provider name, provider user ID, and linked_at timestamp.
2. WHEN a user authenticates via an Identity_Provider, THE Auth_System SHALL match the provider email to an existing user record or create a new user if no match exists.
3. THE Auth_System SHALL allow a user to have both a password and linked Identity_Providers simultaneously.
4. THE Auth_System SHALL allow the OAuth2 feature to remain dormant (no providers configured) without affecting email/password authentication.

### Requirement 10: Migration of Existing Analytics Users

**User Story:** As an existing Analytics user, I want my account to continue working after the unified auth migration, so that I experience no disruption.

#### Acceptance Criteria

1. WHEN the Migration_Tool runs, THE Auth_System SHALL copy all existing records from the analytics `users` table into the unified `users` table preserving all columns: id (UUID), email, password_hash, name, company, email_verified, is_active, created_at, and updated_at.
2. WHEN the Migration_Tool runs, THE Auth_System SHALL create a Product_Enrollment record (product=analytics, role=admin) for each migrated user.
3. WHEN the Migration_Tool runs, THE Auth_System SHALL re-associate existing projects and API_Keys with the migrated user's UUID in the unified table by verifying that the `user_id` foreign key in the `projects` table references a valid record in the unified `users` table.
4. THE Migration_Tool SHALL be idempotent such that running it multiple times produces the same result without duplicating records, using the user's UUID as the deduplication key.
5. IF a migration conflict occurs (duplicate email across products), THEN THE Migration_Tool SHALL log the conflict to standard output including the conflicting email and source product, and skip the duplicate record without halting execution.
6. IF the source analytics database is unreachable or the source `users` table is empty, THEN THE Migration_Tool SHALL exit with a non-zero status code and an error message indicating the failure reason without modifying the unified table.
7. WHEN the Migration_Tool completes successfully, THE Auth_System SHALL output a summary report to standard output containing the total records processed, total records migrated, total records skipped due to conflicts, and total Product_Enrollment records created.
8. WHEN the Migration_Tool runs, THE Auth_System SHALL invalidate all existing analytics user_sessions, requiring migrated users to re-authenticate using the unified login endpoint.

### Requirement 11: Migration of SaaS APIClients

**User Story:** As an existing SaaS client, I want my APIClient account to become a unified user, so that I can access the Client Dashboard with the same credentials.

#### Acceptance Criteria

1. WHEN the Migration_Tool runs, THE Auth_System SHALL create a unified user record for each existing APIClient that has a non-null email, copying the APIClient's email and hashed_password into the unified user record while preserving the APIClient's UUID as the new user's UUID.
2. WHEN the Migration_Tool runs, THE Auth_System SHALL create a Product_Enrollment record (product=search_saas, role=admin) for each migrated APIClient.
3. WHEN the Migration_Tool runs, THE Auth_System SHALL update the owner reference on all existing API_Keys and SearchIndex records belonging to the migrated APIClient to point to the newly created unified user record.
4. IF an APIClient email already exists in the unified users table, THEN THE Migration_Tool SHALL add a search_saas Product_Enrollment to the existing user and re-associate the APIClient's API_Keys and search indices with that existing user without creating a duplicate user record.
5. IF an APIClient has a null email (guest or unclaimed account), THEN THE Migration_Tool SHALL skip that record and log the skipped APIClient ID without halting execution.
6. THE Migration_Tool SHALL be idempotent such that running it multiple times produces the same result without duplicating user records, Product_Enrollments, or re-association operations.

### Requirement 12: Migration of Marketplace Users from Supabase

**User Story:** As a Marketplace user, I want my Supabase account migrated to unified auth, so that I can use one login across the Marketplace and other Skawr products.

#### Acceptance Criteria

1. WHEN the Migration_Tool runs for Supabase users, THE Auth_System SHALL export user records from Supabase and create corresponding unified user records with the same email.
2. WHEN a Supabase user has no password (OAuth-only), THE Auth_System SHALL create the user record without a password_hash and mark the account as requiring password setup or Identity_Provider linkage.
3. WHEN the Migration_Tool runs, THE Auth_System SHALL create a Product_Enrollment record (product=marketplace, role=member) for each migrated Supabase user.
4. IF a Supabase user's email matches an existing unified user, THEN THE Migration_Tool SHALL add a marketplace Product_Enrollment to the existing user without creating a duplicate.

### Requirement 13: Backward Compatibility

**User Story:** As a developer maintaining existing integrations, I want the current auth endpoints and SDK contracts to continue working, so that nothing breaks during the transition.

#### Acceptance Criteria

1. THE Auth_System SHALL continue to expose the existing `/auth/signup`, `/auth/login`, `/auth/refresh`, and `/auth/me` endpoints with the same request/response field names, field types, and HTTP status codes as the pre-migration implementation.
2. THE Auth_System SHALL maintain the factory-pattern API (`create_user_models`, `create_project_models`, `create_auth_router`, `create_projects_router`, `create_auth_dependencies`) with the same function signatures and return types so that existing consuming services can upgrade the library version without modifying their calling code.
3. WHEN an existing JWT_Token (without `product_enrollments` claim) is presented, THE Auth_System SHALL treat the user as enrolled in all products with a member role for backward compatibility.
4. IF a JWT_Token without `product_enrollments` claim is presented and the token signature and expiration are valid, THEN THE Auth_System SHALL accept the token without requiring re-authentication for a deprecation period of no less than 90 days after the unified auth deployment.
5. THE Auth_System SHALL maintain the existing rate limits on auth endpoints (signup: 5 requests per minute per IP, login: 10 requests per minute per IP, refresh: 60 requests per minute per user).
6. THE Auth_System SHALL continue to export the `@skawr/auth-frontend` package public API (`AuthProvider`, `useAuth`, `AuthClient`) with the same component props, hook return shape, and method signatures as the pre-migration version.
7. WHEN a new JWT_Token (containing `product_enrollments` claim) is consumed by an older service that does not parse `product_enrollments`, THE Auth_System SHALL ensure that existing claim fields (`sub`, `email`, `iat`, `exp`) remain in their original positions and formats so that the token is not rejected.

### Requirement 14: Frontend SSO Experience

**User Story:** As a Skawr user, I want a shared login page and product switcher, so that I can move between products without confusion.

#### Acceptance Criteria

1. THE Auth_System SHALL provide a shared login/signup page component that can be embedded by any Product frontend.
2. WHEN authentication succeeds, THE Auth_System SHALL redirect the user to the originating Product's URL or a default product dashboard.
3. THE Auth_System SHALL provide a product switcher UI component that displays all Products the user is enrolled in and allows navigation between them.
4. WHEN a user is not enrolled in a Product they attempt to access, THE Auth_System SHALL display an enrollment prompt rather than an error page.

### Requirement 15: Polar.sh Payment Integration Readiness

**User Story:** As the Skawr platform, I want user identity to be stable and unique, so that subscription billing through Polar.sh can be reliably tied to a single user account.

#### Acceptance Criteria

1. THE Auth_System SHALL guarantee that each user has exactly one UUID primary key that is immutable once assigned, persists across all Products, and is preserved unchanged by the Migration_Tool when migrating users from product-specific tables.
2. THE Auth_System SHALL include the user UUID in the `sub` claim of every JWT_Token and in the `id` field of user profile API responses, such that external payment systems can reference this identifier without additional lookups.
3. THE Auth_System SHALL include an optional `subscription_tier` field on the user record with allowed values: `trial`, `starter`, `growth`, `scale`, or `enterprise`, defaulting to `null` for users with no active subscription.
4. IF an external system attempts to update the `subscription_tier` field, THEN THE Auth_System SHALL accept the update only via a dedicated internal endpoint authenticated with a service-level API_Key, not via user-facing JWT_Token authentication.
5. WHEN the `subscription_tier` field is updated, THE Auth_System SHALL record the previous value, new value, and timestamp in an auditable log without implementing billing calculation or payment processing logic.
